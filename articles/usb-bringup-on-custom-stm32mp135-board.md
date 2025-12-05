---
title: USB Bring-Up on a Custom STM32MP135 Board
author: Jakob Kastelic
date: 4 Dec 2025
topic: Embedded
description: >
   Step-by-step guide to getting bare-metal USB working on a custom STM32MP135
   board, including hardware fixes, HAL configuration, and debugging USB
   enumeration issues.
---

![](../images/zen.jpg)

Getting USB up and running in bare-metal mode using the ST HAL drivers on my
(custom STM32MP135)[https://github.com/js216/stm32mp135_test_board] board took a
couple attempts. After a few false starts with the example projects, I was able
to make the board enumerate correctly, handle data transfers, and even read and
write files reliably. In this article, I'll walk through the hardware tweaks,
HAL configuration, and debugging steps that helped me turn a stubborn USB
interface into a fully working USB Mass Storage device.

### Initial attempts

I gave up trying to make the provided `CDC_Standalone` example from
[`STM32Cube_FW_MP13_V1.2.0`](https://wiki.st.com/stm32mpu/wiki/STM32CubeMP13_Package_-_Getting_started)
to work on the eval board, let alone the custom board. Instead, let's get USB to
work step by step.

First, the `VDD3V3_USBHS` must not be powered on when `VDDA1V8_REG` is not
present. For that, we have the switch U201 (NCP380), but the board unfortunately
uses the adjustable-current version of the switch w/o the adjustment resistor
present, so the USBHS circuitry is disabled. So we first have to solder a
resistor (I had 39k + 10k at hand) to enable power to the USB circuit.

With that fix, if I reset the device with `BOOT=000` (so PA13 LED blinks), then
plug the USB cable, then the LED stops blinking and the device manager shows
`DFU in FS Mode @Device ID /0x501, @Revision ID /0x1003` as it should---so the
hardware works, we just need to fix the code. (Without the added resistor,
Windows was not able to enumerate the device and the Device Manager shows it as
`Unknown USB Device (Device Descriptor Request Failed)`.)

In the `main()` function, I blink LED and print ":" on UART4 every second after
starting the USB using `MX_USB_OTG_HS_PCD_Init()` and `HAL_PCD_Start();`
functions. If I load the code with the USB cable plugged in, the ":" signs get
printed every second as they should, and also the LED blinks. If I unplug the
USB cable, then the printing and blinking stops---the code appears locked up.
The code also locks up if I select "Disable device" in Windows Device Manager.
If I load the code with USB cable not plugged in, only the first ":" gets
printed and then the code locks up.

### VBUS sense?

Before the main loop we also see that `OTG_GCCFG: 0x00000000`, which means that
both of the following are disabled:

- IDEN: USB ID detection enable
- VBDEN: USB VBUS detection enable

Note that the hardware has a permanent 1.5K pullup (up to +3.3V) on D+, so the
USB driver does not need VBUS sensing. (The board is externally powered, so
removing the cable would not unpower the core or the USB PHY.) We explicitly
disable sensing VBUS in `MX_USB_OTG_HS_PCD_Init()`, where we create the
structure passed to `HAL_PCD_Init()` with the following line:

```c
hpcd_USB_OTG_HS.Init.vbus_sensing_enable = DISABLE;
```

With that request, the driver function `USB_DevInit()` clears the enable for
VBUS sensing in the `GCCFG` register:

```c
if (cfg.vbus_sensing_enable == 0U)
{
USBx_DEVICE->DCTL |= USB_OTG_DCTL_SDIS;

/* Deactivate VBUS Sensing B */
USBx->GCCFG &= ~USB_OTG_GCCFG_VBDEN;

/* B-peripheral session valid override enable */
USBx->GOTGCTL |= USB_OTG_GOTGCTL_BVALOEN;
USBx->GOTGCTL |= USB_OTG_GOTGCTL_BVALOVAL;
}
```

### Interrupt storm?

I checked that the USB interrupt service routine (`HAL_PCD_IRQHandler()`) is
linked by locating it in the map file (and not in the "Discarded input
sections"!). Just before the main loop, we print `OTG_GAHBCFG: 0x00000001`,
showing that OTG USB interrupts are unmasked, and `OTG_GINTMSK: 0x803C3810`,
which means the following interrupts are enabled:

- Bit 4: RXFLVLM: Receive FIFO non-empty mask
- Bit 11: USBSUSPM: USB suspend mask
- Bit 12: USBRST: USB reset mask
- Bit 13: ENUMDNEM: Enumeration done mask
- Bit 18: IEPINT: IN endpoints interrupt mask
- Bit 19: OEPINT: OUT endpoints interrupt mask
- Bit 20: IISOIXFRM: Incomplete isochronous IN transfer mask
- Bit 21: IISOOXFRM: Incomplete isochronous OUT transfer mask
- Bit 31: WUIM: Resume/remote wake-up detected interrupt mask

If we `IRQ_Disable(OTG_IRQn)` before the main loop, than "Disable device" and
"Enable device" do not cause the core lockup. So, we just need to find out which
of the OTG USB interrupts exactly are not correctly handled, one by one.

If we enable just `USBSUSPM`, the locked happens. If we allow all the interrupts
that HAL enables, and then disable `USBSUSPM`, the lockup does *not* happen.

If we enable `USBRST` only, lockup does not happen. If we in addition add
`ENUMDNEM`, still no lockup. Add `IEPINT`, no lockup. Add `OEPINT`, no lockup.
Add `IISOIXFRM`, `PXFRM_IISOOXFRM`, and `WUIM`: no lockup.

If `USBRST` is the only enabled OTG interrupt, then the code locks up if the
cable is not plugged in when it starts executing, but it does not lock up if the
cable is present when it starts executing and is then unplugged.

If `USBSUSPM` is the only enabled OTG interrupt, then the code locks up both if
the cable is not present initially, or if it is unplugged later.

### JTAG again

Meanwhile I figured out how to get the JTAG to work mostly reliably. First,
remember to boot with `BOOT=100`, the "Engineering debug mode", otherwise the
JTAG is disabled. Then, the procedure is

1. Turn the 1.35V supply off and on again.
2. Press the reset button on the PCB.
3. Open `JLinkGDBServer.exe`
4. Call `arm-none-eabi-gdb -q -x load.gdb`

The `load.gdb` file is as follows:

    set confirm off
    set pagination off
    file build/main.elf
    target remote localhost:2330
    monitor reset
    monitor flash device=STM32MP135F
    load build/main.elf
    monitor go
    break main
    step

Loaded with the debugger, the program runs as before, and once USB "Disable
device" is clicked from the Windows Device Manager, the following appears on the
debugger after pressing Ctrl-C:

    Program received signal SIGTRAP, Trace/breakpoint trap.
    0x2ffe0104 in Vectors () at drivers/startup_stm32mp135fxx_ca7.c:444
    444       __asm__ volatile(
    (gdb) bt
    #0  0x2ffe0104 in Vectors () at drivers/startup_stm32mp135fxx_ca7.c:444
    Backtrace stopped: previous frame identical to this frame (corrupt stack?)
    (gdb)

Searching the forums, I found a
(post)[https://community.st.com/t5/stm32-mpus-embedded-software-and/stm32mp1-interrupt-causes-undefined-exception-in-arm-mode-but/td-p/745347]
where user bsvi discovered that `startup_stm32mp135fxx_ca7.c` take interrupts to
thumb mode in the `Reset_Handler()`:

    /* Set TE bit to take exceptions in Thumb mode */
    "ORR R0, R0, #(0x1 << 30) \n"

If the vector table is aligned and encoded as ARM mode, the of course it cannot
work. Adding `-mthumb` and the interrupt immediately fired as was able to
confirm via a flashing LED at the top of the `HAL_PCD_IRQHandler()`. Stopping
the debugger there (Ctrl-C) confirmed that the code was executing there.

Better yet, we can remove the `-mthumb` and simply take interrupts to ARM mode:

    /* TE = 0, exceptions enter ARM mode */
    "BIC R0, R0, #(1 << 30) \n"

I changed the debug code at the top of `HAL_PCD_IRQHandler()` to just a print
statement, and it prints any time the USB cable is plugged in and out. Great!

### USB Device Stack

Now that USB interrupts are no longer freezing the whole system, we can begin
work on integrating the ST USB Device "middleware". The initialization proceeds
as the following approximate sequence of function calls:

    MX_USB_Device_Init (usb_device.c)
       USBD_Init (usbd_core.c)
          USBD_LL_Init (usb_conf.c)
             HAL_PCD_Init (usbd_conf.c)
             HAL_PCDEx_SetRxFiFo (stm32mp13xx_hal_pcd_ex.c)
             HAL_PCDEx_SetTxFiFo (stm32mp13xx_hal_pcd_ex.c)
       USBD_RegisterClass (usbd_core.c)
       USBD_CDC_RegisterInterface (usbd_cdc.c)
       USBD_Start (usbd_core.c)
          USBD_LL_Start (usbd_conf.c)
             HAL_PCD_Start (stm32mp13xx_hal_pcd.c)
                USB_DevConnect (stm32mp13xx_ll_usb.c)
             USBD_Get_USB_Status (usbd_conf.c)

The example above is for a CDC-class application, but here we're interested in a
mass-storage class device (MSC). The USB files divide into four types:

- HAL drivers: `stm32mp13xx_ll_usb.c`, `stm32mp13xx_hal_pcd.c`,
  `stm32mp13xx_hal_pcd_ex.c`
- USB device core: `usbd_core.c`, `usbd_ctlreq.h`, `usbd_ioreq.c`
- USB class: `usbd_msc.c`, `usbd_msc_bot.c`, `usbd_msc_data.c`,
  `usbd_msc_scsi.c`
- app-specific: `usb_device.c`, `usbd_conf.c`, `usbd_desc.c`, `usbd_msc_storage.c`

An example of how the ST drivers are used for MSC class is provided in
[this](https://github.com/4ms/stm32mp1-baremetal/tree/master/examples/usb_msc_device)
repository.

For testing, we call the following from the main function:

    USBD_Init(&USBD_Device, &MSC_Desc, 0);
    USBD_RegisterClass(&USBD_Device, USBD_MSC_CLASS);
    USBD_MSC_RegisterStorage(&USBD_Device, &USBD_MSC_fops);
    USBD_Start(&USBD_Device);

The functions complete, and then the main loop is active, blinking LED and
printing to UART. The debug print in `HAL_PCD_IRQHandler` shows that the IRQ is
called a couple times, but after a few seconds, the Windows Device Manager shows
`Unknown USB Device (Device Descriptor Request Failed)`.

As it turns out, I have forgotten to add the callbacks into `usbd_conf.c`. Once
that was done, the USB access from the Windows computer caused an immediate Data
Abort on the STM32MP135.

### Aligned SYSRAM memory access

The aborts happen in `usbd_msc_scsi.c` in lines such as the following:

```c
hmsc->scsi_blk_addr =
    ((uint32_t)params[2] << 24) |
    ((uint32_t)params[3] << 16) |
    ((uint32_t)params[4] << 8) |
    (uint32_t)params[5];

hmsc->scsi_blk_len =
    ((uint32_t)params[7] << 8) |
    (uint32_t)params[8];
```

As it happens, with some optimizations (I'm using `-Os` to make the whole
program fit in SYSRAM!) the compiler optimizes the byte access into a misaligned
32-bit access. Forcing a `volatile` cast fixes the problem, as follows:

```c
hmsc->scsi_blk_addr =
    (((uint32_t)((volatile uint8_t*)params)[2]) << 24) |
    (((uint32_t)((volatile uint8_t*)params)[3]) << 16) |
    (((uint32_t)((volatile uint8_t*)params)[4]) <<  8) |
    ((uint32_t)((volatile uint8_t*)params)[5]);

hmsc->scsi_blk_len =
    (((uint32_t)((volatile uint8_t*)params)[7]) <<  8) |
    ((uint32_t)((volatile uint8_t*)params)[8]);
```

Make sure to repeat this several times! Search for `scsi_blk_addr` in
`usbd_msc_scsi.c` until you've cast all of them correctly.

Then, at last, the USB device enumerates as MSC correctly, and we can even read
and write raw data! However, Windows is not able to format the device.

### Aligned DDR RAM memory access

Now that data can be read and written to, we observe an odd pattern:

    WRITE: eb 3c 90 6d 6b 66 73 2e 66 61
    READ:  eb 00 90 3c 6b 6d 73 66 66 2e

Every other byte is a bit wrong, or reshuffled. Sounds familiar? Yes, it happens
if DDR writes are not aligned to word boundaries, as we experienced before with
the SD card, copying it's data to DDR. (Somehow reads are not affected by this?
ChatGPT says that AXI supports unaligned / byte reads natively, but not writes.)

With the write fixed (i.e., done in correctly aligned units of 4 bytes), the
device format works, and we can even copy files to the mass storage device, and
read them back. The problems is now ... read and write speeds are about 700
kB/s.

### D+ pullup

As it happens, the USB interface on the custom board has a external, physical
1.5K pullup on the D+ line which signals a Full-Speed device. To switch to
High-Speed mode, the device needs to be able to have the pullup present
initially, but then switch it off. Indeed, Device Manager shows that the device
enumerated as a Full-Speed device, hence the low data rates.

Removing the resistor, the device does not enumerate, or appear at all in the
Device Manager. However, we can simply set

    hpcd_USB_OTG_HS.Init.speed = PCD_SPEED_FULL;

in `USBD_LL_Init()` function (`usbd_conf.c`), and then everything works as
before. So something must be wrong with the high-speed mode configuration.

### Cables, hubs, ports

Since removing the 1.5K pullup which was keeping the device in Full-Speed (FS)
mode, the device does not enumerate, neither in DFU mode (with `BOOT` pins set
to `000`), nor using my test firmware (unless I request FS mode directly).

Inserting print statements or debug breakpoints in USB interrupt handler we see
that the USB reset is detected, the device is correctly switched to HS mode
(`speed=0`), the Rx/Tx FIFOs are large enough, the `RXFLVL` interrupt is enabled
but it never arrives. The enumeration completes, but the device does not see any
setup or data packets enter the FIFO, and then the device gets suspended,
presumably because it did not reply to the host's communications. The device
never appears in the Device Manager, or even in (USB Device Tree
Viewer)[https://www.uwe-sieber.de/usbtreeview_e.html].

With `BOOT=000`, pressing reset causes the PA13 LED to blink, and when the USB
cable is attached, the blinking stops. But looking at the device and USB trees,
nothing happens. Even the `STM32_Programmer_CLI -l usb` does not see anything:

          -------------------------------------------------------------------
                           STM32CubeProgrammer v2.18.0
          -------------------------------------------------------------------
    
    =====  DFU Interface   =====
    
    No STM32 device in DFU mode connecte

Now a different USB cable was found, connected to a different hub/port. Again
`BOOT=000`, press reset, PA13 LED blinks, and the new cable is connected, and
the blinking stops. Immediately the Device Manager and the USB Device Tree
Viewer report `DFU in FS Mode @Device ID /0x501, @Revision ID /0x1003`, so the
device enumerated. (About the "FS": I think that's just a cached name, since the
USB Tree also says that "Device Connection Speed  : High-Speed".) And CubeProg:

          -------------------------------------------------------------------
                           STM32CubeProgrammer v2.18.0
          -------------------------------------------------------------------
    
    =====  DFU Interface   =====
    
    Total number of available STM32 device in DFU mode: 1
    
      Device Index           : USB1
      USB Bus Number         : 001
      USB Address Number     : 005
      Product ID             : DFU in HS Mode @Device ID /0x501, @Revision ID /0x1003
      Serial number          : 001E00263133511332303636
      Firmware version       : 0x0110
      Device ID              : 0x0501

Clearly, the bad cable or hub or port was stopping the HS enumeration, at least
in DFU mode. Now let's switch to `BOOT=100`, reset, and load our firmware via
JTAG. And ... it enumerates immediately! Windows offers to format it as FAT32,
and the file write speed is up to about 4 MB/s, and read about 2 MB/s. Great
success! But could have checked the cable first.

### Speed

Regarding the low-ish data rates: it's probably limited by a combination of the
slow implementations of the `usbd_msc_storage.c` backend, and the HAL driver or
other things. For firmware flashing the speed is good enough. More importantly,
it proves that everything is now wired correctly. Nonetheless, let's see if we
can make it go faster than the 2--4 MB/s.

Changing the compiler optimization level from `-Os` to `-O3` brings the write
speed up to 7.6 MB/s. Windows has a built-in disk performance checker which
shows:

    C:\Users\Jkastelic> winsat disk -drive e
    > Disk  Random 16.0 Read                       2.87 MB/s          4.5
    > Disk  Sequential 64.0 Read                   2.91 MB/s          2.2
    > Disk  Sequential 64.0 Write                  7.67 MB/s          2.6
    > Average Read Time with Sequential Writes     8.566 ms          4.9
    > Latency: 95th Percentile                     21.499 ms          4.5
    > Latency: Maximum                             22.485 ms          7.9
    > Average Read Time with Random Writes         9.149 ms          4.7

    winsat disk -write -ran -drive e
    > Disk  Random 16.0 Write                      7.46 MB/s

Next, re-write the `STORAGE_Read` function to use 32-bit writes instead of
forcing 8-bit accesses (as we did previously while debugging the data
corruption). This improves the reads significantly:

    > Disk  Random 16.0 Read                       9.02 MB/s          5.3
    > Disk  Sequential 64.0 Read                   9.39 MB/s          2.8
    > Disk  Sequential 64.0 Write                  7.71 MB/s          2.6
    > Average Read Time with Sequential Writes     3.134 ms          6.6
    > Latency: 95th Percentile                     8.109 ms          5.9
    > Latency: Maximum                             9.516 ms          8.0
    > Average Read Time with Random Writes         3.138 ms          6.5

Now consider the FIFO allocation. The USB OTG core in the STM32MP135 has 4 kB
of total FIFO. If we used all of it just for sending data back to the host, at
the 480 MBit/s (70 MB/s) data rate, the microcontroller would fire interrupts
or DMA requests every 67 μs. (USB devices designed for mass data transfer
probably have larger buffers.) Currently we have

```c
HAL_PCDEx_SetRxFiFo(&hpcd, 0x200);
HAL_PCDEx_SetTxFiFo(&hpcd, 0, 0x40);
HAL_PCDEx_SetTxFiFo(&hpcd, 1, 0x100);
```

Let us significantly increase the buffer that sends data to the host:

```c
HAL_PCDEx_SetRxFiFo(&hpcd, 0x100);
HAL_PCDEx_SetTxFiFo(&hpcd, 0, 0x20);
HAL_PCDEx_SetTxFiFo(&hpcd, 1, 0x2e0);
```

Unfortunately, the read/write performance is essentially unchanged:

> Disk  Random 16.0 Read                       9.89 MB/s          5.4
> Disk  Sequential 64.0 Read                   10.28 MB/s          2.9
> Disk  Sequential 64.0 Write                  7.59 MB/s          2.6
> Average Read Time with Sequential Writes     3.311 ms          6.5
> Latency: 95th Percentile                     8.236 ms          5.9
> Latency: Maximum                             9.306 ms          8.1
> Average Read Time with Random Writes         3.279 ms          6.5

All of that was without DMA. It might be that DMA would make it faster, or at
least unburden the CPU---but in this example, the CPU is not doing anything
except copying the data. (CPU can actually be *faster* in copying; the point of
DMA is to allow the CPU to do other, more interesting things while the copy is
taking place.)

### Code availability

You can find the final version of the USB test in
[this](https://github.com/js216/stm32mp135_test_board/tree/main/baremetal/usb_test)
repository.

It compiles to about 117 kB with `-Os` optimization, so it fits in
SYSRAM directly. If you need more speed, `-O3` makes it compile to about 136 kB.
That's still acceptable if we combine all of the on-chip memory into a single
block, as shown in this excerpt from the [linker
script](https://github.com/js216/stm32mp135_test_board/blob/main/baremetal/usb_test/stm32mp13xx_a7_sysram.ld):

    MEMORY {
          SYSRAM_BASE (rwx)   : ORIGIN = 0x2FFE0000, LENGTH = 128K
          SRAM1_BASE (rwx)    : ORIGIN = 0x30000000, LENGTH = 16K
          SRAM2_BASE (rwx)    : ORIGIN = 0x30004000, LENGTH = 8K
          SRAM3_BASE (rwx)    : ORIGIN = 0x30006000, LENGTH = 8K
          /* InternalMEM = SYSRAM + SRAM1 + SRAM2 + SRAM3 */
          InternalMEM (rwx)   : ORIGIN = 0x2FFE0000, LENGTH = 160K
          DDR_BASE (rwx)      : ORIGIN = 0xC0000000, LENGTH = 512M
    }


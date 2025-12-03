---
title: Linux Bring-Up on a Custom STM32MP135 Board
author: Jakob Kastelic
date:
topic: Linux
description: >
---

![](../images/zen.jpg)

This is a record of steps I took to successfully boot Linux on my custom board
using the STM32MP135 SoC. (Schematics, PCB design files, and code available in
this [repository](https://github.com/js216/stm32mp135_test_board).) The write-up
is in approximate chronological order, written as I go through the debugging
steps.

### Blink

I had previously put together a simple bare-metal
[program](https://github.com/js216/mp135_boot/tree/main/blink_noide) that runs
on the STM32MP135 evaluation board and just blinks the LED. To work on the
custom board, I needed only to remove anything to do with the STPMIC1 and LSE
clock (the low-speed external 32.768 kHz clock), since I did not place these
parts on my board. The [resulting
code](https://github.com/js216/stm32mp135_test_board/tree/main/baremetal/blink)
is pretty simple modulo complexity inherited from the ST drivers.

To download the code, I talked directly to the ROM bootloader on the SoC. See
[this article](boot-stm32mp135-over-uart-with-python) for details.

### DDR

Again, I had previously put together a [simple
program](https://github.com/js216/mp135_boot/tree/main/ddr_test) to test the DDR
on the evaluation board. It fills the memory entirely with pseudorandom bits
(PRBS-31), and then reads it out, checking that the data matches.

For the custom board, the program had to be modified similarly as with blink
(remove STPMIC1, LSE clock) and then it ran. [(Click for
code.)](https://github.com/js216/stm32mp135_test_board/tree/main/baremetal/ddr_test)

There was an issue: all data read back was wrong and subtly corrupted. I double
checked the wiring, DDR parameter configuration (I use the same DDR as the eval
board, so what could it be!?), the code---only to realize the board was not
getting enough current on the 1.35V power supply. With more power, everything
*just worked*!

### JTAG

For JTAG loading it appears to be essential to select "Development boot" (also
called "Engineering boot") by selecting the boot pins in the `100` setting. The
datasheet says this mode is used "Used to get debug access without boot from
flash memory".

There is also a footnote that says that the core is "in infinite loop toggling
PA13", but I did not observe the toggling in the "dev boot" mode, even though it
is of course present (but not documented) in the normal UART boot mode (pins =
`000`).

![](../images/jtag.jpg)

Unfortunately I covered the J-Link connector with solder mask. After trying to
carefully scratch it off using a sewing needle, the connection appears to be
intermittent. Sometimes J-Link was able to download the DDR test program to the
SYSRAM, but most of the time it couldn't. Probably it would work just fine if it
wasn't for the soldermask covering. I wish I had just used a normal pin-header
connector rather than the J-Link needle adapter. So, I'll have to use UART boot
mode for now, and hope that I can get the (much faster) USB mode to work.

### SD card

For the evaluation board, I prepared a simple example that reads a program
(blink) from SD card to DDR, and passes control to the program. The LED blinks,
everything is fine.

On the custom board, I simplified the example so it just tests that DDR and SD
card can be written to and read from. The SD initialization fails as follows.
In file `stm32mp13xx_hal_sd.c`, the function `HAL_SD_Init` calls
`HAL_SD_GetCardStatus` which calls `SD_SendSDStatus`. There, the error flag
`SDMMC_FLAG_DTIMEOUT` is detected, i.e. timeout when trying to get data.

The custom board connections from MCU to SD card pins are as follows:

    PC10/SDMMC1_D2 (B13) → 1 DAT2
    PC11/SDMMC1_D3 (C14) → 2 DAT3/CD
    PD2/SDMMC1_CMD (A15) → 3 CMD with 10k pullup to +3.3V
    +3.3V → 4 VDD
    PC12/SDMMC1_CK (B15) → 5 CLK
    GND → 6 VSS
    PC8/SDMMC_D0 (D14) → 7 DAT0
    PC9/SDMMC_D1 (A16) → 8 DAT1
    PI7 (U16) uSD_DETECT → 9 DET_B with 100K pullup to +3.3V
    (nc) → 10 DET_A

Since the failure happens soon after switching the card into 1.8V mode, I need
to verify the voltages. On the evaluation board, `VDD_SD` is 3.3V on boot, and
when the SD program is running, it lowers it to 2.9V. I modified the code to
leave it at 3.3V, and it worked also: the code read data from SD card correctly.
On my custom board, `VDD_SD` is tied to 3.3V directly. (SD cards should accept
abything from 2.7V to 3.6V.) Thus, the SD card voltage should be okay.

The other voltage to check is the one powering the SoC domain for the SDMMC
controller. The eval board shows that both `VDDSD1` and `VDDSD2` are tied to
`VDD`---the same `VDD` as the rest of the SoC. We can measure that easily via
CN14 pin 13, and it measures 3.3V. On the custom board, these are tied to 3.3V
directly.

On the eval board, I looked at the `SDMMC1_CK` line (about 1.56 MHz),
`SDMMC1_CMD`, and the data lines with a scope probe and I saw 3V logic signals,
so it does not seem that 1.8V logic is used.

Adding lots of print statements to `SD_PowerON`, we get the following when
running on the custom board:

    CMD0: Go Idle State...
    CMD0 result = 0x00000000
    CMD8: Send Interface Condition...
    CMD8 result = 0x00000000
    CMD8 OK -> CardVersion = V2.x
    CMD55: APP_CMD (arg=0)
    CMD55 result = 0x00000000
    ACMD41 loop...
    Loop 0
      CMD55...
      CMD55 result = 0x00000000
      ACMD41...
      ACMD41 result = 0x00000000
      R3 Response = 0x41FF8000
      ValidVoltage = 0
    Loop 1
      CMD55...
      CMD55 result = 0x00000000
      ACMD41...
      ACMD41 result = 0x00000000
      R3 Response = 0xC1FF8000
      ValidVoltage = 1
    ACMD41 success: OCR=0xC1FF8000
    Card reports High Capacity (SDHC/SDXC)
    SD_PowerON: SUCCESS

Followed by the same `HAL_SD_ERROR_DATA_TIMEOUT` error from `SD_SendSDStatus`.
Let's instrument the latter function with prints also. Here's what we get:

    --- SD_SendSDStatus BEGIN ---
    Initial RESP1 = 0x00000900
    CMD16: Set Block Length = 64...
    CMD16 result = 0x00000000
    CMD55: APP_CMD (arg=RCA<<16) = 0xAAAA0000
    CMD55 result = 0x00000000
    Configuring DPSM: len=64, block=64B
    ACMD13: Send SD Status...
    ACMD13 result = 0x00000000
    Waiting for data...
    ERROR: SDMMC_FLAG_DTIMEOUT detected!

#### Pullups?

The SD card initialization was inherited from the evaluation board, where
all the signals are passed through the `EMIF06-MSD02N16` ESD protection chip,
which also features built-in pullups.

In `HAL_SD_MspInit`, we can enable internal pullups on the data lines going to
the SD card. In that case, we get the following printout from the instrumented
version of `SD_SendSDStatus`:

    --- SD_SendSDStatus BEGIN ---
    Initial RESP1 = 0x00000900
    CMD16: Set Block Length = 64...
    CMD16 result = 0x00000000
    CMD55: APP_CMD (arg=RCA<<16) = 0xAAAA0000
    CMD55 result = 0x00000000
    Configuring DPSM: len=64, block=64B
    ACMD13: Send SD Status...
    ACMD13 result = 0x00000000
    Waiting for data...
    RXFIFOHF set — reading 8 words...
      FIFO -> 0x00000000
      FIFO -> 0x00000004
      FIFO -> 0x00900004
      FIFO -> 0x001A050F
      FIFO -> 0x00000000
      FIFO -> 0x00000100
      FIFO -> 0x00000000
      FIFO -> 0x00000000
    RXFIFOHF set — reading 8 words...
      FIFO -> 0x00000000
      FIFO -> 0x00000000
      FIFO -> 0x00000000
      FIFO -> 0x00000000
      FIFO -> 0x00000000
      FIFO -> 0x00000000
      FIFO -> 0x00000000
      FIFO -> 0x00000000
    Data-end flag set, reading remaining FIFO...
    Clearing static DATA flags
    --- SD_SendSDStatus SUCCESS ---

After that, reading from the SD card was possible---but about half of the bytes
read were slightly corrupted.

#### Data corruption

Suspecting that there is something wrong with the 4-bit data transfers, I
switched to `SDMMC_BUS_WIDE_1B` and confirmed with a scope probe that there is
no data on DAT1,2,3, only on DAT0. But data corruption is still there. The clock
speed is only about 1.56 MHz, which seems to rule out signal integrity issues.

I tried a different power supply for the 3.3V supply, and still the same issue.
I added 330uF capacitors on all three power rails (1.25V, 1.35V, 3.3V, althought
1.25V and 1.35V are connected together), and still no improvement. (The PCB
already has a 10U capacitor next to the SD card VDD pin.)

Changing the `ClockEdge` of the `SDHandle.Init` does not fix it. Nor did setting
`PIO_Init_Structure.Speed` to `GPIO_SPEED_FREQ_VERY_HIGH`.

Interestingly the corruption affects only every other byte, and if it is
corrupted, it's always just off by 2 (i.e., only bit number 1 is affected).

Adding the external 3.3V 10k pullup on DAT0 (when running in `SDMMC_BUS_WIDE_1B`
mode) did not fux the corruption either. At any rate, scope traces show very
clean data and clock waveforms (as is to be expected at such a low frequency).

#### Aligned writes to RAM!

The test function used `HAL_SD_ReadBlocks` to write directly into DRAM. If
instead I wrote to a static buffer in SYSRAM, it works just fine.

So reading data from the SD card into a static buffer worked perfectly, but
copying that data into DRAM using a byte-wise method like memcpy caused
intermittent corruption. Only every other byte was sometimes wrong, always off
by exactly 2, and the pattern varied with each read. This behavior was not
reproducible when filling DRAM directly with aligned 32-bit word writes, which
always produced correct data.

The root cause is that the STM32's DRAM interface and AXI bus require strict
32-bit aligned writes. Byte-by-byte or unaligned half-word writes, as performed
by memcpy, can trigger timing-dependent corruption in certain regions of DRAM,
especially when interacting with uncached memory or peripheral-driven data like
SDMMC polling reads. The SD read itself was not at fault; the static buffer
contained the correct bytes.

The fix was to copy the SD block into DRAM using explicit 32-bit aligned word
writes, constructing each word from four bytes of the static buffer. This
ensures all writes are properly aligned and word-sized, eliminating the
intermittent errors and producing fully correct, reproducible data in DRAM.

### USB

I gave up trying to make the provided `CDC_Standalone` example to work on the
eval board, let alone the custom board. Instead, let's get USB to work step by
step.

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

#### VBUS sense?

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

#### Interrupt storm?

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

#### JTAG again

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

#### USB Device Stack

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


### Changes for Rev B

Bug fixes:

- Open solder mask over the JTAG connector
- Add some big electrolytic capacitors on all power rails
- Change U201 (NCP380HMUAJAATBG) to a fixed-current model (e.g.,
  NCP380HMU05AATBG), or else install the current-limit resistor. Better yet,
  replace it with a better switch entirely.

Nonbug improvements:

- Add LSE crystal (32.768 kHz)
- Add button for BOOT selection instead of (or in addition to) DIP switch
- Add another debug LED in a different color (say, green)

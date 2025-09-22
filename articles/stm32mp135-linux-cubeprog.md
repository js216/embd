---
title: STM32MP135 Flashing via USB with STM32CubeProg
author: Jakob Kastelic
date: 7 Sep 2025
topic: Linux
description: >
   Learn how to flash Linux to the STM32MP135 evaluation board over USB using
   STM32CubeProg, without removing the SD card. Step-by-step tutorial with
   commands, setup tips, and discussion of the complex STM32 boot stack.
---

![](../images/cal.jpg)

*This is Part 2 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

In the [previous article](stm32mp135-linux-default-buildroot), we built a Linux
kernel and manually copied it to an SD card. This works for a first test, but
quickly becomes annoying. Here, we show how to use the
[STM32CubeProg](https://www.st.com/en/development-tools/stm32cubeprog.html#get-software)
to flash the SD card without removing it from the evaluation board.

### Tutorial

Note: You may find the extensive explanations in the [Bootlin article about
flashing a similar
chip](https://bootlin.com/blog/building-a-linux-system-for-the-stm32mp1-implementing-factory-flashing/)
helpful.

1. Finish the build process as per the [previous
   article](stm32mp135-linux-default-buildroot), so as to have at least the
   following files under `buildroot/output/images/`:

   - `tf-a-stm32mp135f-dk.stm32`
   - `fip.bin`
   - `u-boot-nodtb.bin`
   - `sdcard.img`

2. Go to the ST website to download the
   [STM32CubeProg.](https://www.st.com/en/development-tools/stm32cubeprog.html#get-software)
   This unfortunately requires a registration and sign-up.

   Get the Linux version, unpack in a new directory, and run the installer (just
   follow its verbose prompts):
   
   ```sh
   $ cd cubeprog
   $ unzip ../stm32cubeprg-lin-v2-20-0.zip
   $ ./SetupSTM32CubeProgrammer-2.20.0.linux
   ```

3. Now plug in all three USB cables for the board. Set the DIP boot switches for
   serial boot (press in all the upper parts of the white rocker switches).
   Press the black reset button. If everything worked, you should be able to see
   the board under your USB devices:

   ```sh
   jk@Lutien:/var/www/articles$ lsusb
   ...
   Bus 001 Device 114: ID 0483:3753 STMicroelectronics STLINK-V3
   Bus 001 Device 012: ID 0483:df11 STMicroelectronics STM Device in DFU Mode
   ...
   ```
   
   The `STLINK-V3` is what you can use to monitor the flashing progress via UART.
   Simply open a serial monitor:
   
   ```sh
   sudo picocom -b 115200 /dev/ttyACM0
   ```

4. Run the STM32CubeProg from the location that you installed it in to check
   that it is able to detect the board:

   ```sh
   $ sudo ~/cube/bin/STM32_Programmer_CLI -l usb
         -------------------------------------------------------------------
                           STM32CubeProgrammer v2.20.0
         -------------------------------------------------------------------
   
   =====  DFU Interface   =====
   
   Total number of available STM32 device in DFU mode: 1
   
     Device Index           : USB1
     USB Bus Number         : 001
     USB Address Number     : 002
     Product ID             : USB download gadget@Device ID /0x501, @Revision ID /0x1003, @Name /STM32MP135F Rev.Y,
     Serial number          : 002800423232511538303631
     Firmware version       : 0x0110
     Device ID              : 0x0501
   ```

5. If that worked, it's time to prepare the images for flashing. Go to
   `buildroot/output/images` and create a file `flash.tsv` with the following
   contents:

   ```sh
   #Opt	Id	Name	Type	IP	Offset	Binary
   -	0x01	fsbl1-boot	Binary	none	0x0	tf-a-stm32mp135f-dk.stm32
   -	0x03	fip_boot	Binary		none	0x0		fip.bin
   -	0x03	ssbl-boot	Binary	none	0x0	u-boot-nodtb.bin
   P	0x10	sdcard	RawImage	mmc0		0x0	sdcard.img
   ```
   
   Finally, run the flashing command itself:
   
   ```sh
   sudo ~/cube/bin/STM32_Programmer_CLI -c port=usb1 -w flash.tsv
   ```

   The STM32CubeProg will go through the sequence of files you wrote into
   `flash.tsv`. First, the Arm Trusted Firmware (TF-A) gets written to the
   memory and executed. It then does some secure magic behind the scenes and
   accepts the next payload via the DFU protocol, the U-Boot. At last, U-Boot
   itself is executed and it in turn accepts the last payload: the SD card
   itself. Which was, after all, the only thing you wanted to transfer anyway
   ...

### Discussion

The tutorial above again presents the simplest method I have found so far, with
a minimum of steps and prerequisites, to flash the SD card of the eval board
without taking the card in and out. What's the issue?

The STM32CubeProg comes in a 291M zip file, which gets installed as a 1.5G
program. We use it to copy a disk image to the SD card. See the problem yet?
Or let's consider the on-board procedure: TF-A (4,212 files and 506,952 lines of
code according to [cloc](https://github.com/AlDanial/cloc)) is used to run
U-Boot (21,632 files and 3,419,116 lines of code), just so that a semi-standard
USB DFU protocol can expose the SD card to write the image.

But why??? ChatGPT explains:

> U-Boot became the standard since vendors upstreamed support there, and it
> offers cross-platform flashing via DFU/fastboot for factories and Windows
> users who can’t `dd` raw disks. It also doubles as the hook for A/B updates,
> rollback, and secure boot. In practice, this forces developers into a complex
> boot stack, even though most boards could just boot Linux directly from
> SD/eMMC and use a tiny DFU mass-storage tool for recovery.

A more likely explanation is that the boot process has acquired an unnecessary
reputation for being difficult, so that few want to mess with it. If there is a
working solution, it will get incorporated into the software stack, no matter
how baroque. The warning has been around for a long time:

> Big building-blocks [...] can lead to more compact code and shorter
> development time. [...] Less clear, however, is how to assess the loss of
> control and insight when the pile of system-supplied code gets so big that one
> no longer knows what's going on underneath.

> [... As] libraries, interfaces, and tools become more complicated, they become
> less understood and less controllable. When everything works, rich programming
> environments can be very productive, but when they fail, there is little
> recourse.[^pract]

All these tool are intended to make our work easier, but as they are piled on
without any reasonable limit, the resulting mess is ironically far more
complicated than the problem they are solving. If the task at hand is to flash
an SD card image, why doesn't the firmware expose the medium as a USB mass
storage device, so that standard tools like `dd` could be used to work with it?
The cynical answer suggests itself ... They didn't know better.

> Those who do not understand Unix are condemned to reinvent it, poorly.[^ray]

Surely it cannot be too difficult to write a simple "bare-metal" program, which
we could load to the board using the simple and well-documented UART protocol
implemented in the ROM of the STM32MP1. The program would be very small and
quick to load. The program would expose the available media as mass storage
devices, and that's it.

But ... You may object, we need U-Boot anyways, otherwise how are we to load
Linux? As we will explain in a future article, that is not so. U-Boot is
entirely unnecessary for a large class of embedded Unix applications.

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><em>2. This article</em></li>
  <li><a href="stm32mp135-without-u-boot">3. STM32MP135 Without U-Boot (TF-A Falcon Mode)</a></li>
  <li><a href="linux-tfa-bl33-qemu">4. Linux as TF-A BL33 on Qemu (No U-Boot)</a></li>
  <li><a href="stm32mp135-without-optee">5. STM32MP135 Without OP-TEE</a></li>
</ul>
</div>

[^pract]:  B. Kernighan and R. Pike Overview: The Practice of Programming.
    Addison-Wesley, 1999.

[^ray]: Attributed to Henry Spencer as his November 1987 Usenet signature in E.
    S.  Raymond: The Art of Unix Programming. Addison-Wesley, 2004.

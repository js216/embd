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
this [repository](https://github.com/js216/stm32mp135_test_board).)

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



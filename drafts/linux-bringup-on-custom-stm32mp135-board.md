---
title: Linux Bring-Up on a Custom STM32MP135 Board
author: Jakob Kastelic
date:
topic: Linux
description: >
---

![](../images/vt.jpg)

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

### SD

*Note: read the full USB story
[here](https://embd.cc/sdcard-on-bare-metal-stm32mp135).*

On the STM32MP135 evaluation board, an SDMMC example reliably reads a program
from an SD card into DDR and executes it, but porting the same code to a custom
board exposed a failure during SD initialization. Although command-level
communication succeeded—CMD0, CMD8, CMD55, and ACMD41 all completed normally and
the card identified as SDHC—the sequence consistently failed later in
`SD_SendSDStatus` with `SDMMC_FLAG_DTIMEOUT`. Hardware checks showed that SD
card power, SDMMC I/O domain voltages, and signal levels all matched the
evaluation board, with clean 3.3 V logic and a low clock rate of about 1.56 MHz.
The decisive difference turned out to be signal pull-ups: the evaluation board
routes SD signals through an ESD device with built-in pull-ups, whereas the
custom board did not. Enabling internal pull-ups on the SD data lines eliminated
the data timeout and allowed SD reads to proceed, confirming that missing
pull-ups were responsible for the initialization failure.

However, once SD transfers succeeded, the data read from the card appeared
corrupted in DDR: roughly every other byte was intermittently wrong, always off
by exactly two, independent of bus width, clock edge, power supply, or signal
integrity. The critical observation was that data read into a static buffer in
SYSRAM was always correct, while corruption appeared only after copying that
data into DDR using byte-wise writes such as memcpy. When DDR was written using
explicit, 32-bit aligned word accesses, the corruption disappeared entirely. The
root cause was therefore not the SD interface but unaligned byte and half-word
writes to DDR, which violate the STM32MP13 DDR/AXI access requirements and can
cause timing-dependent data corruption, especially when interacting with
uncached memory and peripheral-driven transfers. Ensuring that all DDR writes
are word-sized and properly aligned fully resolved the issue and restored
correct, reproducible SD card operation on the custom board.

### USB

*Note: read the full USB story
[here](https://embd.cc/usb-bringup-on-custom-stm32mp135-board).*

Getting USB working on a custom STM32MP135 board involved a few key hardware and
software steps. First, I enabled the USBHS power switch by adding a
current-limit resistor so the PHY would receive power. On the board, I removed
the permanent 1.5 kΩ pullup on the D+ line to allow proper High-Speed
enumeration. I also ensured JTAG worked reliably by booting in engineering debug
mode and verifying the vector table took interrupts in ARM mode.

On the software side, I disabled VBUS sensing in the HAL PCD initialization to
match the externally powered board, configured the Rx/Tx FIFOs, and made sure
all required USB interrupts were correctly handled. For the USB Device stack, I
added the necessary callbacks in `usbd_conf.c` and applied volatile casts to
ensure 32-bit accesses to SYSRAM were aligned, avoiding Data Aborts.

Finally, I verified proper memory alignment for DDR writes to ensure file
transfers worked without byte shuffling, and confirmed enumeration and data
transfers at High-Speed using a good USB cable and port. After these steps, the
board enumerated correctly as an MSC device, and read/write operations
functioned reliably.

### Switch to Non-Secure World

*Note: read the full TrustZone story
[here](https://embd.cc/unsecuring-stm32mp135-trustzone).*

The STM32MP135 integrates the Arm TrustZone extension which partitions the
system into two isolated security domains, the secure and non-secure worlds,
depending on the state of the `NS` bit in the `SCR` register. Before the bit is
flipped, we need to unsecure many parts of the SoC (DDR, DMA masters, etc).

### Board Changes for Rev B

Bug fixes:

- Open solder mask over the JTAG connector
- Change U201 (NCP380HMUAJAATBG) to a fixed-current model (e.g.,
  NCP380HMU05AATBG), or else install the current-limit resistor. Better yet,
  replace it with a better switch entirely (this one, even when supposedly off,
  still reads about 2V, which may end up damaging the device in the long run).
- Remove the 1.5K pullup on USB D+ line

Nonbug improvements:

- Add some big electrolytic capacitors on all power rails
- Add LSE crystal (32.768 kHz)
- Add button for BOOT selection instead of (or in addition to) DIP switch
- Add another debug LED in a different color (say, green)

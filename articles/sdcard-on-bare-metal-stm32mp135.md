---
title: SD card on bare-metal STM32MP135
author: Jakob Kastelic
date: 20 Dec 2025
topic: Embedded
description: >
    Debugging SDMMC failures on a custom STM32MP135 board. Timeouts, pull-ups,
    voltage checks, and a surprising root cause involving unaligned DDR writes
    and AXI requirements.
---

![](../images/deco.jpg)

This article presents my step-by-step debug process for getting the SD card to
work reliably on my [custom
board](https://github.com/js216/stm32mp135_test_board) integrating the
STM32MP135.

### Test program

For the evaluation board, I prepared a [simple
example](https://github.com/js216/mp135_boot/tree/main/sd_to_ddr) that reads a
program (blink) from SD card to DDR, and passes control to the program. The LED
blinks, everything is fine.

On the custom board, I simplified the example so it just tests that DDR and SD
card can be written to and read from. The SD initialization fails as follows.
In file `stm32mp13xx_hal_sd.c`, the function `HAL_SD_Init` calls
`HAL_SD_GetCardStatus` which calls `SD_SendSDStatus`. There, the error flag
`SDMMC_FLAG_DTIMEOUT` is detected, i.e. timeout when trying to get data.

### Wiring

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

### Debug prints

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

The root cause is that the DDR wiring swapped upper and lower data bytes in a
way that only causes problems with non-32-bit data access. (The debugging
process that led to that insight is explained in a [future
article](https://embd.cc/debugging-stm32mp135-kernel-decompression.md).) The SD
read itself was not at fault; the static buffer contained the correct bytes.

The workaround was to copy the SD block into DRAM using explicit 32-bit aligned
word writes, constructing each word from four bytes of the static buffer. This
ensures all writes are properly aligned and word-sized, eliminating the
intermittent errors and producing fully correct, reproducible data in DRAM.

---
title: Stream Data In/Out of ADSP-2156
author: Jakob Kastelic
date:
topic: DSP
description: >
---

![](../images/lmp.jpg)

The ADSP-21569, as demonstrated on the
[EV-21569-SOM](https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/ev-21569-som.html)
and
[EV-SOMCRR-EZLITE](https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/EV-SOMCRR-EZLITE.html)
boards, appears to be optimized for streaming lots of audio channels. What if we
instead need to stream fewer channels at faster sample rates? In this article,
we will try out several possible pathways.

### UART

The first step after ["blink"](https://embd.cc/boot-sharc-dsp-over-uart) works
is to have a debug input/output and UART is always the easiest. Of course we
already had to set it out [previously](https://embd.cc/agentic-coding-on-dsp) to
enable automated agentic code development and testing.

### QSPI: From USB into DSP using FT4222

We can test mass data ingestion without any additional wiring via the QSPI
interface, since the EZLITE board includes a USB-to-SPI adapter
`FT4222HQ-D-T`. (Make sure to follow the QSPI setup instructions in the
[previous](https://embd.cc/sharc-dsp-over-qspi) article to make sure that
FT4222-as-master works.)

With DSP in slave mode, we can write a little test program that ingests the data
using DMA into two buffers, "ping-ponging" between them: DMA writes into one
buffer while we read from the other, and when the first one is full, DMA
starts to write into the second one. If we process the data fast enough, this
guarantees there'll be no contention between the CPU and DMA without requiring
any other synchronization.

In this case, all we are interested in is whether the data is received
correctly. As a simple test, we can write a couple bytes and then read them out
via UART, but then we cannot test the data transfer speed. Instead, we can tell
the CPU to consume the data when DMA buffer fills up and calculate a running
checksum (e.g., XOR all words into a single accumulator).

The data rates from USB into FT4222 and thence into the DSP are as shown in the
table:

| Lanes | SCK    | Mbps actual | Mbps theoretical | % peak |
|-------|--------|-------------|------------------|--------|
| 1     | 10 MHz | 4.4         | 10               | 44 %   |
| 1     | 20 MHz | 5.8         | 20               | 29 %   |
| 1     | 40 MHz | 6.8         | 40               | 17 %   |
| 2     | 10 MHz | 16.1        | 20               | 81 %   |
| 2     | 20 MHz | 27.1        | 40               | 68 %   |
| 2     | 40 MHz | 40.7        | 80               | 51 %   |
| 4     | 10 MHz | 27.1        | 40               | 68 %   |
| 4     | 20 MHz | 41.1        | 80               | 51 %   |
| 4     | 40 MHz | 53.9        | 160              | 34 %   |

"Up to 53.8Mbps data transfer rate in SPI master with quad mode transfer" says
the bullet point on FT4222 datasheet front page. Later on, in Table 4.1 on page
11, the "Max Throughput" is stated as 52.8Mbps. "It also depends on the USB bus
transfer condition."

The quad-lane theoretical maximum takes into account that at most 64K bytes can
be transmitted at once, the clock rate is 40 MHz, and there's an extra 6.65 ms
(or is it 6.47 ms?) of library/USB overhead.

### FT4222 Silicon bug: need 0x00 first byte

Using SPI2 in the 1-lane mode (regular four-wire SPI), the transfer works as
expected. In Python, simply `import ft4222` and then make use of the
`spiMaster_SingleWrite()` function to write the data.

The dual and quad SPI modes, however, are more tricky. First of all, the
`spiMaster_SingleWrite()` refuses to send data outside the single-lane mode.
The library provides `spiMaster_MultiReadWrite()` which does transmit data but
*sometimes* all but the first byte is transmitted incorrectly: the bit
corresponding to D1 stays stuck at 0.

There's a hint in the "User Guide for LibFT4222" (FTDI App Note `AN_329`), in a
section on using the FT4222 in slave mode:

> For some reasons, support lib will append a dummy byte (0x00) at the first
> byte automatically.

We're using the FT4222 in master mode, but it seems that the library author knew
something that the app note writer did not: the chip has a quirk, or perhaps an
undocumented in-band command depending on the contents of the first byte
transmitted.

For example, if the first word transmitted is 0x0d4416c4, then all subsequent
data will be corrupted. However, many other first words do not trigger the bug
(e.g. 0x00000000, 0xFFFFFFFF, 0xc8ad14e5).

The workaround is as indicated in the above quote: always send 0x00 as the first
byte. Annoying, but irrelevant in this instance since all we care about is to
measure what is the maximum reliable data rate.

I have not been able to find this bug documented either in the datasheet or in
the Technical Note `TN_161`, "FT4222H Errata".

### QSPI out of DSP

Getting the data output of the DSP is just a little bit more tricky. We do not
want to switch the FT4222 into slave mode, because then we need to physically
move the S5 jumper on the EZLITE board, which would be annoying to automate.
Moreover, the FT4222 only supports the single-bit data transfer in slave mode,
while the master supports all three bit widths, both data directions.

### GPIO loopback

Some of the tests in the following sections will require wiring SPI and SPORT
ports between each other as "external loopback". To verify wiring continuity, it
is helpful to set up a GPIO example code that verifies which pins are connected
to which pins.

On the EZLITE board, connector P13 breaks out the DAI pins that are used for the
SPORT interface. Note that the pins' presence on the board does not mean they
are connected to anything! (They may be used with other SOM boards.)

| P13 pin | P13 signal    | Notes                          |
|---------|---------------|--------------------------------|
| 7       | `DAI0_PIN13`  | absent both packages           |
| 9       | `DAI0_PIN14`  | absent both packages           |
| 19      | `DAI0_PIN15`  | absent both packages           |
| 21      | `DAI0_PIN16`  | absent both packages           |
| 31      | `DAI0_PIN17`  | absent both packages           |
| 33      | `DAI0_PIN18`  | absent both packages           |
| 2       | `DAI1_PIN01`  |                                |
| 4       | `DAI1_PIN02`  |                                |
| 6       | `DAI1_PIN03`  |                                |
| 8       | `DAI1_PIN04`  |                                |
| 10      | `DAI1_PIN05`  |                                |
| 12      | `DAI1_PIN06`  |                                |
| 14      | `DAI1_PIN07`  |                                |
| 16      | `DAI1_PIN08`  |                                |
| 18      | `DAI1_PIN09`  |                                |
| 20      | `DAI1_PIN10`  |                                |
| 22      | `DAI1_PIN11`  | absent 120-lead LQFP           |
| 24      | `DAI1_PIN12`  | absent 120-lead LQFP           |
| 26      | `DAI1_PIN13`  | absent both packages           |
| 28      | `DAI1_PIN14`  | absent both packages           |
| 30      | `DAI1_PIN15`  | absent both packages           |
| 32      | `DAI1_PIN16`  | absent both packages           |
| 34      | `DAI1_PIN17`  | absent both packages           |
| 36      | `DAI1_PIN18`  | absent both packages           |
| 38      | `DAI1_PIN19`  |                                |
| 40      | `DAI1_PIN20`  |                                |

On the P14 header, we get access to the I2C and two SPI ports. These are highly
multiplexed. For example, the `PA_06` and `PA_07` are `UART0_TX` and `UART0_RX`,
respectively.

| P14 pin | P14 signal | P14 function  | Multiplexed |
|---------|------------| --------------|-------------|
| 25      | `PA_14`    | `TWI2_SCL`    | Fn 0        |
| 27      | `PA_15`    | `TWI2_SDA`    | Fn 0        |
| 2       | `PA_06`    | `SPI0_CLK`    | Fn 0        |
| 4       | `PA_07`    | `SPI0_MISO`   | Fn 0        |
| 6       | `PA_08`    | `SPI0_MOSI`   | Fn 0        |
| 8       | `PA_09`    | `SPI0_SSB`    | Input Tap   |
| 10      | `PB_05`    | `SPI0_SEL2*`  | Fn 2        |
| 12      | `PA_10`    | `SPI1_CLK`    | Fn 1        |
| 14      | `PA_11`    | `SPI1_MISO`   | Fn 1        |
| 16      | `PA_12`    | `SPI1_MOSI`   | Fn 1        |
| 18      | `PA_13`    | `SPI1_SEL1*`  | Fn 1        |
| 20      | `PB_10`    | `SPI1_SEL2*`  | Fn 1        |

A simple code example can be
se://www.st.com/en/evaluation-tools/stm32mp135f-dk.htmlt up that verifies which pin is connected against
which pin. This makes debugging of the following "external loopback" examples
much easier.

### SPI0 into SPI1 loopback

### SPORT internal loopback

### SPORT external loopback

┌───────────────────────────┬─────────────────────────┬─────────┐
│       SPORT4 signal       │ default DAI1 pin buffer │ P13 pin │
├───────────────────────────┼─────────────────────────┼─────────┤
│ SPT4_AD0  (TX data)       │ DAI1_PB01               │ 2       │
├───────────────────────────┼─────────────────────────┼─────────┤
│ SPT4_ACLK (TX clock)      │ DAI1_PB03               │ 6       │
├───────────────────────────┼─────────────────────────┼─────────┤
│ SPT4_AFS  (TX frame sync) │ DAI1_PB04               │ 8       │
├───────────────────────────┼─────────────────────────┼─────────┤
│ SPT4_BD0  (RX data)       │ DAI1_PB05               │ 10      │
├───────────────────────────┼─────────────────────────┼─────────┤
│ SPT4_BCLK (RX clock)      │ DAI1_PB07               │ 14      │
├───────────────────────────┼─────────────────────────┼─────────┤
│ SPT4_BFS  (RX frame sync) │ DAI1_PB08               │ 16      │
└───────────────────────────┴─────────────────────────┴─────────┘

Jumpers on P13 (three wires)

┌────────┬────────────────────┬──────────────────────────────────────┐
│ Jumper │     From → To      │               Carries                │
├────────┼────────────────────┼──────────────────────────────────────┤
│ 1      │ P13 pin 2 ↔ pin 10 │ serial data (SPT4_AD0 → SPT4_BD0)    │
├────────┼────────────────────┼──────────────────────────────────────┤
│ 2      │ P13 pin 6 ↔ pin 14 │ serial clock (SPT4_ACLK → SPT4_BCLK) │
├────────┼────────────────────┼──────────────────────────────────────┤
│ 3      │ P13 pin 8 ↔ pin 16 │ frame sync (SPT4_AFS → SPT4_BFS)     │
└────────┴────────────────────┴──────────────────────────────────────┘

### SPORT with DMA (internal)

### SPORT with DMA (external)

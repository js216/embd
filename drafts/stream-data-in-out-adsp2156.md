---
title: Stream Data In/Out of ADSP-2156
author: Jakob Kastelic
date: 21 Sep 2025
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

### QSPI into DSP

### QSPI out of DSP

### GPIO loopback

Some of the following tests will require wiring SPI and SPORT ports between each
other as "external loopback". To verify wiring continuity, it is helpful to set
up a GPIO example code that verifies which pins are connected to which pins.

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

A simple code example can be set up that verifies which pin is connected against
which pin. This makes debugging of the following "external loopback". examples
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

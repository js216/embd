---
title: Quad SPI without Flash on STM32MP135
author: Jakob Kastelic
date:
topic: Embedded
description: >
---

![](../images/rb.jpg)

The STM32MP135 datasheet is very clear that the `QUADSPI` peripheral is a
"specialized communication interface targeting single, dual or quad SPI flash
memories". But can we use it without a flash memory, to transfer data from a DSP
or FPGA, perhaps with some glue logic in between?

### Eval board connections

To answer our QSPI questions, we can make use of the [STM32MP135FAF7 evaluation
board](https://www.st.com/en/evaluation-tools/stm32mp135f-dk.html).
Conveniently, the expansion connector `CN8` breaks out all the pins we need:

| `QUADSPI_` | Ball | Port | Alt Fn | CN8 pin | CN8 label    | A.k.a.      |
|------------|------|------|--------|---------|--------------|-------------|
| `CLK`      | H3   | PF10 | AF9    | 26      | `EXP_GPIO7`  | `EXP_GPIO7` |
| `BK1_NCS`  | C5   | PD1  | AF9    | 5       | `EXP_GPIO3`  | `I2C5_SCL`  |
| `BK1_IO0`  | R3   | PH3  | AF13   | 19      | `EXP_GPIO10` | `SPI5_MOSI` |
| `BK1_IO1`  | J5   | PF9  | AF10   | 33      | `EXP_GPIO13` | `UART8_RX`  |
| `BK1_IO2`  | N3   | PH6  | AF9    | 3       | `EXP_GPIO2`  | `I2C5_SDA`  |
| `BK1_IO3`  | J1   | PH7  | AF13   | 23      | `EXP_GPIO11` | `SPI5_SCK`  |

While UART8 and SPI5 appear to be unused on the eval board, I2C5 is overloaded
for several devices, amongst them the touchscreen. This is not an issue, just
means we have to disable these devices while doing the QSPI tests.

### GPIO continuity check: scope, FPGA

To begin debugging, first implement a simple bare-metal program that can
configures the pins from the above table as simple GPIO output. Toggling them
via the program, we observe that pins change state on the oscilloscope.

Next, connect an FPGA evaluation board. I'm using the
[iCEstick](https://www.latticesemi.com/en/Products/DevelopmentBoardsAndKits/iCEstick)
from Lattice, featuring the `ICE30HX1K` FPGA. Besides the price, the key
advantage of these Lattice FPGA is the availability of a fully-functioning
open-source development toolchain.

I'm connecting the QSPI signals to the J3 jumper of the iCEstick as follows:

| `QUADSPI_` | CN8 pin | J3 pin | FPGA signal | FPGA pin |
|------------|---------|--------|-------------| ---------|
| `BK1_NCS`  | 5       | 10     | `PIO2_10`   | 44       |
| `CLK`      | 26      | 9      | `PIO2_11`   | 45       |
| `BK1_IO0`  | 19      | 8      | `PIO2_12`   | 47       |
| `BK1_IO1`  | 33      | 7      | `PIO2_13`   | 48       |
| `BK1_IO2`  | 3       | 6      | `PIO2_14`   | 56       |
| `BK1_IO3`  | 23      | 5      | `PIO2_15`   | 60       |

Running a simple demo bitstream, the FPGA can easily printout over UART which
pins are high and which are low as we scan the GPIO pins from the STM32.

---
title: NAND Flash on Bare-Metal STM32MP135
author: Jakob Kastelic
date: 
topic: Embedded
description: >
---

![](../images/.jpg)

Getting the NAND flash peripheral to work on the STM32MP135 appears tricky since
the evaluation board does not include it. In this article, we'll check my
connections; we'll extract the relevant parameters from the datasheet, and try
to use the HAL drivers to access the memory chip on my [custom STM32MP135
board](https://github.com/js216/stm32mp135_test_board).

### Connections

I am using the `MX30LF4G28AD-TI` NAND flash (512 MB) chip, connecting to the
`STM32MP135FAE` SoC, as follows:

| NAND pin | NAND signal | SoC signal      | SoC pin | Notes             |
| -------- | ----------- | --------------- | ------- | ----------------- |
| 9        | `CE#`       | `PG9/FMC_NCE`   | `E1`    | 10k to `VDD_NAND` |
| 16       | `ALE`       | `PD12/FMC_ALE`  | `C6`    |                   |
| 17       | `CLE`       | `PD11/FMC_CLE`  | `E2`    |                   |
| 8        | `RE#`       | `PD4/FMC_NOE`   | `E7`    |                   |
| 18       | `WE#`       | `PD5/FMC_NWE`   | `A6`    |                   |
| 7        | `R/B#`      | `PA9/FMC_NWAIT` | `A2`    | 10k to `VDD_NAND` |
| 29       | `I/O0`      | `PD14/FMC_D0`   | `B3`    |                   |
| 30       | `I/O1`      | `PD15/FMC_D1`   | `C7`    |                   |
| 31       | `I/O2`      | `PD0/FMC_D2`    | `E4`    |                   |
| 32       | `I/O3`      | `PD1/FMC_D3`    | `D5`    |                   |
| 41       | `I/O4`      | `PE7/FMC_D4`    | `A5`    |                   |
| 42       | `I/O5`      | `PE8/FMC_D5`    | `A7`    |                   |
| 43       | `I/O6`      | `PE9/FMC_D6`    | `B6`    |                   |
| 44       | `I/O7`      | `PE10/FMC_D7`   | `B8`    |                   |
| 19       | `WP#`       | `PWR_ON`        | `P14`   | via 10k           |
| 38       | `PT`        | ---             | ---     | 10k to GND        |

`VDD_NAND` is derived from +3.3V, switched on the `NAND_WP#` signal: when
`NAND_WP#` is low, `VDD_NAND` is floating, and with `NAND_WP#` is high,
`VDD_NAND` is powered from +3.3V.

Furthermore, a `1N5819WS` diode allows the system `RESET#` to pull `NAND_WP#`
low when asserted, to assert write protect when system is under reset. When
system is not under reset (i.e., `RESET#` is high), the diode prevents opposite
current flow. A 10k resistor is connected between `PWR_ON` and `NAND_WP#` to
prevent shorting `PWR_ON` to ground when reset is asserted (low).

### Voltages and power switching

The power supply and related voltages read as follows:

| Node       | Operation [V] | Reset [V]      |
| ---------- | ------------- | -------------- |
| +3.3V      | 3.300         | 3.306          |
| `RESET#`   | 3.295         | 0.000          |
| `VDD_NAND` | 0.000         | 0.001          |
| `PWR_ON`   | 3.301         | 3.303          |
| `NAND_WP#` | 3.202         | 0.169          |

The problem immediately jumps out at us: the power switch does not work.
Regardless of the state of `NAND_WP#`, the `VDD_NAND` node stays around zero.

The power switch is an `NCP380`, more precisely the `C145185` from the JLCPCB
parts library in the UDFN6 package (`NCP380HMUAJAATBG`). The active enable level
is "High", which is correct, but the over current limit is "Adj." To fix this,
we have to solder a resistor (anything from 10k to 33k would do) between pin 2
of the switch and ground.

With this fix, `VDD_NAND` reads 3.300V in normal operation, and in reset, 0.5V
slowly decaying towards zero.

### NAND parameters

The NAND datasheet is 93 pages long and includes a lot of numbers, but not so
many as the DDR chip. The STM32MP135 bare-metal BSP package
([STM32CubeMP13](https://wiki.st.com/stm32mpu/wiki/STM32CubeMP13_Package))
includes the FMC NAND driver, and a code example, and this will be our starting
point. The following parameters can be easily read off the NAND datasheet:

Let's leave the following parameters as in the ST example for now:

```c
/* hnand Init */
hnand.Instance  = FMC_NAND_DEVICE;
hnand.Init.NandBank        = FMC_NAND_BANK3; /* Bank 3 is the only available with STM32MP135 */
hnand.Init.Waitfeature     = FMC_NAND_WAIT_FEATURE_ENABLE; /* Waiting enabled when communicating with the NAND */
hnand.Init.MemoryDataWidth = FMC_NAND_MEM_BUS_WIDTH_8; /* An 8-bit NAND is used */
hnand.Init.EccComputation  = FMC_NAND_ECC_DISABLE; /* The HAL enable ECC computation when needed, keep it disabled at initialization */
hnand.Init.EccAlgorithm    = FMC_NAND_ECC_ALGO_BCH; /* Hamming or BCH algorithm */
hnand.Init.BCHMode         = FMC_NAND_BCH_8BIT; /* BCH4 or BCH8 if BCH algorithm is used */
hnand.Init.EccSectorSize   = FMC_NAND_ECC_SECTOR_SIZE_512BYTE; /* BCH works only with 512-byte sectors */
hnand.Init.TCLRSetupTime   = 2;
hnand.Init.TARSetupTime    = 2;

/* ComSpaceTiming */
FMC_NAND_PCC_TimingTypeDef ComSpaceTiming = {0};
ComSpaceTiming.SetupTime = 0x1;
ComSpaceTiming.WaitSetupTime = 0x7;
ComSpaceTiming.HoldSetupTime = 0x2;
ComSpaceTiming.HiZSetupTime = 0x1;

/* AttSpaceTiming */
FMC_NAND_PCC_TimingTypeDef AttSpaceTiming = {0};
AttSpaceTiming.SetupTime = 0x1A;
AttSpaceTiming.WaitSetupTime = 0x7;
AttSpaceTiming.HoldSetupTime = 0x6A;
AttSpaceTiming.HiZSetupTime = 0x1;
```

The following numbers we can easily read off the datasheet:

```c
hnand.Config.PageSize = 4096;     // bytes
hnand.Config.SpareAreaSize = 256; // bytes
hnand.Config.BlockSize = 64;      // pages
hnand.Config.BlockNbr = 4096;     // blocks
hnand.Config.PlaneSize = 1024;    // blocks
hnand.Config.PlaneNbr = 2;        // planes
```

### Initialization

We enable the FMC clock and the relevant GPIOs and then configure pin muxing
(same as the ST example code):

```c
/* Common GPIO configuration */
GPIO_InitTypeDef GPIO_Init_Structure;
GPIO_Init_Structure.Mode      = GPIO_MODE_AF_PP;
GPIO_Init_Structure.Pull      = GPIO_PULLUP;
GPIO_Init_Structure.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;

/* STM32MP135 pins: */
GPIO_Init_Structure.Alternate = GPIO_AF10_FMC;
SetupGPIO(GPIOA, &GPIO_Init_Structure, GPIO_PIN_9); /* FMC_NWAIT: PA9 */
GPIO_Init_Structure.Alternate = GPIO_AF12_FMC;
SetupGPIO(GPIOG, &GPIO_Init_Structure, GPIO_PIN_9); /* FMC_NCE: PG9 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_4); /* FMC_NOE: PD4 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_5); /* FMC_NWE: PD5 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_12); /* FMC_ALE: PD12 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_11); /* FMC_CLE: PD11 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_14); /* FMC_D0: PD14 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_15); /* FMC_D1: PD15 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_0); /* FMC_D2: PD0 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_1); /* FMC_D3: PD1 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_7); /* FMC_D4: PE7 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_8); /* FMC_D5: PE8 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_9); /* FMC_D6: PE9 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_10); /* FMC_D7: PE10 */
```

I verified that the alternate functions for all the NAND-related pins are
exactly as given in the STM32MP135 datasheet.

The firmware can now call `HAL_NAND_Init()`. It succeeds, but then
`HAL_NAND_Reset()` fails. It writes `NAND_CMD_STATUS` (0x70), but reads back
0xff rather than `NAND_READY` (0x40).

On the scope, we can see that the `CE#` signal goes low for about 50ns.

Comparing the connection table shown above to the NAND datasheet, we notice that
unfortunately `ALE` and `CLE` have been swapped. The correct pin assignment
would be `CLE` on pin 16 and `ALE` on pin 17, opposite to the PCB wiring.

### Swapping ALE / CLE


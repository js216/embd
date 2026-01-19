---
title: LCD/CTP on Bare-Metal STM32MP135
author: Jakob Kastelic
date: 19 Jan 2026
topic: Embedded
description: >
   Step-by-step bring-up of an RGB LCD and capacitive touch panel on a
   bare-metal STM32MP135 custom board, covering pin muxing, backlight PWM, I2C
   touch initialization, LTDC timing, and PLL clock configuration needed to
   achieve a stable display.
---

![](../images/lcd.jpg)

In this writeup we'll go through the steps needed to bring up the LCD/CTP
peripheral on the [custom STM32MP135
board](https://github.com/js216/stm32mp135_test_board).

### Connections

I am using the Rocktech `RK050HR01-CT` LCD display, connecting to the
`STM32MP135FAE` SoC, as follows:

| LCD pin  | LCD signal | SoC signal       | SoC pin | Alt. Fn. |
| -------- | ---------- | ---------------- | ------- | -------- |
| 1, 2     | `VLED+/-`  | `PB15/TIM1_CH3N` | `B12`   | AF1      |
| 8        | `R3`       | `PB12/LCD_R3`    | `D9`    | AF13     |
| 9        | `R4`       | `PE3/LCD_R4`     | `D13`   | AF13     |
| 10       | `R5`       | `PF5/LCD_R5`     | `B2`    | AF14     |
| 11       | `R6`       | `PF0/LCD_R6`     | `C13`   | AF13     |
| 12       | `R7`       | `PF6/LCD_R7`     | `G2`    | AF13     |
| 15       | `G2`       | `PF7/LCD_G2`     | `M1`    | AF14     |
| 16       | `G3`       | `PE6/LCD_G3`     | `N1`    | AF14     |
| 17       | `G4`       | `PG5/LCD_G4`     | `F2`    | AF11     |
| 18       | `G5`       | `PG0/LCD_G5`     | `D7`    | AF14     |
| 19       | `G6`       | `PA12/LCD_G6`    | `E3`    | AF14     |
| 20       | `G7`       | `PA15/LCD_G7`    | `E6`    | AF11     |
| 24       | `B3`       | `PG15/LCD_B3`    | `G4`    | AF14     |
| 25       | `B4`       | `PB2/LCD_B4`     | `H4`    | AF14     |
| 26       | `B5`       | `PH9/LCD_B5`     | `A9`    | AF9      |
| 27       | `B6`       | `PF4/LCD_B6`     | `L2`    | AF13     |
| 28       | `B7`       | `PB6/LCD_B7`     | `C1`    | AF14     |
| 30       | `DCLK`     | `PD9/LCD_CLK`    | `E8`    | AF13     |
| 31       | `DISP`     | `PG7`            | `C9`    | ---      |
| 32       | `HSYNC`    | `PE1/LCD_HSYNC`  | `B5`    | AF9      |
| 33       | `VSYNC`    | `PE12/LCD_VSYNC` | `B4`    | AF9      |
| 34       | `DE`       | `PG6/LCD_DE`     | `A14`   | AF13     |

### Backlight

The easiest thing to check is the display backlight, since it's just a single
GPIO pin to turn on/off, or a simple PWM to control the brightness via the duty
cycle.

In our case, the backlight pin is connected to `TIM1_CH3N`, which is alternate
function 1:

```c
GPIO_InitTypeDef gpio;
gpio.Pin       = GPIO_PIN_15;
gpio.Mode      = GPIO_MODE_AF_PP;
gpio.Pull      = GPIO_NOPULL;
gpio.Speed     = GPIO_SPEED_FREQ_LOW;
gpio.Alternate = GPIO_AF1_TIM1;
HAL_GPIO_Init(GPIOB, &gpio);
```

ChatGPT can write the PWM configuration:

```c
__HAL_RCC_TIM1_CLK_ENABLE();

htim1.Instance = TIM1;
htim1.Init.Prescaler         = 99U;
htim1.Init.CounterMode       = TIM_COUNTERMODE_UP;
htim1.Init.Period            = 999U;
htim1.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
htim1.Init.RepetitionCounter = 0;
htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
HAL_TIM_PWM_Init(&htim1);

TIM_OC_InitTypeDef oc;
oc.OCMode       = TIM_OCMODE_PWM1;
oc.Pulse        = 500U;
oc.OCPolarity   = TIM_OCPOLARITY_HIGH;
oc.OCNPolarity  = TIM_OCNPOLARITY_HIGH;
oc.OCIdleState  = TIM_OCIDLESTATE_RESET;
oc.OCNIdleState = TIM_OCNIDLESTATE_RESET;
oc.OCFastMode   = TIM_OCFAST_DISABLE;

HAL_TIM_PWM_ConfigChannel(&htim1, &oc, TIM_CHANNEL_3);
HAL_TIMEx_PWMN_Start(&htim1, TIM_CHANNEL_3);
htim1.Instance->BDTR |= TIM_BDTR_MOE;
```

The only "tricky" part, or the part that AI got wrong, was that we have to use
`HAL_TIMEx_PWMN_Start()` instead of `HAL_TIM_PWM_Start()`, since we're dealing
with the complementary output. With that fixed, the brightness pin showed a
clean square wave output, with duty cycle adjustable in units of `percent`:

```c
__HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, 
      (htim1.Init.Period + 1U) * percent / 100U);
```

Unfortunately, the PCB reversed all pins and the connector is single sided, so
we cannot directly check if the above works on the actual display or not.
Nonetheless, we can see a nice 2.088893 kHz square wave with 50 duty cycle, and
we can tune it from 0% to 100%.

### CTP connections

The Rocktech `RK050HR01-CT` LCD display includes a capacitive touchpad (CTP),
connecting to the `STM32MP135FAE` SoC, as follows:

| CPT pin  | CPT signal | SoC signal       | SoC pin | Alt. Fn. |
| -------- | ---------- | ---------------- | ------- | -------- |
| 1        | `SCL`      | `PH13/I2C5_SCL`  | `A10`   | AF4      |
| 8        | `SDA`      | `PF3/I2C5_SDA`   | `B10`   | AF4      |
| 4        | `RST`      | `PB7`            | `A4`    | ---      |
| 5        | `INT`      | `PH12`           | `C2`    | ---      |

Luckily the 6-pin CTP connector, albeit wired in reverse, has contacts on both
top and bottom sides, so we can simply flip the ribbon cable. With entirely
usual I2C configuration it simply works. Check out the final result
[here](https://github.com/js216/stm32mp135-bootloader/blob/main/src/ctp.c)

My GT911 driver is just under 300 lines of code; it's very interesting that it
takes ST almost 3,000 (yes, it has more features ... Whatever, I don't need
them!)

```sh
stm32cubemp13-v1-2-0/STM32Cube_FW_MP13_V1.2.0/Drivers/BSP/Components/gt911$ cloc .
      12 text files.
      12 unique files.
       1 file ignored.

github.com/AlDanial/cloc v 1.90  T=0.10 s (109.2 files/s, 48189.3 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
CSS                              1            209             56           1446
C                                2            223            636            940
C/C++ Header                     3            159            614            421
Markdown                         2             24              0             62
HTML                             1              0              3             56
SVG                              2              0              0              4
-------------------------------------------------------------------------------
SUM:                            11            615           1309           2929
-------------------------------------------------------------------------------
```

My example code prints out the touch coordinates whenever the touch interrupt
fires. Not much more to do, since the CTP will be used within some application
which will implement more advanced features. The only reason to include this in
the bootloader code is to verify that the I2C connection works.

### LCD

The custom board is wired backwards, but we can verify that the code is correct
on the eval board. Besides forgetting to turn the `LCD_DISP` signal on, it all
worked. You set up a framebuffer somewhere (I just used the beginning of the DDR
memory), and write bits there, and magically the picture appears on the display.
For example, to display solid colors:

```c
volatile uint8_t *lcd_fb = (volatile uint8_t *)DRAM_MEM_BASE;

for (uint32_t y = 0; y < RK043FN48H_HEIGHT; y++) {
   for (uint32_t x = 0; x < RK043FN48H_WIDTH; x++) {
      uint32_t p    = (y * RK043FN48H_WIDTH + x) * 3U;
      lcd_fb[p + 0] = b; // blue
      lcd_fb[p + 1] = g; // green
      lcd_fb[p + 2] = r; // red
   }
}

/* make sure CPU writes reach DDR before LTDC reads */
L1C_CleanDCacheAll();
```

### 40-pin adapter

Making use of an adapter from the 40-pin FFC ribbon cable to jumper wires, we
can verify the signals also on the custom board. We see:

    R[3:7] signal when screen set to red, otherwise low
    G[3:7] signal when screen set to green, otherwise low
    B[3:7] signal when screen set to blue, otherwise low
    DCLK:  10 MHz
    DISP:  3.3V
    HSYNC: 17.6688 kHz, 92.76% duty cycle
    VSYNC: 61.779 Hz, 96.5% duty cycle
    DE:    16.7--16.9 kHz, ~84% duty cycle

We can see the brightness change when adjusting the duty cycle of the backlight.

Left ~2/3 of the screen shows white vertical stripes, the exact pattern of these
stripes depending on what "color" the screen is set to. The right ~1/3 of the
screen is black. This is to be expected, since we're using the same settings for
both displays. Here's the settings which work fine on the eval board:

```c
#define LCD_WIDTH  480U // LCD PIXEL WIDTH
#define LCD_HEIGHT 272U // LCD PIXEL HEIGHT
#define LCD_HSYNC  41U  // Horizontal synchronization
#define LCD_HBP    13U  // Horizontal back porch
#define LCD_HFP    32U  // Horizontal front porch
#define LCD_VSYNC  10U  // Vertical synchronization
#define LCD_VBP    2U   // Vertical back porch
#define LCD_VFP    2U   // Vertical front porch
```

The custom board uses a different display, so let's try different settings:

```c
#define LCD_WIDTH   800U
#define LCD_HEIGHT  480U
#define LCD_HSYNC   1U
#define LCD_HBP     8U
#define LCD_HFP     8U
#define LCD_VSYNC   1U
#define LCD_VBP     16U
#define LCD_VFP     16U
```

Now the screen is totally white, regardless of which color we send it. We notice
that the LCD datasheet specifies a minimum clock frequency of 10 MHz. Note that
on the STM32MP135, the LCD clock comes from `PLL4Q`. Raising the `DCLK` to 24
MHz, the screen works! We get to see all the colors. The `PLL4` configuration
that works for me is

```c
rcc_oscinitstructure.PLL4.PLLState  = RCC_PLL_ON;
rcc_oscinitstructure.PLL4.PLLSource = RCC_PLL4SOURCE_HSE;
rcc_oscinitstructure.PLL4.PLLM      = 2;
rcc_oscinitstructure.PLL4.PLLN      = 50;
rcc_oscinitstructure.PLL4.PLLP      = 12;
rcc_oscinitstructure.PLL4.PLLQ      = 25;
rcc_oscinitstructure.PLL4.PLLR      = 6;
rcc_oscinitstructure.PLL4.PLLRGE    = RCC_PLL4IFRANGE_1;
rcc_oscinitstructure.PLL4.PLLFRACV  = 0;
rcc_oscinitstructure.PLL4.PLLMODE   =
RCC_PLL_INTEGER;
```

### USB stops working

Unfortunately, just as the LCD becomes configured correctly and is able to
display the solid red, green, or blue colors, I noticed that the USB MSC
interface disappeared. If I comment out the LCD init code, so it does not run,
then USB comes back. How could they possibly interact?

Even more interesting, the USB stops working only if *both* of the following
functions are called: `lcd_backlight_init()`, which configures the backlight
brightness PWM, and `lcd_panel_init()`, which does panel timing and pin
configuration.

As it turns out, my 3.3V supply was set with a 0.1A current limit. Having
enabled so many peripherals, the current draw can be a bit higher now.
Increasing the current limit up to 0.2A, and everything works fine. In the
steady state, after init is complete, the board draws just under 0.1A from the
3.3V supply. (For the record, I'm drawing about 0.26A from the combined 1.25V /
1.35V supply.)

### Conclusion

Bringing up the LCD on the custom board ultimately came down to matching the
panel's exact timing and, critically, running the pixel clock within the range
specified by the datasheet. Once the LTDC geometry and `PLL4Q` frequency were
correct, the display worked immediately, confirming that the signal wiring and
framebuffer logic were sound.

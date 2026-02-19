---
title: PWM, LCD, and CTP from Kernel on STM32MP135
author: Jakob Kastelic
date: 20 Feb 2026
topic: Linux
description: >
   Learn how to configure PWM backlight control, LTDC display timings, and
   Goodix CTP touch events on the STM32MP135 using the Linux kernel. This guide
   covers DTS configuration, register comparisons between bare-metal and Linux,
   and driver verification using modetest and evtest.
---

![](../images/w.jpg)

*This is Part 10 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

### Backlight with GPIO

The display backlight is controlled via a single GPIO:

```
panel_backlight: panel-backlight {
	compatible = "gpio-backlight";
	gpios = <&gpiob 15 GPIO_ACTIVE_HIGH>;
	default-on;
	default-brightness-level = <1>;
	status = "okay";
};
```

With that, the backlight can be turned on and off as follows:

```
# echo 1 > /sys/class/backlight/panel-backlight/brightness
# echo 0 > /sys/class/backlight/panel-backlight/brightness
```

There's no tricks to this, so long as we make sure that the GPIO mentioned in
the DTS matches the one on the circuit schematic.

### Backlight and PWM

To control the brightness, we need to enable the PWM corresponding to this GPIO
pin and make sure the panel backlight is controlled by this PWM.

We have already implemented this [previously](lcd-ctp-on-baremetal-stm32mp135)
in bare-metal using the HAL driver. We can check the `TIM1`, `GPIOB`, and
`GPIOC` registers to see what is the effect of our configuration. In the
following table, "Before" and "After" are on bare metal before and after
configuring the PWM output.

| Register            | Address    | Before     | After      |
| ------------------- | ---------- | ---------- | ---------- |
| `TIM1_CR1`          | 0x44000000 | 0x00000000 | 0x00000001 |
| `TIM1_SR`           | 0x44000010 | 0x00000000 | 0x0003001f |
| `TIM1_CCMR2`        | 0x4400001c | 0x00000000 | 0x00000068 |
| `TIM1_CCER`         | 0x44000020 | 0x00000000 | 0x00000400 |
| `TIM1_CNT`          | 0x44000024 | 0x00000000 | 0x000001eb |
| `TIM1_PSC`          | 0x44000028 | 0x00000000 | 0x00000063 |
| `TIM1_ARR`          | 0x4400002c | 0x00000000 | 0x000003e7 |
| `TIM1_CCR3`         | 0x4400003c | 0x00000000 | 0x000001f4 |
| `TIM1_BDTR`         | 0x44000044 | 0x00000000 | 0x00008000 |
| `TIM1_DMAR`         | 0x4400004c | 0x00000000 | 0x00000001 |
| `TIM1_AF1`          | 0x44000060 | 0x00000000 | 0x00000001 |
| `TIM1_AF2`          | 0x44000064 | 0x00000000 | 0x00000001 |
| `TIM1_VERR`         | 0x440003f4 | 0x00000000 | 0x00000035 |
| `TIM1_IPIDR`        | 0x440003f8 | 0x00000000 | 0x00120002 |
| `TIM1_SIDR`         | 0x440003fc | 0x00000000 | 0xa3c5dd01 |
|                     |            |            |            |
| `GPIOB_MODER`       | 0x50003000 | 0xffbfffff | 0xbfbfffff |
| `GPIOB_AFR[1]`      | 0x50003024 | 0x0000b000 | 0x1000b000 |
|                     |            |            |            |
| `GPIOC_IDR`         | 0x50004010 | 0x00001f00 | 0x00000f00 |
|                     |            |            |            |
| `RCC_MP_APB2ENSETR` | 0x50000708 | 0x00000000 | 0x00000001 |
| `RCC_MP_APB2ENCLRR` | 0x5000070c | 0x00000000 | 0x00000001 |

The bare-metal bootloader configures the PWM for 3.0489 kHz operating with 50%
duty cycle.

Now let's configure the PWM in the DTS as follows:

```
		timers1: timer@44000000 {
			#address-cells = <1>;
			#size-cells = <0>;
			compatible = "st,stm32-timers";
			reg = <0x44000000 0x400>;
			interrupts = <GIC_SPI 25 IRQ_TYPE_LEVEL_HIGH>,
				     <GIC_SPI 26 IRQ_TYPE_LEVEL_HIGH>,
				     <GIC_SPI 27 IRQ_TYPE_LEVEL_HIGH>,
				     <GIC_SPI 28 IRQ_TYPE_LEVEL_HIGH>;
			interrupt-names = "brk", "up", "trg-com", "cc";
			clocks = <&rcc TIM1_K>;
			clock-names = "int";
			status = "okay";

			pwm1: pwm {
				compatible = "st,stm32-pwm";
				#pwm-cells = <3>;
				status = "okay";
				pinctrl-0 = <&pwm1_pins>;
				pinctrl-names = "default";
			};
```

When the PWM driver module is inserted, we can control the screen brightness as
follows:

```
modprobe pwm-stm32
cd /sys/class/pwm/pwmchip0
echo 2 > export
echo 1000000 > pwm2/period
echo 500000 > pwm2/duty_cycle
echo 1 > pwm2/enable
```

After that, the registers read:

| Register            | Value      |
| ------------------- |------------|
| `TIM1_CR1`          | 0x00000081 |
| `TIM1_SR`           | 0x0003001f |
| `TIM1_CCMR2`        | 0x00000068 |
| `TIM1_CCER`         | 0x00000500 |
| `TIM1_CNT`          | 0x00008a35 |
| `TIM1_PSC`          | 0x00000004 |
| `TIM1_ARR`          | 0x0000ee33 |
| `TIM1_CCR3`         | 0x0000771a |
| `TIM1_BDTR`         | 0x00008000 |
| `TIM1_DMAR`         | 0x00000081 |
| `TIM1_AF1`          | 0x00000001 |
| `TIM1_AF2`          | 0x00000001 |
| `TIM1_VERR`         | 0x00000035 |
| `TIM1_IPIDR`        | 0x00120002 |
| `TIM1_SIDR`         | 0xa3c5dd01 |
| `GPIOB_MODER`       | 0xbfbf7fff |
| `GPIOB_AFR[1]`      | 0x1000b000 |
| `GPIOC_IDR`         | 0x00001f00 |
| `RCC_MP_APB2ENSETR` | 0x00000001 |
| `RCC_MP_APB2ENCLRR` | 0x00000001 |

Finally, we need to make the panel backlight driver automatically talk to the
PWM driver so that the backlight can be adjusted as brightness and not as PWM.
We add the following to the DTS:

```
panel_backlight: panel-backlight {
	compatible = "pwm-backlight";
	pwms = <&pwm1 2 1000000 0>;
	brightness-levels = <0 16 32 64 128 255>;
	default-brightness-level = <4>;
	power-supply = <&v3v3_ao>;
	default-on;
	status = "okay";
};
```

The `panel_backlight` is referenced from `panel_rgb`, but still does not turn on
automatically. Apparently the `pwm-backlight` driver does not have a
DTS-controlled "power on" option, so we have to turn it on manually:

```
echo 0 > /sys/class/backlight/panel-backlight/bl_power
```

With that, the backlight brightness and power control work as they should via
the `/sys/class/backlight/` controls.

### Display image on LCD

Let's add two lines to the Buildroot configuration to make the `modetest`
command available:

```
BR2_PACKAGE_LIBDRM=y
BR2_PACKAGE_LIBDRM_INSTALL_TESTS=y
```

I am using the Rocktech `RK050HR01-CT` LCD display and the following DTS
fragment:

```
panel_rgb: panel-rgb {
	compatible = "rocktech,rk050hr18-ctg", "panel-dpi";
	enable-gpios = <&gpiog 7 GPIO_ACTIVE_HIGH>;
	backlight = <&panel_backlight>;
	power-supply = <&v3v3_ao>;
	data-mapping = "rgb565";
	status = "okay";

	width-mm = <108>;
	height-mm = <65>;

	port {
		panel_in_rgb: endpoint {
			remote-endpoint = <&ltdc_out_rgb>;
		};
	};

	panel-timing {
		clock-frequency = <24000000>;
		hactive = <800>;
		vactive = <480>;
		hsync-len = <4>;
		hfront-porch = <8>;
		hback-porch = <8>;
		vsync-len = <4>;
		vfront-porch = <16>;
		vback-porch = <16>;
		hsync-active = <0>;
		vsync-active = <0>;
		de-active = <1>;
		pixelclk-active = <1>;
	};
};
```

Run just `modetest` to determine the numbers (CRTC 41, connector 32) of the
display:

```
# modetest | head
trying to open device '/dev/dri/card0'... done
opened device `STMicroelectronics SoC DRM` on driver `stm` (version 1.0.0 at 20170330)
Encoders:
id      crtc    type    possible crtcs  possible clones
31      41      DPI     0x00000001      0x00000001

Connectors:
id      encoder status          name            size (mm)       modes   encoders
32      31      connected       DPI-1           108x65          1       31
```

Modetest is now able to display a test pattern on the LCD with the following
command:

```
# modetest -M stm -s 32@41:800x480
opened device `STMicroelectronics SoC DRM` on driver `stm` (version 1.0.0 at 20170330)
setting mode 800x480-56.72Hz on connectors 32, crtc 41
```

### Capacitive touchpad (CTP)

Adjust the pin configuration in the DTS according to the way the PCB is wired.
For completeness, here's mine:

```
i2c5: i2c@4c006000 {
	compatible = "st,stm32mp13-i2c";
	reg = <0x4c006000 0x400>;
	interrupt-names = "event", "error";
	interrupts = <GIC_SPI 114 IRQ_TYPE_LEVEL_HIGH>,
		     <GIC_SPI 115 IRQ_TYPE_LEVEL_HIGH>;
	clocks = <&rcc I2C5_K>;
	resets = <&rcc I2C5_R>;
	#address-cells = <1>;
	#size-cells = <0>;
	st,syscfg-fmp = <&syscfg 0x4 0x10>;
	i2c-analog-filter;
	feature-domains = <&etzpc STM32MP1_ETZPC_I2C5_ID>;
	pinctrl-names = "default", "sleep";
	pinctrl-0 = <&i2c5_pins_a>;
	pinctrl-1 = <&i2c5_sleep_pins_a>;
	i2c-scl-rising-time-ns = <170>;
	i2c-scl-falling-time-ns = <5>;
	clock-frequency = <400000>;
	status = "okay";

	goodix: goodix-ts@5d {
		compatible = "goodix,gt911";
		reg = <0x5d>;
		pinctrl-names = "default";
		pinctrl-0 = <&goodix_pins_a>;
		interrupt-parent = <&gpioh>;
		interrupts = <12 IRQ_TYPE_EDGE_FALLING>;
		reset-gpios = <&gpiob 7 GPIO_ACTIVE_LOW>;
		AVDD28-supply = <&v3v3_ao>;
		VDDIO-supply = <&v3v3_ao>;
		touchscreen-size-x = <800>;
		touchscreen-size-y = <480>;
		status = "okay" ;
	};
};
```

The `I2C5` pins are set as follows:

```
i2c5_pins_a: i2c5-0 {
	pins {
		pinmux = <STM32_PINMUX('H', 13, AF4)>, /* I2C5_SCL */
			 <STM32_PINMUX('F', 3, AF4)>; /* I2C5_SDA */
		bias-disable;
		drive-open-drain;
		slew-rate = <0>;
	};
};
```

Now verify that the CTP driver has been initialized correctly:

```
# dmesg | grep -i good
[    1.071181] Goodix-TS 0-005d: ID 911, version: 1060
[    1.074418] input: Goodix Capacitive TouchScreen as /devices/platform/soc/5c007000.etzpc/4c006000.i2c/i2c-0/0-005d/input/input0
```

Let's use `evtest` (add `BR2_PACKAGE_EVTEST=y` in Buildroot) to verify that
we can receive touchpad events. With `evtest` running, we can touch the
touchpad and see that the events are streaming in:

```
# evtest
Event: time 54.972748, -------------- SYN_REPORT ------------
Event: time 54.976560, type 3 (EV_ABS), code 53 (ABS_MT_POSITION_X), value 575
Event: time 54.976560, type 3 (EV_ABS), code 54 (ABS_MT_POSITION_Y), value 236
Event: time 54.976560, type 3 (EV_ABS), code 0 (ABS_X), value 575
Event: time 54.976560, type 3 (EV_ABS), code 1 (ABS_Y), value 236
```

!include[articles/linux-on-stm32mp135.html]

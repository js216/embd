---
title: PWM, LCD, and CTP from Kernel on STM32MP135
author: Jakob Kastelic
date:
topic: Linux
description: >
---

![](../images/w.jpg)

*This is Part 10 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

### Backlight PWM

The display backlight is controlled via a single GPIO and so it can be turned on
and off as follows:

```
# echo 1 > /sys/class/backlight/panel-backlight/brightness
# echo 0 > /sys/class/backlight/panel-backlight/brightness
```

To control the brightness, we need to enable the PWM corresponding to this GPIO
pin and make sure the panel backlight is controlled by this PWM.

!include[articles/linux-on-stm32mp135.html]


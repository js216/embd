---
title: Linux Late Boot Debugging on STM32MP135
author: Jakob Kastelic
date:
topic: Linux
description: >
---

![](../images/rain.jpg)


*This is Part 8 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

In this article we will proceed with debugging the late boot of Linux on a 
[custom board](https://github.com/js216/stm32mp135_test_board) populated with
the STM32MP135 SoC. The starting point will be the build that runs on the
evalution board as described in the [previous
article](https://embd.cc/build-linux-for-stm32mp135-in-under-50-lines-of-makefile).

### Pinout, DTS simplification

First, 

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><a href="stm32mp135-linux-cubeprog">2. STM32MP135 Flashing via USB with STM32CubeProg</a></li>
  <li><a href="stm32mp135-without-u-boot">3. STM32MP135 Without U-Boot (TF-A Falcon Mode)</a></li>
  <li><a href="linux-tfa-bl33-qemu">4. Linux as TF-A BL33 on Qemu (No U-Boot)</a></li>
  <li><a href="stm32mp135-without-optee">5. STM32MP135 Without OP-TEE</a></li>
  <li><a href="linux-bringup-on-custom-stm32mp135-board">6. Linux Bring-Up on a Custom STM32MP135 Board</a></li>
  <li><a href="build-linux-for-stm32mp135-in-under-50-lines-of-makefile">7. Build Linux for STM32MP135 in under 50 Lines of Makefile</a></li>
  <li><em>8. This article</em></li>
</ul>
</div>

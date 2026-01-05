---
title: Linux Late Boot Debugging on STM32MP135
author: Jakob Kastelic
date:
topic: Linux
description: >
---

![](../images/vt.jpg)

*This is Part 7 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

In the [previous
article](https://embd.cc/linux-bringup-on-custom-stm32mp135-board) we took a
[custom STM32MP135 board](https://github.com/js216/stm32mp135_test_board) from a
simple LED blink to passing the kernel early boot stage, printing the "Booting
Linux" message. Now, it's time to finish the kernel initialization all the way
up to running our first process: the `init` process.

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><a href="stm32mp135-linux-cubeprog">2. STM32MP135 Flashing via USB with STM32CubeProg</a></li>
  <li><a href="stm32mp135-without-u-boot">3. STM32MP135 Without U-Boot (TF-A Falcon Mode)</a></li>
  <li><a href="linux-tfa-bl33-qemu">4. Linux as TF-A BL33 on Qemu (No U-Boot)</a></li>
  <li><a href="stm32mp135-without-optee">5. STM32MP135 Without OP-TEE</a></li>
  <li><a href="linux-bringup-on-custom-stm32mp135-board">6. Linux Bring-Up on a Custom STM32MP135 Board</a></li>
  <li><em>7. This article</em></li>
</ul>
</div>

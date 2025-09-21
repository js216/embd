---
title: STM32MP135 Without OP-TEE
author: Jakob Kastelic
date: 17 Sep 2025
topic: Linux
description: >
---

![](../images/pdp1120.jpg)

*This is Part 5 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

Arm chips, such as the STM32MP135, implementing the TrustZone extension divide
the execution into two worlds: a normal, non-secure world inhabited by the
application operating system, and a secure world serviced by a secure OS such as
OP-TEE. The ST wiki[^wiki] assures us that OP-TEE is required on all STM32MP1
produces "due to the hardware architecture". It is our purpose in this article
to show that that is not the case: *OP-TEE is in fact entirely optional*.

The only mechanism to enter the "secure world" is via the `SMC` instruction
(secure monitor call). This is analogous to how user-space applications invoke
kernel system calls via the `SVC` (supervisor call) instruction to enter
privileged mode. So long as the kernel does not issue the `SMC` instruction, the
secure world need never be entered. Thus, we can restate our purpose as removing
all secure monitor calls from the kernel configuration.

The tutorial in the present article is somewhat more involved than the preceding
ones in the series. For this reason I offer the ["Quick Start"](quick-start)
version, where the required modifications to kernel drivers are offered as
patches to apply to a particular version. For those interested, the ["Long
Version"](#long-version) fills in the details. As in other articles, we conclude
with a brief discussion.

### Quick Start

TODO: copy from the `stm32mp135_simple` README.

### Long Version

### Discussion

STM32MP135 presents a SDK that is, to my mind, overly complicated. To port the
setup from the evaluation board to a new board requires the understanding of
three bootloaders (ROM, TF-A, U-Boot), two operating systems (Linux, OP-TEE),
and a stack of other software. Most of this arose out of a desire to simplify
the process; for example, U-Boot aims to be the one universal bootloader in
embedded systems, so as to not have to learn a new one for each platform. But
the ironic end result is that after piling on so many "simplifications", the net
result is more complicated than having none of them.

The claim[^wiki] that OP-TEE is mandatory probably arises out of a desire to
avoid having to maintain two separate development branches, a secure and a
non-secure one. This must be even more so considering the need to support the
GUI-based configuration utilities (STM32Cube), or the Yocto-based distributions.

However, as a developer I would prefer to be offered a minimal working
configuration where OP-TEE would be an "opt-in" configuration, rather than
tightly bundling it in with the kernel. Many (most?) applications do not call
for secure-world services; these get included only due to the large cost of
*removing* it from the provided SDKs.

### Upstreaming Status

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><a href="stm32mp135-linux-cubeprog">2. STM32MP135 Flashing via USB with STM32CubeProg</a></li>
  <li><a href="stm32mp135-without-u-boot">3. STM32MP135 Without U-Boot (TF-A Falcon Mode)</a></li>
  <li><a href="linux-tfa-bl33-qemu">4. Linux as TF-A BL33 on Qemu (No U-Boot)</a></li>
  <li><em>5. This article</em></li>
</ul>
</div>

[^wiki]: ST wiki: [How to disable OP-TEE secure
    services](https://wiki.st.com/stm32mpu/wiki/How_to_disable_OP-TEE_secure_services)

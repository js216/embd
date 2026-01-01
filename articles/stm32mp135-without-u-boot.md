---
title: STM32MP135 Without U-Boot (TF-A Falcon Mode)
author: Jakob Kastelic
date: 11 Sep 2025
modified: 20 Sep 2025
topic: Linux
description: >
   Learn how to boot the STM32MP1 Linux kernel directly with Arm Trusted
   Firmware (TF-A) in Falcon mode, bypassing U-Boot. Step-by-step instructions
   to do it manually or with Buildroot integration.
---

![](../images/red.jpg)

*This is Part 3 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

In this article, we use Arm Trusted Firmware (TF-A) to load the Linux kernel
directly, without using U-Boot.[^st] I have seen the idea of omitting the
Secondary Program Loader (SPL) referred to as "falcon mode", since it makes the
boot process (slightly) faster. However, I am primarily interested in it as a
way of reducing overall complexity of the software stack.

In this article, we will implement this in two ways. First, we modify the files
as needed manually. At the end of the article, we provide an alternative method:
directly integrate the changes into Buildroot.

### Prerequisites

To get started, make sure to have built the default configuration as per the
[first article](stm32mp135-linux-default-buildroot) of this series. Very
briefly, this entails cloning the official Buildroot repository, selecting a
defconfig, and compiling:

```
$ git clone https://gitlab.com/buildroot.org/buildroot.git --depth=1
$ cd buildroot
$ make stm32mp135f_dk_defconfig
$ make menuconfig # add the STM32MP_USB_PROGRAMMER=1 flag to TF-A build
$ make
```

It is also recommended to learn how to flash the SD card without removing it via
a USB connection, as explained in the [second
article](stm32mp135-linux-cubeprog).

### Tutorial

The procedure is pretty simple. All we need to do is to modify some files,
adjust some build parameters, recompile, and the new SD card image is ready to
test.

1. Before making any modifications, make a backup of the file containing U-Boot.

   ```
   $ cd output/images
   $ cp fip.bin fip_uboot.bin
   ```

   Double check that the above `fip.bin` was built using the additional ATF
   build variable `STM32MP_USB_PROGRAMMER=1`, otherwise USB flashing will not
   work!

   Open `flash.tsv`, and update the `fip.bin` to `fip_uboot.bin` there as well.

   (Despite removing U-Boot from the boot process, we are still going to use it
   to flash the SD card image via USB using the STM32CubeProg.)

2. Two TF-A files need to be modified, so navigate to the TF-A build directory:

   ```
   $ cd ../build/arm-trusted-firmware-lts-v2.10.5
   ```

   Since the kernel is much bigger than U-Boot, it takes longer to load. We need
   to adjust the SD card reading timeout. In `drivers/st/mmc/stm32_sdmmc2.c`,
   find the line

   ```
   timeout = timeout_init_us(TIMEOUT_US_1_S);
   ```

   and replace it with

   ```
   timeout = timeout_init_us(TIMEOUT_US_1_S * 5);
   ```

   Next, we would like to load the kernel deep enough into the memory space so
   that relocation of the compressed image is not necessary. In file
   `plat/st/stm32mp1/stm32mp1_def.h`, find the line

   ```
   #define STM32MP_BL33_BASE              STM32MP_DDR_BASE
   ```

   and replace it with

   ```
   #define STM32MP_BL33_BASE              (STM32MP_DDR_BASE + U(0x2008000))
   ```

   Finally, in order to allow loading such a big `BL33` as the kernel image, we
   adjust the max size. In the same file, find the line

   ```
   #define STM32MP_BL33_MAX_SIZE          U(0x400000)
   ```

   and replace it with

   ```
   #define STM32MP_BL33_MAX_SIZE          U(0x3FF8000)
   ```

3. Next, we need to modify a couple build parameters. Open the `make menuconfig`
   and navigate to `Bootloaders ---> ARM Trusted Firmware (ATF)`.

   - Under `BL33`, change from U-Boot to None.

   - Under `Additional ATF build variables`, make sure that U-Boot is not
     present and add the following key-value pairs:

     ```
     BL33=$(BINARIES_DIR)/zImage BL33_CFG=$(BINARIES_DIR)/stm32mp135f-dk.dtb
     ```

   Select "Ok" and "Esc" out of the menus, making sure to save the new
   configuration.

   Next, open the file
   `board/stmicroelectronics/common/stm32mp1xx/genimage.cfg.template` and
   increase the size of the `fip` partition, for example:

   ```
   partition fip {
   	image = "fip.bin"
   	size = 8M
   }
   ```

   Finally, since U-Boot will no longer be around to pass the Linux command line
   arguments, we can instead pass them through the device tree source. Open the
   file `output/build/linux-6.12.22/arch/arm/boot/dts/st/stm32mp135f-dk.dts`
   (you may have a different Linux version, just modify the path as appropriate)
   and add the `bootargs` into the `chosen` section, as follows:

   ```
   chosen {
   	stdout-path = "serial0:115200n8";
   	bootargs = "root=/dev/mmcblk0p4 rootwait";
   };
   ```

4. Now we can rebuild the TF-A, the device tree blob, and regenerate the SD card
   image. Thanks to the magic of Buildroot, all it takes is:

   ```
   $ make linux-rebuild
   $ make arm-trusted-firmware-rebuild
   $ make
   ```

   Keep in mind that rebuilding TF-A is needed any time the Linux kernel or DTS
   or TF-A sources change, since the kernel gets packaged into the `fip` by the
   TF-A build process. In this case, the first `make` rebuilds the DTB, the
   second packages it in the `fip`, and the third makes sure it gets into the SD
   card.

5. Set DIP switch to serial boot (press in the upper all of all rockers) and
   flash to SD card:

   ```
   $ sudo ~/cube/bin/STM32_Programmer_CLI -c port=usb1 -w output/images/flash.tsv
   ```

   Then reconfigure the DIP switches for SD card boot (press the bottom side of
   the second rocker switch from the left), and press the black reboot button.

If you watch the serial monitor carefully, you will notice that we transition
from TF-A directly to OP-TEE and Linux. Success! No U-Boot in the boot process:

```
NOTICE:  Model: STMicroelectronics STM32MP135F-DK Discovery Board
NOTICE:  Board: MB1635 Var1.0 Rev.E-02
NOTICE:  BL2: v2.10.5(release):lts-v2.10.5
NOTICE:  BL2: Built : 20:58:52, Sep 10 2025
NOTICE:  BL2: Booting BL32
I/TC: Early console on UART#4
I/TC: 
I/TC: Embedded DTB found
I/TC: OP-TEE version: Unknown_4.3 (gcc version 14.3.0 (Buildroot 2025.08-rc3-87-gbbb0164de0)) #1 Thu Sep  4 03:06:46 UTC 2025 arm
...
(more OP-TEE messages here)
...
[    0.000000] Booting Linux on physical CPU 0x0
[    0.000000] Linux version 6.12.22 (jk@Lutien) (arm-buildroot-linux-gnueabihf-gcc.br_real (Buildroot 2025.08-rc3-87-gbbb0164de0) 14.3.0, GNU ld (GNU Binutils) 2.43.1) #1 SMP PREEMPT Wed Sep  3 20:23:46 PDT 2025
[    0.000000] CPU: ARMv7 Processor [410fc075] revision 5 (ARMv7), cr=10c5387d
```

### Buildroot integration

Instead of following the above instructions, we can automate the build process
by integrating it into Buildroot. To this end, I provide the GitHub repository
[`stm32mp135_simple`](https://github.com/js216/stm32mp135_simple) that can be
used as follows.

Clone the Buildroot repository. To make the procedure reproducible, let's start
from a fixed commit (latest at the time of this writing):

```
$ git clone https://gitlab.com/buildroot.org/buildroot.git
$ cd buildroot
$ git checkout 5b6b80bfc5237ab4f4e35c081fdac1376efdd396
```

Obtain this repository with the patches we need. Copy the defconfig and the
board-specific files into the Buildroot tree.

```
$ git clone git@github.com:js216/stm32mp135_simple.git
$ cd buildroot # NOT stm32mp135_simple
$ git apply ../stm32mp135_simple/patches/add_falcon.patch
$ git apply ../stm32mp135_simple/patches/increase_fip.patch
$ cp ../configs/stm32mp135_simple/stm32mp135f_dk_falcon_defconfig configs
$ cp -r ../board/stm32mp135_simple/stm32mp135f-dk-falcon board/stmicroelectronics
```

Build as usual, but using the new defconfig:

```
$ make stm32mp135f_dk_falcon_defconfig
$ make
```

Flash to the SD card and boot into the new system. You should reach the login
prompt exactly as in the default configuration---but without involving U-Boot

### Discussion

To port the "default" STM32MP135 setup[^def] to a new board design, one is
expected to be comfortable writing and modifying the drivers and device tree
sources that work with

- Arm Trusted Firmware (Primary Program Loader)
- OP-TEE (Trusted Execution Environment)
- U-Boot (Secondary Program Loader)
- Linux kernel
- Buildroot, or, worse, Yocto

That is a tall order for a new embedded developer trying to get started
integrating Linux in their products. To make things worse, there is at present
almost no literature to be found suggesting that a simpler, saner method exists.
Certainly the chip vendors themselves do not encourage it.[^no]

With this article, we have began chipping away at the unnecessary complexity. We
have removed U-Boot from the boot chain. (We still use it for copying the SD
card image via USB. One thing at a time!) Since our goal is to *run Linux*, the
list above gives us a blueprint for the work that remains to be done: get rid of
everything that is *not Linux*.

The software that you do not run is software you do not have to understand,
test, debug, maintain, and be responsible for when it breaks down ten years down
the line in some deeply embedded application, perhaps in outer space.

### Upstreaming Status

19/12/2024: original Buildroot mailing list submission [(1/1)](https://lists.buildroot.org/pipermail/buildroot/2024-December/769250.html)

16/12/2025: response by Arnout Vandecappelle [(link)](https://lists.buildroot.org/pipermail/buildroot/2025-May/778563.html)

17/9/2025: amended submission [(v2 0/2, ](https://lists.buildroot.org/pipermail/buildroot/2025-September/786595.html)
[1/2, ](https://lists.buildroot.org/pipermail/buildroot/2025-September/786596.html)
[2/2)](https://lists.buildroot.org/pipermail/buildroot/2025-September/786597.html)

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><a href="stm32mp135-linux-cubeprog">2. STM32MP135 Flashing via USB with STM32CubeProg</a></li>
  <li><em>3. This article</em></li>
  <li><a href="linux-tfa-bl33-qemu">4. Linux as TF-A BL33 on Qemu (No U-Boot)</a></li>
  <li><a href="stm32mp135-without-optee">5. STM32MP135 Without OP-TEE</a></li>
  <li><a href="linux-bringup-on-custom-stm32mp135-board">6. Linux Bring-Up on a Custom STM32MP135 Board</a></li>
</ul>
</div>

[^def]: See the ST Wiki, [OpenSTLinux
    distribution](https://wiki.st.com/stm32mpu/wiki/OpenSTLinux_distribution)
    (cited 09/11/2025)

[^st]: This approach is inspired by the ST wiki article [How to optimize the
    boot time](https://wiki.st.com/stm32mpu/wiki/How_to_optimize_the_boot_time),
    under "Optimizing boot-time by removing U-Boot". (cited 09/11/2025)

[^no]: As per the [ST
    forum,](https://community.st.com/t5/stm32-mpus-embedded-software-and/start-linux-kernel-from-tf-a/td-p/91321)
    (cited 09/11/2025) the approach outlined in the present article is
    officially *not* supported by ST.

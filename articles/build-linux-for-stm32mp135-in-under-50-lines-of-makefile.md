---
title: Build Linux for STM32MP135 in under 50 Lines of Makefile
author: Jakob Kastelic
date: 6 Jan 2026
modified: 9 Jan 2026
topic: Linux
description: >
   Step-by-step guide to build a minimal Linux root filesystem for the
   STM32MP135 including kernel and DTB build, init, and SD image setup.
---

![](../images/rain.jpg)

*This is Part 7 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

In the [previous
article](https://embd.cc/linux-bringup-on-custom-stm32mp135-board) we took a
[custom STM32MP135 board](https://github.com/js216/stm32mp135_test_board) from a
simple LED blink to passing the kernel early boot stage, printing the "Booting
Linux" message. Now, it's time to finish the kernel initialization all the way
up to running our first process: the `init` process.

We'll do it in two steps. First, we make it run on the official [evaluation
board](https://www.st.com/en/evaluation-tools/stm32mp135f-dk.html) for the SoC.
In a future article, we will consider what needs to be changed in order to make
this work on a [custom board](https://github.com/js216/stm32mp135_test_board).

### Boot Linux on eval board

First, we need to obtain and build the bootloader. Note that we need to enable
the STPMIC1, since it is used on the eval board:

```sh
git clone git@github.com:js216/stm32mp135-bootloader.git
cd stm32mp135-bootloader
make CFLAGS_EXTRA=-DUSE_STPMIC1x=1
cd ..
```

Next, we obtain the Linux kernel from the ST repository (contains a few
non-standard ST-provided drivers):

```sh
git clone https://github.com/STMicroelectronics/linux.git
git checkout v6.1-stm32mp-r1.1
```

Let's apply some patches (mainly to allow non-secure boot without
[U-Boot](https://embd.cc/stm32mp135-without-u-boot),
[OPTEE](https://embd.cc/stm32mp135-without-optee), or
[TF-A](https://embd.cc/linux-bringup-on-custom-stm32mp135-board)), and copy over
the Device Tree Source (DTS), and the kernel configuration:

```sh
git clone git@github.com:js216/stm32mp135_test_board.git

cd linux
git linux apply ../configs/evb/patches/linux/*.patch
cd ..

cp config/evb/linux.config linux/.config
cp config/evb/board.dts linux/arch/arm/boot/dts/
```

Now we can build the Device Tree Blob (DTB) and the kernel itself:

```sh
cd linux
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- board.dtb
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- zImage
cd ..
```

Next, we need an init script. (Of course, you can also run the kernel without
it, but be prepared for a kernel panic at the end of the boot, telling you the
init is missing.) An init script can be essentially any program, even a "Hello,
world!", but if the init program quits, the kernel enters a panic again.

I asked AI to write a minimal init, without any C standard library dependencies
(find the result
[here](https://github.com/js216/stm32mp135_test_board/blob/main/configs/evb/init.c)).
Let's compile it, making sure to tell the compiler to not link any extra code
with it:

```sh
arm-linux-gnueabihf-gcc -Os -nostdlib -static -fno-builtin \
   -Wl,--gc-sections config/init.c -o build/init
```

Now that we have an init program, we need a root filesystem to put it on:

```sh
mkdir -p build/rootfs.dir/sbin
cp build/init build/rootfs.dir/sbin/init
dd if=/dev/zero of=build/rootfs bs=1M count=10
mke2fs -t ext4 -F -d build/rootfs.dir build/rootfs
```

Finally, we collect all the pieces together with a simple Python script included
in the bootloader distribution:

```sh
python3 bootloader/scripts/sdimage.py build/sdcard.img \
   bootloader/build/main.stm32 \
   linux/arch/arm/boot/dts/board.dtb \
   linux/arch/arm/boot/zImage \
   --partition build/rootfs
```

Write this image to the SD card and start the system, and prepare to be greeted
by the very useless shell implemented in the minimal
[init program](https://github.com/js216/stm32mp135_test_board/blob/main/configs/evb/init.c)):

```sh
[    1.940577] Run /sbin/init as init process
Hello, world!
$ ls
ls: command not found
$ Hey!
Hey!: command not found
```

That's it!

### The Makefile

Here's the full 49 lines:

```makefile
CONFIG_DIR := configs/custom
CROSS_COMPILE = arm-linux-gnueabihf-
LINUX_OPTS = ARCH=arm CROSS_COMPILE=$(CROSS_COMPILE)

all: boot config dtb kernel init root sd

boot:
	$(MAKE) -C bootloader -j$(shell nproc) CFLAGS_EXTRA=-DUSE_STPMIC1x=1

patch:
	for p in $(CONFIG_DIR)/patches/linux/*.patch; do \
		if git -C linux apply --check ../$$p; then \
			git -C linux apply ../$$p; \
		fi \
	done

config:
	cp $(CONFIG_DIR)/linux.config linux/.config

dtb:
	cp $(CONFIG_DIR)/board.dts linux/arch/arm/boot/dts/
	$(MAKE) -C linux $(LINUX_OPTS) board.dtb

kernel:
	$(MAKE) -C linux $(LINUX_OPTS) -j$(shell nproc) zImage

init:
	mkdir -p build
	$(CROSS_COMPILE)gcc -Os -nostdlib -static -fno-builtin \
		-Wl,--gc-sections $(CONFIG_DIR)/init.c -o build/init

root:
	rm -rf build/rootfs.dir
	mkdir -p build/rootfs.dir/sbin
	cp build/init build/rootfs.dir/sbin/init
	dd if=/dev/zero of=build/rootfs bs=1M count=10
	mke2fs -t ext4 -F -d build/rootfs.dir build/rootfs

sd:
	python3 bootloader/scripts/sdimage.py build/sdcard.img \
		bootloader/build/main.stm32
		linux/arch/arm/boot/dts/board.dtb \
		linux/arch/arm/boot/zImage \
		--partition build/rootfs

clean:
	$(MAKE) -C linux $(LINUX_OPTS) clean
	$(MAKE) -C bootloader clean
	rm -rf build
```

### Discussion

The Makefile that reproduces the steps above is less than 50 lines long and
creates a minimal, bootable SD card image in a very straightforward way: build
the kernel, the DTB, and a userspace program (init), and package everything into
a single SD card image. The next simplest thing to accomplish the same result is
the "lightweight" [Buildroot](https://buildroot.org/), which needs nearly 100k
lines of make. What could possibly be happening in all that code!?

The sentiment
has been captured by the Reddit user `triffid_hunter` in a recent
[comment](https://www.reddit.com/r/embedded/comments/1pqg3ty/embedded_systems_are_really_hard_to_learn):

> I find that the hardest part about embedded is the horrendously obtuse
> manufacturer-provided toolchains.
> 
> If I can find a way to ditch them and switch to gcc+Makefile+basic C
> libraries, that's the first thing I'll do.

Buildroot is a relatively clean solution to the problem of supporting a huge
number of packages on a wide variety of boards, but most of that complexity is
not needed for a single-board project. (Yocto is an even more complex system,
which we won't cover here---its simplicity for the user comes at the cost of
massive implementation complexity.) From my point of view, all these hundreds of
thousands of lines of code are simply "accidental complexity" as articulated by
ESR:

>  Accidental complexity happens because someone didn't find the simplest way to
>  implement a specified set of features. Accidental complexity can be
>  eliminated by good design, or good redesign.[^acc]

The "root cause" of the highly complex toolchains has been identified by
Anna-Lena Marx (inovex GmbH) in a talk[^talk] last year: the goals of SoC
vendors and product manufacturers are not aligned. The SoC vendor wants to show
off all the features of their devices, and they want a Board Support Package
(BSP) that supports several, even all, of the devices in their portfolio. They
want a "turnkey solution" that allows an engineer to go from nothing to a
full-featured demo in ten minutes.

In contrast, a product manufacturer who wants to use embedded Linux in their
application-specific product wants a minimal software stack, as close as
possible to the upstream stable versions in order to be stable, secure, &
maintainable. It's the difference between merely using the system, and owning
it.

From the product side, I can concur that the SoC BSPs can be a nightmare to work
with! They are simple to get started with, being a packaged "turnkey solution",
but require a massive amount of work to unpeel all the abstraction layers that
the SoC vendor found necessary to support their entire ecosystem of devices. ST,
being perhaps the most "hacker friendly" vendor, likely has the cleanest, most
"upstreamed" offering, and still there's loads of cruft that must be removed
before getting to something workable.

I would like a world where SoC vendors ship their product with simple,
straightforward *documentation*, rather than monolithic code examples. Give me
the smallest possible building blocks and tell me how to connect them together
to accomplish something, rather than give the huge all-in-one example code that
can take many tens of hours to pull apart and reassemble. In other words, I
expect a Linux distribution to approach to the ideal of [Unix
philosophy](https://embd.cc/unix-contributions) much more closely, all the more
so in an embedded, resource-constrained, highly reliable application.

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

[^talk]: Anna-Lena Marx (inovex GmbH): *Your Vendor's BSP Is Probably Not Built
  for Product Longevity*. Yocto Project Summit, December 2025. Quoted on
  1/5/2026 from [this URL](https://marx.engineer/content/talks/2025_Yocto-Summit_Your-Vendors-BSP-Is-Probably-Not-Built-For-Product-Longevity.pdf)

[^acc]: Eric S. Raymond: The Art of Unix Programming. Addison-Wesley, 2004.

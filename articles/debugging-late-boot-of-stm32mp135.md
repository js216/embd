---
title: Debugging the Late Boot of STM32MP135
author: Jakob Kastelic
date: 19 Feb 2026
topic: Linux
description: >
   Bringing a custom STM32MP135 board through late Linux boot: fixing the device
   tree, enabling BusyBox with Buildroot, deploying DTBs over SSH, and
   implementing a minimal RCC-based restart handler.
---

![](../images/ah.jpg)

*This is Part 9 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

In this article we will take the [custom STM32MP135
board](https://github.com/js216/stm32mp135_test_board) through the end of the
Linux boot process. In a [previous
article](linux-bringup-on-custom-stm32mp135-board) we saw the "Booting Linux"
message for the first time; now it's time to run our own programs *under* the
OS and configure some of the devices.

### Device Tree Source (DTS)

Having fixed the
[DDR](https://embd.cc/debugging-stm32mp135-kernel-decompression) issues
(swizzling gone wrong) in a [new
revision](https://github.com/js216/stm32mp135_test_board/tree/main/kicad/Rev_B_26jan26)
of the board, wrote the [50
lines](https://embd.cc/build-linux-for-stm32mp135-in-under-50-lines-of-makefile)
of Makefile needed to build the bootloader and kernel and the root file system,
it only remains to fix up the device tree source.

The STMicroelectronics kernel repository contains a comprehensive
[DTS](https://github.com/STMicroelectronics/linux/blob/v6.6-stm32mp/arch/arm/boot/dts/st/stm32mp135f-dk.dts)
that works on the [evaluation
board](https://www.st.com/en/evaluation-tools/stm32mp135f-dk.html), together
with the [pin assignment
file](https://github.com/STMicroelectronics/linux/blob/v6.6-stm32mp/arch/arm/boot/dts/st/stm32mp13-pinctrl.dtsi).
It's an excellent starting point since only a few lines need to be adjusted to
accommodate the slightly different pinout used on the larger BGA package (0.8mm)
used on my custom board. See the DTS files
[here](https://github.com/js216/stm32mp135_test_board/tree/main/dtbs) for the
final result.

The board started to boot but did not find the root filesystem on the SD card,
even though the bootloader successfully copied the kernel from the card into
DDR. As it turns out, the board miswired the "card detect" pin, so we have to
ignore it in the DTS:

```c

&sdmmc1 {
	...
	broken-cd;
	...
}
```

### Init and BusyBox

With the fixed DTS, the boot process finishes with this:

```
[    1.332380] Run /sbin/init as init process
Hello, world!
$ hello
hello: command not found
```

Naturally the `hello` command does not exist, nor any other. Mind you, my
[`init`](https://github.com/js216/stm32mp135-bootloader/blob/9cc63614864888377c57de91ef8eb8337c215348/test/linux/init.c)
(PID = 1) program is essentially just "Hello, world!" and entirely vibecoded at
that.

The next step is to have a more useful set of tools installed on the target,
such as BusyBox. We can easily enough build it as follows:

    git clone git://busybox.net/busybox.git
    cd busybox
    make menuconfig # select static build
    make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-

But when we copy the resulting binary as `init`, we discover that it would
really like to have a proper `inittab`, and a couple device files. With the
"Hello, world!" `init`, we created the root filesystem as follows:

```makefile
root:
	mkdir -p build/rootfs.dir/sbin
	cp build/init build/rootfs.dir/sbin/init
	dd if=/dev/zero of=build/rootfs bs=1M count=10
	mke2fs -t ext4 -F -d build/rootfs.dir build/rootfs
```

But to add the device files we need to work as root or do something more clever.

### Buildroot

It's reasonable to yield to the temptation of build automation. (Why the
hesitation? Package management and build systems inevitably result in a massive
increase in complexity of a system, because it becomes easy to add more stuff
into a build.)

Obtain Buildroot:

    git clone https://gitlab.com/buildroot.org/buildroot.git

Create a very minimal `buildroot/.config` such as the following:

    BR2_arm=y
    BR2_cortex_a7=y
    BR2_TOOLCHAIN_BUILDROOT_UCLIBC=y
    BR2_PACKAGE_HOST_LINUX_HEADERS_CUSTOM_6_1=y
    BR2_CCACHE=y
    BR2_CCACHE_DIR="/tmp/buildroot-ccache"
    BR2_ENABLE_DEBUG=y
    BR2_SHARED_STATIC_LIBS=y
    BR2_ROOTFS_DEVICE_CREATION_STATIC=y
    BR2_TARGET_GENERIC_ROOT_PASSWD="root"
    BR2_ROOTFS_OVERLAY="board/stmicroelectronics/stm32mp135-test/overlay"
    BR2_PACKAGE_DROPBEAR=y
    BR2_PACKAGE_IPERF3=y
    BR2_TARGET_ROOTFS_EXT2=y
    BR2_TARGET_ROOTFS_EXT2_4=y
    BR2_TARGET_ROOTFS_EXT2_SIZE="5M"

Note the overlay directory: it can be empty, or you can use it to copy any
additional files onto the target filesystem. Run make and a long time later
(enough to get and build the toolchain and the two selected packages) the root
file system image will appear under `buildroot/output/images`.

The advantage of this approach is that we can quickly and directly rebuild the
kernel and the DTB without invoking Buildroot, while being able to quickly get
all the packages compiled from Buildroot and included in the target system.

### Copying DTB over ssh

So far, installing a new DTB required rebuilding the SD image and writing it to
the target using our bootloader. Since DTB is a tiny file, it's much faster if
we could just change the DTB and not the whole SD card image. Let's do it over
ssh so as to easily automate it from the ["50 line
Makefile"](build-linux-for-stm32mp135-in-under-50-lines-of-makefile).

First we need to make sure the target has an SSH server. This is provided by the
Dropbear package that we have added to the Buildroot configuration. By default,
ssh will ask for a password each time which is tedious and insecure. Instead,
let's copy our public key to the overlay directory:

```
cp ~/.ssh/id_ed25519.pub overlay/root/.ssh/authorized_keys
```

Moreover, each time Dropbear is started from a "clean" Buildroot-generated
rootfs, it will generate its own host key which we'll have to manually accept.
Instead, let's pre-seed the target key by copying the generated key from the
target one time (replace the IP address with that of your target):

```
mkdir -p overlay/etc/dropbear
scp root@172.25.0.132:/etc/dropbear/dropbear_ed25519_host_key overlay/etc/dropbear
```

Finally, to install the new DTB over ssh, copy it over and then write it to the
second SD card partition:

```
ssh root@172.25.0.132 "dd of=/dev/mmcblk0p2" < linux/arch/arm/boot/dts/custom.dtb
```

### Restart handler

After installing the new DTB we need to reboot the system. This can be done by
power cycling the board, but that quickly get tiresome. In the default
configuration, the PSCI interface communicates with the "secure" OS or
bootloader (TF-A), but to my mind that's complexity we can do without.

Thus, we need to implement a "restart handler" so that the `reboot` command will
be able to reboot the system. It will be very simple: it needs to flip one bit
in the `GRSTCSETR` register. As we can read in the RM0475 reference manual for
this SoC, that register has only one bit, called `MPSYSRST`, where writing '1'
generates a system reset.

Notice that the device tree already defines a driver to talk to the RCC unit:

```
rcc: rcc@50000000 {
	compatible = "st,stm32mp13-rcc", "syscon";
	reg = <0x50000000 0x1000>;
	#clock-cells = <1>;
	#reset-cells = <1>;
	clock-names = "hse", "hsi", "csi", "ck_lse", "lsi";
	clocks = <&clk_hse>,
		 <&clk_hsi>,
		 <&clk_csi>,
		 <&clk_lse>,
		 <&clk_lsi>;
};
```

This `st,stm32mp13-rcc` driver is to be found under
`drivers/clk/stm32/clk-stm32mp13.c`. First we define the register and bit needed
to execute the reset:

```c
#define RCC_MP_GRSTCSETR                0x114
#define RCC_MP_GRSTCSETR_MPSYSRST       BIT(0)
```

Then the reset handler is very simple:

```c
static int stm32mp1_restart(struct sys_off_data *data)
{
	void __iomem *rcc_base = data->cb_data;

	pr_info("System reset requested...\n");
	dsb(sy);
	writel(RCC_MP_GRSTCSETR_MPSYSRST, rcc_base + RCC_MP_GRSTCSETR);

	while (1)
		wfe();

	return NOTIFY_DONE;
}
```

Finally, we need to register this reset handler. A good place is at the bottom
of `stm32mp1_rcc_init()`:

```c
devm_register_sys_off_handler(dev, SYS_OFF_MODE_RESTART,
	SYS_OFF_PRIO_HIGH, stm32mp1_restart, rcc_base);
```

!include[articles/linux-on-stm32mp135.html]

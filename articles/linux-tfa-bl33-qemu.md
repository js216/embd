---
title: Linux as TF-A BL33 on Qemu (No U-Boot)
author: Jakob Kastelic
date: 15 Sep 2025
modified: 18 Sep 2025
topic: Linux
description: >
   Step-by-step guide to booting Linux directly as BL33 with Arm Trusted
   Firmware (TF-A) on QEMU, bypassing U-Boot. Learn how to adjust Buildroot,
   modify the DTB and initramfs, and integrate the process into your own board
   files.
---

![](../images/pdp1.jpg)

*This is Part 4 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

With Qemu, anyone can customize the Linux boot process and run it without the
need for custom hardware. In this article, we will adapt a Buildroot defconfig
to make TF-A boot Linux and OP-TEE directly without U-Boot.

This approach was suggested by A. Vandecappelle on the Buildroot mailing
list[^list]. He was correct to point out that it would be
interesting to see a Qemu simulation of the "Falcon mode" boot process:

> Perhaps it would also be a good idea to add a variant of the qemu defconfigs
> that tests this option. We can use the `qemu_arm_vexpress_tz_defconfig`, drop
> U-Boot from it, and switch to booting to Linux directly from TF-A.

First, we will look at the "normal" boot process with U-Boot to understand how
to remove it. Then, we will provide tutorial-style steps to remove U-Boot from
the boot process. Then, we suggest with how to integrate this into Buildroot. We
conclude with a discussion of alternative approaches.

### "Normal" boot process

In the `qemu_arm_vexpress_tz_defconfig` defconfig, Qemu is instructed to load
Arm Trusted Firmware (TF-A) as "`bios`". Qemu auto-generates a Device Tree Blob
(DTB) and loads it in memory at the start of RAM. As the Qemu
documentation[^qemu] explains:

> - For guests using the Linux kernel boot protocol (this means any non-ELF file
>   passed to the QEMU `-kernel` option) the address of the DTB is passed in a
>   register (`r2` for 32-bit guests, or `x0` for 64-bit guests)
>
> - For guests booting as "bare-metal" (any other kind of boot), the DTB is at
>   the start of RAM (0x4000_0000)

In our case, TF-A is booted in the "bare-metal" mode. We can see in file
`plat/qemu/qemu/include/platform_def.h` that this is so:

```
#define PLAT_QEMU_DT_BASE           NS_DRAM0_BASE
```

TF-A patches the Qemu-provided DTB by inserting the information about the
reserved memory addresses used by the secure OS (OP-TEE), as well as the
protocol (PSCI) that Linux is to use to communicate with OP-TEE. Then, it passes
control to U-Boot.

U-Boot only task in this configuration, as far as I can tell, is to load the
initial compressed filesystem image into some range of memory addresses, then
patch the DTB with these addresses. Then, it passes control to the Linux kernel.

Linux reads the DTB, either from the address given in register r2 or perhaps
from the pre-defined memory location (not sure). Then, it reads the
`initrd-start` location from the `chosen` node, decompresses the filesystem,
locates the init process, and runs it.

Thus to remove U-Boot, we just have to load the initramfs ourselves, and add its
address to the DTB. Of course, we must also tell TF-A to not load the U-Boot and
instead run Linux directly. In the following section, we explain how to do that.

### Falcon-mode tutorial

1. Obtain Buildroot and check out and build the defconfig that we're starting
   from:

   ```
   $ git clone https://gitlab.com/buildroot.org/buildroot.git --depth=1
   $ make qemu_arm_vexpress_tz_defconfig
   $ make
   ```

   This builds everything and gives the script `start_qemu.sh` (under
   `output/images`) with the suggested Qemu command line.

2. Extract the DTB by modifying the Qemu command as follows (note the
   `dumpdtb=qemu.dtb`):

   ```
   $ qemu-system-arm -machine virt,dumpdtb=qemu.dtb -cpu cortex-a15
   ```

3. Uncompile the DTB into the source format so we can edit it:

   ```
   $ dtc -I dtb -O dts qemu.dtb > new.dts
   ```

   Open `new.dts` in a text editor and modify the `chosen` node as follows,
   adding the location of the initramfs (initrd):

   ```
   chosen {
   	linux,initrd-end = <0x00 0x7666e09d>;
   	linux,initrd-start = <0x00 0x76000040>;
   	bootargs = "test console=ttyAMA0,115200 earlyprintk=serial,ttyAMA0,115200";
   	stdout-path = "/pl011@9000000";
   };
   ```

   Compile it back into the DTB format:

   ```
   dtc -I dts -O dtb new.dts > new.dtb
   ```

4. Open `make menuconfig` and navigate to `Bootloaders ---> Arm Trusted Firmware
   (ATF)`. Switch the BL33 to `None`, and add the following Additional ATF build
   variables:

   ```
   BL33=$(BINARIES_DIR)/zImage
   ```

   Exit and save new configuration and rebuild:

   ```
   $ make arm-trusted-firmware-rebuild
   $ make
   ```

   Check that `output/images` contains updated `fip.bin`, which should be about
   5 or 6M in size since it contains the whole kernel rather than just U-Boot.

5. Run Qemu with the following commands:

   ```
   $ cd output/images
   $ exec qemu-system-arm -machine virt -dtb art.dtb -device \
        loader,file=rootfs.cpio.gz,addr=0x76000040 -machine secure=on -cpu \
        cortex-a15 -smp 1 -s -m 1024 -d unimp -netdev user,id=vmnic -device \
        virtio-net-device,netdev=vmnic -nographic \
        -semihosting-config enable=on,target=native -bios flash.bin
   ```

   This is of course just the old command from `start-qemu.sh`, with the DTB and
   initramfs added. With some luck, you should see messages from TF-A directly
   transitioning into the ones from the kernel, with no U-Boot in between:

   ```
   NOTICE:  Booting Trusted Firmware
   NOTICE:  BL1: v2.7(release):v2.7
   NOTICE:  BL1: Built : 20:55:52, Sep 12 2025
   NOTICE:  BL1: Booting BL2
   NOTICE:  BL2: v2.7(release):v2.7
   NOTICE:  BL2: Built : 20:55:52, Sep 12 2025
   NOTICE:  BL1: Booting BL32
   Booting Linux on physical CPU 0x0
   Linux version 6.12.27 (jk@Lutien) (arm-buildroot-linux-gnueabihf-gcc.br_real (Buildroot -g5b6b80bf) 14.3.0, GNU ld (GNU Binutils) 2.43.1) #2 SMP Fri Sep 12 20:03:32 PDT 2025
   CPU: ARMv7 Processor [414fc0f0] revision 0 (ARMv7), cr=10c5387d
   CPU: div instructions available: patching division code
   CPU: PIPT / VIPT nonaliasing data cache, PIPT instruction cache
   OF: fdt: Machine model: linux,dummy-virt
   OF: fdt: Ignoring memory range 0x40000000 - 0x60000000
   ```

### TF-A support for Linux as BL33

We saw above that TF-A is happy to boot Linux directly so long as we just point
it to a kernel image for the BL33 executable. It turns out that there we can
find limited support for this use case already in the TF-A source tree via the
`ARM_LINUX_KERNEL_AS_BL33` flag.

The flag is specific to a few platforms. For AArch64 on Qemu, the documentation
(`docs/plat/qemu.rst`, as well as `docs/plat/arm/arm-build-options.rst`)
explains that the flag makes TF-A pass the Qemu-generated DTB to the kernel via
the `x0` register. We see the implementation of it in
`plat/qemu/common/qemu_bl2_setup.c` (and very similar lines in
`plat/arm/common/arm_bl31_setup.c`):

```
#if ARM_LINUX_KERNEL_AS_BL33
		/*
		 * According to the file ``Documentation/arm64/booting.txt`` of
		 * the Linux kernel tree, Linux expects the physical address of
		 * the device tree blob (DTB) in x0, while x1-x3 are reserved
		 * for future use and must be 0.
		 */
		bl_mem_params->ep_info.args.arg0 =
			(u_register_t)ARM_PRELOADED_DTB_BASE;
		bl_mem_params->ep_info.args.arg1 = 0U;
		bl_mem_params->ep_info.args.arg2 = 0U;
		bl_mem_params->ep_info.args.arg3 = 0U;
```

On AArch32, the flag as currently implemented is intended for operation with
`SP_MIN`. This is clear from the documentation: "for AArch32 ``RESET_TO_SP_MIN``
must be 1 when using" the `ARM_LINUX_KERNEL_AS_BL33` flag
(`docs/plat/arm/arm-build-options.rst`). The `plat/arm/common/arm_common.mk`
Makefile enforces this.

Unfortunately this limits the potential use cases of `ARM_LINUX_KERNEL_AS_BL33`
to AArch64, or else to AArch32 with `SP_MIN` enabled. The Buildroot defconfig we
have adapted in the previous section uses OP-TEE instead of `SP_MIN`, and it is
also possible to use no BL32 at all.

### Patching initramfs address

In the tutorial above, we dumped the Qemu DTB and modified it just to add two
lines into the `chosen` node. The same can be done by TF-A.

The file `plat/qemu/common/qemu_bl2_setup.c` defines the function `update_dt()`
which is used for precisely this purpose, updating the DTB with some extra
board-specific details. (In the defconfig, it inserts PSCI nodes.)

We can insert the two `chosen` lines in the middle of `update_dt()`:

```
fdt_setprop_u64(fdt, fdt_path_offset(fdt, "/chosen"),
        "linux,initrd-start", 0x76000040);
fdt_setprop_u64(fdt, fdt_path_offset(fdt, "/chosen"),
        "linux,initrd-end",   0x7666e09d);
```

On recompile, there is no need to manually modify the DTB anymore.

The disadvantage of this approach is that we have to patch TF-A, making our
defconfig fragile against future changes in TF-A. It would be better to include
that DTB compilation as a post-build script in Buildroot.

### Discussion

Is it practical to assume that the initramfs will be loaded in memory before
TF-A even starts executing? Of course not. But on a real embedded platform, such
as the setup from the [previous article](stm32mp135-without-u-boot), the root
filesystem is the SD card or some other non-volatile storage. There appears to
be no good reason to use U-Boot since TF-A can read from these just fine. If, on
the other hand, your setup requires some complicated configuration of the root
filesystem, possibly involving Ethernet, then U-Boot may well be a good choice.
Still, I believe that the best tool for the job is the simplest one that works
reliably.

It is also not reasonable to assume that the DTB would be loaded in memory
before TF-A even begins execution. After all, as the only bootloader, it is its
job to load it and point the kernel to where it loaded it. As P. Maydell
explains on the qemu-discuss mailing list[^disc], providing the `-dtb` option to
Qemu "overrides the autogenerated file. But generally you shouldn't do that."
Instead, the Qemu user should provide the DTB, if emulating real hardware, or
else to have the Qemu

> autogenerate the DTB matching whatever it does, like the virt board. This is
> the unusual case -- virt only does this because it is a purely "virtual" board
> that doesn't match any real physical hardware and which changes depending on
> what the user asked for.

For example, on STM32MP1, the TF-A `fiptool` is used to package the DTB in a
form that TF-A is able to load it in memory using the `BL33_CFG` flag, as we
have used in [previous article](stm32mp135-without-u-boot).

There may be other ways to load the DTB and initramfs in Qemu, but the one
presented in our tutorial above appears to be the easiest. We could, for
example, modify Qemu to allow using the `-initrd` command line flag without the
`-kernel` flag, and emit the DTB with the appropriate address. Or, we could
teach TF-A how to read the initramfs file via the semihosting or virtio
protocols, load it into memory, and modify the DTB accordingly.

However, the tutorial method above works without modifying Qemu or TF-A code. It
uses an explicit DTB, as one is likely to do on a physical embedded target.
Since it passes the initramfs using an explicit command line option, it avoids
hard-coding it into any compiled code.

### Upstreaming Status

17/9/2025: first submission of the Qemu defconfig
[(link)](https://lists.buildroot.org/pipermail/buildroot/2025-September/786597.html)

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><a href="stm32mp135-linux-cubeprog">2. STM32MP135 Flashing via USB with STM32CubeProg</a></li>
  <li><a href="stm32mp135-without-u-boot">3. STM32MP135 Without U-Boot (TF-A Falcon Mode)</a></li>
  <li><em>4. This article</em></li>
  <li><a href="stm32mp135-without-optee">5. STM32MP135 Without OP-TEE</a></li>
  <li><a href="linux-bringup-on-custom-stm32mp135-board">6. Linux Bring-Up on a Custom STM32MP135 Board</a></li>
</ul>
</div>

[^list]: Buildroot mailing list, Fri May 16 2025 message:
    [boot/arm-trusted-firmware: optional Linux as
    BL33](https://lists.buildroot.org/pipermail/buildroot/2025-May/778563.html)
    (cited on 09/15/2025)

[^qemu]:
    Qemu: ['virt' generic virtual
    platform](https://www.qemu.org/docs/master/system/arm/virt.html#hardware-configuration-information-for-bare-metal-programming)
    (cited 09/15/2025).

[^disc]: qemu-discuss mailing list, Thu 4 Aug 2022 message: [Re: how to prevent automatic
    dtb
    load?](https://lists.gnu.org/archive/html/qemu-discuss/2022-08/msg00007.html)
    (cited 09/15/2025)

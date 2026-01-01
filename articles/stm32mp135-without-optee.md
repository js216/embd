---
title: STM32MP135 Without OP-TEE
author: Jakob Kastelic
date: 26 Sep 2025
topic: Linux
description: >
   Learn how to run Linux on the STM32MP135 without OP-TEE. This guide explains
   removing secure monitor calls, configuring the kernel, and replacing SCMI
   clocks for a fully non-secure setup.
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

The present article is somewhat more involved than the preceding ones in the
series. For this reason I offer the ["Quick Start"](#quick-start) version, where
the required modifications to kernel drivers are offered as patches to apply to
a particular version. For those interested, the ["Theory"](#theory) section fill
in the details. As in other articles, we conclude with a brief discussion.

### Quick Start

Start by cloning Buildroot as above. However, this time we check out a different
sequence of patches and board files:

```
$ git clone https://gitlab.com/buildroot.org/buildroot.git
$ git clone git@github.com:js216/stm32mp135_simple.git

$ cd buildroot
$ git checkout 3645e3b781be5cedbb0e667caa70455444ce4552

$ git apply ../stm32mp135_simple/patches/add_falcon.patch
$ cp ../stm32mp135_simple/configs/stm32mp135f_dk_nonsecure_defconfig configs
$ cp -r ../stm32mp135_simple/board/stm32mp135f-dk-nonsecure board/stmicroelectronics
```

Now build:

```
$ make stm32mp135f_dk_nonsecure_defconfig
$ make
```

Write the generated image to the SD card (either directly with a tool such as
`dd`, or using the STM32CubeProg as explained
[here](stm32mp135-linux-cubeprog)). Watch it boot up without U-Boot, and without
OP-TEE.

### Theory

To understand the modifications we are about to do in the next section, we need
to take a closer look at the boot process from TF-A to OP-TEE to Linux. In
particular, we need to explain how secure monitor calls (SMC) calls work; the
use of secure interrupts (`FIQ`) in OP-TEE; and explain how SCMI clocks work

#### Boot process from TF-A to OP-TEE to Linux

When Arm Trusted Firmware (TF-A) is done with its own initialization, it loads
several images into memory. In the STM32MP1 case, these are defined in the
array `bl2_mem_params_desc` in file
`plat/st/stm32mp1/plat_bl2_mem_params_desc.c`, and include the following:

- `FW_CONFIG_ID`: firmware config, which is mostly just the information on
TrustZone memory regions that is used by TF-A itself

- `BL32_IMAGE_ID`: the OP-TEE executable

- `BL32_EXTRA1_IMAGE_ID`, `BL32_EXTRA2_IMAGE_ID`, and `TOS_FW_CONFIG_ID`: some
  stuff needed by OP-TEE

- `BL33_IMAGE_ID`: the non-trusted bootloader (U-Boot) or directly Linux itself,
  if operating in the "falcon mode"

- `HW_CONFIG_ID`: the Device Tree Blob (DTB) used by U-Boot or Linux, whichever
  is run as "BL33"

Just before passing control to OP-TEE, the TF-A prints a couple messages in the
`bl2_main()` function (`bl2/bl2_main.c`), and then runs `bl2_run_next_image`
(`bl2/aarch32/bl2_run_next_image.S`). There, we disable MMU, put the OP-TEE
entry address into the link register (either `lr` or `lr_svc`), load the `SPSR`
register, and then do an "exception return" to atomically change the program
counter to the link register value, and restore the Current Program Status
Register (`CPSR`) from the Saved Program Status Register (`SPSR`).

#### How do secure monitor calls (SMC) work?

The ARMv7-A architecture provides optional TrustZone extension, which are
implemented on the STM32MP135 chips (as well as the virtualisation
extension). In this scheme, the processor is at all times executing in one of
two "worlds", either the secure or the non-secure one.

The `NS` bit of the
[`SCR`](https://developer.arm.com/documentation/ddi0406/c/System-Level-Architecture/System-Control-Registers-in-a-VMSA-implementation/VMSA-System-control-registers-descriptions--in-register-order/SCR--Secure-Configuration-Register--Security-Extensions?lang=en)
register defines which world we're currently in. If `NS=1`, we are in non-secure
world, otherwise we're in the secure world. The one exception to this is that
when the processor is running in
[Monitor mode](https://developer.arm.com/documentation/ddi0406/c/System-Level-Architecture/The-System-Level-Programmers--Model/ARM-processor-modes-and-ARM-core-registers/ARM-processor-modes?lang=en#CIHGHDGI);
in that case, the code is executing the secure world and `SCR.NS` merely
indicates which world the processor was in before entering the Monitor mode.
(The current processor mode is given by the `M` bits of the
[`CPSR`](https://developer.arm.com/documentation/ddi0406/c/System-Level-Architecture/The-System-Level-Programmers--Model/ARM-processor-modes-and-ARM-core-registers/Program-Status-Registers--PSRs-?lang=en#CIHBFGJG)
register.)

The processor starts execution in the secure world. How do we transition to the
non-secure world? Outside of Monitor mode, Arm does not recommend direct
manipulation of the `SCR.NS` bit to change from the secure world to the
non-secure world or vice versa. Instead, the right way is to first change into
Monitor mode, flip the `SCR.NS` bit, and leave monitor mode. To enter Monitor
mode, execute the `SMC` instruction. This triggers the SMC exception, and the
processor begins executing the SMC handler.

The location of the SMC handler has to be previously stored in the
[`MVBAR` register](https://developer.arm.com/documentation/ddi0406/c/System-Level-Architecture/System-Control-Registers-in-a-VMSA-implementation/VMSA-System-control-registers-descriptions--in-register-order/MVBAR--Monitor-Vector-Base-Address-Register--Security-Extensions).
The initial setup required is as follows:

1. Write a SMC handler. As an example, consult OP-TEE source code, which
   provides the handler `sm_smc_entry`, defined in `core/arch/arm/sm/sm_a32.S`.

2. Create a vector table for monitor mode. As specified in the
   [Arm architecture](https://developer.arm.com/documentation/ddi0406/b/System-Level-Architecture/The-System-Level-Programmers--Model/Exceptions/Exception-vectors-and-the-exception-base-address?lang=en)
   manual, the monitor vector table has eight entries:

   1. Unused
   2. Unused
   3. Secure Monitor Call (SMC) handler
   4. Prefetch Abort handler
   5. Data Abort handler
   6. Unused
   7. `IRQ` interrupt handler
   8. `FIQ` interrupt handler

   Obviously entry number 3 has to point to the SMC handler defined previously.
   For example, OP-TEE defines the following vector table in
   `core/arch/arm/sm/sm_a32.S`:

       LOCAL_FUNC sm_vect_table , :, align=32
       UNWIND(	.cantunwind)
       	b	.		/* Reset			*/
       	b	.		/* Undefined instruction	*/
       	b	sm_smc_entry	/* Secure monitor call		*/
       	b	.		/* Prefetch abort		*/
       	b	.		/* Data abort			*/
       	b	.		/* Reserved			*/
       	b	.		/* IRQ				*/
       	b	sm_fiq_entry	/* FIQ				*/
       END_FUNC sm_vect_table

   We see only the SMC and `FIQ` handlers are installed, since OP-TEE setup
   disables all other Monitor-mode interrupts and exceptions.

3. Install the vector table to the `MVBAR` register. The OP-TEE source code
   defines the following macros in `out/core/include/generated/arm32_sysreg.h`:

       /* Monitor Vector Base Address Register */
       static inline __noprof uint32_t read_mvbar(void)
       {
       	uint32_t v;

       	asm volatile ("mrc p15, 0, %0, c12, c0, 1" : "=r"  (v));

       	return v;
       }

       /* Monitor Vector Base Address Register */
       static inline __noprof void write_mvbar(uint32_t v)
       {
       	asm volatile ("mcr p15, 0, %0, c12, c0, 1" : : "r"  (v));
       }

   This merely follows the Arm manual on how to access the
   [`MVBAR` register](https://developer.arm.com/documentation/ddi0406/c/System-Level-Architecture/System-Control-Registers-in-a-VMSA-implementation/VMSA-System-control-registers-descriptions--in-register-order/MVBAR--Monitor-Vector-Base-Address-Register--Security-Extensions).

With this setup in place, to transition from the secure world to the non-secure
world, the steps are as follows:

1. Place the arguments to the SMC handler into registers `r0` through `r4` (or
   as many as are needed by the handler), and execute the SMC instruction. For
   example, just before passing control to the non-secure world, OP-TEE
   `reset_primary` function (called from the `_start` function) does the
   following:

       mov	r4, #0
       mov	r3, r6
       mov	r2, r7
       mov	r1, #0
       mov	r0, #TEESMC_OPTEED_RETURN_ENTRY_DONE
       smc	#0

2. This puts the processor into Monitor mode, and it begins execution at the
   previously-installed SMC handler. The handler stores secure-mode registers
   into some memory location for future use, then sets the `SCR.NS` bit:

       read_scr r0
       orr	r0, r0, #(SCR_NS | SCR_FIQ) /* Set NS and FIQ bit in SCR */
       write_scr r0

   This also sets the `SCR.FIQ` bit, which means that `FIQ` interrupts are also
   taken to Monitor mode. In this way, OP-TEE assigns `IRQ` interrupts to the
   non-secure world, and `FIQ` interrupts to the secure-world. Of course, this
   means that the Monitor-mode vector table needs a `FIQ` handler (as mentioned
   in passing above), and the system interrupt handler (GIC on STM32MP135) needs
   to be configured to pass "secure" interrupts as `FIQ`.

3. After adjusting the stack pointer and restoring the non-secure register
   values from the stack, the SMC handler returns:

       add	sp, sp, #(SM_CTX_NSEC + SM_NSEC_CTX_R0)
       pop	{r0-r7}
       rfefd	sp!

   The return location and processor mode is stored on the stack and
   automatically retrieved by the `rfefd sp!` instruction. Of course this means
   they have to be previously stored in the right place on the stack; see
   `sm_smc_entry` source code for details.

#### Secure interrupts in OP-TEE

As mentioned above, OP-TEE code, before returning to non-secure mode, enables
the `SCR.FIQ` bit, which means that `FIQ` interrupts get taken to Monitor mode,
serviced by the `FIQ` handler that is installed in the Monitor-mode vector table
(the table address is stored in the `MVBAR` register).

As mentioned above, an arbitrary number of system interrupts may be passed as a
`FIQ` to the processor core. OP-TEE handles these interrupts in `itr_handle()`
(defined in `core/kernel/interrupt.c`). The individual interrupt handlers are
stored in a linked list, which `itr_handle()` traverses until it finds a handler
whose interrupt number (`h->it`) matches the given interrupt.

For example, the handler for the `TZC` interrupt (TrustZone memory protection)
is defined in `core/arch/arm/plat-stm32mp1/plat_tzc400.c`, as the
`tzc_it_handler()` function.

#### How do SCMI clocks work?

In general, to configure clocks, Linux uses the
[Common Clock Framework](https://www.kernel.org/doc/Documentation/clk.txt). Each
clock needs to define some common operations, such as `enable()`, `disable()`,
`set_rate()`, and so on, as relevant to each particular clock.

Since in the ST-recommended scheme the clock configuration is done entirely in
the secure world, the STM32MP135 clock drivers
(`drivers/clk/stm32/clk-strm32mp13.c`) make use of the SCMI clock driver
(`drivers/clk/clk/scmi.c`). The latter provides a translation from the common
clock functions to SCMI functions. For example, `enable()` is implemented as
follows:

    static int scmi_clk_enable(struct clk_hw *hw)
    {
    	struct scmi_clk *clk = to_scmi_clk(hw);
    	return scmi_proto_clk_ops->enable(clk->ph, clk->id);
    }

This is just a wrapper around the SCMI clock enable function, as found in the
`scmi_proto_clk_ops` structure (which contains all the SCMI-protocol clock
operations).

At Linux boot, when the SCMI clock driver is being "probed", it asks OP-TEE
about the number of supported clocks, and then retrieves information about each
one in sequence. Thus it acquires a list of clocks, with a header file defining
the sequential ID numbers (`include/dt-bindings/clock/stm32mp13-clks.h`):

    /* SCMI clock identifiers */
    #define CK_SCMI_HSE		0
    #define CK_SCMI_HSI		1
    #define CK_SCMI_CSI		2
    #define CK_SCMI_LSE		3
    #define CK_SCMI_LSI		4
    #define CK_SCMI_HSE_DIV2	5
    #define CK_SCMI_PLL2_Q		6
    #define CK_SCMI_PLL2_R		7
    #define CK_SCMI_PLL3_P		8
    #define CK_SCMI_PLL3_Q		9
    #define CK_SCMI_PLL3_R		10
    #define CK_SCMI_PLL4_P		11
    #define CK_SCMI_PLL4_Q		12
    #define CK_SCMI_PLL4_R		13
    #define CK_SCMI_MPU		14
    #define CK_SCMI_AXI		15
    #define CK_SCMI_MLAHB		16
    #define CK_SCMI_CKPER		17
    #define CK_SCMI_PCLK1		18
    #define CK_SCMI_PCLK2		19
    #define CK_SCMI_PCLK3		20
    #define CK_SCMI_PCLK4		21
    #define CK_SCMI_PCLK5		22
    #define CK_SCMI_PCLK6		23
    #define CK_SCMI_CKTIMG1		24
    #define CK_SCMI_CKTIMG2		25
    #define CK_SCMI_CKTIMG3		26
    #define CK_SCMI_RTC		27
    #define CK_SCMI_RTCAPB		28

(There must be some way to ensure that the same sequential number is used in
 Linux as in OP-TEE, or else the clocks would get confused. Presumably the same
 header file is used in Linux as in OP-TEE.)

The SCMI clock numbers are then used in device trees. For example, in
`core/arch/arm/dts/stm32mp131.dtsi`, we see some of these constants being used:

    rcc: rcc@50000000 {
    	compatible = "st,stm32mp13-rcc", "syscon";
    	reg = <0x50000000 0x1000>;
    	#clock-cells = <1>;
    	#reset-cells = <1>;
    	clock-names = "hse", "hsi", "csi", "lse", "lsi";
    	clocks = <&scmi_clk CK_SCMI_HSE>,
    		 <&scmi_clk CK_SCMI_HSI>,
    		 <&scmi_clk CK_SCMI_CSI>,
    		 <&scmi_clk CK_SCMI_LSE>,
    		 <&scmi_clk CK_SCMI_LSI>;
    };

Thus, when the driver compatible with `"st,stm32mp13-rcc"` (implemented in
`drivers/clk/stm32/clk-stm32mp13.c`) needs to refer to its `"hse"` clock, it
calls the `scmi_clk` and gives it the `CK_SCMI_HSE` parameter. Recall that
`scmi_clk` is defined in the same `DTSI` file, under `firmware` / `scmi`:

    scmi_clk: protocol@14 {
    	reg = <0x14>;
    	#clock-cells = <1>;
    };

There are some SCMI clocks, however, which are used by the `"st,stm32mp13-rcc"`
driver, which are not listed in the device tree. For example, in
`drivers/clk/stm32/clk-stm32mp13.c` we find many definitions such as the
following:

    static const char * const sdmmc12_src[] = {
    	"ck_axi", "pll3_r", "pll4_p", "ck_hsi"
    };

Here `ck_axi`, `pll3_r`, etc., refer to SCMI clocks, but these are not mentioned
in the device tree. How can the kernel find them? The way it works is that
during SCMI clock driver initialization, the driver registers these clocks (and
others as per the listing from the `stm32mp13-clks.h` header file above). When,
later, the `"st,stm32mp13-rcc"` driver is being initialized, it is able to refer
to these clocks simply by their name.

This means that the SCMI driver needs to be probed before the `RCC` driver. To
ensure this, note the following part of the device tree:

    rcc: rcc@50000000 {
        ...
    	clocks = <&scmi_clk CK_SCMI_HSE>,
    		 <&scmi_clk CK_SCMI_HSI>,
    		 <&scmi_clk CK_SCMI_CSI>,
    		 <&scmi_clk CK_SCMI_LSE>,
    		 <&scmi_clk CK_SCMI_LSI>;
    };

The reference to SCMI clocks here does not mean that these particular clocks
(`HSE,` `HSI,` `CSI,` `LSE,` `LSI)` are used by the `RCC` driver. Rather, it
ensures that the SCMI clock driver is a dependency of the `RCC` driver, and gets
initialized first. It would have been much nicer if the device tree `RCC` node
listed all the clocks that are used by `RCC` rather than just referring to them
by their name string (such as `"pll3_r"`), but that's the way ST implemented
things. In particular, this means that if we unset the `CONFIG_COMMON_CLK_SCMI`
entry in the kernel configuration, the kernel will no longer boot, without
printing any error message at all; the `RCC` driver will fail to work properly
since it can no longer refer to many of the clocks it needs by their name
string.

There is no need to understand SCMI clocks further, so long as we can replace
them all with "real" clocks, with registers under direct control of the `RCC`
driver from the Linux kernel.

### Discussion

STM32MP135 presents an SDK that is, to my mind, overly complicated. To port the
setup from the evaluation board to a new board requires the understanding of
three bootloaders (ROM, TF-A, U-Boot), two operating systems (Linux, OP-TEE),
and a stack of other software. Most of this arose out of a desire to simplify
the process; for example, U-Boot aims to be the one universal bootloader in
embedded systems, so as to not have to learn a new one for each platform. But
the ironic end result is that after piling on so many "simplifications", the net
result is more complicated than having none of them.

The claim that OP-TEE is mandatory probably arises out of a desire to avoid
having to maintain two separate development branches, a secure and a non-secure
one. This must be even more so considering the need to support the GUI-based
configuration utilities (STM32Cube), or the Yocto-based distributions.

However, as a developer I would prefer to be offered a minimal working
configuration where OP-TEE would be an "opt-in" configuration, rather than
tightly bundling it in with the kernel. Many (most?) applications do not call
for secure-world services; these get included only due to the large cost of
*removing* it from the provided SDKs.

### Upstreaming Status

09/26/2025: I have made the modifications available in the repository
[`stm32mp135_simple`](https://github.com/js216/stm32mp135_simple), as mentioned
in the quick tutorial above. I do not at present have the intention of
upstreaming it, since it would involve a lot of effort updating it to the latest
version of Buildroot (or TF-A and Linux), only to watch it become obsolete again
during the upstreaming process.

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><a href="stm32mp135-linux-cubeprog">2. STM32MP135 Flashing via USB with STM32CubeProg</a></li>
  <li><a href="stm32mp135-without-u-boot">3. STM32MP135 Without U-Boot (TF-A Falcon Mode)</a></li>
  <li><a href="linux-tfa-bl33-qemu">4. Linux as TF-A BL33 on Qemu (No U-Boot)</a></li>
  <li><em>5. This article</em></li>
  <li><a href="linux-bringup-on-custom-stm32mp135-board">6. Linux Bring-Up on a Custom STM32MP135 Board</a></li>
</ul>
</div>

[^wiki]: ST wiki: [How to disable OP-TEE secure
    services](https://wiki.st.com/stm32mpu/wiki/How_to_disable_OP-TEE_secure_services)

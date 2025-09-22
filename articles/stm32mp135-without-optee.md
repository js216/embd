---
title: STM32MP135 Without OP-TEE
author: Jakob Kastelic
date: 20 Sep 2025
modified: 21 Sep 2025
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
ones in the series. For this reason I offer the ["Quick Start"](#quick-start)
version, where the required modifications to kernel drivers are offered as
patches to apply to a particular version. For those interested, the
["Theory"](#theory) and ["Long Version"](#long-version) sections fill in the
details. As in other articles, we conclude with a brief discussion.

### Quick Start

TBD: copy from the `stm32mp135_simple` README.

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

We now proceed with the "long version" of the tutorial make Linux boot on the
STM32MP135 eval board without running OP-TEE in the background.

### Long Version

We begin with the defconfig modified to not require U-Boot, such as the one
created in the [previous article](stm32mp135-without-u-boot) (probably optional,
but I mention it so we can all start from the same starting point).

Having that set up and working, we will need to do the following tasks, as
explained in the coming subsections:

- Reassign the `STPMIC1` and `I2C4` from OP-TEE to the Linux kernel
- Configure clocks (`RCC)` from Arm Trusted Firmware (TF-A)
- Configure ETZPC from TF-A
- Check for additional SMC calls
- Unsecure access to the `RCC` registers
- Configure all clocks from Linux
- Remove remaining SMC calls
- Discover what OP-TEE does before starting Linux

#### Move `STPMIC1` and `I2C4` from OP-TEE to Linux

1. Move the entire `&i2c4 {...}` tree (about 180 lines of code!) from the OP-TEE
   device tree source (`optee-os-4.3.0/core/arch/arm/dts/stm32mp135f-dk.dts`) to
   the Linux DTS (`linux-6.12.36/arch/arm/boot/dts/st/stm32mp135f-dk.dts`).
   OP-TEE will not need to know about `I2C4` and `STPMIC1,` but Linux will.

   Also copy over the `vin: vin { ... }` and `v3v3_ao: v3v3_ao { ... }` nodes.

2. Notice that the `&i2c4` tree refers to `pinctrl-0 = <&i2c4_pins_a>`, which is
   not defined by default. Without it, the driver will not know what pins we're
   using for the `I2C4` peripheral. Copy the pin mux definition to the
   appropriate Linux DTS file (`arch/arm/boot/dts/stm32mp13-pinctrl.dtsi`) from
   the corresponding OP-TEE file (`core/arch/arm/dts/stm32mp13-pinctrl.dtsi`):

       i2c4_pins_a: i2c4-0 {
       	pins {
       		pinmux = <STM32_PINMUX('E', 15, AF6)>, /* I2C4_SCL */
       			 <STM32_PINMUX('B', 9, AF6)>; /* I2C4_SDA */
       		bias-disable;
       		drive-open-drain;
       		slew-rate = <0>;
       	};
       };

3. The Linux driver for the `STPMIC1` requires two small changes. In
   `drivers/regulator/stpmic1_regulator.c`, we need to tell it that the switched
   regulator (`pwr_sw2` in the device tree, and `3V3_SW` on the STM32MP135F-DK
   schematic) is 3.3V, not 5V. Locate the lines starting with `#define
   REG_SW_OUT(ids, base) { \` and change the following `.fixed_uV = 5000000` to
   `.fixed_uV = 3300000`.

   The second change is in file `drivers/mfd/stpmic1.c`. In function
   `stpmic1_probe()`, comment out (or remove) the lines

       if (ddata->irq < 0) {
       	dev_err(dev, "Failed to get main IRQ: %d\n", ddata->irq);
       	return ddata->irq;
       }

   and also

       /* Initialize PMIC IRQ Chip & associated IRQ domains */
       ret = devm_regmap_add_irq_chip(dev, ddata->regmap, ddata->irq,
       			       IRQF_ONESHOT | IRQF_SHARED,
       			       0, &stpmic1_regmap_irq_chip,
       			       &ddata->irq_data);
       if (ret) {
       	dev_err(dev, "IRQ Chip registration failed: %d\n", ret);
       	return ret;
       }

4. Remove all references to SCMI from the Linux DTS
   (`linux-6.12.36/arch/arm/boot/dts/st/stm32mp135f-dk.dts`), making sure they
   are replaced with corresponding references to the `STPMIC1`:

      - `scmi_v3v3_sw` -> `v3v3_sw`
      - `scmi_vdd_adc` -> `vdd_adc`
      - `scmi_vdd_sd` -> `vdd_sd`
      - `scmi_vdd_usb` -> `vdd_usb`
      - `scmi_v1v8_periph` -> `v1v8_periph`
      - Delete the entire `&scmi_regu { ... }` tree

Note with all these changes, OP-TEE may no longer work (without further changes
or additions). This is not a problem, since the whole point here is to remove
`I2C4` from OP-TEE's control.

#### How to configure clocks from TF-A

1. Make a copy of the TF-A DTS file, so that it will persist from build to
   build. Note the location and set it in the Buildroot configuration. For
   example, set
   `$(BR2_EXTERNAL_THINKSRS_PATH)/board/stm32mp1/TFA_stm32mp135f-dk.dts` in the
   configuration option `BR2_TARGET_ARM_TRUSTED_FIRMWARE_CUSTOM_DTS_PATH`.

   Likewise, make a copy of the file `stm32mp135f-dk-fw-config.dts`, and include
   it in the same configuration option.

2. Copy the entire `&rcc { ... }` section from the OP-TEE DTS to the TF-A DTS,
   except for the two `pinctrl` lines at the top. In this case, it looks like
   this:

       &rcc {
       	compatible = "st,stm32mp13-rcc", "syscon", "st,stm32mp13-rcc-mco";

       	st,clksrc = <
       		CLK_MPU_PLL1P
       		CLK_AXI_PLL2P
       		CLK_MLAHBS_PLL3
       		CLK_RTC_LSE
       		CLK_MCO1_HSE
       		CLK_MCO2_DISABLED
       		CLK_CKPER_HSE
       		CLK_ETH1_PLL4P
       		CLK_ETH2_PLL4P
       		CLK_SDMMC1_PLL4P
       		CLK_SDMMC2_PLL4P
       		CLK_STGEN_HSE
       		CLK_USBPHY_HSE
       		CLK_I2C4_HSI
       		CLK_I2C5_HSI
       		CLK_USBO_USBPHY
       		CLK_ADC2_CKPER
       		CLK_I2C12_HSI
       		CLK_UART1_HSI
       		CLK_UART2_HSI
       		CLK_UART35_HSI
       		CLK_UART4_HSI
       		CLK_UART6_HSI
       		CLK_UART78_HSI
       		CLK_SAES_AXI
       		CLK_DCMIPP_PLL2Q
       		CLK_LPTIM3_PCLK3
       		CLK_RNG1_PLL4R
       	>;

       	st,clkdiv = <
       		DIV(DIV_MPU, 1)
       		DIV(DIV_AXI, 0)
       		DIV(DIV_MLAHB, 0)
       		DIV(DIV_APB1, 1)
       		DIV(DIV_APB2, 1)
       		DIV(DIV_APB3, 1)
       		DIV(DIV_APB4, 1)
       		DIV(DIV_APB5, 2)
       		DIV(DIV_APB6, 1)
       		DIV(DIV_RTC, 0)
       		DIV(DIV_MCO1, 0)
       		DIV(DIV_MCO2, 0)
       	>;

       	st,pll_vco {
       		pll1_vco_2000Mhz: pll1-vco-2000Mhz {
       			src = <CLK_PLL12_HSE>;
       			divmn = <1 82>;
       			frac = <0xAAA>;
       		};

       		pll1_vco_1300Mhz: pll1-vco-1300Mhz {
       			src = <CLK_PLL12_HSE>;
       			divmn = <2 80>;
       			frac = <0x800>;
       		};

       		pll2_vco_1066Mhz: pll2-vco-1066Mhz {
       			src = <CLK_PLL12_HSE>;
       			divmn = <2 65>;
       			frac = <0x1400>;
       		};

       		pll3_vco_417Mhz: pll3-vco-417Mhz {
       			src = <CLK_PLL3_HSE>;
       			divmn = <1 33>;
       			frac = <0x1a04>;
       		};

       		pll4_vco_600Mhz: pll4-vco-600Mhz {
       			src = <CLK_PLL4_HSE>;
       			divmn = <1 49>;
       		};
       	};

       	/* VCO = 1300.0 MHz => P = 650 (CPU) */
       	pll1: st,pll@0 {
       		compatible = "st,stm32mp1-pll";
       		reg = <0>;

       		st,pll = <&pll1_cfg1>;

       		pll1_cfg1: pll1_cfg1 {
       			st,pll_vco = <&pll1_vco_1300Mhz>;
       			st,pll_div_pqr = <0 1 1>;
       		};

       		pll1_cfg2: pll1_cfg2 {
       			st,pll_vco = <&pll1_vco_2000Mhz>;
       			st,pll_div_pqr = <0 1 1>;
       		};
       	};

       	/* VCO = 1066.0 MHz => P = 266 (AXI), Q = 266, R = 533 (DDR) */
       	pll2: st,pll@1 {
       		compatible = "st,stm32mp1-pll";
       		reg = <1>;

       		st,pll = <&pll2_cfg1>;

       		pll2_cfg1: pll2_cfg1 {
       			st,pll_vco = <&pll2_vco_1066Mhz>;
       			st,pll_div_pqr = <1 1 0>;
       		};
       	};

       	/* VCO = 417.8 MHz => P = 209, Q = 24, R = 11 */
       	pll3: st,pll@2 {
       		compatible = "st,stm32mp1-pll";
       		reg = <2>;

       		st,pll = <&pll3_cfg1>;

       		pll3_cfg1: pll3_cfg1 {
       			st,pll_vco = <&pll3_vco_417Mhz>;
       			st,pll_div_pqr = <1 16 36>;
       		};
       	};

       	/* VCO = 600.0 MHz => P = 50, Q = 10, R = 50 */
       	pll4: st,pll@3 {
       		compatible = "st,stm32mp1-pll";
       		reg = <3>;
       		st,pll = <&pll4_cfg1>;

       		pll4_cfg1: pll4_cfg1 {
       			st,pll_vco = <&pll4_vco_600Mhz>;
       			st,pll_div_pqr = <11 59 11>;
       		};
       	};

       	st,clk_opp {
       		/* CK_MPU clock config for MP13 */
       		st,ck_mpu {

       			cfg_1 {
       				hz = <650000000>;
       				st,clksrc = <CLK_MPU_PLL1P>;
       				st,pll = <&pll1_cfg1>;
       			};

       			cfg_2 {
       				hz = <1000000000>;
       				st,clksrc = <CLK_MPU_PLL1P>;
       				st,pll = <&pll1_cfg2>;
       			};
       		};
       	};
       };

3. From the OP-TEE DTS `$rcc { ... }` section, remove everything except:

       &rcc {
       	compatible = "st,stm32mp13-rcc", "syscon", "st,stm32mp13-rcc-mco";

       	st,clksrc = <
       		CLK_RNG1_PLL4R
       	>;

       	st,clkdiv = <
       		DIV(DIV_MPU, 1)
       	>;
       };

   This is needed because of a bug in the OP-TEE `rcc` driver, where it attempts
   to set the dividers and clocks even if none are provided.

Now all the clocks are effectively set by TF-A.

#### How to configure ETZPC from TF-A

To relieve OP-TEE of the ETZPC configuration duty, follow these steps:

1. To include the ETZPC driver in the Arm Trusted Firmware (TF-A) makefile, add
   the following line at the end of `plat/st/common/common.mk`:

       BL2_SOURCES		+=	drivers/st/etzpc/etzpc.c

2. In the STM32MP1 platform files included in TF-A, the ETZPC `DECPROT`
   assignments are incorrect. Replace all of `STM32MP1_ETZPC_` defines in
   `plat/st/stm32mp1/stm32mp1_def.h` with the values given in Table 85, "`DECPROT`
   assignment", of the STM32MP13xx Reference manual:

       #define STM32MP1_ETZPC_VREFBUF_ID	0
       #define STM32MP1_ETZPC_LPTIM2_ID	1
       #define STM32MP1_ETZPC_LPTIM3_ID	2
       #define STM32MP1_ETZPC_LTDC_ID		3
       #define STM32MP1_ETZPC_DCMIPP_ID	4
       #define STM32MP1_ETZPC_USBPHYCTRL_ID	5
       #define STM32MP1_ETZPC_DDRCTRLPHY_ID	6
       #define STM32MP1_ETZPC_IWDG1_ID		12
       #define STM32MP1_ETZPC_STGENC_ID	13
       #define STM32MP1_ETZPC_USART1_ID	16
       #define STM32MP1_ETZPC_USART2_ID	17
       #define STM32MP1_ETZPC_SPI4_ID		18
       #define STM32MP1_ETZPC_SPI5_ID		19
       #define STM32MP1_ETZPC_I2C3_ID		20
       #define STM32MP1_ETZPC_I2C4_ID		21
       #define STM32MP1_ETZPC_I2C5_ID		22
       #define STM32MP1_ETZPC_TIM12_ID		23
       #define STM32MP1_ETZPC_TIM13_ID		24
       #define STM32MP1_ETZPC_TIM14_ID		25
       #define STM32MP1_ETZPC_TIM15_ID		26
       #define STM32MP1_ETZPC_TIM16_ID		27
       #define STM32MP1_ETZPC_TIM17_ID		28
       #define STM32MP1_ETZPC_ADC1_ID		32
       #define STM32MP1_ETZPC_ADC2_ID		33
       #define STM32MP1_ETZPC_OTG_ID		34
       #define STM32MP1_ETZPC_RNG_ID		40
       #define STM32MP1_ETZPC_HASH_ID		41
       #define STM32MP1_ETZPC_CRYP_ID		42
       #define STM32MP1_ETZPC_SAES_ID		43
       #define STM32MP1_ETZPC_PKA_ID		44
       #define STM32MP1_ETZPC_BKPSRAM_ID	45
       #define STM32MP1_ETZPC_ETH1_ID		48
       #define STM32MP1_ETZPC_ETH2_ID		49
       #define STM32MP1_ETZPC_SDMMC1_ID	50
       #define STM32MP1_ETZPC_SDMMC2_ID	51
       #define STM32MP1_ETZPC_MCE_ID		53
       #define STM32MP1_ETZPC_FMC_ID		54
       #define STM32MP1_ETZPC_QSPI_ID		55
       #define STM32MP1_ETZPC_SRAM1_ID		60
       #define STM32MP1_ETZPC_SRAM2_ID		61
       #define STM32MP1_ETZPC_SRAM3_ID		62


3. Add the ETZPC node to the TF-A DTS file (`fdts/stm32mp131.dtsi`), under `soc
   { ... }`:

       etzpc: etzpc@5c007000 {
       	compatible = "st,stm32mp13-etzpc";
       	reg = <0x5c007000 0x400>;
       	clocks = <&rcc TZPC>;
       	#address-cells = <1>;
       	#size-cells = <1>;
       };

4. In the platform-specific TF-A BL2 (that is, bootloader) file
   `plat/st/stm32mp1/bl2_plat_setup.c`, add the ETZPC driver header file:

       #include <drivers/st/etzpc.h>

   Later in the same file, at the end of the function `bl2_platform_setup()`,
   add the desired ETZPC configuration:

       /* Configure ETZPC */
       if (etzpc_init() != 0) {
       	panic();
       }
       etzpc_configure_decprot(STM32MP1_ETZPC_SDMMC1_ID, ETZPC_DECPROT_NS_RW);

5. Repeat this process with as many `etzpc_configure_decprot()` calls as
   required for one's needs. For example, to duplicate the OP-TEE configuration
   (except for unsecuring `I2C4,` as per the steps at the beginning of this
   guide), we need the following:

       etzpc_configure_decprot(STM32MP1_ETZPC_ADC1_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_ADC2_ID,       ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_BKPSRAM_ID,    ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_CRYP_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_DCMIPP_ID,     ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_DDRCTRLPHY_ID, ETZPC_DECPROT_NS_R_S_W);
       etzpc_configure_decprot(STM32MP1_ETZPC_ETH1_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_ETH2_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_FMC_ID,        ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_HASH_ID,       ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_I2C3_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_I2C4_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_I2C5_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_IWDG1_ID,      ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_LPTIM2_ID,     ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_LPTIM3_ID,     ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_LTDC_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_MCE_ID,        ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_OTG_ID,        ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_PKA_ID,        ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_QSPI_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_RNG_ID,        ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SAES_ID,       ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SDMMC1_ID,     ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SDMMC2_ID,     ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SPI4_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SPI5_ID,       ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SRAM1_ID,      ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SRAM2_ID,      ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_SRAM3_ID,      ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_STGENC_ID,     ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_TIM12_ID,      ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_TIM13_ID,      ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_TIM14_ID,      ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_TIM15_ID,      ETZPC_DECPROT_S_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_TIM16_ID,      ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_TIM17_ID,      ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_USART1_ID,     ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_USART2_ID,     ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_USBPHYCTRL_ID, ETZPC_DECPROT_NS_RW);
       etzpc_configure_decprot(STM32MP1_ETZPC_VREFBUF_ID,    ETZPC_DECPROT_NS_RW);

6. Remove the ETZPC section (`&etzpc {...}`) from the OP-TEE DTS file
   `core/arch/arm/dts/stm32mp135f-dk.dts`.

Instead of following steps 1 through 6, we can apply the patch file
`0001-allow-large-bl33-and-config-etzpc-rcc.patch` to the TF-A code.

#### Check for additional SMC calls

At this stage, Linux is still issuing many SMC calls. We can see that by
inserting a function that prints a message into the OP-TEE SMC handler, as
follows.

1. In OP-TEE, define two "print" functions in `core/arch/arm/kernel/boot.c`:

       void __print_from_secure_smc(void)
       {
          EMSG_RAW("SMC from Secure");
       }

       void __print_from_nonsecure_smc(void)
       {
          EMSG_RAW("SMC from Non-Secure");
       }

2. Call these two functions from the OP-TEE secure monitor call (SMC) handler.
   Open `core/arch/arm/sm/sm_a32.S`, in function `sm_smc_entry`, and call
   `__print_from_secure_smc()` after checking the `SCR_NS` bit:

       /* Find out if we're doing an secure or non-secure entry */
       read_scr r1
       tst	r1, #SCR_NS
       bne	.smc_from_nsec
       bl __print_from_secure_smc

   A couple lines later, insert the "print from non-secure":

       .smc_from_nsec:
       	bl __print_from_nonsecure_smc

In the default configuration, I count as many as 1017 "SMC from Non-Secure"
messages reported by OP-TEE. What is going on? Some clues are to be found in the
Linux DTS file, `arch/arm/boot/dts/stm32mp131.dtsi`. In the `firmware { ... }`
section, there is an `optee` node with `method = "smc"`, as well as a `scmi`
sub-tree, listing `scmi_perf`, `scmi_clk`, `scmi_reset`, and `scmi_voltd`. We
need to go through these one by one and see whether they can be removed.

#### Unsecure access to the `RCC` registers

Before Linux can do its own clock configuration, `RCC` must be set so as to
allow non-secure access to the clock configurations. According to the STM32MP135
reference manual, the `RCC_SECCFGR` register can be used to "securely allocate
and partition each corresponding `RCC` resource/sub-function either to the
secure world or to the non-secure world."

1. In TF-A, add the following at the end of `bl2_platform_setup()` in file
   `plat/st/stm32mp1/bl2_plat_setup.c`:

       /* Allow non-secure access to all RCC clocks */
       mmio_write_32(stm32mp_rcc_base() + RCC_SECCFGR, 0);

2. (Optional.) To confirm that the clocks stay unsecured through the boot
   process (in particular, that OP-TEE does not mess with it), we can add the
   following function to the Linux `RCC` driver in
   `drivers/clk/stm32/clk-stm-32-core.c`:

       #include "stm32mp13_rcc.h"

       void print_seccfgr(void __iomem *rcc_base)
       {
               /* Read RCC secure configuration register */
       	uint32_t seccfgr = ioread32(rcc_base + RCC_SECCFGR);
       	printk(KERN_WARNING "Hello2! RCC_SECCFGR = 0x%x\n", seccfgr);

               const char* names[] = {
                  "RCC_SECCFGR_HSISEC", "RCC_SECCFGR_CSISEC", "RCC_SECCFGR_HSESEC",
                  "RCC_SECCFGR_LSISEC", "RCC_SECCFGR_LSESEC", "Res", "Res", "Res",
                  "RCC_SECCFGR_PLL12SEC", "RCC_SECCFGR_PLL3SEC", "RCC_SECCFGR_PLL4SEC",
                  "RCC_SECCFGR_MPUSEC", "RCC_SECCFGR_AXISEC", "RCC_SECCFGR_MLAHBSEC",
                  "Res", "Res", "RCC_SECCFGR_APB3DIVSEC", "RCC_SECCFGR_APB4DIVSEC",
                  "RCC_SECCFGR_APB5DIVSEC", "RCC_SECCFGR_APB6DIVSEC",
                  "RCC_SECCFGR_TIMG3SEC", "RCC_SECCFGR_CPERSEC", "RCC_SECCFGR_MCO1SEC",
                  "RCC_SECCFGR_MCO2SEC", "RCC_SECCFGR_STPSEC", "RCC_SECCFGR_RSTSEC",
                  "Res", "Res", "Res", "Res", "Res", "RCC_SECCFGR_PWRSEC",
               };

               for (int i=0; i<32; i++) {
                  printk(KERN_WARNING "%s\t\t\t%s\r\n", names[i],
                        ((seccfgr & (1U << i)) == 0) ? ("Non-Secure") : ("Secure"));
               }
       }

   Call this function at the end of `stm32_rcc_init()`:

       int stm32_rcc_init(struct device *dev, const struct of_device_id *match_data,
       		   void __iomem *base)
       {
       ...
       	print_seccfgr(base);
       	return 0;
       }

   If everything works out, the following printout appears in the kernel log
   when it boots:

       [    4.756561] Hello2! RCC_SECCFGR = 0x0
       [    4.756637] RCC_SECCFGR_HSISEC			Non-Secure
       [    4.756668] RCC_SECCFGR_CSISEC			Non-Secure
       [    4.756693] RCC_SECCFGR_HSESEC			Non-Secure
       [    4.756718] RCC_SECCFGR_LSISEC			Non-Secure
       [    4.756742] RCC_SECCFGR_LSESEC			Non-Secure
       [    4.756766] Res			Non-Secure
       [    4.756788] Res			Non-Secure
       [    4.756809] Res			Non-Secure
       [    4.756831] RCC_SECCFGR_PLL12SEC			Non-Secure
       [    4.756855] RCC_SECCFGR_PLL3SEC			Non-Secure
       [    4.756880] RCC_SECCFGR_PLL4SEC			Non-Secure
       [    4.756904] RCC_SECCFGR_MPUSEC			Non-Secure
       [    4.756928] RCC_SECCFGR_AXISEC			Non-Secure
       [    4.756951] RCC_SECCFGR_MLAHBSEC			Non-Secure
       [    4.756975] Res			Non-Secure
       [    4.756997] Res			Non-Secure
       [    4.757019] RCC_SECCFGR_APB3DIVSEC			Non-Secure
       [    4.757043] RCC_SECCFGR_APB4DIVSEC			Non-Secure
       [    4.757068] RCC_SECCFGR_APB5DIVSEC			Non-Secure
       [    4.757093] RCC_SECCFGR_APB6DIVSEC			Non-Secure
       [    4.757117] RCC_SECCFGR_TIMG3SEC			Non-Secure
       [    4.757142] RCC_SECCFGR_CPERSEC			Non-Secure
       [    4.757242] RCC_SECCFGR_MCO1SEC			Non-Secure
       [    4.757273] RCC_SECCFGR_MCO2SEC			Non-Secure
       [    4.757298] RCC_SECCFGR_STPSEC			Non-Secure
       [    4.757323] RCC_SECCFGR_RSTSEC			Non-Secure
       [    4.757347] Res			Non-Secure
       [    4.757369] Res			Non-Secure
       [    4.757390] Res			Non-Secure
       [    4.757412] Res			Non-Secure
       [    4.757433] Res			Non-Secure
       [    4.757455] RCC_SECCFGR_PWRSEC			Non-Secure

See section 10.8.1, "`RCC` secure configuration register (`RCC_SECCFGR`)", of
the STM32MP135 reference manual for more information about the above printout.

#### Configure all clocks from Linux

In this section, we explain how to configure all necessary system clocks
directly from the Linux kernel, without the use of SMC calls to OP-TEE via the
SCMI protocol.

1. Disable `CONFIG_COMMON_CLK_SCMI` entry in the kernel configuration (under
   Device Drivers -> Common Clock Framework -> Clock driver controlled via SCMI
   interface). This prevents the inclusion of the SCMI clock driver
   (`clk-scmi.c`), and thereby the registration of unnecessary SCMI clocks.

   Additionally, the following entries will not be needed:

       CONFIG_ARM_SCMI_POWER_DOMAIN
       CONFIG_SENSORS_ARM_SCMI
       CONFIG_REGULATOR_ARM_SCMI
       CONFIG_RESET_SCMI
       CONFIG_ARM_SCMI_TRANSPORT_MAILBOX
       CONFIG_TRUSTED_FOUNDATIONS
       CONFIG_ARM_SMC_WATCHDOG
       CONFIG_CPU_FREQ
       CONFIG_CPU_IDLE
       CONFIG_ARM_SMCCC_SOC_ID
       CONFIG_ARM_SCMI_TRANSPORT_SMC

2. Patch the kernel clock driver for STM32 to include the clocks formerly
   managed by OP-TEE. This requires substantial changes in the kernel source
   tree under `drivers/clk/stm32`, as well as to the device DTS files in
   `arch/arm/boot/dts`. Rather than doing it manually, use the provided patch
   file `0004-add-stm32mp1-basic-clock-drivers.patch`.

3. In TF-A, in file `plat/st/stm32mp1/bl2_plat_setup.c`, add the following lines
   at the end of `bl2_platform_setup()`:

       /* Allow non-secure access to all RCC clocks */
       mmio_write_32(stm32mp_rcc_base() + RCC_SECCFGR, 0);

       /* Allow non-secure access to all RTC registers */
       #define RTC_SECCFGR 0x20
       mmio_write_32(RTC_BASE + RTC_SECCFGR, 0);

   Alternatively, apply the patch `0002-unsecure-rcc-rtc.patch`.

4. Now the entire `scmi { ... }` subtree is no longer needed in
   `arch/arm/boot/dts/stm32mp131.dtsi`. Remove it, and also remove references to
   `scmi` items in this DTS file, and any included from it. Unfortunately, the
   `optee { ... }` node is still required.

#### Remove further SMC calls

Now we're down to about 75 SMC calls. Steps to cut it down further:

1. In `arch/arm/mach-stm32/KConfig`, remove the following line:

       select ARM_PSCI if ARCH_MULTI_V7

   Open `make linux-menuconfig` and disable `CONFIG_ARM_PSCI` (under Kernel
   Features -> Support for the ARM Power State Coordination Interface (PSCI)).

   This removes about eight SMC calls, including a couple at the very beginning
   of the boot sequence.

2. In `arch/arm/boot/dts/stm32mp131.dtsi`, remove the entire `pm_domain { ... }`
   subtree. Search for references to `pd_core_ret` and `pd_core`, and remove
   them. This gets rid of another eight or so SMC calls.

3. (Optional.) Many of the remaining SMC calls are through the OP-TEE driver in
   the Linux kernel, `drivers/tee/optee/smc_abi.c`. In `optee_smccc_smc()`, add
   `dump_stack();` at the beginning of the function to trace down all of these
   SMC calls.

4. In the board DTS file, look for the lines:

       nvmem-cells = <&ethernet_mac1_address>;
       nvmem-cell-names = "mac-address";

   and replace them with an explicit statement of the MAC address:

       mac-address = [00 19 B3 11 00 00];

   This way, the kernel does not need to look for the MAC address in `NVMEM,`
   which is under control of OP-TEE. (Alternatively, we can unsecure `NVMEM`
   itself, but that seems like more work.)

   Remove also the references to `NVMEM` in other DTS files, such as the following
   lines in `arch/arm/boot/dts/stm32mp131.dtsi` under `cpus/cpu0`:

       nvmem-cells = <&part_number_otp>;
       nvmem-cell-names = "part_number";

   And also under `adc2`:

       nvmem-cells = <&vrefint>;
       nvmem-cell-names = "vrefint";

5. Now we can remove the following keys from the kernel configuration:

       CONFIG_ARM_SCMI_PROTOCOL
       CONFIG_TEE

With that, there is only one more SMC call remaining --- the initial SMC call
from within OP-TEE to transfer control to Linux. In other words, OP-TEE is now
doing nothing at all after Linux gets started. However, before that happens,
OP-TEE still does a couple things. Let's track them down.

#### Things OP-TEE does before starting Linux

Before passing control to Linux, OP-TEE does several things:

- Clear the `GPIOx_SECCFGR` bits to allow non-secure access to GPIO.

- Configure the GIC interrupt controller.

- Register the SMC handler.

- Call the SMC handler, passing DTB address and Linux entry point.

To be able to remove OP-TEE, we have to do these configuration tasks from TF-A,
as follows:

1. In `plat/st/stm32mp1/bl2_plat_setup.c`, add the GPIO driver header file:

       #include <drivers/st/stm32_gpio.h>

   Later in the same file, at the end of the function `bl2_platform_setup()`,
   add the code to allow unsecure access to GPIO:

       /* Allow non-secure access to all GPIO banks */
       for (unsigned int bank = GPIO_BANK_A; bank <= GPIO_BANK_I; bank++) {
       	uintptr_t base = stm32_get_gpio_bank_base(bank);
       	unsigned long clock = stm32_get_gpio_bank_clock(bank);

       	clk_enable(clock);
       	mmio_write_32(base + GPIO_SECR_OFFSET, 0);
       	clk_enable(clock);
       }

2. In `plat/st/stm32mp1/bl2_plat_setup.c`, call the GIC initialization function
   at the end of `bl2_el3_plat_prepare_exit()`:

       /* Initialize GIC interrupt controller */
       stm32mp135_gic_init();

   The function needs to be adapted from OP-TEE source code, as follows:

       #define GICC_BASE    0xA0022000
       #define GICD_BASE    0xA0021000
       #define STM32MP135_GIC_MAX_REG  5
       #define GICC_PMR                (0x004)

       void stm32mp135_gic_init(void)
       {
       	for (size_t n = 0; n <= STM32MP135_GIC_MAX_REG; n++) {
       		/* Disable interrupts */
       		mmio_write_32(GICD_BASE + GICD_ICENABLER + 4*n, 0xffffffff);
       		/* Make interrupts non-pending */
       		mmio_write_32(GICD_BASE + GICD_ICPENDR + 4*n, 0xffffffff);
       	};

       	for (size_t n = 0; n <= STM32MP135_GIC_MAX_REG; n++) {
       		/* Mark interrupts non-secure */
       		if (n == 0) {
       			/* per-CPU inerrupts config:
       			 * ID0-ID7(SGI)	  for Non-secure interrupts
       			 * ID8-ID15(SGI)  for Secure interrupts.
       			 * All PPI config as Non-secure interrupts.
       			 */
       			mmio_write_32(GICD_BASE + GICD_IGROUPR + 4*n, 0xffff00ff);
       		} else {
       			mmio_write_32(GICD_BASE + GICD_IGROUPR + 4*n, 0xffffffff);
       		}
       	}

       	/* Set the priority mask to permit Non-secure interrupts, and to
       	 * allow the Non-secure world to adjust the priority mask itself
       	 */
       	mmio_write_32(GICC_BASE + GICC_PMR, GIC_HIGHEST_NS_PRIORITY);
       }

   Note that this function cannot be called from `bl2_platform_setup()`, at
   least not without further modifications to the code. The STM32MP135 manual
   says that "Memory regions marked as normal memory cannot access any of the
   GIC registers, instead access caches or external memory as required." The
   function `bl2_platform_setup()` is run with MMU enabled, so attempting to
   access the registers directly probably causes a page fault; all I can see is
   that the device freezes.

3. In `bl2/aarch32/bl2_run_next_image.S`, define the following constants:

       #define CPSR_MODE_SVC	U(0x13)
       #define CPSR_I		BIT(7)
       #define CPSR_F		BIT(6)
       #define SCR_NS		(1U << 0)
       #define ACTLR_SMP	(1U << 6)
       #define SCTLR_M		(1U << 0)
       #define SCTLR_C		(1U << 2)
       #define SCTLR_I		(1U << 12)
       #define SCTLR_TE	(1U << 30)
       #define SCTLR_SPAN	(1U << 23)
       #define SCTLR_A		(1U << 1)

   Define the following macros:

       .macro write_actlr reg
       mcr     p15, 0, \reg, c1, c0, 1
       .endm

       .macro read_actlr reg
       mrc     p15, 0, \reg, c1, c0, 1
       .endm

       .macro read_sctlr reg
       mrc     p15, 0, \reg, c1, c0, 0
       .endm

       .macro write_sctlr reg
       mcr     p15, 0, \reg, c1, c0, 0
       .endm

       .macro write_mvbar reg
       mcr     p15, 0, \reg, c12, c0, 1
       .endm

       .macro read_scr reg
       mrc     p15, 0, \reg, c1, c1, 0
       .endm

       .macro write_scr reg
       mcr     p15, 0, \reg, c1, c1, 0
       .endm

   Define the SMC handler:

       func sm_smc_entry
       	/* Update SCR */
       	read_scr r0
       	orr	r0, r0, #SCR_NS
       	write_scr r0
       	mov	r0, #0

       	/* Return from the secure monitor call */
       	push	{r4}
       	push	{r3}
       	rfefd	sp
       endfunc sm_smc_entry

   Define the SM vector table:

       func sm_vect_table
       	.balign 32
       	b	.		/* Reset			*/
       	b	.		/* Undefined instruction	*/
       	b	sm_smc_entry	/* Secure monitor call		*/
       	b	.		/* Prefetch abort		*/
       	b	.		/* Data abort			*/
       	b	.		/* Reserved			*/
       	b	.		/* IRQ				*/
       	b	.		/* FIQ				*/
       endfunc sm_vect_table

4. In the same file, replace `bl2_run_next_image` with the following function:

       func bl2_run_next_image
       	mov	r8,r0

       	/*
       	 * MMU needs to be disabled because both BL2 and BL32 execute
       	 * in PL1, and therefore share the same address space.
       	 * BL32 will initialize the address space according to its
       	 * own requirement.
       	 */
       	bl	disable_mmu_icache_secure
       	stcopr	r0, TLBIALL
       	dsb	sy
       	isb
       	mov	r0, r8
       	bl	bl2_el3_plat_prepare_exit

       	/* Enable coherent requests to the processor */
       	read_actlr r0
       	orr	r0, r0, #ACTLR_SMP
       	write_actlr r0

       	/* Setup core configuration in CP15 SCTLR */
       	read_sctlr r0
       	bic	r0, r0, #SCTLR_M	/* disable MPU */
       	bic	r0, r0, #SCTLR_C	/* disable data and unified caches */
       	bic	r0, r0, #SCTLR_I	/* disable instruction caches */
       	bic	r0, r0, #SCTLR_TE	/* exceptions taken in ARM state */
       	orr	r0, r0, #SCTLR_SPAN
       	bic	r0, r0, #SCTLR_A	/* disable alignment fault checking */
       	write_sctlr r0
       	isb

       	/* Set monitor vector (MVBAR) */
       	ldr	r0, =sm_vect_table
       	write_mvbar r0

       	/* Will switch to SVC mode with IRQ and FIQ disabled */
       	mov	r4, #(CPSR_MODE_SVC | CPSR_I | CPSR_F)

       	/* Linux entry address */
       	ldr	r3, [r8, #ENTRY_POINT_INFO_LR_SVC_OFFSET]

       	/* Linux arguments */
       	add	r8, r8, #ENTRY_POINT_INFO_ARGS_OFFSET
       	ldm	r8, {r0, r1, r2}

       	/* Call the Secure Monitor handler */
       	mov	r1, #0
       	mov	r0, #0
       	smc	#0
       endfunc bl2_run_next_image

3. In `plat/st/stm32mp1/bl2_plat_setup.c`, add the header files for TrustZone
   memory protection:

       #include <drivers/arm/tzc400.h>
       #include <dt-bindings/soc/stm32mp13-tzc400.h>

   In the same file, remove function `prepare_encryption()` entirely. Remove the
   body of the function `bl2_plat_handle_post_image_load()` and replace it with
   a simple `return 0;`.

   In `bl2_el3_plat_prepare_exit()`, remove the statement
   `stm32mp1_security_setup();` and replace it with the following:

       /* Configure TrustZone memory protection */
       tzc400_init(STM32MP1_TZC_BASE);
       tzc400_disable_filters();
       tzc400_configure_region0(TZC_REGION_S_NONE, TZC_REGION_NSEC_ALL_ACCESS_RDWR);
       tzc400_set_action(TZC_ACTION_INT);
       tzc400_enable_filters();

Now that OP-TEE no longer runs, there is no need to load it in the `FIP` package
or the memory. Remove it as follows:

1. In TF-A (`bl2/aarch32/bl2_run_next_image.S`), in `bl2_run_next_image`,
    replace `ENTRY_POINT_INFO_LR_SVC_OFFSET` with `ENTRY_POINT_INFO_PC_OFFSET`.

2. In `plat/st/stm32mp1/plat_bl2_mem_params_desc.c`, remove the entries
   corresponding to `BL32_IMAGE_ID`, `BL32_EXTRA1_IMAGE_ID`,
   `BL32_EXTRA2_IMAGE_ID`, and `TOS_FW_CONFIG_ID`.

   In entries for `HW_CONFIG_ID` and `BL33_IMAGE_ID`, replace
   `IMAGE_ATTRIB_SKIP_LOADING` with `0`.

   For all three entries, fill out the `image_base` and `image_max_size` fields,
   as follows. For `FW_CONFIG_ID`, add:

      .image_info.image_base = STM32MP_FW_CONFIG_BASE,
      .image_info.image_max_size = STM32MP_FW_CONFIG_MAX_SIZE,

   For `HW_CONFIG_ID`, add:

       .image_info.image_base = STM32MP_HW_CONFIG_BASE,
       .image_info.image_max_size = STM32MP_HW_CONFIG_MAX_SIZE,

   For `BL33_IMAGE_ID`, add:

       .image_info.image_base = STM32MP_BL33_BASE,
       .image_info.image_max_size = STM32MP_BL33_MAX_SIZE,

   For `BL33_IMAGE_ID`, add the `EP_FIRST_EXE` flag to the flags already given
   in `SET_STATIC_PARAM_HEAD()`. Add the following line:

       .ep_info.pc = STM32MP_BL33_BASE,

3. In Buildroot configuration (`make menuconfig`), under Bootloaders, disable
   `optee_os` (`BR2_TARGET_OPTEE_OS`).

   Under "Additional ATF build variables"
   (`BR2_TARGET_ARM_TRUSTED_FIRMWARE_ADDITIONAL_VARIABLES`), remove
   `AARCH32_SP=optee`.

4. In the TF-A Makefile, remove the line that says `NEED_BL32 := yes`.

All the above changes to TF-A can also be found in `0003-remove-optee.patch`.


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

TBD

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

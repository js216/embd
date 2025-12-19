---
title: Unsecuring STM32MP135 TrustZone
author: Jakob Kastelic
date:
topic: Embedded
description: >
---

![](../images/mia.jpg)

The STM32MP135 integrates the Arm TrustZone extension which partitions the
system into two isolated security domains, the secure and non-secure worlds,
depending on the state of the `NS` bit. On reset, it executes in the secure
world (`NS=0`), but in normal operation, we want `NS=1`.

In this article, we explain how to execute the world transitions in a bare-metal
environment. See [this article](https://embd.cc/stm32mp135-without-optee) to
learn how to do it in the context of Arm Trusted Firmware (TF-A) and Linux.

### Change worlds with SMC handler

The `NS` bit is only supposed to be flipped in the Secure Monitor handler,
invoked with the `smc` instruction. Thus a minimum handler might look as follows
(assumes the return address is passed in via `r3`):

```asm
.align 2
sm_smc_entry:
   mrc p15, 0, r0, c1, c1, 0 // read SCR
   orr r0, r0, #SCR_NS
   mcr p15, 0, r0, c1, c1, 0 // write SCR
   mov r0, #0

   mov r4, #(CPSR_MODE_SVC | CPSR_I | CPSR_F)
   push  {r4} // CPSR after return
   push  {r3} // PC after return
   rfefd sp
```

We see that the `NS` bit lives in the `SCR` register, and that there is a
special syntax to access that register. To exit from the SMC handler, we push
the desired exception state (SVC mode with IRQ and FIQ disabled) on the stack
together with the return address, and then exit with `rfefd sp`.

### Installing the SMC handler

Before we can call `smc`, we should create the exception table. If the SMC is
the only exception we care about, a minimal table might look as follows:

```asm
.align 5
sm_vect_table:
   b .            // Reset
   b .            // Undefined instruction
   b sm_smc_entry // Secure monitor call
   b .            // Prefetch abort
   b .            // Data abort
   b .            // Reserved
   b .            // IRQ
   b .            // FIQ
```

Then, sometime before calling `smc`, install it in the `MVBAR` register as
follows:

```asm
ldr r0, =sm_vect_table
mcr p15, 0, r0, c12, c0, 1 // MVBAR
```

### Unsecuring the system

The system and peripherals must be set up with access allowed from the
non-secure world before we flip the `NS` bit, otherwise the system will just
freeze. Here's a list of things that must be unsecured before the flip:

- DDR unsecured via the TZC-400 firewall
- GIC distributor and CPU interface
- ETZPC = Embedded TrustZone Protection Controller
- Clock and reset control (RCC)
- RTC registers
- Pin controller / all GPIO banks
- AHB/APB bridges, peripheral sub-matrices
- Console UART
- Timer sources
- SYSRAM / SRAM blocks
- DMA1 / DMA2 / DMAMUX
- DMA masters: SDMMC, ETH, USB OTG, SPI, ...
- SCU must be enabled, coherency configured
- Exception vectors & CPU state: SCTLR, ACTLR, Cache state, MMU state

In the following sections, we will examine these one by one, showing how to
unsecure then and how to verify they have been unsecured.

### DDR / TZC-400



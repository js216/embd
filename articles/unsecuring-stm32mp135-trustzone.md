---
title: Unsecuring STM32MP135 TrustZone
author: Jakob Kastelic
date: 22 Dec 2025
topic: Embedded
description: >
   A practical guide to disabling TrustZone protections on the STM32MP135,
   covering secure monitor calls, SCR.NS transitions, and unsecuring DDR, GIC,
   ETZPC, clocks, GPIOs, and peripherals for bare-metal execution.
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
- Timer source/s
- SYSRAM / SRAM blocks
- DMA1 / DMA2 / DMAMUX
- DMA masters: SDMMC, ETH, USB OTG, SPI, ...
- SCU must be enabled, coherency configured
- Exception vectors & CPU state: SCTLR, ACTLR, Cache state, MMU state

In the following sections, we will examine these one by one, showing how to
unsecure then and how to verify they have been unsecured.

### Unsecure DDR with TZC-400

Let's configure the TZC to allow DDR `Region0` R/W non-secure access for all
IDs. While we can use the TZC to partition the RAM into several regions, we will
use `Region0` only which is always enabled. (The region implicitly covers the
entire address space.)

```c
TZC->GATE_KEEPER = 0;
TZC->REG_ID_ACCESSO = 0xFFFFFFFF;
TZC->REG_ATTRIBUTESO = 0xC0000001;
TZC->GATE_KEEPER |= 1U;
```

First, the "gate keeper" is disabled so that we can modify the configuration.
Then, we set the access bits to all ones, so that that each NSAID gets both
write and read permission. Next, we set the attributes so that secure global
write and read are enabled, and the filter is enabled for the region. Finally,
we "close" the gate keeper so that the configuration is active.

To verify that the configuration worked, we print out all the fields from the
TZC struct defined in the CMSIS Device Peripheral Access Layer Header File
(`stm32mp135fxx_ca7.h`):

    [TZC dump] begin
      BUILD_CONFIG     = 0x00001F08
      ACTION           = 0x00000000
      GATE_KEEPER      = 0x00010001
      SPECULATION_CTRL = 0x00000000
      REG_BASE_LOWO    = 0x00000000
      REG_BASE_HIGHO   = 0x00000000
      REG_TOP_LOWO     = 0xFFFFFFFF
      REG_TOP_HIGHO    = 0x00000000
      REG_ATTRIBUTESO  = 0xC0000001
      REG_ID_ACCESSO   = 0xFFFFFFFF
    [TZC dump] end

Of course, we will not be able to verify that the configuration actually works
till we unsecure everything else on the list. Then, we will switch the CPU to
nonsecure world and verify that read and write from DDR succeeds.

### GIC distributor

The Generic Interrupt Controller is split into two parts: the Distributor (GICD)
takes care of the global IRQ configuration, while the CPU interface (GICC) does
the per-CPU IRQ delivery. In TrustZone, there are two interrupt groups:

- Group 0 corresponds to the Secure world
- Group 1 corresponds to the Non-Secure world

Now we go step by step, enabling non-secure access to/from interrupts. First we
configure the interrupts themselves as non-secure:

Allow both Group 0 and 1 interrupts to be forwarded from the GICD to the CPU
interfaces. The GICD control register (`GICD_CTLR`) is included in the CMSIS
file `core_ca.h` in the `GICDistributor_Type` struct:

```c
GICDistributor->CTLR = 0x03U;
```

Just before switching to non-secure world, we will disable all interrupts, mark
them as non-pending, and move to Group 1 (non-secure):

```c
const int num_reg = 5;
for (uint32_t n = 0; n <= num_reg; n++) {
  GICDistributor->ICENABLER[n] = 0xffffffff;
  GICDistributor->ICPENDR[n]   = 0xffffffff;
  GICDistributor->IGROUPR[n]   = 0xffffffff;
}
```

### GIC CPU interface

In the CPU interface control register, enable Group 1 signaling:

```c
GICInterface->CTLR |= 0x03U;
```

Priority masking: allow all priority levels to pass through:

```c
GICInterface->PMR = 0xFFU;
```

Now we can dump all the GICC registers after handoff:

```
[GICC dump] begin
  CTLR    = 0x00000003
  PMR     = 0x000000F8
  BPR     = 0x00000002
  IAR     = 0x000003FF
  EOIR    = 0x00000000
  RPR     = 0x000000FF
  HPPIR   = 0x000003FF
  ABPR    = 0x00000003
  AIAR    = 0x000003FF
  AEOIR   = 0x00000000
  AHPPIR  = 0x000003FF
  STATUSR = 0x00000000
  APR[0]   = 0x00000000
  APR[1]   = 0x00000000
  APR[2]   = 0x00000000
  APR[3]   = 0x00000000
  NSAPR[0] = 0x00000000
  NSAPR[1] = 0x00000000
  NSAPR[2] = 0x00000000
  NSAPR[3] = 0x00000000
  IIDR    = 0x0102143B
  DIR     = 0x00000000
[GICC dump] end
```

This means:

- `CTLR` enables Group 0 and 1 interrupts
-  `PMR` sets `PRIORITY[4:0] = 0b11111`, which allows all non-secure interrupts
   to be signaled
- `BPR` controls how the 8-bit interrupt priority field is split into a group
  priority field
- `IAR` shows `CPUID = 0`, and `INTERRUPT_ID` = 1023, which indicates a
  "Spurious interrupt ID" (no pending interrupt at the CPU interface)
- `EOIR`: `CPUID = 0`, end-of-interrupt ID = 0, i.e. no interrupt being
  completed
- `RPR`: `PRIORITY[4:0] = 0b11111`, current running priority on the CPU
  interface indicates no active interrupt

### ETZPC = Enhanced TrustZone Protection Controller

Now we open access to all peripherals protected by ETZPC. Luckily the ST HAL
includes a function to open the entire ETZPC to non-secure access:

```c
__HAL_RCC_ETZPC_CLK_ENABLE();

// unsecure SYSRAM
LL_ETZPC_SetSecureSysRamSize(ETZPC, 0);

// unsecure peripherals
LL_ETZPC_Set_All_PeriphProtection(ETZPC,
     LL_ETZPC_PERIPH_PROTECTION_READ_WRITE_NONSECURE);
```

Let's print out the ETZPC registers after running this:

```

[ETZPC dump] begin
  TZMA0_SIZE       = 0x8000000D
  TZMA1_SIZE       = 0x00000000
  DECPROT0         = 0xFFFFFFFF
  DECPROT1         = 0xFFFFFFFF
  DECPROT2         = 0xFFFFFFFF
  DECPROT3         = 0xFFFFFFFF
  DECPROT4         = 0x00000000
  DECPROT5         = 0x00000000
  DECPROT_LOCK0    = 0x00000000
  DECPROT_LOCK1    = 0x00000000
  DECPROT_LOCK2    = 0x00000000
  HWCFGR           = 0x00004002
  IP_VER           = 0x00000020
  ID               = 0x00100061
  SID              = 0xA3C5DD01
[ETZPC dump] end
```

This means that SYSRAM and ETZPC are fully non-secure.

### Clock and reset control (RCC)

Through the RCC secure configuration register (`RCC_SECCFGR`), we may configure
various clocks to be either secure or non-secure. Easy enough to unsecure:

```c
RCC->SECCFGR = 0x00000000;
```

### Pin controller / all GPIO banks

Likewise, after enabling the GPIOs, we need to allow non-secure access to them:

```c
GPIOA->SECCFGR = 0x00000000;
GPIOB->SECCFGR = 0x00000000;
GPIOC->SECCFGR = 0x00000000;
GPIOD->SECCFGR = 0x00000000;
GPIOE->SECCFGR = 0x00000000;
GPIOF->SECCFGR = 0x00000000;
GPIOG->SECCFGR = 0x00000000;
GPIOH->SECCFGR = 0x00000000;
```

### State of the boot process so far

With the steps above done, a program will run in the non-secure world (`NS=1`).
However, most of the diagnostics to get there will probe secure-only registers,
such as those used by the TZC, which will result in an immediate undefined
instruction or similar abort.

In other words, in non-secure world, you are limited to non-secure things!

---
title: Action Without Clinging
author: Jakob Kastelic
date: 21 Sep 2025
topic: Incoherent Thoughts
description: >
   Detach from control and ownership. Let action flow naturally without fixation
   on goals.
---

![](../images/lmp.jpg)

Here's the catch I want to flag: on the 21569, DAI0_PIN13..PIN18 are not reachable from any SPORT —
  the SRU source tables 22-10/11/12 mark selection codes 0x0C,0x0D,0x10,0x11 as Reserved in all three
  groups, so SPORT signals cannot be routed onto DAI0_PB13..PB18. Those pins on P13's left column are
  only useful for non-SPORT peripherals.

  The good news is DAI1 has its own SRU instance with identical structure (HRM table 22-16/17/18), and
  21569 does have SPORT4..SPORT7 at register base 0x31002400+ routed through DAI1 exactly the way
  SPORT0..3 route through DAI0. Their default pin-buffer assignments mirror SPORT0's on DAI0:

  ┌───────────────────────────┬─────────────────────────┬─────────┐
  │       SPORT4 signal       │ default DAI1 pin buffer │ P13 pin │
  ├───────────────────────────┼─────────────────────────┼─────────┤
  │ SPT4_AD0  (TX data)       │ DAI1_PB01               │ 2       │
  ├───────────────────────────┼─────────────────────────┼─────────┤
  │ SPT4_ACLK (TX clock)      │ DAI1_PB03               │ 6       │
  ├───────────────────────────┼─────────────────────────┼─────────┤
  │ SPT4_AFS  (TX frame sync) │ DAI1_PB04               │ 8       │
  ├───────────────────────────┼─────────────────────────┼─────────┤
  │ SPT4_BD0  (RX data)       │ DAI1_PB05               │ 10      │
  ├───────────────────────────┼─────────────────────────┼─────────┤
  │ SPT4_BCLK (RX clock)      │ DAI1_PB07               │ 14      │
  ├───────────────────────────┼─────────────────────────┼─────────┤
  │ SPT4_BFS  (RX frame sync) │ DAI1_PB08               │ 16      │
  └───────────────────────────┴─────────────────────────┴─────────┘

  Proposed jumpers on P13 (three wires)

  ┌────────┬────────────────────┬──────────────────────────────────────┐
  │ Jumper │     From → To      │               Carries                │
  ├────────┼────────────────────┼──────────────────────────────────────┤
  │ 1      │ P13 pin 2 ↔ pin 10 │ serial data (SPT4_AD0 → SPT4_BD0)    │
  ├────────┼────────────────────┼──────────────────────────────────────┤
  │ 2      │ P13 pin 6 ↔ pin 14 │ serial clock (SPT4_ACLK → SPT4_BCLK) │
  ├────────┼────────────────────┼──────────────────────────────────────┤
  │ 3      │ P13 pin 8 ↔ pin 16 │ frame sync (SPT4_AFS → SPT4_BFS)     │
  └────────┴────────────────────┴──────────────────────────────────────┘

I have connected C3 to DAI1_PIN20 (P13 pin 40), and C4 to SPI0_MISO (P14 pin 3)

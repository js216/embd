---
title: Ethernet on Bare-Metal STM32MP135
author: Jakob Kastelic
date: 21 Jan 2026
topic: Embedded
description: >
   Bringing up Ethernet on the STM32MP135 in bare metal, with pitfalls in RMII
   clocking, PHY straps, and PLL configuration.
---

![](../images/si.jpg)

In this writeup we'll go through the steps needed to bring up the Ethernet
peripheral (`ETH1`) on the STM32MP135 [eval
board](https://www.st.com/en/evaluation-tools/stm32mp135f-dk.html) as well as a
[custom board](https://github.com/js216/stm32mp135_test_board).

### Eval board connections to PHY

The evaluation board uses the `LAN8742A-CZ-TR` Ethernet PHY chip, connected to
the SoC as follows:

| PHY pin  | PHY signal     | SoC signal        | SoC pin | Alt. Fn. | Notes   |
| -------- | -------------- | ----------------- | ------- | -------- | ------- |
| 16       | `TXEN`         | `PB11/ETH1_TX_EN` | `AA2`   | AF11     |         |
| 17       | `TXD0`         | `PG13/ETH1_TXD0`  | `AA9`   | AF11     |         |
| 18       | `TXD1`         | `PG14/ETH1_TXD1`  | `Y10`   | AF11     |         |
| 8        | `RXD0/MODE0`   | `PC4/ETH1_RXD0`   | `Y7`    | AF11     | 10k PU  |
| 7        | `RXD1/MODE1`   | `PC5/ETH1_RXD1`   | `AA7`   | AF11     | 10k PU  |
| 11       | `CRS_DV/MODE2` | `PC1/ETH1_CRS_DV` | `Y9`    | **AF10** | 10k PU  |
| 13       | `MDC`          | `PG2/ETH1_MDC`    | `V3`    | AF11     |         |
| 12       | `MDIO`         | `PA2/ETH1_MDIO`   | `Y4`    | AF11     | 1k5 PU  |
| 15       | `nRST`         | `ETH1_NRST`       | `IO9`   |          | MPC IO  |
| 14       | `nINT/RECLKO`  | `PA1/ETH1_RX_CLK` | `AA3`   | AF11     |         |

### Reset pin

In this design, the Ethernet PHY connected to ETH1 has its own 25MHz crystal.
Note the `ETH1_RX_CLK` connection, which uses the `MCP23017T-E/ML` I2C I/O
expander.

One wonders if it was really necessary to complicate Ethernet bringup by
requiring this extra step (I2C + IO config) on an SoC that has 320 pins. True to
form, the simple IO expander needs more than 1,300 lines of ST driver code plus
lots more in the pointless `BSP` abstraction layer wrapper.

With a driver that complicated, it's easier to start from scratch. As it
happens, writing these GPIO pins involves just two I2C transactions. The I2C
code is trivial, find it
[here](https://github.com/js216/stm32mp135-bootloader/blob/main/src/mcp23x17.c).

### Sending an Ethernet frame from eval board

Again ST code examples are very complex, but it takes just over 300 lines of
code to send an Ethernet frame, by way of verifying that data can be transmitted
over this interface. I asked ChatGPT to summarize what happens in the
[code](https://github.com/js216/stm32mp135-bootloader/blob/main/src/eth.c):

1. **Configure the pins for Ethernet** First, all the GPIO pins required by the
   RMII interface are set up. Each pin is switched to its Ethernet alternate
   function, configured for push-pull output, and set to a high speed. This
   ensures the STM32's MAC can physically drive the Ethernet lines correctly. If
   you're using an external GPIO expander like the MCP23x17, it is also
   initialized here, and relevant pins are set high to enable the PHY or other
   control signals.

2. **Enable the Ethernet clocks** Before the MAC can operate, the clocks for the
   Ethernet peripheral---MAC, TX, RX, and the reference clock---are enabled in
   the RCC. This powers the Ethernet block inside the STM32 and allows it to
   communicate with the PHY.

3. **Initialize descriptors and buffers** DMA descriptors for transmit (TX) and
   receive (RX) are allocated and zeroed. The transmit buffer is allocated and
   aligned to 32 bytes, as required by the DMA. A TX buffer descriptor is
   created, pointing to the transmit buffer. This descriptor tells the HAL
   exactly where the frame data is and how long it is.

4. **Configure the Ethernet peripheral structure** The `ETH_HandleTypeDef` is
   populated with the MAC address, RMII mode, pointers to the TX and RX
   descriptors, and the RX buffer size. The clock source for the peripheral is
   selected. At this stage, the HAL has all the information needed to manage the
   hardware.

5. **Initialize the MAC and PHY** Calling `HAL_ETH_Init()` programs the MAC with
   the descriptor addresses, frame length settings, and other features like
   checksum offload. The PHY is reset and auto-negotiation is enabled via MDIO.
   Reading the PHY ID verifies that the PHY is responding correctly.

6. **Start the MAC** With `HAL_ETH_Start()`, the MAC begins normal operation,
   monitoring the RMII interface for frames to transmit or receive.

7. **Build the Ethernet frame** A frame is constructed in memory. The first 6
   bytes are the destination MAC (broadcast in this case), the next 6 bytes are
   the source MAC (the STM32's MAC), followed by a 2-byte EtherType. The payload
   is copied into the frame (e.g., a short test string), and the frame is padded
   to at least 60 bytes to satisfy Ethernet minimum length requirements.

8. **Transmit the frame** The TX buffer descriptor is updated with the frame
   length and pointer to the buffer. `HAL_ETH_Transmit()` is called, which
   programs the DMA to fetch the frame from memory and put it onto the Ethernet
   wire. After this call completes successfully, the frame is sent, and you can
   see it in Wireshark on the network.

For the record, when a cable is connected, the PHY sees the link is up:

    > eth_status
    Ethernet link is up
      Speed: 100 Mbps
      Duplex: full
      BSR = 0x782D, PHYSCSR = 0x1058

### Custom board connections to PHY

The custom board (Rev A) also uses the `LAN8742A-CZ-TR` Ethernet PHY chip,
connected to the SoC as follows:

| PHY pin  | PHY signal     | SoC signal        | SoC pin | Alt. Fn. | Notes   |
| -------- | -------------- | ----------------- | ------- | -------- | ------- |
| 16       | `TXEN`         | `PB11/ETH1_TX_EN` | `N5`    | AF11     |         |
| 17       | `TXD0`         | `PG13/ETH1_TXD0`  | `P8`    | AF11     |         |
| 18       | `TXD1`         | `PG14/ETH1_TXD1`  | `P9`    | AF11     |         |
| 8        | `RXD0/MODE0`   | `PC4/ETH1_RXD0`   | `U6`    | AF11     | 10k PU  |
| 7        | `RXD1/MODE1`   | `PC5/ETH1_RXD1`   | `R7`    | AF11     | 10k PU  |
| 11       | `CRS_DV/MODE2` | `PA7/ETH1_CRS_DV` | `U2`    | **AF11** | 10k PU  |
| 13       | `MDC`          | `PG2/ETH1_MDC`    | `R1`    | AF11     |         |
| 12       | `MDIO`         | `PG3/ETH1_MDIO`   | `L5`    | AF11     | 1k5 PU  |
| 15       | `nRST`         | `PG11`            | `M3`    |          | 10k PD  |
| 14       | `nINT/RECLKO`  | `PG12/ETH1_PHY_INTN` | `T1` | AF11     | 10k PU  |
| 5        | `XTAL1/CLKIN`  | `PA11/ETH1_CLK`   | `T2`    | AF11     |         |

The differences with respect to eval board are:

| Signal         | Eval board        | Custom board         |
| -------------- | ----------------- | -------------------  |
| `ETH1_CRS_DV`  | `PC1/ETH1_CRS_DV` | `PA7/ETH1_CRS_DV`    |
| `ETH1_MDIO`    | `PA2/ETH1_MDIO`   | `PG3/ETH1_MDIO`      |
| `nRST`         | GPIO expander     | `PG11`, 10k pulldown |
| `nINT/REFCLKO` | `PA1/ETH1_RX_CLK` | `PG12/ETH1_PHY_INTN` |
| `XTAL1/CLKIN`  | 25 MHz XTAL       | `PA11/ETH1_CLK`      |

That is, two different port assignments, direct GPIO for reset instead of
expander, clock to be output from the SoC to the PHY, and using `INTN` signal
instead of `RX_CLK`. All alternate functions are 11, while on the eval board one
of them (`CRS_DV`) was 10.

### Transmit Ethernet frame from custom board

First, we need to set the clock correctly. Since Ethernet does not have a
dedicated crystal on the custom board, we need to source it from a PLL. In
particular, we can set PLL3Q to output `24/2*50/24=25` MHz, and select the
`ETH1` clock source:

```c
pclk.PeriphClockSelection = RCC_PERIPHCLK_ETH1;
pclk.Eth1ClockSelection   = RCC_ETH1CLKSOURCE_PLL3;
if (HAL_RCCEx_PeriphCLKConfig(&pclk) != HAL_OK)
   ERROR("ETH1");
```

With the scope, I can see a 25 MHz clock on the `ETH_CLK` trace and the `nRST`
pin is driven high (3.3V). Nonetheless, `HAL_ETH_Init()` returns with an error.

Of course, we forgot to tell the HAL what the Ethernet clock source is. On the
eval board, we had

```c
eth_handle.Init.ClockSelection = HAL_ETH1_REF_CLK_RX_CLK_PIN;
```

But on the custom board, the SoC provides the clock to the PHY:

```c
eth_handle.Init.ClockSelection = HAL_ETH1_REF_CLK_RCC;
```

### Mistake in HAL driver?

With the RCC clock selected for Ethernet, yet again `HAL_ETH_Init()` fails. This
time, it tries to select the RCC clock source:

```c
if (heth->Init.ClockSelection == HAL_ETH1_REF_CLK_RCC)
{
  syscfg_config |= SYSCFG_PMCSETR_ETH1_REF_CLK_SEL;
}
HAL_SYSCFG_ETHInterfaceSelect(syscfg_config);
```

The Ethernet interface and clocking setup is done in the `PMCSETR` register,
together with some other configuration.

```c
void HAL_SYSCFG_ETHInterfaceSelect(uint32_t SYSCFG_ETHInterface)
{
   assert_param(IS_SYSCFG_ETHERNET_CONFIG(SYSCFG_ETHInterface));
   SYSCFG->PMCSETR = (uint32_t)(SYSCFG_ETHInterface);
}
```

Now the driver trips over the assertion. The assertion macro expects the
config word to pure interface selection, forgetting that the same register also
carries the `ETH1_REF_CLK_SEL` field (amongst others!):

```
#define IS_SYSCFG_ETHERNET_CONFIG(CONFIG)                                      \
   (((CONFIG) == SYSCFG_ETH1_MII) || ((CONFIG) == SYSCFG_ETH1_RMII) ||         \
    ((CONFIG) == SYSCFG_ETH1_RGMII) || ((CONFIG) == SYSCFG_ETH2_MII) ||        \
    ((CONFIG) == SYSCFG_ETH2_RMII) || ((CONFIG) == SYSCFG_ETH2_RGMII))
#endif /* SYSCFG_DUAL_ETH_SUPPORT */
```

If we comment out this assertion, the initialization proceeds without further
errors. However, link is still down.

### Biasing transformer center taps

Even with an Ethernet cable plugged in, link is down:

```c
// Read basic status register
if (HAL_ETH_ReadPHYRegister(&eth_handle, LAN8742_ADDR,
      LAN8742_BSR, &v) != HAL_OK) {
   my_printf("PHY BSR read failed\r\n");
   return;
}

if ((v & LAN8742_BSR_LINK_STATUS) == 0u) {
   my_printf("Link is down (no cable or remote inactive)\r\n");
   return;
}
```

On the schematic diagram of the custom board, we notice that the RJ-45
transformer center taps (`TXCT`, `RXCT` on the `J1011F21PNL` connector) are
decoupled to ground, but are not connected to 3.3V unlike on the eval board. The
`LAN8742A` datasheet does not talk about it explicitly, but instead shows a
schematic diagram (Figure 3-23) where the two center taps are tied together and
pulled up to 3.3V via a ferrite bead.

Tying the center taps to 3.3V, we still get no link. Printing the PHY Basic
Status Register, we see:

    Link is down (no cable or remote inactive)
    BSR = 0x7809

This means: link down, auto-negotiation not complete.

`REF_CLK` pin is not outputting a 50 MHz clock but instead sits at about 3.3V.

### LEDs and straps

The PHY chip shares LED pins with straps.

`LED1` is shared with `REGOFF` and is tied to the anode of the LED, which pulls
down the pin such that `REGOFF=0` and the regulator is enabled. We measure that
`VDDCR` is at 1.25V, which indicates that the internal regulator started
successfully. During board operation, this pin is low (close to 0V).

`LED2` is shared with the `nINTSEL` pin, and is connected to the LED cathode.
During board operation, this pin is high (close to 3.3V). Selecting `nINTSEL=1`
means `REF_CLK` In Mode, as is explained in Table 3-6: "`nINT/REFCLKO` is an
active low interrupt output. The `REF_CLK` is sourced externally and must be
driven on the `XTAL1/CLKIN` pin."

Section 3.7.4 explains further regarding the "Clock In" mode:

> In `REF_CLK` In Mode, the 50 MHz `REF_CLK` is driven on the `XTAL1/CLKIN` pin.
> This is the traditional system configuration when using RMII [...]
>
> In `REF_CLK` In Mode, the 50 MHz `REF_CLK` is driven on the `XTAL1/CLKIN` pin.
> A 50 MHz source for `REF_CLK` must be available external to the device when
> using this mode. The clock is driven to both the MAC and PHY as shown in
> Figure 3-7.

Furthermore, according to Section 3.8.1.6 of the PHY datasheet, the absence of a
pulldown resistor on `LED2/nINTSEL` pin means that `LED2` output is active low.
That means that the anode of `LED2` should have been tied to `VDD2A` according
to Fig. 3-15, rather than ground as is currently the case.

This means we have two alternatives:

- Add a 10k pulldown from `LED2/nINTSEL` to ground, and flip the polarity of the
  LED (connect the PHY to anode, or pin 9 of the connector). This would select
  `nINTSEL=0`. In that case, a 25 MHz clock is to be provided to `XTAL1/CLKIN`.

- Keep `LED2/nINTSEL` connected to the LED cathode, without any pulldown
  resistor. This selects `nINTSEL=1`. However, make sure to connect the LED
  anode (pin 9, `+LEDR`, of connector) to `VDD2A` instead of `GND`. In this
  case, a 50 MHz clock is to be provided to `XTAL1/CLKIN`.

In this instance I chose the latter option and ordered PLL3Q to output
`24/2*50/12=50` MHz. The link is briefly up and the green `LED2` blinks:

    > eth_status
    Ethernet link is up
      Speed: 100 Mbps
      Duplex: full
      BSR = 0x782D, PHYSCSR = 0x1058

But strange enough, when I check the status just a moment later, the link is
down again:

    > eth_status
    Link is down (no cable or remote inactive)
    BSR = 0x7809

Checking repeatedly, sometimes it's up, and sometimes it's down.

I see that the current drawn from the 3.3V supply switches between 0.08A and
0.13A continuously, every second or two.

### Digging in registers

Printing out some more info in both situations:

    Link is down (no cable or remote inactive)
      BSR = 0x7809, PHYSCSR = 0x0040, ISFR = 0x0098, SMR = 0x60E0, SCSIR = 0x0040
    SYSCFG_PMCSETR = 0x820000
    > e
    Ethernet link is up
      Speed: 100 Mbps
      Duplex: full
      BSR = 0x782D, PHYSCSR = 0x1058, ISFR = 0x00CA, SMR = 0x60E0, SCSIR = 0x1058
    SYSCFG_PMCSETR = 0x820000

PHY Basic Status Register `BSR`, when link is down, shows the following status:

- No T4 ability
- TX with full duplex ability
- TX with half duplex ability
- 10 Mbps with full duplex ability
- 10 Mbps with half duplex ability
- Auto-negotiate process not completed
- No remote fault
- Able to perform auto-negotiation function
- Link is down
- No jabber condition detected.
- Supports extended capabilities registers

When link is up, `BSR` shows (of course) that link is up, and also that
the auto-negotiate process completed.

The PHY Special Control/Status Register (`PHYSCSR`), when link is down, does not
have a meaningful speed indication (`000`), or anything else. When link is up,
it shows speed as `100BASE-TX full-duplex` (`110`), and that auto-negotiation is
done.

The PHY Interrupt Source Flag Register (`PHYISFR`), when link is down, shows
Auto-Negotiation LP Acknowledge, Link Down (link status negated), and `ENERGYON`
generated. When link is up, we get Auto-Negotiation Page Received,
Auto-Negotiation LP Acknowledge, `ENERGYON` generated, and Wake on LAN (`WoL`)
event detected.

The PHY Special Modes Register (`PHYSMR`), when link is either up or down, shows
the same value: 0x60E0. This means that `PHYAD=00000` (PHY address), and
`MODE=111` (transceiver mode of operation is set to "All capable.
Auto-negotiation enabled.".

The PHY Special Control/Status Indications Register (`PHYSCSIR`), when link is
up, shows Reversed polarity of `10BASE-T`, even though link is 100 Mbps.

SoC `PMCSETR` has two fields set: `ETH1_SEL` is set to 100, meaning RMII, and
`ETH1_REF_CLK_SEL` is set to 1, meaning that the reference clock (RMII mode)
comes from the RCC.

### Solution: PLL config (again!)

Painfully obvious in retrospect, but the problem was that `PLL3`, from which
we've derived the Ethernet clock, was set to fractional mode:

```c
rcc_oscinitstructure.PLL3.PLLFRACV  = 0x1a04;
rcc_oscinitstructure.PLL3.PLLMODE   = RCC_PLL_FRACTIONAL;
```

If instead we derive the clock from `PLL4`, which is already set to integer
mode, then sending the Ethernet frame *just works*, and the link gets up and
stays up:

```c
rcc_oscinitstructure.PLL4.PLLFRACV  = 0;
rcc_oscinitstructure.PLL4.PLLMODE   = RCC_PLL_INTEGER;
// ...
pclk.PeriphClockSelection = RCC_PERIPHCLK_ETH1;
pclk.Eth1ClockSelection   = RCC_ETH1CLKSOURCE_PLL4;
```

Of course! Ethernet requires a perfectly precise 50 MHz clock, up to about 50
ppm. On the eval board that was not a problem: the PHY had its own crystal, and
it returned a good 50 MHz clock directly back to the SoC's MAC.

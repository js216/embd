---
title: SHARC+ DSP Over QSPI
author: Jakob Kastelic
date: 9 Feb 2026
topic: DSP
description: >
   Boot an ADSP-2156 SHARC+ DSP over QSPI using the FT4222 USB-to-SPI/I²C
   interface. Configure GPIO, enable SPI master mode, and accelerate booting
   compared to UART.
---

![](../images/sn.jpg)

In the [previous article](boot-sharc-dsp-over-uart), we compiled a "blink"
program and sent it to the ADSP-2156 chip via UART. Now we can try to do the
same over a faster interface: QSPI.

### FTDI USB to I2C & SPI

The quad `SPI2` interface on the evaluation board
[EV-SOMCRR-EZLITE](https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/EV-SOMCRR-EZLITE.html)
is connected to the `FT4222HQ-D-T` chip that connects to one of the USB-C ports
on the carrier boards.

FTDI provides [software
examples](https://ftdichip.com/software-examples/ft4222h-software-examples/) for
the FT4222HQ on various operating systems. There is also a Python library,
[ft4222](https://pypi.org/project/ft4222/), which we'll use for this test.

First we make sure the computer sees the FTDI chip:

```py
import ft4222
for i in range(ft4222.createDeviceInfoList()):
    print(ft4222.getDeviceInfoDetail(i, False))
```

In the printout, we see `FT4222 A` and `FT4222 B`. The first one is used for I2C
and SPI, and the second for GPIO. 

### GPIO expander

The same FTDI part also controls an I2C GPIO expander, `ADP5587ACPZ-1`, which is
in charge of the LEDs on the carrier boards as well as the QSPI interface. We'll
be interested in the following pins at `U22`:

    C0 = USBI_SPI0_EN*
    C1 = USBI_SPI1_EN*
    C2 = USB_QSPI_EN*
    C3 = USB_QSPI_RESET*
    C4 = ETH0_RESET
    C5 = ADAU1372_PWRDWN*
    C6 = PUSHBUTTON_EN
    C7 = DS8 (green LED on SOMCRR)
    C8 = DS7 (green LED on SOMCRR)
    C9 = DS6 (green LED on SOMCRR)

Let's open the I2C device:

```py
dev = ft4222.openByDescription('FT4222 A')
dev.i2cMaster_Init(100)
```

We can write to it by means of this helper function:

```py
def wr(d):
    for a, b, c in d:
        dev.i2cMaster_WriteEx(
            a, ft4222.I2CMaster.Flag.START_AND_STOP, bytes([b, c]))
```

First, we'll make sure that all pins are set as GPIO (as opposed to "keypad"
mode):

```py
wr([(0x30, 0x1D, 0x00)]) # R7:0 -> GPIO
wr([(0x30, 0x1E, 0x00)]) # C7:0 -> GPIO
wr([(0x30, 0x1F, 0x00)]) # C9:8 -> GPIO
```

Next, we would like to set the pin output states to `USBI_SPI0,1` disabled,
`USB_QSPI` neither enabled nor under reset, `ETH0` reset asserted, `ADAU1372`
powered down, pushbutton disabled, LEDs off:

```py
# default output config
wr([(0x30, 0x18, 0b1000_1111)])
wr([(0x30, 0x19, 0b0000_0011)])
```

Finally, to make this configuration active, we enable the outputs on all port-C
pins. Make sure to do this *after* configuring the pin output states, otherwise
you can put the FT4222 into reset (pins default to 0 output states, and pulling
`USB_QSPI_RESET*` low puts the FT4222 into reset).

```py
wr([(0x30, 0x24, 0xff)]) # C7:0 -> output
wr([(0x30, 0x25, 0xff)]) # C9:8 -> output
```

To test that this all works, we can enable the three green LEDs on the SOMCRR
one by one:

```py
wr([(0x30, 0x18, 0b0001_1111)]) # enable LED DS8
wr([(0x30, 0x19, 0b0000_0010)]) # enable LED DS7
wr([(0x30, 0x19, 0b0000_0000)]) # enable LED DS6
```

These are the *green* LEDs on the SOMCRR board, not the yellow ones on the SOM
board.

### QSPI master vs slave

The FT4222 can act either as an SPI master or a slave, and so can the SHARC.
Both modes are of interest to us:

| FT4222 | SHARC  | `S5` Set | Application                     |
| ------ | ------ | -------- | ------------------------------- |
| Master | Slave  | 2-3 / Dn | Boot SHARC from USB             |
| Slave  | Master | 1-2 / Up | Transmit data from SHARC to USB |

`S5` is the slide switch located on the SOMCRR board next to the USB-C QSPI
connector. With the SOMCRR board oriented so the USB-C connectors are on the
top, the `S5` slider is in the 1-2 position when it is pushed up (towards the
USB-C connectors), and 2-3 when it is down (away from USB-C connectors).

### SPI boot

To enable the SPI boot, we need to make three hardware selections:

1. Enable the SPI interface by pulling `USB_QSPI_EN*` low:

   ```py
   wr([(0x30, 0x18, 0b1001_1011)])
   ```

   Make sure to follow the steps from the previous section to set the GPIO
   expander into GPIO mode, set to correct output defaults, etc., or else it
   will not work!

2. Flip the `S5` switch up so that the 2-3 position is selected, making the
   FT4222 the SPI master. The switch slider must face away from the USB-C
   connectors.

3. Set the rotary boot mode selector switch to mode 2 decimal (010 binary,
   "External SPI2 host").

While the `elfloader` utility supports both `-b UARTHOST` and `-b SPIHOST`
flags, it appears to generate the same bootstream with either flag. So, let's
try to use the same bootstream as we had used in the Blink example from the
[previous article](boot-sharc-dsp-over-uart), except to make sure to send 0x03
as the first byte as instructed by the SHARC manual:

```py
boot_buffer = bytearray([0x03]) # SPICMD = 0x3: Keep single-bit mode
with open('blink.ldr', 'r') as f:
    for line in f:
        boot_buffer.append(int(line.strip(), 16))
```

The SHARC hardware reference manual describes SPI mode 1 where the clock idles
low and data is sampled on falling edge and shifted out on rising edge:

> In SPI slave boot mode, the boot kernel sets the `SPI_CTL.CPHA` bit and clears
> the `SPI_CTL.CPOL` bit. Therefore the `SPI_MISO` pin is latched on the falling
> edge of the `SPI_MOSI` pin.

With that in mind, we can initialize the FT4222 device for SPI as follows,
send the bootstream, and close the device:

```py
dev = ft4222.openByDescription('FT4222 A')
dev.spiMaster_Init(
    ft4222.SPIMaster.Mode.SINGLE,
    ft4222.SPIMaster.Clock.DIV_8,
    ft4222.SPI.Cpol.IDLE_LOW,
    ft4222.SPI.Cpha.CLK_TRAILING,
    ft4222.SPIMaster.SlaveSelect.SS0)
dev.spiMaster_SingleWrite(boot_buffer, True)
dev.close()
```

On my first attempt, this did not work since I had the `S5` switch set in the
wrong polarity (the slider should face *away* from the USB-C connectors!).
Fixing that, the code boots in an instant---much, much faster than the couple
seconds it took over UART.

### Boot time

With a bootstream of only about 62 kB, the boot time is not a significant
consideration. For larger binaries, ADI offers estimates[^bt] of how long the
boot will take as a function of the binary size. Here's some representative
numbers from the SPI2 figure:

| Size / kB | Single | Dual   | Quad   |
| --------- | ------ | ------ | ------ |
| 2000      | 0.3 s  | 0.15 s | 0.08 s |
| 4000      | 0.6 s  | 0.3 s  | 0.15 s |
| 8000      | 1.1 s  | 0.6 s  | 0.3 s  |

Chances are that your bootstream is much, much smaller than these figures, so it
would in general add a negligible duration to the boot process.

[^bt]: Analog Devices, Engineer-to-Engineer Note EE-447: *Tips and Tricks Using
  the ADSP-SC59x/ADSP-2159x/ADSP-2156x Processor Boot ROM.* V01, May 11, 2023.

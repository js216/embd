---
title: Boot SHARC+ DSP Over UART
author: Jakob Kastelic
date: 6 Feb 2026
topic: DSP
description: >
   The ADSP-21569 SHARC+ can boot without CCES or debug hardware. Learn how UART
   boot works, what preload/init code really does, and how to simplify the
   workflow.
---

![](../images/sh.jpg)

Most microcontrollers can be built and programmed without vendor IDEs or
expensive debug probes. The ADSP-21569 SHARC DSP, at first glance, appears to be
an exception. The official workflow assumes Analog Devices' CrossCore Embedded
Studio IDE and dedicated expensive debugging hardware. But instead we can just
boot the thing over plain UART---the hardware supports it, the manuals describe
it, and the tools exist to generate the boot streams.

These are my notes getting started with the Analog Devices SHARC processor
installed on the
[EV-21569-SOM](https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/ev-21569-som.html)
evaluation board, plugged into the
[EV-SOMCRR-EZLITE](https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/EV-SOMCRR-EZLITE.html)
carrier board. Since there is very little information available online about
these chips, compared to the more "usual" parts from ST or NXP, I hope the
writeup will be of some use to someone.

### Hardware setup

Hardware setup: install the SOM board into the SOMCRR board and establish the
Default Configuration specified in the [EV-SOMCRR-EZLITE
Manual](https://www.analog.com/media/en/technical-documentation/user-guides/ev-somcrr-ezlite_manual.pdf).

Connect the provided 12V 1.6A power supply to the `POWER IN` connector on the
SOMCRR board. Connect a USB A-to-C cable to `P16`, labeled `USB-C DA` (debug
agent).

### Software setup

Although the debug tools are relatively expensive, Analog Devices offers a
board-locked license that allows the CCES IDE to be used without additional cost
after purchasing the evaluation boards.

Install the [CrossCore Embedded
Studio](https://www.analog.com/en/resources/evaluation-hardware-and-software/software/adswt-cces.html#software-relatedhardware)
from the Analog Devices website. I'm using "Product version" `3.0.2.0
(w2410301)` with "IDE version" `3.0.2029.202410301506`.

Install also the EV-21569-EZKIT Board Support Package, Current Release (Rev.
3.0.0) from the SOM website; this provides some additional code examples to
start from.

### Blink from the IDE

Code sharing is less common in the DSP ecosystem compared to some other software
domains. However, basic reference examples are included within the IDE. To
access them, follow these steps:

```
File
  New
    Project ...
    C/C++
      CrossCore Project
        Next >
        (enter project name, say "test")
        Next >
        (select ADSP-21569 revision "any")
        Next >
        Finish
"Click here to browse all examples."
```

Search for `blink` under Keywords, select the `LED_Blink` example for
`EV-2156x EZ-KIT v2.0.0 [2.0.0]`, and press "Open example". Now we can delete
the `"test"` project created just before: right click it in the Project
Explorer, select "Delete", and also check "Delete project contents on disk".

Only the `LEDBlink` project remains; compile it (Project -> Build All) and run
it (Run -> Debug, followed by Run -> Resume). With some luck, all three yellow
LEDs on the SOM board will start blinking. Great!

### Boot from UART

Previously we have run the code through the "Debug Agent", which is an
`ATSAME70Q21B-CFNT` on the SOM carrier board. Now, let's try to download the
same program through the UART interface.

Locate the `P14` pin header on the right side of the carrier board, right under
the Analog Devices logo. Locate the two top right pins, labelled `SPI0` `CLK`
and `MISO`. Cross-referencing with the datasheet, we learn that these two pins
are `UART0_TX` and `UART0_RX`, respectively. Connect them to a 3.3V UART to USB
adapter (I'm using the `UMFT230XB-01` adapter).

The Processor Hardware Reference[^ref] describes the UART Slave Boot Mode. In
particular, the part supports Autobaud Detection which works as follows:

1. Send the `@` character (`0x40`) to the UART RXD input.
2. DSP returns four bytes: `0xBF`, `UART_CLK [15:8]`, `UART_CLK [7:0]`, `0x00`.
3. Send the entire boot stream.

**Step 1.** Let's attempt this in Python:

```python
import serial
s = serial.Serial('COM20', baudrate=115200, timeout=1)
s.write(b'@')
res = s.read(4)
```

If we `print(res)`, we get out `b'\xbf2\x00\x00'`. Great, the processor
succeeded with the autobaud detection.

**Step 2.** Next, we need to convert the ELF file produced by the IDE
(`LEDBlink_21569.dxe`) into a form suitable for loading into the chip. I'm
running the `elfloader` (part of the CCES installation) from WSL2 as follows:

```
/mnt/c/analog/cces/3.0.2/elfloader.exe \
   -proc ADSP-21569 -b UARTHOST -f ASCII -Width 8 -verbose \
   LEDBlink_21569.dxe -o blink.ldr
```

**Step 3.** Back in Python, we can take the file and shove it into the DSP one
byte at a time:

```python
with open('blink.ldr', 'r') as f:
    for line in f:
        d = int(line.strip(), 16)
        s.write(bytes([d]))
```

After a few seconds of blinking on the `RX` and `TX` LEDs on the SOM, indicating
the `UART0` activity, we see the familiar blinking of the yellow `LED4`, `LED6`,
and `LED7`, as before.

That's great news, as it provides a way to program the part without any
specialized hardware tools. For example, in an embedded application an
application processor could send the DSP its boot code via UART. It's a bit
slow, but presumably the same process could work over a faster interface like
`SPI2`.

### Bad news?

If we unplug the USB DA connection to the SOMCRR board, we find that the Python
code example above does not communicate with the board anymore (no response to
the Autobaud command). But if we plug the USB cable back into the debug agent,
then it all works fine. It works even with the CCES program closed.

Silly mistake! The USB connector was the only shared ground between the computer
and the DSP board. Attaching a ground wire between the USB to serial adapter and
`P14`, and all is well again.

### Preload executable

Let's take a closer look at how the IDE runs the code. Go into Run -> Debug
Configurations, and add a new "Application with CrossCore Debugger". Click
through the wizard and notice that it adds a "preload" ELF file such as the
following one, to be run before the blink code runs:

    C:\analog\cces\3.0.2\SHARC\ldr\ezkit21569_preload.dxe

What does this do? Let's navigate to the following location in the CCES
documentation:

    CrossCore® Embedded Studio 3.0.2 >
      Integrated Development Environment >
        Debugging Targets >
          Debugging ADSP-SC5xx SHARC+ and ARM Projects

The first sentence says that "preload files are used for the ADSP-SC5xx EZ-KITs
and processors only". These files are "equivalent to initcodes, but used during
the debugging phase of development". From my reading of this section, it appears
that the preload files configure external memory, if using it, and only for the
multi-core parts. Thus, on ADSP-21569 we should have no use for it.

Nevertheless, the project comes with pre-built init code executables even on
ADSP-21569. In fact, the source code is provided for *two* 

    C:\analog\cces\3.0.2\SHARC\ldr\21569_init
    C:\analog\cces\3.0.2\SHARC\ldr\21569_preload

One of these is an "initialization code project" and the other is "CCES preload
code project". Clear as mud! I think the `init` is used for production
applications, while the `preload` version is used only when running the code
directly from the CCES, but they do more or less the same thing: configure
clocks, and the DDR.

Clock configuration is the reason why these files are provided not just for
ADSP-SC5xx, but also for the 2156x. However, in this basic tutorial we will not
modify the clocks, so the init code is not, in fact, needed after all.

### Preload exe vs init code

LDR files produced by the `elfloader` utility support an `-init` switch, as does
the processor bootstream itself. The hardware reference manual explains:

> An initialization block instructs the boot kernel to perform a function call
> to the target address after the entire block has loaded. The function called
> is referred to as the *initialization code (Initcode) routine.*
>
> Traditionally, an Initcode routine is used to set up the system PLL, bit
> rates, wait states, and the external memory controllers. Boot time can be
> significantly reduced when an init block is executed early in the boot
> process.

We read in the CCES documentation that the init code can also be packaged into a
separate project/program, instead of being a part of the full application's boot
stream:

> The preload executables are simple programs that invoke the init code
> functionality to configure the processor prior to loading the main
> application.

But the CCES documentation warns:

> Do not use the preload executables when building bootable LDR files with the
> -init switch. The preload executables are not configured for use for LDR
> initialization blocks.

In other words, to use the `-init` switch, we should compile the `21569_init`
version of the initialization project.

However, no init code is needed for the blink project, since we do not need to
adjust any of the clock parameters---the default values work.

### Blink with a Makefile

CCES scatters various related files all over the file system, making it seem
more complicated to build a project than is necessary. If we collect all the
files together, it's not so bad. Here's what the IDE-provided Blink example
needs to put together:

```
OBJ = \
  ConfigSoftSwitches_EV_SOMCRR_EZLITE_LED_OFF.doj \
  ConfigSoftSwitches_EV_SOMCRR_EZLITE_LED_ON.doj \
  SoftConfig_EV_21569_SOM_Blink1.doj \
  SoftConfig_EV_21569_SOM_Blink2.doj \
  adi_gpio.doj \
  adi_initialize.doj \
  app_IVT.doj \
  app_heaptab.doj \
  app_startup.doj \
  main.doj \
  pinmux_config.doj \
  sru_config.doj \
```

These files are either assembly files, like `app_IVT.s` and `app_startup.s`, or
plain C files, like all the rest of them. Some are auto-generated, like
`adi_initialize.c` (initializes SRU and pin-mux), `app_heaptab.c`,
`pinmux_config.c`, and `sru_config.c`. The "Soft Config" files are essentially
copies of each other, two files to turn the LED on, and two files to turn it off
(seriously---the only difference in these files is the "data" written to the
LED). This leaves just `main.c`, and the GPIO driver. By the standards of modern
SoCs with tens of peripherals, all of this is almost trivial.

The compilation rules are as simple as can be. For the sake of explicitness,
here they are:

```
blink.ldr: blink.dxe
	$(ELFL) $(ELFFLAGS) $< -o $@

blink.dxe: $(OBJ)
	$(CC) $(LDFLAGS) -o $@ $^

%.doj: %.s
	$(ASM) $(ASFLAGS) -o $@ $<

%.doj: %.c
	$(CC) $(CFLAGS) -c -o $@ $<
```

We have met the `ELFL`, or `elfloader`, rule above already: it creates the
bootstream from an ELF input. The rest are standard linking, assembly, and
compilation steps. The toolchain gets installed with CCES and is unfortunately
entirely closed-source:

```
CC   = /mnt/c/analog/cces/3.0.2/cc21k.exe
ASM  = /mnt/c/analog/cces/3.0.2/easm21k.exe
ELFL = /mnt/c/analog/cces/3.0.2/elfloader.exe
```

The remaining piece of the Makefile are the flags. I'll give `CFLAGS`, the other
two are very similar:

```
CFLAGS = \
  -proc ADSP-21569 -si-revision any -flags-compiler \
  --no_wrap_diagnostics -g -DCORE0 -D_DEBUG -DADI_DEBUG \
  -structs-do-not-overlap -no-const-strings -no-multiline -warn-protos \
  -double-size-32 -char-size-8 -swc -gnu-style-dependencies
```

### Discussion

The Blink example is accompanied by a lengthy license agreement that imposes
significant restrictions, such as prohibiting external distribution and public
posting of source code. This makes it impractical to release modifications
without careful review.

The process to build and run the Blink example is somewhat fragile and may break
in future versions of the Eclipse-based IDE, making it difficult to fully
automate.

Due to the complexity of modern IDEs, it is not always clear which source files
beyond main.c are included in the build. While this is not critical for a simple
example like Blink, developers should be aware of the build inputs and
dependencies when working on more complex projects to ensure proper provenance
and supply chain transparency.

Notably, ADI appears to rely on a "security through obscurity" approach,
reflecting a limited transparency regarding security mechanisms. This approach
limits developers' ability to audit or verify the security of the system:

> The sources for ROM code are not available in CCES to protect the
> ADSP-SC5xx/ADSP-215xx secure booting and encryption details.[^ccref]

It is noteworthy that the SHARC+ processor family currently lacks open-source
toolchain components---such as an assembler, linker, compiler, loader, and
debugging tools---which may limit accessibility for experimentation and early
evaluation, potentially affecting broader adoption among engineers.

[^ref]: Analog Devices: *ADSP-21562/3/5/6/7/9 SHARC+ Processor Hardware
  Reference*. Revision 1.1, October 2022. Part Number 82-100137-01.

[^ccref]: Analog Devices: CrossCore Embedded Studio 3.0.2 > SHARC-FX
  Development Tools Documentation > Loader and Utilities Manual > Loader.

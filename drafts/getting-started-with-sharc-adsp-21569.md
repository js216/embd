---
title: Getting Started with ADSP-21569
author: Jakob Kastelic
date:
topic: Embedded
description: >
---

![](../images/sh.jpg)

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
SOMCRR board. Connect a USB A-to-C cable to P16, labeled `USB-C DA` (debug
agent).

### Software setup

Although the debug tools are relatively expensive, Analog Devices offers a
board-locked license that allows the CCES IDE to be used without additional cost
after purchasing the evaluation boards.

Install the [CrossCore Embedded
Studio](https://www.analog.com/en/resources/evaluation-hardware-and-software/software/adswt-cces.html#software-relatedhardware)
from the Analog Devices website. I'm using "Product version" 3.0.2.0 (w2410301)
with "IDE version" 3.0.2029.202410301506.

Install also the EV-21569-EZKIT Board Support Package – Current Release (Rev.
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
Click here to browse all examples.
```

Search for `blink` under Keywords, select the `LED_Blink` example for
`EV-2156x EZ-KIT v2.0.0 [2.0.0]`, and press "Open example". Now we can delete
the `"test"` project created just before: right click it in the Project
Explorer, select "Delete", and also check "Delete project contents on disk".

Only the `LEDBlink` project remains; compile it (Project -> Build All) and run
it (Run -> Debug, followed by Run -> Resume). With some luck, all three yellow
LEDs on the SOM board will start blinking. Great!

### Boot from UART



### Blink with a Makefile



### Discussion

The Blink example is accompanied by a lengthy license agreement that imposes
significant restrictions, such as prohibiting external distribution and public
posting of source code. This makes it impractical to release modifications
without careful review.

Additionally, the process to build and run the Blink example is somewhat fragile
and may break in future versions of the Eclipse-based IDE, making it difficult
to fully automate.

Finally, due to the complexity of modern IDEs, it is not always clear which
source files beyond main.c are included in the build. While this is not critical
for a simple example like Blink, developers should be aware of the build inputs
and dependencies when working on more complex projects to ensure proper
provenance and supply chain transparency.

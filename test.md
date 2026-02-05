---
title: Test article for Markdown converter testing
author: Jakob Kastelic
date: 5 Feb 2026
topic: Meta
description: >
   Testing the converter.
---

*Italics at front.*

![](../images/brid.jpg)

There can be a [link
text](https://www.st.com/en/evaluation-tools/stm32mp135f-dk.html) as well as
[another link](https://github.com/js216/stm32mp135_test_board).

Note that a link can also be code:
[`STM32Cube_FW_MP13_V1.2.0`](https://wiki.st.com/stm32mpu/wiki/STM32CubeMP13_Package_-_Getting_started)
(and there's nothing wrong with it).

Here's some more text:

>  Accidental complexity happens because someone didn't find the simplest way to
>  implement a specified set of features. Accidental complexity can be
>  eliminated by good design, or good redesign.[^acc]

1. A very long list item.
   
   This list item has multiple paragraphs.

   ```
   One of the paragraphs is code block.

   The code block has an empty line.

   Code can have unbalanced underscores: _
   ```

   Some text between the lines.[^talk]

       Another paragraph is also code.
       
       Except this code is indented 4 spaces w.r.t. the list item.
       Here also we have unbalanced characters: *

   This list continues here and has another underscore in a code example (`_`),
   but this time it is in backticks. Smart "quotes" can be used---and em dashes,
   and also numerical ranges: 2--5, which would use en dashes.

Now this is no longer a list item, just a normal paragraph. Code has underscores
pretty often: `SP_MIN`; just make sure the underscore is contained. Sometimes "a
quoted text has code: `SP_MAX`", so that text outside quotes is not affected.

We can also have "in
quotes some code `RESET_TO_SP_MIN;` why not?", and outside the quotes also:
`ARM_LINUX_KERNEL_AS_BL33` flag (`docs/plat/arm/arm-build-options.rst`). The
`plat/arm/common/arm_common.mk` Makefile enforces this.

Unfortunately this limits the potential use cases of `ARM_LINUX_KERNEL_AS_BL33`
to AArch64, or else to AArch32 with `SP_MIN` enabled. The Buildroot defconfig we
have adapted in the previous section uses OP-TEE instead of `SP_MIN`, and it is
also possible to use no BL32 at all.

C should by syntax highlighted:

```c
void UART0_SERIAL_RX_TX_IRQHANDLER(void)
{
   uint32_t intStatus = UART_GetStatusFlags(UART0);
   if ((kUART_RxDataRegFullFlag | kUART_RxOverrunFlag) & intStatus) {
      const uint8_t data = UART_ReadByte(UART0);
      xQueueSendToBackFromISR(rx_queue, &data, NULL);
   }
}
```

Also Python:

```Python
def interp_cmd(b):
    if b == 0x00:
        return "Get"
```

How about a little JSON?

```json
"PSRR (Input offset voltage versus power supply)": {
   "min": 65,
   "typ": 100,
   "max": null,
   "unit": "dB"
 },
```

We can have *italics* or **bold** fonts.

[^talk]: Anna-Lena Marx (inovex GmbH): *Your Vendor's BSP Is Probably Not Built
  for Product Longevity*. Yocto Project Summit, December 2025. Quoted on
  1/5/2026 from [this URL](https://marx.engineer/content/talks/2025_Yocto-Summit_Your-Vendors-BSP-Is-Probably-Not-Built-For-Product-Longevity.pdf)

[^acc]: Eric S. Raymond: The Art of Unix Programming. Addison-Wesley, 2004.

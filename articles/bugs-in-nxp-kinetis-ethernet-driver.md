---
title: Bugs in NXP Kinetis Ethernet Driver
author: Jakob Kastelic
date: 10 Sep 2025
topic: Embedded
description: >
    An analysis of three bugs found so far in the NXP Kinetis ethernet driver as
    used on the K64.
---

![](../images/lev63.jpg)

The SDK[^sdk] drivers provided by NXP for use on the Kinetis K64 platform are
extensive, well-tested and ... not perfect. This article shows three bugs found
in the ethernet driver. Note that none of this is original content; I merely put
it together here for my future reference.

### Forgetting to check for zero-length buffers

I have only seen this bug happen once in two years and have not found a way to
reproduce it at will. So the analysis below may or may not be correct.

The symptom was that the firmware froze upon triggering the assertion in
`lwip/port/enet_ethernetif_kinetis.c`:

> "Buffer returned by `ENET_GetRxFrame()` doesn't match any RX buffer descriptor"

After some Googling I found [this forum
thread,](https://community.nxp.com/t5/i-MX-RT-Crossover-MCUs/Ethernet-RX-assertion/m-p/1625123)
which suggests, in a roundabout way, that there is a missing check in
`fsl_enet.c`. We have to add following to `ENET_GetRxFrame()`:

```c
if (curBuffDescrip->length == 0U)
{
    /* Set LAST bit manually to let following drop error frame
       operation drop this abnormal BD.
    */
    curBuffDescrip->control |= ENET_BUFFDESCRIPTOR_RX_LAST_MASK;
    result = kStatus_ENET_RxFrameError;
    break;
}
```

The NXP engineer on the forum explains: "I didn't use this logic because I never
meet this corner case and consider it a redundant operation." I was curious if
this "corner case" every happens, so I added a breakpoint, which got triggered
after about two days of constant testing.

ChatGPT seems to think this check is necessary (but then again, I seem to be
able to convince it of just about anything I do or do not believe in):

> If you omit the check and DMA ever delivers a BD with `length == 0`: Your code
> will think it’s still in the middle of assembling a frame. It will not see the
> `LAST` bit yet, so it will happily advance to the next BD. That means the
> logic walks into an inconsistent state: `rxBuffer` may point to nothing, your
> `rxFrame` bookkeeping goes out of sync, and later you’ll crash on a buffer
> underrun, invalid pointer, or corrupted frame queue.

It remains to be seen if this check was behind my original crash, and if the
body of the if statement is appropriate to handle the condition of unexpected
zero-length buffer descriptor.

*Credit: User pjanco first reported the error, while AbnerWang posted the
solution.*
[[source]](https://community.nxp.com/t5/i-MX-RT-Crossover-MCUs/Ethernet-RX-assertion/m-p/1625123)

### Incorrect memory deallocation

In `fsl_enet.c`, the function `ENET_GetRxFrame()` tries to deallocate the
pointer of the receive buffer:

```c
while (index-- != 0U)
{
    handle->rxBuffFree(base, &rxFrame->rxBuffArray[index].buffer,
        handle->userData, ringId);
}
```

First need to unpack some definitions to understand what the above means.

1. If we dig into the `rxBuffFree()` function, we discover it in the file
   `lwip/port/enet_ethernetif_kinetis.c`. The buffer to be deallocated is passed
   as a pointer `void * buffer`, and freed 

   ```c
   int idx = ((rx_buffer_t *)buffer) - ethernetif->RxDataBuff;
   ethernetif->RxPbufs[idx].buffer_used = false;
   ```

2. Next, what are `rxFrame` and `rxBuffArray`? The first one is of type
   `enet_rx_frame_struct_t`, which is defined in `fsl_enet.h`:

   ```c
   typedef struct _enet_rx_frame_struct
   {
       enet_buffer_struct_t *rxBuffArray;
       ...
   } enet_rx_frame_struct_t;
   ```

   This allows us to see what is the type of `rxBuffArray`:

   ```c
   typedef struct _enet_buffer_struct
   {
       void *buffer;
       uint16_t length;
   } enet_buffer_struct_t;
   ```

3. Finally, what is `ethernetif->RxDataBuff`? We find it declared in
   `lwip/port/enet_ethernetif_kinetis.c` as the static array in the function
   `ethernetif0_init()`:

   ```c
   SDK_ALIGN(static rx_buffer_t rxDataBuff_0[ENET_RXBUFF_NUM],
       FSL_ENET_BUFF_ALIGNMENT);
   ethernetif_0.RxDataBuff = &(rxDataBuff_0[0]);
   ```

   More precisely, `RxDataBuff` is a pointer to the first element of this array.
   This pointer therefore has the type `rx_buffer_t*`.

   That type itself is declared at the top of the same file as an aligned
   version of a `uint8_t` buffer:

   ```c
   typedef uint8_t rx_buffer_t[SDK_SIZEALIGN(ENET_RXBUFF_SIZE,
       FSL_ENET_BUFF_ALIGNMENT)];
   ```

Now we can take a step back and think whether the `idx` calculation would be
best done with the buffer itself, or a pointer to it. The calculation subtracts
the following:

- `rxFrame->rxBuffArray[index].buffer`, of type `void*`, is a pointer to the
  memory location that stores the ethernet frame.

- `ethernetif->RxDataBuff`, of type `rx_buffer_t*`

The corrected code should pass the buffer pointer stored in .buffer, not the
address of the .buffer field (omit the `&`):

```c
handle->rxBuffFree(base, rxFrame->rxBuffArray[index].buffer,
    handle->userData, ringId);
```

*Credit: This bug was found by KC on 7/31/2024.*

### Buffers not zero-initialized

Another bug in `ethernetif0_init()` in `enet_ethernetif_kinetis.c`: the ethernet
buffer descriptor structs are declared static:

```c
AT_NONCACHEABLE_SECTION_ALIGN(
    static enet_rx_bd_struct_t rxBuffDescrip_0[ENET_RXBD_NUM],
    FSL_ENET_BUFF_ALIGNMENT);
AT_NONCACHEABLE_SECTION_ALIGN(
    static enet_tx_bd_struct_t txBuffDescrip_0[ENET_TXBD_NUM],
    FSL_ENET_BUFF_ALIGNMENT);
```

The assumption is that since they are declared `static`, the descriptors will be
zero-initialized at system startup. However, the macro
`AT_NONCACHEABLE_SECTION_ALIGN` potentially places these descriptor in a special
section that can bypass the zero-initialization, depending on the startup code
and linker script.

In that case, we need to manually zero out these buffers. I put the following at
the top of `ethernetif_enet_init()` in `enet_ethernetif_kinetis.c`:

```c
// Buffer descriptors must be initialized to zero
memset(&ethernetif->RxBuffDescrip[0], 0x00, ENET_RXBD_NUM*sizeof(ethernetif->RxBuffDescrip[0]));
memset(&ethernetif->TxBuffDescrip[0], 0x00, ENET_TXBD_NUM*sizeof(ethernetif->TxBuffDescrip[0]));
```

*Credit: This bug was also found by KC.*

[^sdk]: I am using SDK version 2.11.0 for the MK64FN1M0xxx12.

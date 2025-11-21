---
title: Boot STM32MP135 Over UART With Python
author: Jakob Kastelic
date: 19 Nov 2025
modified: 21 Nov 2025
topic: Embedded
description: >
  Flash and boot the STM32MP135 using its ROM UART bootloader with a minimal
  Python script, covering protocol details, command formats, and step-by-step
  use on both the evaluation board and a custom board.
---

![](../images/brid.jpg)

*This article is also available as a [Jupyter
notebook.](https://github.com/js216/mp135_boot/tree/main/uart_boot)*

[Previously](stm32mp135-linux-cubeprog.md) we have explored how to flash the
STM32MP135 using the STM32CubeProg over USB and remained puzzled why we need
1.5G of code just to transfer some serial data. Here, we will flash the chip
by talking to the built-in ROM bootloader over UART with a couple lines of
Python, as explained in an ST app note[^app]. The article is in three sections:
(1) define the communication functions, (2) use them on the evaluation board,
(3) use them on a custom board.

### Comm Functions

This section documents how the STM32MP1 ROM bootloader communicates over UART,
including the supported commands, packet formats, checksum rules, and Python
helper functions used to implement the protocol. Skip to the [next
section](#flash-the-evaluation-board) to see how these functions are used.

The supported commands are listed below:

```Python
def interp_cmd(b):
    if b == 0x00:
        return "Get"
    elif b == 0x01:
        return "Get Version"
    elif b == 0x02:
        return "Get ID"
    elif b == 0x03:
        return "Get phase"
    elif b == 0x11:
        return "Read Memory"
    elif b == 0x12:
        return "Read Partition"
    elif b == 0x21:
        return "Start (Go)"
    elif b == 0x31:
        return "Download (Write Memory)"
    else:
        return "???"
```

All communications from STM32CubeProgrammer (PC) to the device are verified as
follows:

- The UART/USART even parity is checked.

- For each command the host sends a byte and its complement (XOR = 0x00).

- The device performs a checksum on the sent/received datablocks. A byte
  containing the computed XOR of all previous bytes is appended at the end of
  each communication (checksum byte). By XORing all received bytes, data +
  checksum, the result at the end of the packet must be 0x00. A timeout must be
  managed in any waiting loop to avoid any blocking situation.

```Python
def pack_cmd(cmd):
    if cmd not in [0x00, 0x01, 0x02, 0x03, 0x11, 0x12, 0x21, 0x31]:
        raise RuntimeError("Invalid cmd requested.")
    # command followed by its complement
    return struct.pack("BB", cmd, 0xff-cmd)
```

Each command packet is either accepted (ACK answer), discarded (NACK answer) or
aborted (unrecoverable error):

```Python
def interp_byte(b):
    if b == 0x79:
        return "ACK"
    elif b == 0x1F:
        return "NACK"
    elif b == 0x5F:
        return "ABORT"
    else:
        return format(b, '#04x')

def get_ack(note=""):
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\t{interp_byte(r)}{note}")
    if interp_byte(r) != "ACK":
        raise RuntimeError("Did not receive ACK.")
```

Once the serial boot mode is entered (boot pins set to 000), all the UART/USART
instances are scanned by the ROM code, monitoring for each instance the
`USARTx_RX` line pin, waiting to receive the 0x7F data frame (one start bit,
0x7F data bits, none parity bit and one stop bit).

```Python
def uart_init():
    mp1.write_raw(struct.pack("B", 0x7F))
    get_ack(note="")
```

The Get command returns the bootloader version and the supported commands. When
the device receives the Get command, it transmits the version and the supported
command codes to the host. The commands not supported are removed from the list.

```Python
def get():
    # Get command
    mp1.write_raw(pack_cmd(0x00))
    
    # Response: ACK
    get_ack()

    # Response: number of following bytes – 1
    num_bytes = mp1.read_bytes(1)[0]
    if num_bytes >= 0:
        print(f"{format(num_bytes, '#04x')}\t\t{num_bytes} + 1 bytes to follow")
    else:
        print(f"{format(num_bytes, '#04x')}")
        raise RuntimeError("Did not receive number of bytes to follow.")

    # Response: Bootloader version
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\tversion {int(hex(0x10)[2:])/10}")
    
    # Response: device ID
    for i in range(num_bytes):
        r = mp1.read_bytes(1)[0]
        print(f"{format(num_bytes, '#04x')}\t\tcmd = {interp_cmd(r)}")
    
    # Response: ACK
    get_ack()
```

The Get version command is used to get the version of the running component.
When the device receives the command, it transmits the version to the host.

```Python
def get_version():
    # Get version command
    mp1.write_raw(pack_cmd(0x01))
    
    # Response: ACK
    get_ack()
    
    # Response: Bootloader version
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\tversion {int(hex(0x10)[2:])/10}")

    # Response: Option byte 1
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\tOption byte 1")
    
    # Response: Option byte 2
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\tOption byte 2")

    # Response: ACK
    get_ack()
```

The Get ID command is used to get the version of the device ID (identification).
When the device receives the command, it transmits the device ID to the host.

```Python
def get_id():
    # Get ID command
    mp1.write_raw(pack_cmd(0x02))
    
    # Response: ACK
    get_ack()

    # Response: number of following bytes – 1
    r = mp1.read_bytes(1)[0]
    if r >= 0:
        print(f"{format(r, '#04x')}\t\t{r} + 1 bytes to follow")
    else:
        print(f"{format(r, '#04x')}")
        raise RuntimeError("Did not receive number of bytes to follow.")

    # Response: device ID
    r = mp1.read_bytes(2)
    if r == b'\x05\x00':
        print(format(r[0], '#04x'), format(r[1], '#04x'), "\tSTM32MP15x")
    elif r == b'\x05\x01':
        print(format(r[0], '#04x'), format(r[1], '#04x'), "\tSTM32MP13x")
    else:
        print(format(r[0], '#04x'), format(r[1], '#04x'))
        raise RuntimeError("Did not receive device ID.")

    # Response: ACK
    get_ack()
```

The Get phase command enables the host to get the phase ID, in order to identify
the next partition that is going to be downloaded.

The download address, when present, provides the destination address in memory.
A value of 0xFFFFFFFF means than the partition is going to be written in NVM.

Phase ID = 0xFF corresponds to an answered value Reset, in this case the
information bytes provide the cause of the error in a string just before
executing the reset.

The ROM code sends phase = TF-A

```
Byte 1: ACK
Byte 2 N = 6
Byte 3: phase ID (file containing FSBL = TF-A, 1)
Byte 4-7: 0x2FFC2400 on STM32MP15x, 0x2FFDFE00 on STM32MP13x
Byte 8: X = 1
Byte 9: 0: reserved
Byte 10: ACK
```

```Python
def get_phase():
    # Get phase command
    mp1.write_raw(pack_cmd(0x03))
    
    # Response: ACK
    get_ack()

    # Response: number of following bytes – 1
    r = mp1.read_bytes(1)[0]
    if r >= 0:
        print(f"{format(r, '#04x')}\t\t{r} + 1 bytes to follow")
    else:
        print(f"{format(r, '#04x')}")
        raise RuntimeError("Did not receive number of bytes to follow.")

    # Response: phase ID
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\tPhase ID")

    # Response: download address
    r = mp1.read_bytes(4)
    print(format(r[3], '#04x'), end='')
    print(format(r[2], '02x'), end='')
    print(format(r[1], '02x'), end='')
    print(format(r[0], '02x'), end='')
    print("\tDownload address")

    # Response: number of additional bytes
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\t{r} additional bytes following")
    
    # Response: reserved
    r = mp1.read_bytes(1)[0]
    print(f"{format(r, '#04x')}\t\t{r} Reserved")

    # Response: ACK
    get_ack()
```

The download command is used to download a binary code (image) into the SRAM
memory or to write a partition in NVM.

Two types of operations are available:

- Normal operation: download current partition binary to the device. For
initialization phase the partitions are loaded in SRAM, otherwise for writing
phase the partition are written in NVM.

- Special operation: download non-signed data to non-executable memory space

A Start command is necessary to finalize these operations after the download
command.

The Packet number is used to specify the type of operation and the number of the
current packet. The table below gives the description of the packet number.

Byte | Value  | Description
:---:|:------:|:------------------------------------------|
  3  | 0x00   | Normal operation: write in current phase  |
  .  | 0xF2   | Special operation: OTP write              |
  .  | 0xF3   | Special operation: Reserved               |
  .  | 0xF4   | Special operation PMIC: NVM write         |
  .  | Others | Reserved                                  |
 0-2 | ---    | Packet number, increasing from 0 to 0xFFFFFF (*) 

Packet number it is not an address as on STM32 MCU with only memory mapped
flash, but the index of the received packet. The offset of the packet N the
offset in the current partition/phase is N* 256 bytes when only full packets are
used.

```Python
def download(num, data):
    # Data sanity check
    print(f"Packet number {num} of length {len(data)}:")
    if len(data) > 256:
        raise RuntimeError("Too much data to send.")
        
    # Send "Download" command
    mp1.write_raw(pack_cmd(0x31))
    
    # Response: ACK
    get_ack(" command")
    
    # Packet number
    i0 = (num >> 0*8) & 0xff
    i1 = (num >> 1*8) & 0xff
    i2 = (num >> 2*8) & 0xff
    mp1.write_raw(struct.pack("BBBB", 0x00, i2, i1, i0))

    # Checksum byte: XOR (byte 3 to byte 6)
    mp1.write_raw(struct.pack("B", i2 ^ i1 ^ i0))
    
    # Response: ACK
    get_ack(" packet number")
    
    # Packet size (0 < N < 255)
    mp1.write_raw(struct.pack("B", len(data) - 1))
    
    # N-1 data bytes
    for d in data:
        mp1.write_raw(struct.pack("B", d))
        
    # Checksum byte: XOR (byte 8 to Last-1)
    checksum = len(data) - 1
    for d in data:
        checksum ^= d
    mp1.write_raw(struct.pack("B", checksum))

    # Response: ACK
    get_ack(" data")
```

The Read memory command is used to read data from any valid memory address in
the system memory.

When the device receives the read memory command, it transmits the ACK byte to
the application. After the transmission of the ACK byte, the device waits for an
address (4 bytes) and a checksum byte, then it checks the received address. If
the address is valid and the checksum is correct, the device transmits an ACK
byte, otherwise it transmits a NACK byte and aborts the command.

When the address is valid and the checksum is correct, the device waits for N (N
= number of bytes to be received -1) and for its complemented byte (checksum).
If the checksum is correct the device transmits the needed data (N+1 bytes) to
the application, starting from the received address. If the checksum is not
correct, it sends a NACK before aborting the command.

```Python
def read_memory(addr, num_bytes):
    print("Note: read memory command not supported by ROM code STM32MP13x.")
    
    # Data sanity check
    if num_bytes > 256:
        raise RuntimeError("Too much data to receive.")
        
    # Send "Read memory" command
    mp1.write_raw(pack_cmd(0x11))
    
    # Response: ACK
    get_ack(" command")

    # Start address
    i0 = (addr >> 0*8) & 0xff
    i1 = (addr >> 1*8) & 0xff
    i2 = (addr >> 2*8) & 0xff
    mp1.write_raw(struct.pack("BBBB", 0x00, i2, i1, i0))

    # Checksum byte: XOR (byte 3 to byte 6)
    mp1.write_raw(struct.pack("B", i2 ^ i1 ^ i0))
    
    # Response: ACK
    get_ack(" start address")
    
    # Number of bytes to be received – 1 (N = [0, 255])
    # (also Checksum byte: XOR)
    mp1.write_raw(pack_cmd(num_bytes - 1))
    
    # Response: ACK
    get_ack(" number of bytes")
```

The Start command is used:

- To execute the code just downloaded in the memory or any other code by
branching to an address specified by the application. When the device receives
the Start command, it transmits the ACK byte to the application. If the address
is valid the device transmits an ACK byte and jumps to this address, otherwise
it transmits a NACK byte and aborts the command.

- To finalize the last download command, when the host indicates the address =
0xFFFFFFFF.

```Python
def start(addr):
    # Send "Start" command
    mp1.write_raw(pack_cmd(0x21))
    
    # Response: ACK
    get_ack(" command")

    # Start address
    i0 = (addr >> 0*8) & 0xff
    i1 = (addr >> 1*8) & 0xff
    i2 = (addr >> 2*8) & 0xff
    i3 = (addr >> 3*8) & 0xff
    mp1.write_raw(struct.pack("BBBB", i3, i2, i1, i0))

    # Checksum byte: XOR (byte 3 to byte 6)
    mp1.write_raw(struct.pack("B", i3 ^ i2 ^ i1 ^ i0))
    
    # Response: ACK
    get_ack(" address")
```

To download a complete file:

```Python
def down_file(fname='tf-a-stm32mp135f-dk.stm32'):
    # size of each chunk (must be <= 256 bytes)
    sz = 256

    # open file with the bitstream
    with open(fname, 'rb') as f:
        fb = f.read()

    # split file into this many chunks
    num_chunks = int(np.ceil(len(fb) / sz))

    # send each chunk one by one
    for i in tqdm(range(num_chunks)):
        chunk = fb[i*sz : (i+1)*sz]
        download(i, chunk)
        
    # necessary to finalize download
    start(0xFFFFFFFF)
```

### Flash the Evaluation Board

We simply run the functions one after the other and verify that the output
printed matches what's shown here.

As an example, we will use the Blink program that we develop, compile, and
package in [this repo.](https://github.com/js216/mp135_boot/tree/main/blink_noide)

```
>>> uart_init()
0x79		ACK

>>> get()
0x79		ACK
0x06		6 + 1 bytes to follow
0x40		version 1.0
0x06		cmd = Get
0x06		cmd = Get Version
0x06		cmd = Get ID
0x06		cmd = Get phase
0x06		cmd = Start (Go)
0x06		cmd = Download (Write Memory)
0x79		ACK

>>> get_version()
0x79		ACK
0x10		version 1.0
0x00		Option byte 1
0x00		Option byte 2
0x79		ACK

>>> get_id()
0x79		ACK
0x01		1 + 1 bytes to follow
0x05 0x01 	STM32MP13x
0x79		ACK

>>> get_phase()
0x79		ACK
0x06		6 + 1 bytes to follow
0x01		Phase ID
0x2ffdfe00	Download address
0x01		1 additional bytes following
0x00		0 Reserved
0x79		ACK

>>> down_file(fname='blink.stm32')
Packet number 0 of length 256:
0x79		ACK command
0x79		ACK packet number
0x79		ACK data
...
(skip over lots of packets)
...
Packet number 264 of length 156:
0x79		ACK command
0x79		ACK packet number
0x79		ACK data
0x79		ACK command
0x79		ACK address
```

After a little bit, the red LED on the evaluation board will blink. Success!

### Flash a Custom Board

Amazingly, the exact same procedure works on any custom board, so long as it
breaks out the UART4 pin and applies 3.3V and 1.35V power supplies in the
correct sequence. Find the schematics and layout files for my board in
[this repository.](https://github.com/js216/stm32mp135_test_board)

Since the custom board does not use STPMIC1, the code for the blink example is
even simpler. Find it [here.](https://github.com/js216/stm32mp135_test_board/tree/main/baremetal/blink)

The UART wires (green/yellow) and the two power supplies is all that needs to be
connected, and then the red LED (middle of the PCB) will blink. Yes, the setup
is that simple!

![](../images/first_blink.jpg)

[^app]: ST application note AN5275, "USB DFU/USART protocols used in STM32MP1
    Series bootloaders".

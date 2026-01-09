---
title: Debugging STM32MP135 Kernel Decompression
author: Jakob Kastelic
date:
topic: Linux
description: >
   Tracing a silent STM32MP135 Linux boot hang: kernel decompression, JTAG
   debugging, and the DDR wiring mistake that caused deterministic corruption.
---

![](../images/altair.jpg)

*This is Part 8 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

My [STM32MP135 board](https://github.com/js216/stm32mp135_test_board) includes
DDR3L RAM and initial tests shows that I can fill it up with pseudo-random data
and read it back correctly. ST provides a DDR test
[utility](https://github.com/STMicroelectronics/STM32DDRFW-UTIL) with a suite of
memory tests, all of which pass. I decided to take it a step further and test
the memory on a more intensive real-world task: "unzipping" a compressed file.

### Summary

The result of the decompression test was very bad: most of the file was
uncompressed correctly, with just a few bits always wrong, and just a few of
them only sometimes wrong. I spent two or three days tracing my way through the
"unzip" code, instruction by instruction, to try to catch where exactly it goes
wrong.

In the end, I made an embarrassing discovery: I have partially swapped byte
lanes. DDR3L on this SoC has two byte lanes, each consisting of {data, mask,
strobe}. I have connected the data bits correctly, but swapped the mask & strobe
between the two bytes. (Six high speed traces, some on inner layers—there's no
fixing that by hand.) Had I also swapped the data bits, everything would have
been fine; indeed, the eval board swaps all the wires, which led me astray.
(Partially.)

Sadly, AI was of no help in this instance. Given my DDR3L wiring, I can convince
it either way: the connections are good; the connections are not good. In the
end, only Rev B will tell for sure.

### Problem statement

In this article we will proceed with debugging boot of the compressed Linux
kernel image (`zImage`) on a [custom
board](https://github.com/js216/stm32mp135_test_board) populated with the
STM32MP135 SoC. The starting point will be the build that runs on the
evaluation board as described in the [previous
article](https://embd.cc/build-linux-for-stm32mp135-in-under-50-lines-of-makefile).

Despite booting just fine, the `zImage` gets stuck on boot on the custom board,
without any messages printed to the UART console. Following along with the
debugger shows that the decompressor code does run, but it's not clear where
exactly it gets stuck.

### Power supply

It is possible that the burst of DDR activity during the high-speed
decompression draws more current than the 1.35V supply is able to provide,
despite the decoupling capacitance.

Indeed, on the scope I see a 30mV drop in the 1.35V supply voltage for about
500ms. However, if I raise the supply voltage by the 30mV, the boot still gets
stuck. This was with kernel being written to 0xC2008000 and the DTB to
0xC4008000, which means that relocation isn't necessary. My interpretation is
that the scope trace shows that decompression takes about half a second.

Interestingly, if the kernel is written to 0xC0008000 and DTB to 0xC2008000, in
which case relocation is necessary, the 20mV supply drop is shorter, about
150ms, and is followed by 10ms of a bigger drop, 120mV. That drop is indeed
enough to disturb the decompression, since raising the supply voltage setpoint
to 1.38V makes the bigger voltage drop be followed by 500ms of the usual 30mV
drop. My interpretation: relocation takes 150ms, followed by 500ms of
decompression, but the power supply is not stiff enough for
relocation/decompression.

Soldering 1000uF electrolytic capacitors to the 1.25V and 1.35V rails, the
effect is that both relocation and decompression complete (according to the
scope trace, i.e., the 150ms and 500ms voltage drops are visible) with the two
rails at 1.35V, 1.30V, 1.25V, 1.20V, 1.15V, but not below that. Restoring the
supply setpoint to 1.35V, we see that the relocation and decompression complete
as expected.

In order to avoid wasting time with relocation, we will from now on load the
kernel to 0xC2000000 and the device tree to 0xC4000000. The scope trace of the
1.35V rail shows a small voltage drop for 500ms (decompression).

### UART print during decompression

It's not reassuring that we get zero console output during decompression. Trying
to get at least some output, I added `CONFIG_DEBUG_LL=y` to the `.config` file
and accepted most of the default options suggested by make:

```
Kernel low-level debugging functions (read help!) (DEBUG_LL) [Y/n/?] y
  Kernel low-level debugging port
  > 1. Use STM32MP1 UART for low-level debug (STM32MP1_DEBUG_UART) (NEW)
    2. Kernel low-level debugging via EmbeddedICE DCC channel (DEBUG_ICEDCC) (NEW)
    3. Kernel low-level debug output via semihosting I/O (DEBUG_SEMIHOSTING) (NEW)
    4. Kernel low-level debugging via 8250 UART (DEBUG_LL_UART_8250) (NEW)
    5. Kernel low-level debugging via ARM Ltd PL01x Primecell UART (DEBUG_LL_UART_PL01X) (NEW)
  choice[1-5?]:
Enable flow control (CTS) for the debug UART (DEBUG_UART_FLOW_CONTROL) [N/y/?] (NEW)
Physical base address of debug UART (DEBUG_UART_PHYS) [0x40010000] (NEW)
Virtual base address of debug UART (DEBUG_UART_VIRT) [0xfe010000] (NEW)
Early printk (EARLY_PRINTK) [N/y/?] (NEW) y
Write the current PID to the CONTEXTIDR register (PID_IN_CONTEXTIDR) [N/y/?] n
```

However, no output appeared on the UART. Loading `Image` (rather than `zImage`)
produces the early prints, but the decompression hang mystery persists.

### JTAG

Note: follow along this section with the help of `linusw`'s article, ["How the
ARM32 Linux kernel
decompresses"](https://people.kernel.org/linusw/how-the-arm32-linux-kernel-decompresses).

Let's try to follow along the decompression using a J-Link debug probe. First,
open the GDB server and connect to it:

```
JLinkGDBServer.exe -device STM32MP135F -if swd -port 2330
arm-none-eabi-gdb.exe -q -x load.gdb
```

Where the `load.gdb` script contains:

```
file build/main.elf
add-symbol-file build/compressed 0xc2000000
target remote localhost:2330
monitor reset
monitor flash device=STM32MP135F
load build/main.elf
monitor go
break handoff.S:93
```

Step instruction a few times till reaching just after the handoff code:

```
(gdb) bt
#0  0xc2000004 in _text () at arch/arm/boot/compressed/head.S:202
```

This shows that execution has begun at the beginning of the decompressor, in
file `arch/arm/boot/compressed/head.S`, in the `start:` label. We can step
through the code lines (`n` command in gdb) until reaching the line `bne
not_angel`, which we have to step into (`si`):

```
(gdb) si
not_angel () at arch/arm/boot/compressed/head.S:245
245                     safe_svcmode_maskall r0
```

Go forward (`n`) a few steps till reaching the C function
`fdt_check_mem_start()` (`arch/arm/boot/compressed/fdt_check_mem_start.c`), then
call `finish` to get out of it and continue stepping through the `not_angel`
section:

```
(gdb) finish
Run till exit from #0  fdt_check_mem_start (mem_start=1, fdt=0xc4000000) at
arch/arm/boot/compressed/fdt_check_mem_start.c:106
not_angel () at arch/arm/boot/compressed/head.S:312
312                     add     r4, r0, #TEXT_OFFSET
Value returned is $3 = 3221225472
(gdb) n
323                     mov     r0, pc
324                     cmp     r0, r4
325                     ldrcc   r0, .Lheadroom
326                     addcc   r0, r0, pc
327                     cmpcc   r4, r0
328                     orrcc   r4, r4, #1              @ remember we skipped cache_on
329                     blcs    cache_on
```

Step into `cache_on` and later `call_cache_fn`, and go through the many lines
till reaching the return from `__armv7_mmu_cache_on:`. Thus we reach the
`restart:` section:

```
(gdb) b 902
Breakpoint 3 at 0xc200055c: file arch/arm/boot/compressed/head.S, line 902.
(gdb) c
Continuing.

Breakpoint 3, __armv7_mmu_cache_on () at arch/arm/boot/compressed/head.S:902
902                     mcr     p15, 0, r0, c7, c5, 4   @ ISB
(gdb) n
903                     mov     pc, r12
(gdb) si
restart () at arch/arm/boot/compressed/head.S:331
331     restart:        adr     r0, LC1
```

Continue stepping through until reaching the `wont_overwrite:` section, and
then `not_relocated:`, where we clear BSS. Step through that, and we reach the
beginning of the decompression proper: the `decompress_kernel()` function in
`arch/arm/boot/compressed/misc.c`. Interestingly, we step right past the
`putstr("Uncompressing Linux...");` line without seeing anything printed on the
UART console.

The function `decompress_kernel()` calls `do_decompress()`, which calls
`__decompress` which calls `__gunzip`. Calling `finish` on the latter exactly
correlates with the 500ms of the voltage drop observed on the 1.35V supply as
mentioned above. Now we're back in the `decompress_kernel()` function, which
should print " done, booting the kernel.\n" (but doesn't, since there's
something wrong with my `putstr` function).

We return back to the `not_relocated:` section of the compressed `head.S` and
call `get_inflated_image_size` to find out how large the decompressed kernel
is:

```
not_relocated () at arch/arm/boot/compressed/head.S:636
636                     get_inflated_image_size r1, r2, r3
638                     mov     r0, r4                  @ start of inflated image
639                     add     r1, r1, r0              @ end of inflated image
(gdb) p/x $r0
$3 = 0xc0008000
(gdb) p/x $r1
$4 = 0xc1241f48
(gdb)
```

Subtracting the `r1` and `r0` values, we see that the uncompressed kernel is
exactly 19111752 bytes in size, which is identical to the size of the
`arch/arm/boot/Image` file. So far so good!

Next, the startup code cleans caches and turns them off again and jumps to
`__enter_kernel` just like we may do directly, had we loaded the uncompressed
image in memory with the bootloader. This places the pointer to the DTB into
`r2` and passes control to the kernel:

```
__enter_kernel () at arch/arm/boot/compressed/head.S:1435
1435                    mov     r0, #0                  @ must be 0
1436                    mov     r1, r7                  @ restore architecture number
1437                    mov     r2, r8                  @ restore atags pointer
1438     ARM(           mov     pc, r4          )       @ call kernel
```

Just before the jump to the kernel, we can check that the register values make
sense: `r0` and `r1` are zero, `r2` has the DTB address, and the decompressed
kernel will run from location `0xC0008000` (= `TEXT_OFFSET`):

```
(gdb) p $r0
$5 = 0
(gdb) p $r1
$6 = 0
(gdb) p/x $r2
$8 = 0xc4000000
(gdb) p/x $r4
$9 = 0xc0008000
(gdb)
```

One fateful step and we're running in the uncompressed kernel proper. Let's
load the symbols from the main kernel ELF file to see what's going on:

```
(gdb) si
0xc0008000 in ?? ()
(gdb) add-symbol-file build/vmlinux 0xc0008000
add symbol table from file "build/vmlinux" at
        .text_addr = 0xc0008000
Reading symbols from build/vmlinux...
(gdb)
```

Interesting, just one more step and the debugger stops as some much later point:

```
gdb) si
0xc0114620 in perf_swevent_init_hrtimer (event=0xc0008000 <stext>) at kernel/events/core.c:10836
10836                   hwc->sample_period = event->attr.sample_period;
(gdb) bt
#0  0xc0114620 in perf_swevent_init_hrtimer (event=0xc0008000 <stext>) at kernel/events/core.c:10836
#1  perf_swevent_init_hrtimer (event=0xc0008000 <stext>) at kernel/events/core.c:10818
#2  cpu_clock_event_init (event=0xc0008000 <stext>) at kernel/events/core.c:10902
#3  0xc271e9f0 in ?? ()
```

But if we `finish` running the `perf_swevent_init_hrtimer` function, then
somehow we end up back in `arch/arm/kernel/head.S`. Debugging from that point
onwards appears to have gone totally insane!

### Decompressor handoff to regular kernel code

Let's start again from scratch. Set a breakpoint at the point where the
uncompressed kernel is supposed to begin executing:

```
(gdb) b *0xc0008000
Breakpoint 6 at 0xc0008000: file arch/arm/kernel/head.S, line 501.
(gdb) c
Continuing.

Breakpoint 6, stext () at arch/arm/kernel/head.S:501
501             mov     r0, r0
(gdb) p $pc
$11 = (void (*)()) 0xc0008000 <stext>
```

This is strange: program counter is in the expected location, but we're on line
501 into `head.S`, rather than closer to the beginning of the file. The reason
is that we have incorrectly instructed GDB that the entire `vmlinux` starts at
0xC0008000, instead of just the first section. We can fix it by clearing the
symbol file, re-loading the symbols at their natural link address, and
verifying everything makes sense:

```
(gdb) symbol-file
Error in re-setting breakpoint 1: No source file named handoff.S.
No symbol file now.
(gdb) file build/vmlinux
Reading symbols from build/vmlinux...
(gdb) p/x &stext
$15 = 0xc0008000
(gdb) si
__hyp_stub_install () at arch/arm/kernel/hyp-stub.S:73
73              store_primary_cpu_mode  r4, r5
(gdb) finish
Run till exit from #0  __hyp_stub_install () at arch/arm/kernel/hyp-stub.S:73
stext () at arch/arm/kernel/head.S:105
105             safe_svcmode_maskall r9
```

Now we're simply running through the beginning of the normal kernel start in
section `ENTRY(stext)` in file `arch/arm/kernel/head.S`. By single stepping
through the code, we can find the exact section where things go badly wrong:

```
stext () at arch/arm/kernel/head.S:162
162             badr    lr, 1f                          @ return (PIC) address
167             mov     r8, r4                          @ set TTBR1 to swapper_pg_dir
169             ldr     r12, [r10, #PROCINFO_INITFUNC]
170             add     r12, r12, r10
171             ret     r12

__v7_ca7mp_setup () at arch/arm/mm/proc-v7.S:302
302             do_invalidate_l1
0xc01197fc      302             do_invalidate_l1
0xc0119800      302             do_invalidate_l1
0xc0119804      302             do_invalidate_l1

v7_invalidate_l1 () at arch/arm/mm/cache-v7.S:40
40              mov     r0, #0
41              mcr     p15, 2, r0, c0, c0, 0   @ select L1 data cache in CSSELR
(gdb)
0x2fff2f08 in ?? ()
```

We see that after the last `mcr` instruction, the code lands up in SYSRAM
instead of the DDR, from where we've been executing so far. That address
corresponds to the vectors as have been installed by the bootloader; in
particular, we have gotten into the dummy SVC handler.

Let's examine the program instructions at the point just before where the
failure occurs:

```
Breakpoint 7, v7_invalidate_l1 () at arch/arm/mm/cache-v7.S:40
40              mov     r0, #0
(gdb) x/4x $pc
0xc0118b2c <v7_invalidate_l1>:  0xe3a00000      0x2f400f10      0xffffffff      0xee300f10
```

Very interesting! The expected instruction, `0xe3a00000`, is followed by
`0x2f400f10` and `0xffffffff`. The first one is the "mystery" SVC call, and the second one
is simply undefined:

```
(gdb) set {int}0xc0000000 = 0x2f400f10
(gdb) x/i 0xc0000000
   0xc0000000:  svccs   0x00400f10
(gdb) set {int}0xc0000000 = 0xffffffff
(gdb) x/i 0xc0000000
   0xc0000000:                  @ <UNDEFINED> instruction: 0xffffffff
```

For comparison, here's the instructions we expect to find from the disassembly
of the ELF file:

```
$ arm-linux-gnueabi-objdump -d linux/vmlinux | grep -A 4 "v7_invalidate_l1"
c0118b2c <v7_invalidate_l1>:
c0118b2c:       e3a00000        mov     r0, #0
c0118b30:       ee400f10        mcr     15, 2, r0, cr0, cr0, {0}
c0118b34:       f57ff06f        isb     sy
c0118b38:       ee300f10        mrc     15, 1, r0, cr0, cr0, {0}
```

### DDR corruption pattern

Let's compare the binary pattern between the expected and actual instructions:

```
Expected: 0xee400f10 = 0b11101110010000000000111100010000
Actual:   0x2f400f10 = 0b00101111010000000000111100010000
---------------------------------------------------------
Diff:       ^^           ^^     ^
```

Three bits have been flipped in this instruction, changing it from `mcr` to
`svc`. This could be explained if DDR is miswired or misconfigured. However,
the pattern of data corruption is repeatable: reboot after reboot, the same
instruction gets corrupted in exactly the same way!

To prove that the DDR is capable of holding data at this address, we can write
it manually and step through the instructions without any weird jumps to
vectors:

```
(gdb) x/4x $pc
0xc0118b2c <v7_invalidate_l1>:  0xe3a00000      0x2f400f10      0xffffffff      0xee300f10
(gdb) set {int}0xc0118b30 = 0xee400f10
(gdb) set {int}0xc0118b34 = 0xf57ff06f
(gdb) x/4x $pc
0xc0118b2c <v7_invalidate_l1>:  0xe3a00000      0xee400f10      0xf57ff06f      0xee300f10
(gdb) si
41              mcr     p15, 2, r0, c0, c0, 0   @ select L1 data cache in CSSELR
42              isb
43              mrc     p15, 1, r0, c0, c0, 0   @ read cache geometry from CCSIDR
45              movw    r3, #0x3ff
```

We can also load and run the decompressor as usual and set a breakpoint to
0xC0008000, where the uncompressed kernel is supposed to take over. Then, we
simply overwrite whatever the decompressor has written from gdb:

```
(gdb) restore build/Image binary 0xc0008000
Restoring binary file build/Image into memory (0xc0008000 to 0xc1241f48)
(gdb) c
```

Nothing has been printed to the console, since apparently the decompressor
disabled the console, but if we stop the debugger (Ctrl-C), we see that the
kernel proceeded with the boot and finally came to a stop when mounting the
root filesystem (understandable, since we haven't given it a rootfs yet):

```
(gdb) bt
#0  0xc0b87034 in __timer_delay (cycles=63999) at arch/arm/lib/delay.c:50
#1  0xc0bb2238 in panic (fmt=0xc0defa0c "VFS: Unable to mount root fs on %s") at kernel/panic.c:451
#2  0xc1001878 in mount_block_root (name=0x51 <error: Cannot access memory at address 0x51>, name@entry=0xc0defaa0 "/dev/root", flags=3900) at init/do_mounts.c:432
#3  0xc1001b50 in mount_root () at init/do_mounts.c:592
#4  0xc1001cc8 in prepare_namespace () at init/do_mounts.c:644
#5  0xc1001448 in kernel_init_freeable () at init/main.c:1644
#6  0xc0bc5f18 in kernel_init (unused=<optimized out>) at init/main.c:1519
#7  0xc0100148 in ret_from_fork () at arch/arm/kernel/entry-common.S:148
```

### Deterministic DDR corruption

Let's assume that the data corruption is deterministic (repeatable) because it
is caused by a voltage drop. Since the voltage drop corresponds to the CPU/DDR
activity, the same activity causes the same voltage drop, which causes the same
corruption.

Let's check the same instruction at different supply voltages. At 1.35V, 1.30V,
1.25V, the corruption is:

```
0xc0118b2c <v7_invalidate_l1>:  0xe3a00000 0x2f400f10 0x00000000 0xee300f10
```

At 1.20V, the pattern is more interesting: the third instruction gets corrupted
each time, but differently each reset:

```
0xc0118b2c <v7_invalidate_l1>:  0xe3a00000 0x2f400f10 0xe464f8f6 0xee300f10
# or this one:
0xc0118b2c <v7_invalidate_l1>:  0xe3a00000 0x2f400f10 0xcbfd2cb6 0xee300f10
# or this one:
0xc0118b2c <v7_invalidate_l1>:  0xe3a00000 0x2f400f10 0xaefc67e9 0xee300f10
```

Even more strange: restoring voltage back up to 1.35V, the third instruction
now gets corrupted differently every time, while the first and last are always
correct, and the second one is always corrupted the same way.

### Check SD card and bootloader copy integrity

One obvious way that data corruption could happen is the if the compressed
`zImage` was written wrong to the SD card, or if the bootloader writes it to
DDR wrong. First, we check how big the `zImage` is, and then ask the debugger
to dump the data from the DDR to a file, at the point just before the handoff
from the bootloader into the decompressor:

```
$ ls -l linux/arch/arm/boot/zImage
-rwxr-xr-x 1 jk jk 7461288 Jan  7 11:09 linux/arch/arm/boot/zImage

Breakpoint 1, handoff_jump () at src/handoff.S:93
93         smc #0
(gdb) dump binary memory dump.bin 0xC2000000 0xC271d9a8
```

We see that the original image is identical to the one we obtained from the
dump, so the SD card and bootloader writes are not corrupted:

```
9040ec8b8da5e613aa6e56060cc0cacf6779eec670c3a4123177cd07aff63300  zImage
9040ec8b8da5e613aa6e56060cc0cacf6779eec670c3a4123177cd07aff63300  dump.bin
```

### Test DDR using STM32DDRFW-UTIL

ST provides a [utility](https://github.com/STMicroelectronics/STM32DDRFW-UTIL)
which they recommend to run as a part of any new PCB bring-up. I have done that
already and did not think much of it since all tests passed. Let's take a
closer look.

My "version" of the utility can be found in
[this](https://github.com/js216/stm32mp135_test_board/tree/main/baremetal/STM32DDRFW-UTIL)
repository. I made two small changes: instead of requiring the complicated
"Cube" software suite, there is a simple Makefile so that the whole utility can
be compiled easily with a single `make` invocation. Second, I have commented
out the three or so lines that initialize the STPMIC1, since my board does not
use that power controller.

Let's load the utility through the debugger, since it is running already:

```
(gdb) file build/fwutil.elf
Reading symbols from build/fwutil.elf...
(gdb) load
Loading section .RESET, size 0xe000 lma 0x2ffe0000
Loading section .ARM, size 0x8 lma 0x2ffee000
Loading section .init_array, size 0x4 lma 0x2ffee008
Loading section .fini_array, size 0x4 lma 0x2ffee00c
Loading section .data, size 0x7fa lma 0x2ffee010
Start address 0x2ffe0000, load size 59402
Transfer rate: 260 KB/sec, 7425 bytes/write.
(gdb) c
Continuing.
```

On the serial console, we are greeted with the expected prompt:

```
=============== UTILITIES-DDR Tool ===============
Model: STM32MP13XX_DK
RAM: DDR3-1066 bin F 1x4Gb 533MHz v1.53
0:DDR_RESET
DDR>
```

As the utility readme instructs us, let us enter the `DDR_READY` step and then
execute all the tests:

```
DDR>step 3
step to 3:DDR_READY
1:DDR_CTRL_INIT_DONE
2:DDR_PHY_INIT_DONE
3:DDR_READY
DDR>test 0
result 1:Test Simple DataBus = Passed
result 2:Test DataBusWalking0 = Passed
result 3:Test DataBusWalking1 = Passed
result 4:Test AddressBus = Passed
result 5:Test MemDevice = Passed
result 6:Test SimultaneousSwitchingOutput = Passed
result 7:Test Noise = Passed
result 8:Test NoiseBurst = Passed
result 9:Test Random = Passed
result 10:Test FrequencySelectivePattern = Passed
result 11:Test BlockSequential = Passed
result 12:Test Checkerboard = Passed
result 13:Test BitSpread = Passed
result 14:Test BitFlip = Passed
result 15:Test WalkingZeroes = Passed
result 16:Test WalkingOnes = Passed
Result: Pass [Test All]
```

This takes about a second to complete, and on the scope trace monitoring the
1.35V supply we see a tiny (maybe 2-5mV) dip during this time.

After all the tests are done, we can use the `save` command to get the DDR
parameters from the utility. Here are the dynamic ones, reporting on the
status:

```
/* ctl.dyn */
#define DDR_STAT 0x00000001
#define DDR_INIT0 0x4002004e
#define DDR_DFIMISC 0x00000001
#define DDR_DFISTAT 0x00000001
#define DDR_SWCTL 0x00000001
#define DDR_SWSTAT 0x00000001
#define DDR_PCTRL_0 0x00000001

/* phy.dyn */
#define DDR_PIR 0x00000000
#define DDR_PGSR 0x0000001f
#define DDR_ZQ0SR0 0x80021dee
#define DDR_ZQ0SR1 0x00000000
#define DDR_DX0GSR0 0x00008001
#define DDR_DX0GSR1 0x00000000
#define DDR_DX0DLLCR 0x40000000
#define DDR_DX0DQTR 0xffffffff
#define DDR_DX0DQSTR 0x3db02001
#define DDR_DX1GSR0 0x00008001
#define DDR_DX1GSR1 0x00000000
#define DDR_DX1DLLCR 0x40000000
#define DDR_DX1DQTR 0xffffffff
#define DDR_DX1DQSTR 0x3db02001
```

All the other parameters returned from the utility are identical to the values
already used in the bootloader. Thus, I hope I can assume that the DDR
configuration in the bootloader is identical to the one used in the bootloader.

### When does data get corrupted

Above we have found that while decompression appears to finish successfully, it
in fact leaves behind lots of partially corrupted data. The uncompressed kernel
starts executing, only the trip into the SVC handler because of a corrupted
instruction. Now, let's try to track down exactly when the data first gets
corrupted.

As seen above, in the current configuration, decompression takes place in the
`__gunzip` routine (`decompress_inflate.c`). The decompression is done by
`zlib_inflate()` (`lib/zlib_inflate/inflate.c`). First, clear the memory
location that we're interested in observing:

```
set {unsigned int}0xc0118b2c = 0x0
set {unsigned int}0xc0118b30 = 0x0
set {unsigned int}0xc0118b34 = 0x0
set {unsigned int}0xc0118b38 = 0x0
```

Verify it has been cleared:

```
(gdb) x/4x 0xc0118b2c
0xc0118b2c:     0x00000000      0x00000000      0x00000000      0x00000000
```

Some interesting breakpoints:

```
(gdb) b *0xc2001878
Breakpoint 20 at 0xc2001878: file arch/arm/boot/compressed/../../../../lib/zlib_inflate/inflate.c, line 63.
(gdb) b *0xc2001fa4
Breakpoint 34 at 0xc2001fa4: file arch/arm/boot/compressed/../../../../lib/zlib_inflate/inflate.c, line 582.
```

As it turns out, the corruption appears after the second call to `inflate_fast`:

```
(gdb) c
Continuing.

Breakpoint 36, zlib_inflate (strm=0xc271ea44, strm@entry=0xc271e9c0, flush=1072676126, flush@entry=0) at arch/arm/boot/compressed/../../../../lib/zlib_inflate/inflate.c:582
582                     inflate_fast(strm, out);
(gdb) x/4x 0xc0118b2c
0xc0118b2c:     0x00000000      0x00000000      0x00000000      0x00000000
(gdb) c
Continuing.

Breakpoint 36, zlib_inflate (strm=0xc271ea44, strm@entry=0xc271e9c0, flush=1072590367, flush@entry=0) at arch/arm/boot/compressed/../../../../lib/zlib_inflate/inflate.c:582
582                     inflate_fast(strm, out);
(gdb) x/4x 0xc0118b2c
0xc0118b2c:     0xe3a00000      0x2f400f10      0xffedecfd      0xee300f1
```

While we press `c` (or `continue`) in GDB, `inflate_fast()` runs and very
briefly (about 3.5ms), a voltage drop of about 30--40mV is observed on the
1.35V supply. In the same period, `VREF_DDR0`, `VREF_DDR1`, and `VREF_DDR2`
droops are barely perceptible.

We can go a step further and set a watchpoint, so the debugger triggers on the
first access of the given memory location:

```
(gdb) watch *(uint32_t *)0xc0118b2c
Hardware watchpoint 38: *(uint32_t *)0xc0118b2c
```

Set the memory locations to zero as before, and after the watchpoint triggers,
single step through the execution and each time check the memory. Skipping
ahead many such steps, we see how the value gets progressively filled in:

```
0xc0118b2c:     0xe3a00000      0x00000000      0x00000000      0x00000000
0xc0118b2c:     0xe3a00000      0x00000010      0x00000000      0x00000000
0xc0118b2c:     0xe3a00000      0x00000f10      0x00000000      0x00000000
0xc0118b2c:     0xe3a00000      0x00400f10      0x00000000      0x00000000
0xc0118b2c:     0xe3a00000      0x2f400f10      0x00000000      0x00000000
```

We see how it fills up in steps of half byte: zero, `10`, `0f`, `40`, `2f`.
That final `2f` is erroneous; it should be `ee` as we have seen previously in
the disassembly of `vmlinux`.

The code loop that populates this word can be found in
`lib/zlib_inflate/inffast.c`, lines 119 through 308; in particular, the line
that wrote the incorrect `2f` is number 247, in the middle of this section:

```
/* Align out addr */
if (!((long)(out - 1) & 1)) {
   *out++ = *from++;
   len--;
}
```

### Key insight: 8-bit corruption

Let's recap the situation so far. DDR appears to work as far as my own tests
are concerned: I can fill the memory with pseudo-random data and read it all
back correctly. The STM32DDRFW-UTIL tests all pass. The kernel runs if it's
loaded into memory uncompressed, but the decompression fails. Remembering
further back, when writing the bootloader I had to force all DDR writes to be
32-bit aligned. All of this brings to mind the quote from [Jay
Carlson](https://jaycarlson.net/embedded-linux/):

> if your design *doesn't* work, length-tuning is probably the *last* thing you
> should be looking at. For starters, make sure you have all the pins connected
> properly — even if the failures appear intermittent. For example, accidentally
> swapping byte lane strobes / masks (like I've done) will cause 8-bit
> operations to fail without affecting 32-bit operations. Since the bulk of RAM
> accesses are 32-bit, things will appear to kinda-sorta work.

Let's take a good hard look at the connections on my custom board ([Rev
A](https://github.com/js216/stm32mp135_test_board/blob/main/kicad/Rev_A_27may25/schematics.pdf))
between the memory chip (`MT41K256M16TW-107:P TR`) and the SoC
(`STM32MP135FAE`):

| DDR pin | DDR signal | SoC signal | SoC pin | Notes             |
| ------- | ---------- | ---------- | ------- | ----------------- |
| `M2`    | `BA0`      | `BA0`      | `G17`   |                   |
| `N8`    | `BA1`      | `BA1`      | `L16`   |                   |
| `M3`    | `BA2`      | `BA2`      | `G13`   |                   |
| `N3`    | `A0`       | `A0`       | `G16`   |                   |
| `P7`    | `A1`       | `A1`       | `K15`   |                   |
| `P3`    | `A2`       | `A2`       | `F17`   |                   |
| `N2`    | `A3`       | `A3`       | `G15`   |                   |
| `P8`    | `A4`       | `A4`       | `M14`   |                   |
| `P2`    | `A5`       | `A5`       | `E16`   |                   |
| `R8`    | `A6`       | `A6`       | `M17`   |                   |
| `R2`    | `A7`       | `A7`       | `G14`   |                   |
| `T8`    | `A8`       | `A8`       | `L15`   |                   |
| `R3`    | `A9`       | `A9`       | `F16`   |                   |
| `L7`    | `A10/AP`   | `A10`      | `J14`   |                   |
| `R7`    | `A11`      | `A11`      | `K13`   |                   |
| `N7`    | `A12/BC#`  | `A12`      | `K17`   |                   |
| `T3`    | `A13`      | `A13`      | `F14`   |                   |
| `T7`    | `A14`      | `A14`      | `L17`   |                   |
| `D3`    | `UDM`      | `DQM0`     | `D15`   |                   |
| `E7`    | `LDM`      | `DQM1`     | `N14`   |                   |
| `B7`    | `UDQS#`    | `DQS0N`    | `C16`   |                   |
| `C7`    | `UDQS`     | `DQS0P`    | `C17`   |                   |
| `G3`    | `LDQS#`    | `DQS1N`    | `R16`   |                   |
| `F3`    | `LDQS`     | `DQS1P`    | `R17`   |                   |
| `E3`    | `DQ0`      | `DQ4`      | `B16`   |                   |
| `F7`    | `DQ1`      | `DQ2`      | `C13`   |                   |
| `F2`    | `DQ2`      | `DQ0`      | `B17`   |                   |
| `F8`    | `DQ3`      | `DQ5`      | `D16`   |                   |
| `H3`    | `DQ4`      | `DQ3`      | `D17`   |                   |
| `H8`    | `DQ5`      | `DQ7`      | `E15`   |                   |
| `G2`    | `DQ6`      | `DQ1`      | `C15`   |                   |
| `H7`    | `DQ7`      | `DQ6`      | `E14`   |                   |
| `D7`    | `DQ8`      | `DQ8`      | `N16`   |                   |
| `C3`    | `DQ9`      | `DQ9`      | `P17`   |                   |
| `C8`    | `DQ10`     | `DQ10`     | `N15`   |                   |
| `C2`    | `DQ11`     | `DQ15`     | `T16`   |                   |
| `A7`    | `DQ12`     | `DQ11`     | `P15`   |                   |
| `A2`    | `DQ13`     | `DQ12`     | `R15`   |                   |
| `B8`    | `DQ14`     | `DQ13`     | `P16`   |                   |
| `A3`    | `DQ15`     | `DQ14`     | `T17`   |                   |
| `K3`    | `CASN`     | `CASN`     | `J15`   |                   |
| `K9`    | `CKE`      | `CKE`      | `K14`   | 10k pulldown      |
| `K7`    | `CK#`      | `CLKN`     | `J17`   | 100R to CK at DDR |
| `J7`    | `CK`       | `CLKP`     | `J16`   |                   |
| `L2`    | `CS#`      | `CSN`      | `H16`   |                   |
| `K1`    | `ODT`      | `ODT`      | `H15`   |                   |
| `J3`    | `RAS#`     | `RASN`     | `H17`   |                   |
| `T2`    | `RESET#`   | `RESETN`   | `E17`   | 10k pulldown      |
| `L3`    | `WE#`      | `WEN`      | `H13`   |                   |

Let's check carefully what the DDR datasheet considers "upper" vs "lower":

> `DQ[7:0]` Lower byte of bidirectional data bus for the x16 configuration.
>
> `DQ[15:8]` Upper byte of bidirectional data bus for the x16 configuration.

In other words, we should have mapped `DQ[7:0]` together with the DDR signals
`LDM` and `LDQS`, while the upper byte `DQ[15:8]` should have been placed
together with `UDM` and `USDQS`. Looking at the table above, we see that the
mask/strobe signals are swapped:

    DDR:UDM → SoC:DQM0
    DDR:LDM → SoC:DQM1

But the data bits are not swapped, so this is incorrect:

    DDR:DQ[7:0]  → SoC[7:0]  (scrambled)
    DDR:DQ[15:8] → SoC[15:8] (scrambled)

My confusion can be traced back to the eval board design, which similarly swaps
the mask/strobe wires, except they also (correctly) swap the two `DQ` lanes. AI
seems to be of little use: I can easy convince them either way regarding the
correctness of my "semi-byte swap".

### Simple software test for DDR correctness

We saw above that the official ST DDR utility did not detect any problems with
my incorrectly-wired DDR. After some prompting, Gemini 3 gave me the following
test:

```c
void ddr_align_test(int argc, uint32_t arg1, uint32_t arg2, uint32_t arg3)
{
    (void)argc; (void)arg1; (void)arg2; (void)arg3;
    uint32_t sctlr;

    // 1. READ SCTLR
    __asm__ volatile("mrc p15, 0, %0, c1, c0, 0" : "=r" (sctlr));
    
    // 2. DISABLE CACHE (Bit 2) AND MMU (Bit 0)
    uint32_t sctlr_disabled = sctlr & ~((1 << 2) | (1 << 0));
    __asm__ volatile("mcr p15, 0, %0, c1, c0, 0" : : "r" (sctlr_disabled));
    __asm__ volatile("isb sy"); // Instruction sync barrier

    my_printf("!!! CACHE DISABLED !!! Testing raw hardware wires...\r\n");

    volatile uint8_t *p8 = (volatile uint8_t *)0xc0001000;
    
    // Perform a partial write
    p8[0] = 0xAA;
    __asm__ volatile("dsb sy"); // Force pin toggle
    
    if (p8[0] != 0xAA) {
        my_printf("FAILURE DETECTED: Byte 0 is 0x%02x (expected 0xAA)\r\n", p8[0]);
    } else {
        my_printf("SUCCESS: Byte 0 worked without cache.\r\n");
    }

    // 3. RE-ENABLE CACHE
    __asm__ volatile("mcr p15, 0, %0, c1, c0, 0" : : "r" (sctlr));
    __asm__ volatile("isb sy");
}
```

On the evaluation board, the printout is:

```
Eval board: !!! CACHE DISABLED !!! Testing raw hardware wires... 
SUCCESS: Byte 0 worked without cache.
```

On my board:

```
!!! CACHE DISABLED !!! Testing raw hardware wires...
FAILURE DETECTED: Byte 0 is 0x55 (expected 0xAA)
```

### Next steps

While the explanation in the previous section (swapped byte lanes) seems
plausible enough to stop debugging at this point and wait for "Rev B", in the
process I noted other possible avenues to explore:

- Lower slew rate / drive strength or increase output impedance, to reduce
  crosstalk
- Disable data masking entirely, if DDR PHY supports it
- Disable cache during decompression?
- Try out slower slew-rate settings and increasing output impedance for DDR
  controller
- Lower DDR frequency and see if the corruption pattern is the same, worse,
  better?
- Experiment: Run bootloader, Run FWUTIL, Do NOT reset, Jump directly into Linux
- Add more capacitance to the VREF nodes (1uF in parallel with the current
  0.1uF)
- Try to read out from DDR PHY registers the per-byte DQS delays, and per-bit DQ
  delays, and compare with PCB geometry
- Repeat training again and again and see if there's any variations (can I
  detect training failures?)
- Read out write levelling and DQS delay (read leveling) calibration results
- My usual CPU-based DDR tests do not uncover a single bit flip, while the
  heavily cached kernel decompressor shows huge corruption in the decompressed
  output. How to reproduce that in my own code? Could the caches be
  misconfigured, so they are somehow inappropriate for my PCB while being fine
  on the eval board? Maybe caches don't do the same kind of training that DDR
  does.

### LSB swizzling

Just because we found one issue with my connections, it does not mean we have
found all of them. From the [same](https://jaycarlson.net/embedded-linux/)
article by Jay Carlson:

> Because DDR memory doesn't care about the order of the bits getting stored,
> you can swap individual bits --- except the least-significant one if you're
> using write-leveling --- in each byte lane with no issues.

I have not been able to find any evidence of the LSB swapping restriction in ST
literature (datasheet, reference manual, app notes). Indeed, one app note[^app]
just says that the DDR3L connection features "two swappable bytes, and swappable
bits in the same byte".

However, the `MT41K` DDR3L datasheet includes a section on Write Leveling which
explains what's up:

> For better signal integrity, DDR3 SDRAM memory modules have adopted fly-by
> topology for the commands, addresses, control signals, and clocks. Write
> leveling is a scheme for the memory controller to adjust or de-skew the DQS
> strobe (DQS, DQS#) to CK relationship at the DRAM with a simple feedback
> feature provided by the DRAM.  Write leveling is generally used as part of the
> initialization process, if required. For normal DRAM operation, this feature
> must be disabled. [...]
>
> When write leveling is enabled, the rising edge of DQS samples CK, and the
> prime DQ outputs the sampled CK’s status. The prime DQ for a x4 or x8
> configuration is DQ0 with all other DQ (DQ[7:1]) driving LOW. The prime DQ for
> a x16 configuration is DQ0 for the lower byte and DQ8 for the upper byte.

So, just in case, we should make sure not to "swizzle" the two LSBs in each
byte.

<div class="series-box">
<h3 id="series-list">All Articles in This Series</h3>
<ul>
  <li><a href="stm32mp135-linux-default-buildroot">1. STM32MP135 Default Buildroot Configuration</a></li>
  <li><a href="stm32mp135-linux-cubeprog">2. STM32MP135 Flashing via USB with STM32CubeProg</a></li>
  <li><a href="stm32mp135-without-u-boot">3. STM32MP135 Without U-Boot (TF-A Falcon Mode)</a></li>
  <li><a href="linux-tfa-bl33-qemu">4. Linux as TF-A BL33 on Qemu (No U-Boot)</a></li>
  <li><a href="stm32mp135-without-optee">5. STM32MP135 Without OP-TEE</a></li>
  <li><a href="linux-bringup-on-custom-stm32mp135-board">6. Linux Bring-Up on a Custom STM32MP135 Board</a></li>
  <li><a href="build-linux-for-stm32mp135-in-under-50-lines-of-makefile">7. Build Linux for STM32MP135 in under 50 Lines of Makefile</a></li>
  <li><em>8. This article</em></li>
</ul>
</div>

[^app]: Application note AN5692: DDR memory routing guidelines for STM32MP13x
  product lines. January 2023.

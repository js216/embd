---
title: NAND Flash on STM32MP135
author: Jakob Kastelic
date: 13 Mar 2026
topic: Linux
description: >
   Bringing up raw NAND flash on the STM32MP135: wiring, FMC configuration,
   bad-block handling, and booting Linux with UBI/UBIFS from a custom board.
---

![](../images/34.jpg)

*This is Part 10 in the series: Linux on STM32MP135. [See other
articles.](#series-list)*

Getting the NAND flash peripheral to work on the STM32MP135 appears tricky since
the evaluation board does not include it. In this article, we'll check my
connections; we'll extract the relevant parameters from the datasheet, and try
to use the HAL drivers to access the memory chip on my [custom STM32MP135
board](https://github.com/js216/stm32mp135_test_board). Then, we'll set things
up so we can boot the kernel from it.

### Connections

I am using the `MX30LF4G28AD-TI` NAND flash (512 MB) chip, connecting to the
`STM32MP135FAE` SoC, as follows:

| NAND pin | NAND signal | SoC signal      | SoC pin | Notes             |
| -------- | ----------- | --------------- | ------- | ----------------- |
| 9        | `CE#`       | `PG9/FMC_NCE`   | `E1`    | 10k to `VDD_NAND` |
| 16       | `ALE`       | `PD12/FMC_ALE`  | `C6`    |                   |
| 17       | `CLE`       | `PD11/FMC_CLE`  | `E2`    |                   |
| 8        | `RE#`       | `PD4/FMC_NOE`   | `E7`    |                   |
| 18       | `WE#`       | `PD5/FMC_NWE`   | `A6`    |                   |
| 7        | `R/B#`      | `PA9/FMC_NWAIT` | `A2`    | 10k to `VDD_NAND` |
| 29       | `I/O0`      | `PD14/FMC_D0`   | `B3`    |                   |
| 30       | `I/O1`      | `PD15/FMC_D1`   | `C7`    |                   |
| 31       | `I/O2`      | `PD0/FMC_D2`    | `E4`    |                   |
| 32       | `I/O3`      | `PD1/FMC_D3`    | `D5`    |                   |
| 41       | `I/O4`      | `PE7/FMC_D4`    | `A5`    |                   |
| 42       | `I/O5`      | `PE8/FMC_D5`    | `A7`    |                   |
| 43       | `I/O6`      | `PE9/FMC_D6`    | `B6`    |                   |
| 44       | `I/O7`      | `PE10/FMC_D7`   | `B8`    |                   |
| 19       | `WP#`       | `PWR_ON`        | `P14`   | via 10k           |
| 38       | `PT`        | ---             | ---     | 10k to GND        |

`VDD_NAND` is derived from +3.3V, switched on the `NAND_WP#` signal: when
`NAND_WP#` is low, `VDD_NAND` is floating, and with `NAND_WP#` is high,
`VDD_NAND` is powered from +3.3V.

Furthermore, a `1N5819WS` diode allows the system `RESET#` to pull `NAND_WP#`
low when asserted, to assert write protect when system is under reset. When
system is not under reset (i.e., `RESET#` is high), the diode prevents opposite
current flow. A 10k resistor is connected between `PWR_ON` and `NAND_WP#` to
prevent shorting `PWR_ON` to ground when reset is asserted (low).

### Voltages and power switching

The power supply and related voltages read as follows:

| Node       | Operation [V] | Reset [V]      |
| ---------- | ------------- | -------------- |
| +3.3V      | 3.300         | 3.306          |
| `RESET#`   | 3.295         | 0.000          |
| `VDD_NAND` | 0.000         | 0.001          |
| `PWR_ON`   | 3.301         | 3.303          |
| `NAND_WP#` | 3.202         | 0.169          |

The problem immediately jumps out at us: the power switch does not work.
Regardless of the state of `NAND_WP#`, the `VDD_NAND` node stays around zero.

The power switch is an `NCP380`, more precisely the `C145185` from the JLCPCB
parts library in the UDFN6 package (`NCP380HMUAJAATBG`). The active enable level
is "High", which is correct, but the over current limit is "Adj." To fix this,
we have to solder a resistor (anything from 10k to 33k would do) between pin 2
of the switch and ground.

With this fix, `VDD_NAND` reads 3.300V in normal operation, and in reset, 0.5V
slowly decaying towards zero.

### NAND parameters

The NAND datasheet is 93 pages long and includes a lot of numbers, but not so
many as the DDR chip. The STM32MP135 bare-metal BSP package
([STM32CubeMP13](https://wiki.st.com/stm32mpu/wiki/STM32CubeMP13_Package))
includes the FMC NAND driver, and a code example, and this will be our starting
point. The following parameters can be easily read off the NAND datasheet:

Let's leave the following parameters as in the ST example for now:

```c
/* hnand Init */
hnand.Instance  = FMC_NAND_DEVICE;
hnand.Init.NandBank        = FMC_NAND_BANK3; /* Bank 3 is the only available with STM32MP135 */
hnand.Init.Waitfeature     = FMC_NAND_WAIT_FEATURE_ENABLE; /* Waiting enabled when communicating with the NAND */
hnand.Init.MemoryDataWidth = FMC_NAND_MEM_BUS_WIDTH_8; /* An 8-bit NAND is used */
hnand.Init.EccComputation  = FMC_NAND_ECC_DISABLE; /* The HAL enable ECC computation when needed, keep it disabled at initialization */
hnand.Init.EccAlgorithm    = FMC_NAND_ECC_ALGO_BCH; /* Hamming or BCH algorithm */
hnand.Init.BCHMode         = FMC_NAND_BCH_8BIT; /* BCH4 or BCH8 if BCH algorithm is used */
hnand.Init.EccSectorSize   = FMC_NAND_ECC_SECTOR_SIZE_512BYTE; /* BCH works only with 512-byte sectors */
hnand.Init.TCLRSetupTime   = 2;
hnand.Init.TARSetupTime    = 2;

/* ComSpaceTiming */
FMC_NAND_PCC_TimingTypeDef ComSpaceTiming = {0};
ComSpaceTiming.SetupTime = 0x1;
ComSpaceTiming.WaitSetupTime = 0x7;
ComSpaceTiming.HoldSetupTime = 0x2;
ComSpaceTiming.HiZSetupTime = 0x1;

/* AttSpaceTiming */
FMC_NAND_PCC_TimingTypeDef AttSpaceTiming = {0};
AttSpaceTiming.SetupTime = 0x1A;
AttSpaceTiming.WaitSetupTime = 0x7;
AttSpaceTiming.HoldSetupTime = 0x6A;
AttSpaceTiming.HiZSetupTime = 0x1;
```

The following numbers we can easily read off the datasheet:

```c
hnand.Config.PageSize = 4096;     // bytes
hnand.Config.SpareAreaSize = 256; // bytes
hnand.Config.BlockSize = 64;      // pages
hnand.Config.BlockNbr = 4096;     // blocks
hnand.Config.PlaneSize = 1024;    // blocks
hnand.Config.PlaneNbr = 2;        // planes
```

### Initialization

We enable the FMC clock and the relevant GPIOs and then configure pin muxing
(same as the ST example code):

```c
/* Common GPIO configuration */
GPIO_InitTypeDef GPIO_Init_Structure;
GPIO_Init_Structure.Mode      = GPIO_MODE_AF_PP;
GPIO_Init_Structure.Pull      = GPIO_PULLUP;
GPIO_Init_Structure.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;

/* STM32MP135 pins: */
GPIO_Init_Structure.Alternate = GPIO_AF10_FMC;
SetupGPIO(GPIOA, &GPIO_Init_Structure, GPIO_PIN_9); /* FMC_NWAIT: PA9 */
GPIO_Init_Structure.Alternate = GPIO_AF12_FMC;
SetupGPIO(GPIOG, &GPIO_Init_Structure, GPIO_PIN_9); /* FMC_NCE: PG9 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_4); /* FMC_NOE: PD4 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_5); /* FMC_NWE: PD5 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_12); /* FMC_ALE: PD12 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_11); /* FMC_CLE: PD11 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_14); /* FMC_D0: PD14 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_15); /* FMC_D1: PD15 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_0); /* FMC_D2: PD0 */
SetupGPIO(GPIOD, &GPIO_Init_Structure, GPIO_PIN_1); /* FMC_D3: PD1 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_7); /* FMC_D4: PE7 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_8); /* FMC_D5: PE8 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_9); /* FMC_D6: PE9 */
SetupGPIO(GPIOE, &GPIO_Init_Structure, GPIO_PIN_10); /* FMC_D7: PE10 */
```

I verified that the alternate functions for all the NAND-related pins are
exactly as given in the STM32MP135 datasheet.

The firmware can now call `HAL_NAND_Init()`. It succeeds, but then
`HAL_NAND_Reset()` fails. It writes `NAND_CMD_STATUS` (0x70), but reads back
0xff rather than `NAND_READY` (0x40).

On the scope, we can see that the `CE#` signal goes low for about 50ns.

Comparing the connection table shown above to the NAND datasheet, we notice that
unfortunately `ALE` and `CLE` have been swapped. The correct pin assignment
would be `CLE` on pin 16 and `ALE` on pin 17, opposite to the PCB wiring.

### Swapping ALE / CLE

I thought I could swap the wires by soldering to raw PCB traces, but I gave up
on that plan and made a Rev B PCB. Then, the `fmc_init()` function just works,
and I learned that my chip reports the following information (defines so that
the bootloader can verify the chip at boot):

```c
#define FMC_MAKER             0xC2U
#define FMC_DEV               0xDCU
#define FMC_3RD               0x90U
#define FMC_4TH               0xA2U
```

With that, we can ask AI to cook up some code to read and write to the NAND
Flash and use it as the storage backend for the USB MSC code instead of the SD
card. We're now running out of SRAM space, so we can use conditional compilation
flags to disable SD card when NAND is used and vice versa.

### NAND initialization

First the FMC needs to be initialized, which we'll do in `fmc_ini()`. This
function uses the ST HAL to do the following tasks:

- enable FMC clock and reset the FMC unit
- enable the clock for MDMA and the relevant GPIOs
- setup the pin muxing for all FMC pins
- set FMC interrupt priority and enable the IRQ
- populate the parameters for the FMC structure based on the NAND chip datasheet
- call `HAL_NAND_Reset()`, and then `HAL_NAND_Read_ID()` to verify communication
  with the NAND chip

Now the NAND chip is presumed ready to use.

### Bad blocks

Unlike SD cards, NAND chips do not attempt any automatic error correction. Up to
about 2% of the blocks are bad, which seems a shockingly high percentage for
anyone not used to manual error correction.

Thus, we first need to scan the NAND chip for bad blocks (*before* erasing it!)
as recommended in the `MX30LF4G28AD-TI` datasheet:

> The bad blocks are included in the device while it gets shipped. During the
> time of using the device, the additional bad blocks might be increasing;
> therefore, it is recommended to check the bad block marks and avoid using the
> bad blocks. Furthermore, please read out the bad block information before any
> erase operation since it may be cleared by any erase operation.
>
> While the device is shipped, the value of all data bytes of the good blocks
> are FFh. The 1st byte of the 1st and 2nd page in the spare area for bad block
> will be 00h. The erase operation at the bad blocks is not recommended.

The `fmc_scan()` function just iterates over all blocks, using the following
function to check if the block is good or bad:

```c
static int is_bad_oob(uint32_t blk)
{
   uint8_t oob[FMC_OOB_SIZE_BYTES];
   NAND_AddressTypeDef a = page_addr(blk, 0);
   if (HAL_NAND_Read_SpareArea_8b(&hnand, &a, oob, 1) != HAL_OK)
      return 1;
   if (oob[0] != 0xFFU)
      return 1;
   a = page_addr(blk, 1);
   if (HAL_NAND_Read_SpareArea_8b(&hnand, &a, oob, 1) != HAL_OK)
      return 1;
   return oob[0] != 0xFFU;
}
```

The NAND datasheet further recommends keeping a table of the bad blocks in the
application:

> Although the initial bad blocks are marked by the flash vendor, they could be
> inadvertently erased and destroyed by a user that does not pay attention to
> them. To prevent this from occurring, it is necessary to always know where any
> bad blocks are located. Continually checking for bad block markers during
> normal use would be very time consuming, so it is highly recommended to
> initially locate all bad blocks and build a bad block table and reference it
> during normal NAND flash use. This will prevent having the initial bad block
> markers erased by an unexpected program or erase operation. Failure to keep
> track of bad blocks can be fatal for the application. For example, if boot
> code is programmed into a bad block, a boot up failure may occur.

In the bootloader code, we keep the bad blocks tables as a simple file-global
static array:

```c
static uint8_t bad[FMC_PLANE_NBR * FMC_PLANE_SIZE_BLOCKS];
```

With that implemented, the code prints on boot the number of bad blocks found,
and we can manually rescan:

```
FMC: 3 bad block(s) found
> fmc_scan
bad: blk 1699
bad: blk 1735
bad: blk 1761
scan done: 3 bad / 2048 total
```

### Basic tests

Now that we know where all the bad blocks are, we can erase the device, either
just a specified number of blocks, or the whole:

```
> fmc_erase 10
FMC: erasing 10 blocks
done: 0 pre-marked bad, 0 newly bad, 0 s, avg 96.1 MB/s

> fmc_erase 100
FMC: erasing 100 blocks
done: 0 pre-marked bad, 0 newly bad, 0 s, avg 105.0 MB/s

> fmc_erase
FMC: erasing 2048 blocks
skip 1699 (pre-marked bad) 0 new-bad)  104.9 MB/s
skip 1735 (pre-marked bad)
skip 1761 (pre-marked bad)
done: 3 pre-marked bad, 0 newly bad, 4 s, avg 104.5 MB/s
```

We can directly test the write and the read:

```
> fmc_test_write
FMC write: 2048 blocks
blk 2043/2048  4.9 MB/s  (0 errs)
done: 0 errs, 102 s, avg 4.9 MB/s

> fmc_test_read
FMC read: 2048 blocks
blk 2040/2048  3.7 MB/s  (1002651436 bit errs)
done: 0 rd errs, 1002651436 bit errs (post-ECC), 137 s, avg 3.7 MB/s
```

Next, we test the USB interface. To simplify matters, the USB interface will
present itself as a Mass Storage Class (flash drive) to the host, but will write
all data directly to a 256MB block set aside in the DDR memory, and also read it
from there. Later, when the data is transferred from the host to the target, we
can commit it to flash with a separate command, and also read it from there.

To test the write, we will create a big file full of random data:

```
dd if=/dev/urandom of=file_256M.dat bs=1M count=256
```

The write from USB to DDR worked at 17.6 MB/s, which is respectable. A prior USB
test showed a ~7 MB/s limit; I presume we now have a more efficient
implementation. Immediate USB read for verification showed 19.3 MB/s and all
data was received correctly. With the data transferred onto the DDR RAM of the
target, we can now commit it to the flash memory:

```
> fmc_flush
FMC flush: 1024 blocks
blk 1007/1024  2.2 MB/s  (1007 written, 0 skipped)
done: 1024 written, 0 skipped, 0 new-bad, 111 s, avg 2.2 MB/s
```

If we trigger another flush immediately afterwards, it works much faster since
instead of erasing and re-writing, we just read and skip if the block is the
same as what's there already:

```
> fmc_flush
FMC flush: 1024 blocks
blk 1014/1024  4.8 MB/s  (0 written, 1014 skipped)
done: 0 written, 1024 skipped, 0 new-bad, 52 s, avg 4.8 MB/s
```

The data is now written on the flash. We can reset the device, disconnect it
from power, and when it starts up again, perhaps a year later, it should still
retain the data. In this case, I did a reset and then used the load operation to
return the data from NAND flash to the DDR memory:

```
> fmc_load
FMC load: 1024 blocks
blk 1008/1024  5.1 MB/s  (0 rd errs)
done: 0 rd errs, 49 s, avg 5.1 MB/s
```

Now we can read the data from the USB interface. Again it reads at about 19.5
MB/s and all data has been received correctly. Great, we now have a working
flash drive!

### Boot from NAND flash

Instead of flashing 256M of random bits, we can now load an image that contains
the bootloader, kernel, etc. Again we copy it over the USB MSC interface to DDR
RAM, and then call `fmc_flush` to commit it to the NAND flash memory. Then, we
can run a function to check that the first two blocks contain the bootloader
with a valid STM32 header:

```
> fmc_test_boot
boot check: block 0
  version 2.0  image_len 129284  entry 0x2ffe0000  load 0x2ffe0000
  ext header: OK
  checksum OK (0x00c9f3b8)
boot check: block 1
  version 2.0  image_len 129284  entry 0x2ffe0000  load 0x2ffe0000
  ext header: OK
  checksum OK (0x00c9f3b8)
partition table: block 2
  checksum OK  total_blocks 138  5 partition(s)
  [0] bootloader        block 0  len 2
  [1] dtb               block 3  len 1
  [2] kernel            block 4  len 34
  [3] rootfs            block 38  len 100
  [4] ptable            block 2  len 1
DTB: block 3
  FDT magic OK  totalsize 53981 bytes
```

With that checked, we can set the boot pins to 011 to force boot from NAND, hit
reboot, and watch in marvel as the system boots up just fine from NAND. No more
need for the expensive SD cards and their sockets!

### Enabling NAND in Buildroot and kernel

To make it work with Linux, we enable the Linux support for the UBI file system
by enabling the following flags (in my case they were enabled already, so no
change):

```
CONFIG_MTD_UBI
CONFIG_MTD_NAND_STM32_FMC2
CONFIG_UBIFS_FS
```

Next, we need to tell Buildroot about our flash drive. Define the following
additional keys (either in the defconfig directly, or open menuconfig and find
them there---I did the latter):

```
BR2_TARGET_ROOTFS_UBI=y
BR2_TARGET_ROOTFS_UBI_PEBSIZE=0x40000
BR2_TARGET_ROOTFS_UBI_SUBSIZE=4096
BR2_TARGET_ROOTFS_UBIFS_LEBSIZE=0x3e000
BR2_TARGET_ROOTFS_UBIFS_MINIOSIZE=0x1000
BR2_TARGET_ROOTFS_UBIFS_MAXLEBCNT=1800
```

To determine `MAXLEBCNT`, we figure as follows:

  - Total flash: MX30LF4G28AD = 4 Gbit = 512 MB = 2048 blocks
  - Rootfs starts at block 68
  - Rootfs blocks: 2048 − 68 = 1980 blocks
  - UBI overhead: ~2 blocks for internal volumes
  - Usable LEBs: ~1978

To be safe, let's round down to 1800.

When we rebuild Buildroot, we notice new images appear under
`buildroot/output/images`: `rootfs.ubi` and `rootfs.ubifs`.  Use
rootfs.ubi---it's the complete UBI image ready to write to flash. `rootfs.ubifs`
is just the inner filesystem; it still needs to be wrapped in a UBI volume,
which is what `rootfs.ubi` already is.

### Configure the DTS

The same kernel will work both with the SD card and the NAND flash; that's the
point of the DTS. But this means we need to enable NAND support in the DTS, as
follows:

1. Add an FMC NAND pinctrl group inside the `pinctrl@50002000` node (matching
the exact pins the bootloader configures):

```c
fmc_nand_pins: fmc-nand-0 {
	pins1 {
		pinmux = <STM32_PINMUX('D', 14, AF12)>,  /* FMC_D0  */
			 <STM32_PINMUX('D', 15, AF12)>,  /* FMC_D1  */
			 <STM32_PINMUX('D',  0, AF12)>,  /* FMC_D2  */
			 <STM32_PINMUX('D',  1, AF12)>,  /* FMC_D3  */
			 <STM32_PINMUX('E',  7, AF12)>,  /* FMC_D4  */
			 <STM32_PINMUX('E',  8, AF12)>,  /* FMC_D5  */
			 <STM32_PINMUX('E',  9, AF12)>,  /* FMC_D6  */
			 <STM32_PINMUX('E', 10, AF12)>,  /* FMC_D7  */
			 <STM32_PINMUX('D',  4, AF12)>,  /* FMC_NOE */
			 <STM32_PINMUX('D',  5, AF12)>,  /* FMC_NWE */
			 <STM32_PINMUX('D', 11, AF12)>,  /* FMC_CLE */
			 <STM32_PINMUX('D', 12, AF12)>,  /* FMC_ALE */
			 <STM32_PINMUX('G',  9, AF12)>;  /* FMC_NCE */
	 	bias-disable;
	 	drive-push-pull;
	 	slew-rate = <3>;
	};
	pins2 {
		pinmux = <STM32_PINMUX('A', 9, AF10)>;   /* FMC_NWAIT */
		bias-disable;                              /* external 10k pull-up */
	};
};
```

2. Enable the FMC and NAND nodes and add the `nand@0` device with partitions:

```c
fmc: memory-controller@58002000 {
	compatible = "st,stm32mp1-fmc2-ebi";
	reg = <0x58002000 0x1000>;
	ranges = <0 0 0x60000000 0x04000000>, /* EBI CS 1 */
		 <1 0 0x64000000 0x04000000>, /* EBI CS 2 */
		 <2 0 0x68000000 0x04000000>, /* EBI CS 3 */
		 <3 0 0x6c000000 0x04000000>, /* EBI CS 4 */
		 <4 0 0x80000000 0x10000000>; /* NAND */
	#address-cells = <2>;
	#size-cells = <1>;
	clocks = <&rcc FMC_K>;
	resets = <&rcc FMC_R>;
	feature-domains = <&etzpc STM32MP1_ETZPC_FMC_ID>;
	pinctrl-names = "default";
	pinctrl-0 = <&fmc_nand_pins>;
	status = "okay";

	nand-controller@4,0 {
		compatible = "st,stm32mp1-fmc2-nfc";
		reg = <4 0x00000000 0x1000>,
		      <4 0x08010000 0x1000>,
		      <4 0x08020000 0x1000>,
		      <4 0x01000000 0x1000>,
		      <4 0x09010000 0x1000>,
		      <4 0x09020000 0x1000>;
		#address-cells = <1>;
		#size-cells = <0>;
		interrupts = <GIC_SPI 49 IRQ_TYPE_LEVEL_HIGH>;
		dmas = <&mdma 24 0x2 0x12000a02 0x0 0x0>,
		       <&mdma 24 0x2 0x12000a08 0x0 0x0>,
		       <&mdma 25 0x2 0x12000a0a 0x0 0x0>;
		dma-names = "tx", "rx", "ecc";
		status = "okay";

		nand@0 {
			reg = <0>;
			nand-on-flash-bbt;
			nand-ecc-algo = "bch";
			nand-ecc-strength = <8>;
			nand-ecc-step-size = <512>;
			#address-cells = <1>;
			#size-cells = <1>;

			partitions {
				compatible = "fixed-partitions";
				#address-cells = <1>;
				#size-cells = <1>;

				partition@0 {
				    label = "bootloader";
				    reg = <0x00000000 0x00080000>; /* blocks 0-1 */
				    read-only;
				};
				partition@80000 {
				    label = "ptable";
				    reg = <0x00080000 0x00040000>; /* block 2 */
				    read-only;
				};
				partition@c0000 {
				    label = "dtb";
				    reg = <0x000c0000 0x00040000>; /* block 3 */
				};
				partition@100000 {
				    label = "kernel";
				    reg = <0x00100000 0x01000000>; /* blocks 4-67, 16 MB */
				};
				partition@1100000 {
				    label = "rootfs";
				    reg = <0x01100000 0x1ef00000>; /* block 68 to end, ~495 MB */
				};
			};
		};
	};
};
```

3. Change bootargs in the chosen node:

```c
bootargs = "ubi.mtd=rootfs root=ubi0:rootfs rootfstype=ubifs clk_ignore_unused";
```

The ubi.mtd=rootfs matches the partition label, so the kernel finds it by name
regardless of MTD index.

### Make the final NAND image

Package everything into a single NAND image ready for flashing:

```
python3 bootloader/scripts/nandimage.py \
   buildroot/output/images/nand.img \
   --boot bootloader/build/main.stm32 \
   --dtb linux/arch/arm/boot/dts/$(DTS).dtb \
   --kernel linux/arch/arm/boot/zImage \
   --rootfs
   buildroot/output/images/rootfs.ubi
```

Write this image to the bootloader RAM via the USB "flash drive" interface,
flush it to the NAND, and just to be sure, restart the devies and verify that
it was written right:

```
> fmc_flush
FMC flush: 115 blocks
blk 99/115  3.0 MB/s  (61 written, 38 skipped)
done: 77 written, 38 skipped, 0 new-bad, 9 s, avg 2.9 MB/s

> r
System reset requested...
bad: blk 1699
bad: blk 1735
bad: blk 1761
scan done: 3 bad / 2048 total

> Press any key to stop autoload ..

> fmc_test_boot
boot check: block 0
  version 2.0  image_len 129284  entry 0x2ffe0000  load 0x2ffe0000
  ext header: OK
  checksum OK (0x00cbcb26)
boot check: block 1
  version 2.0  image_len 129284  entry 0x2ffe0000  load 0x2ffe0000
  ext header: OK
  checksum OK (0x00cbcb26)
partition table: block 2
  checksum OK  total_blocks 115  5 partition(s)
  [0] bootloader        block 0  len 2
  [1] dtb               block 3  len 1
  [2] kernel            block 4  len 34
  [3] rootfs            block 68  len 47
  [4] ptable            block 2  len 1
DTB: block 3
  FDT magic OK  totalsize 54934 bytes
```

Now we're ready to boot the system: load kernel and DTB into memory, and start it up!

```
> fmc_bload
bload: DTB  blk 3+1 -> 0xc4000000
bload: kernel blk 4+34 -> 0xc2000000
bload: done

> j
Jumping to address 0xC2000000...
[    0.000000] Booting Linux on physical CPU 0x0
...
[    2.581401] ubi0: attaching mtd4
[    3.352526] ubi0: scanning is finished
[    3.376597] ubi0: volume 0 ("rootfs") re-sized from 45 to 1936 LEBs
[    3.382515] ubi0: attached mtd4 (name "rootfs", size 495 MiB)
[    3.387286] ubi0: PEB size: 262144 bytes (256 KiB), LEB size: 253952 bytes
[    3.394064] ubi0: min./max. I/O unit sizes: 4096/4096, sub-page size 4096
[    3.400865] ubi0: VID header offset: 4096 (aligned 4096), data offset: 8192
[    3.407754] ubi0: good PEBs: 1973, bad PEBs: 7, corrupted PEBs: 0
[    3.413821] ubi0: user volume: 1, internal volumes: 1, max. volumes count: 128
[    3.421132] ubi0: max/mean erase counter: 1/0, WL threshold: 4096, image sequence number: 776612721
[    3.430341] ubi0: available PEBs: 0, total reserved PEBs: 1973, PEBs reserved for bad PEB handling: 33
[    3.439406] ubi0: background thread "ubi_bgt0d" started, PID 69
[    3.446064] clk: Not disabling unused clocks
[    3.453791] UBIFS (ubi0:0): Mounting in unauthenticated mode
[    3.585956] UBIFS (ubi0:0): UBIFS: mounted UBI device 0, volume 0, name "rootfs", R/O mode
[    3.593117] UBIFS (ubi0:0): LEB size: 253952 bytes (248 KiB), min./max. I/O unit sizes: 4096 bytes/4096 bytes
[    3.602971] UBIFS (ubi0:0): FS size: 454574080 bytes (433 MiB, 1790 LEBs), max 1800 LEBs, journal size 9404416 bytes (8 MiB, 38 LEBs)
[    3.614882] UBIFS (ubi0:0): reserved for root: 0 bytes (0 KiB)
[    3.620754] UBIFS (ubi0:0): media format: w4/r0 (latest is w5/r0), UUID D9C4AE58-EAE8-4A96-B306-979CE84378B9, small LPT model
[    3.643062] VFS: Mounted root (ubifs filesystem) readonly on device 0:17.
[    3.657604] devtmpfs: mounted
[    3.662754] Freeing unused kernel image (initmem) memory: 1024K
[    3.668681] Run /sbin/init as init process
[    3.959212] UBIFS (ubi0:0): background thread "ubifs_bgt0_0" started, PID 72

Welcome to Buildroot
buildroot login:
```

Success!

!include[articles/linux-on-stm32mp135.html]

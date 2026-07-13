---
title: Agentic Schematics and PCB Review Checklist
author: Jakob Kastelic
date: 13 Jul 2026
topic: Agents
description: >
   A comprehensive checklist for automated schematic and PCB review, covering
   connectivity, power, components, signal integrity, layout, and
   manufacturability.
---

![](../images/mp.jpg)

Automated schematic and PCB review can catch subtle design errors long before
they become expensive prototype failures. These checks examine connectivity,
power distribution, component ratings, datasheet compliance, signal integrity,
controlled impedance, layout, manufacturability, and documentation. They are
intended to complement ERC, DRC, simulation, and experienced engineering review
by systematically identifying inconsistencies, missing protections, incorrect
footprints, routing problems, and other issues that conventional design tools
may overlook.

### 1. Schematic: connectivity and correctness

101. Check for net-name and label typos and near-duplicate net names; a typo
     like DCKLP vs DCLKP silently splits a net and leaves the signal
     unconnected.

102. Verify no communication bus or connector pinout is swapped end to end:
     confirm MISO/MOSI, TX/RX, and connector pin order match at both ends.

103. Verify every hierarchical and sheet pin direction (input vs output), and
     confirm labels match across sheets; a wrong direction or mismatched label
     mis-connects the signal.

104. Check for redundant or duplicate drivers on any net, and flag must-float
     pins (mode or status pins in SPI mode) that are tied instead of left
     unconnected.

105. Confirm each differential or paired signal reaches the matching pins at
     both ends, but first check the schematic for a design-intent note (a
     deliberate clock inversion is harmless).

106. Verify every boot, reset, and config strap is pulled to the correct rail
     and value for the intended mode.

107. Check for populated components that have no functional connection (stray or
     leftover parts) and flag them for removal or connection.

### 2. Schematic: power and supplies

201. Verify each device is powered at the correct supply and voltage level:
     confirm op-amp V+/V- is not reversed, that divider-set input levels (an
     oscillator input, a DAC reference range) match what the part needs, and
     that reference and analog-supply pins (VREF, VDDA, DDR VREF) connect to
     their intended net.

202. Obtain each IC's datasheet and verify it has the required decoupling and
     bypass at the specified values and locations (a PHY VDDCR bulk capacitor, a
     converter reference bypass, a synthesizer's per-rail caps); do not assume a
     generic 0.1uF per pin.

203. Verify critical resistors have the correct value and tolerance; confirm a
     DDR ZQ calibration resistor is a 1% part.

204. Check that every external or exposed connector line has ESD protection, and
     verify USB high-speed lines carry the correct series elements (flag any
     series resistors on D+/D-).

205. Verify each signal is assigned to the correct FPGA or IO-bank voltage
     domain.

206. Check that exposed inputs and the power input have the protection they
     need: reverse-polarity protection on the supply, and clamp or series
     protection on connector-facing inputs against overvoltage.

207. Check that a reset or brownout supervisor holds the processor and logic in
     reset until the supplies are valid, with a threshold and reset polarity
     that match the parts.

208. Check that inductors and ferrite beads are rated for their DC current: buck
     inductors above peak current without saturating, and beads with acceptable
     DC resistance and current rating for the rail they feed.

### 3. Schematic: pins and pulls

301. Check that no active input pin is left floating; unused inputs should be
     tied to a defined level.

302. Check that every required pull-up and pull-down is present (I2C,
     open-drain, reset, and enable lines) and ties to the correct rail.

### 4. Schematic: regulators, clocks, and domain interfaces

401. Verify each regulator's feedback network sets the intended output voltage
     and is stable; check the divider value and any compensation capacitor.

402. Check that noise-sensitive rails use a linear regulator rather than a
     switcher.

403. Check that every signal crossing a voltage domain is level-shifted or
     translated into the receiving domain.

404. Check that clocks and fast digital or communication lines carry the correct
     series damping or termination, and none where the interface forbids it.

405. Verify each part is the correct variant (for example a load switch without
     an unwanted internal pull-down).

406. Verify rails that must sequence or gate on another rail are enabled in the
     right order.

407. Check the PLL and clock reference chain: verify reference frequencies,
     divider and multiplier settings, and the lock source are consistent (for
     example a 24 MHz reference locked from a 12 MHz source or taken from the
     clock generator).

408. Check that each crystal's load capacitors match the crystal's specified
     load capacitance.

### 5. Components: ratings, footprints, symbols

501. Read each capacitor's voltage rating from the MPN rather than the BOM
     Voltage field, and flag any blank rating, tempco, or MPN field that leaves
     a part uncheckable.

502. Flag any capacitor whose voltage rating is at or below the rail it sits on.

503. Verify the dielectric: check that references, PLL loop filters, and crystal
     loads use C0G/NP0, and that bulk caps and caps near hot parts use X7R
     rather than X5R.

504. Check for class-II DC-bias derating, but flag it only where the derated
     capacitor is the sole bypass; accept it where the rail already carries bulk
     or a C0G capacitor.

505. Verify each footprint matches the MPN's real package size, and confirm the
     MPN-encoded value and voltage match the BOM fields; a size mismatch
     tombstones or fails to assemble.

506. Obtain the datasheet pinout drawing for each part and verify the symbol's
     pin functions against it (not extracted text, which drops overbars), so
     inverted or complementary pins are not misread.

507. Verify every footprint pad has a matching symbol pin, including
     No-Connects, so a missing power or signal pad is not buried in "no net for
     pad N" warnings; check that connector shield tabs and unused transformer or
     balun terminals are tied explicitly.

### 6. Nets and impedance

601. Check that every high-speed net is assigned a controlled-impedance class at
     the right target and not left in Default: USB at 90 ohm differential;
     Ethernet, LVDS, and clock pairs at 100 ohm differential; DDR single-ended
     and CK/DQS as appropriate for the memory and controller.

602. Verify each net-class directive lands on a wire of the target net, and that
     the class is defined with a width and gap in the project file; a class
     referenced but never defined falls through to Default.

603. Check that after any AC-coupling capacitor or series 0 ohm resistor, the
     auto-named IC-side stub carries its own controlled-impedance directive;
     otherwise it stays in Default.

604. Verify class membership from the board, not the exported netlist: the KiCad
     netlist export drops directives on sheet-local labels while keeping them on
     hierarchical and global labels.

605. Flag any auto-named net that is actually a supply or reference island and
     should get a real name, especially when the auto-name taken from a signal
     pin disguises a rail.

606. Do not flag low-frequency analog pairs for controlled impedance or skew;
     their large length or skew deltas are usually filter-branch or stub
     artifacts, not defects.

### 7. PCB: signal integrity

701. Verify every controlled-impedance trace holds its class target width along
     its whole length; flag any deviation or mid-trace width step.

702. Compute intra-pair skew from package-compensated length data (die-to-ball
     length plus the tool's true routed length, which includes via depth);
     exclude termination and pull stubs, and weigh skew against the signal's own
     period.

703. Verify both legs of a pair run on the same layer.

704. At every fast-net layer transition, check for a GND stitching via next to
     the signal via, and confirm it actually connects copper on both reference
     planes (DRC does not verify this).

705. Verify DDR length matching from the package-compensated spreadsheet, and
     for any control net with a pull or termination resistor measure the
     controller-to-DRAM path, not total net copper.

### 8. PCB: power, thermal, copper

801. Check that core and high-current rails are delivered as planes, not narrow
     tracks.

802. Check for thermal vias under regulator tab and EP pads.

803. Measure decoupling distance pin-to-pad, not part-origin to part-origin.

804. Enable the isolated copper check (often left on "ignore") and flag floating
     copper islands.

805. Check PCB geometry for routing collisions: interfering or overlapping
     tracks, tracks running under parts that should be clear, and any geometry
     error beyond the controlled-impedance and copper-island checks.

806. Check that power traces and vias are sized for their current at the board
     copper weight, not just for impedance.

807. Check the mixed-signal grounding: verify analog and digital return currents
     are managed so digital return current does not flow through the analog
     reference area.

### 9. Verification and documentation

901. Run ERC and DRC and check that all warnings are resolved (floating pins,
     conflicting outputs, unconnected nets, clearance and geometry), and review
     every suppressed warning or DRC exclusion to confirm it is intentional.

902. Check that critical rails and R&D-only nets are annotated with their
     abs-max or expected voltage and intended use.

903. Check reference-designator and value hygiene: no duplicate or wrong
     reference designators, and component values in a consistent canonical
     format (for example 10nF rather than 0.01uF or 10000pF, and R/K/M resistor
     suffixes).

904. Check for cosmetic typos in text notes, comments, symbol names, and
     silkscreen strings that do not affect the netlist but look unprofessional
     when others read the schematic or board.

905. Check that the bare PCB is itself a line item on the BOM with its own part
     number.

906. Check that each schematic sheet's title block is complete: company logo,
     PCB part number, title, company name and address, date, designer initials,
     and revision.

### 10. Manufacturability

1001. If panelized, check that breakaway rails are present for assembly support;
      if V-cuts are used, check that components are at least 1/8" from the
      V-cuts, 1/4" for MLCCs oriented perpendicular to the cuts.

1002. Check that the board has fiducial markers and that they are at least 5mm
      from the edge of the board.

1003. Check that the ground and power planes under the reference crystals are
      cut away and no traces pass under it, so it can produce a reliable clock.

1004. Check that surface-mount parts are about 1mm from large through-hole
      connectors so they can be hand-soldered without damaging the connectors,
      and that parts perpendicular to the connectors are rotated 90 degrees for
      easier hand-soldering.

1005. Check that solder-mask expansion is set to an appropriate value (likely
      non-zero).

1006. Check that the Ethernet PHY is oriented to minimize TX and RX trace
      lengths, that its termination resistors are close to their traces to
      minimize stub length (see the PHY eval-board layout), and that TX and RX
      are on separate layers if they cross.

1007. Check for testpoints on key signals (e.g., raw DAC outputs, SPI) so
      technicians can probe them without shorting to a supply.

1008. Check that ground testpoints are distributed around the board so a scope
      probe ground is always within reach.

1009. Check that both pads of every 2-pin component have equal-width traces to
      prevent tombstoning.

1010. Check enclosure and mechanical-drawing compliance: connector positions and
      spacing match the current mechanical-drawing revision, and the board with
      its tall and edge components fits the enclosure.

1011. Check that the silkscreen carries the board part number, revision,
      engineer initials, and date.

1012. Check that silkscreen is clear of pads, and that polarized parts and IC
      pin 1 are marked.

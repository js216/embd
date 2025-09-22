# New Rules for High-Speed Digital Design

- All nodes need to be connected to what they need to be connected to
- Differential pairs should go on the same level and together
- Each trace can have up to three vias
- During the initial connection stage of the layout, choose one color for horizontal traces anbd all other traces should be vertical (or vice versa)
- Place decoupling capacitors right next to the power pins, or don't place them at all (so for BGA packages, they go on the bottom of the board)
- Make all traces as short as practical but no shorter
- Do *not* spend any time length matching, or impedance matching any of the traces
- Any trace can go on any layer, but keep the power and ground layers free of signals
- Prototype small circuit fragments as soon as possible

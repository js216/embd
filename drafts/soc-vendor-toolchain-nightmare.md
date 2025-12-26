https://www.reddit.com/r/embedded/comments/1pqg3ty/embedded_systems_are_really_hard_to_learn/?utm_source=chatgpt.com
Embedded systems are really hard to learn
12/20/2025

triffid_hunter
•
6d ago

> I find that the hardest part about embedded is the horrendously obtuse manufacturer-provided toolchains.
> 
> If I can find a way to ditch them and switch to gcc+Makefile+basic C libraries, that's the first thing I'll do.

--------------------------------------------------------------------------------

https://marx.engineer/content/talks/2025_Yocto-Summit_Your-Vendors-BSP-Is-Probably-Not-Built-For-Product-Longevity.pdf
2025_Yocto-Summit_Your-Vendors-BSP-Is-Probably-Not-Built-For-Product-Longevity

Your Vendor’s BSP Is Probably Not Built for Product Longevity
Now What?
Anna-Lena Marx, inovex GmbH
Yocto Project Summit, 2025.12

Our Goals are not Aligned

Board/Silicon Vendor Focus and Goals:

● Showcase all product features
○ CPU
○ special co-processors
○ unique selling points
● Provide an easy starting point for customers
● Provide several BSP variants for the whole product
portfolio
○ often several BSP variants needed
e.g Linux, Android, QNX, …
○ must be easy and manageable for the vendor!
● Sell silicon
… and move to the next product

Integrator/Product Manufacturer Goals:

● Build and ship one product
○ stable, secure & maintainable
○ minimal software stack
→ reduced surface for attacks and CVEs
○ low maintenance effort needed
○ expected lifespan: 5 - 20 years
● Fulfil target market regulations
○ e.g. Cyber Resilience Act,
IEC 62304 (Medical Devices), …
○ Security Updates
○ …
● Sell this product
… and support it over its lifetime

--------------------------------------------------------------------------------




The SoC Vendor Toolchain Nightmare
How turnkey solutions bury engineers under accidental complexity

1. The promise: “It just works”
The sales pitch:

Download our SDK

Run one script

Get Linux on your board

Why this is appealing to vendors

Why this is appealing to management

Why engineers should already be suspicious

2. Turnkey systems vs engineering systems
What “turnkey” actually means in practice

The Boeing 747 cockpit of a lawn mower

When abstraction hides understanding instead of enabling it

The difference between:

Using a system

Owning a system

3. Accidental complexity, formally defined
Essential vs accidental complexity (Brooks)

What problem are we actually trying to solve?

How SoC SDKs solve a different problem:

vendor validation

support tickets

demo boards

Why the complexity is purely accidental

4. The usual suspects: a taxonomy of pain
Layered shell scripts calling Python calling CMake

Magic environment variables

Generated files that must never be edited

Auto-patched kernels with no upstream history

Device trees modified by opaque tools

“Do not touch” directories that you must touch to fix bugs

Silent coupling between unrelated components

5. Conway’s Law in silicon form
Toolchains reflect the vendor organization

Hardware team, BSP team, SDK team, marketing demos

Each group adds a layer

Nobody removes layers

Result: an archaeological dig instead of a system

6. Cargo cult engineering
Copying scripts without understanding them

“This file must be here or the build breaks”

Engineers afraid to delete anything

Fear-driven development

Why this persists even among senior engineers

7. The hidden cost: paralysis
Simple changes take weeks

Kernel upgrades feel impossible

Debugging becomes spelunking

Engineers stop experimenting

Knowledge becomes tribal and fragile

8. Why vendors do this (and why it won’t change)
Support cost minimization

One-size-fits-all BSPs

Marketing-driven timelines

Vendors are not incentivized to teach you

The tragedy of “example code”

9. The alternative: give engineers power, not buttons
Modules instead of monoliths

Explicit build steps instead of scripts

Readable Makefiles over frameworks

Upstream kernels, not forks

Board support as data, not magic

10. A sane mental model for engineers
You are assembling known components:

bootloader

kernel

device tree

root filesystem

None of this is mysterious

If you understand it once, you understand it forever

11. Why a long README beats a thousand scripts
Documentation as empowerment

Repeatability through understanding

Engineers who know how to rebuild everything

Changing one thing without breaking ten others

12. Conclusion: from consumers to engineers
Turnkey systems create users

Transparent systems create engineers

The goal is not “it boots”

The goal is control, confidence, and changeability

Optional closing line (fits your voice)
If you’re given a Boeing 747 and told to push the throttles forward, you can fly.
If you’re given parts and shown how they fit, you can build a Cessna — or anything else.

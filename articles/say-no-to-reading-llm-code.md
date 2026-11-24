---
title: Say No to Reading LLM Code
author: Jakob Kastelic
date: 24 Nov 2026
topic: Agents
description:
   An argument for letting go of the need to read and understand every line of
   LLM-generated code, and rethinking what it means to understand software in
   the age of AI agents.
---

![](../images/rb.jpg)

An idea is becoming increasingly hard to dismiss: it's okay to *not* read the
code written by LLM agents. This is a 180-degree reversal of the cautious
attitude I assumed when first getting used to working with "AI".

### Two Streams

For the last few months, I divided the software I produce into two parallel
streams:

- **Important stuff:** customers will depend on it, my reputation is on the
  line, so I have to understand it completely, all the way down to each line of
  code.

- **Fun stuff:** Throwaway scripts, internal utilities, apps designed strictly
  for my own personal use, weird "how hard can it be" experiments.

In the second group of software, I vibe-coded away with reckless abandon. Let
Claudes and GPTs throw together whatever disgusting tangle of inelegance they
want, I don't care: just make it work. And ... It worked!

### Shift in Understanding

Reading the LLM outputs was always an unpleasant experience: comments that make
no sense, redundant parallel code paths, implementations either too general or
not general enough for the task at hand. How could you trust that for anything
that actually matters!?

But then I noticed a subtle shift: the "throwaway" scripts, programs, apps ended
up in my daily use, rather than being thrown away. For sure, I would tell the
agents to make numerous improvements or even from-scratch rewrites, and the
result remained opaque, unpleasant to try and understand. It was time for me to
let go of the need to understand.

More precisely, there's a need to rethink what it means to understand a piece of
software. Up to now, this involved reading the code and simulating its execution
in your brain, in addition to higher level concepts. However, with LLM code that
is not practical: the model is not designed to produce readable output, and as
the "frontier" gets pushed further, we will produce increasingly ambitious
programs that go beyond the ability of a single human brain to understand in a
realistic amount of time. (For a three-year project, I cannot devote five years
to reading the code.)

As has been pointed out many times, there was an analogous "shift in
understanding" when handwritten assembly gave way to compiled code. Elegant,
compact, efficient algorithms hand-tuned to work perfectly with a given computer
architecture got replaced by messy, almost entirely unreadable compiler outputs,
initially replete with bugs. (In fact, compiler bugs remain significant if
infrequent sources of exploitable vulnerabilities.) After some period of
struggle ("you cannot write an OS in a high-level language!"), the objections
receded into history.

I have no reply to those that would object that "it's not the same", that the
LLM code is an entirely different beast to "autocoder" or compiler code. The
analogy may be strained, but I do not worry: it'll stretch out in time.

### Explosion of Complexity

I do worry about the inevitable explosion of complexity, as has long been the
case:

> For a brief period, personal computers have offered programmers a chance to
> build small software systems of outstanding quality using the best available
> programming languages and design methods [...] The simple operating procedures
> and small stores of personal computers make it both possible and essential to
> limit the complexity of software. [...] The recent development of the
> complicated programming language Ada combined with new microprocessors with
> large stores will soon make the development of incomprehensible, unreliable
> software inevitable even for personal computers.[^br]

LLM code is now continuing the trend, making software more incomprehensible than
anything we had been able to devise previously. That is an unfortunate departure
from the "simple" world of pre-agentic code. The best consolation we have
available is that handwritten code is still possible, even if not practical for
realistic "useful" projects---it makes for a wonderful hobby.

[^br]: P. Brinch Hansen 1982. Programming a Personal Computer. Prentice-Hall,
    Englewood Cliffs, NJ.

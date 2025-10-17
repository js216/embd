---
title: Always Mutate the Entire Global State
author: Jakob Kastelic
date: 17 Oct 2025
topic: Philosophy
description: >
   Eliminate elusive bugs by embracing perfect impurity: rebuild the entire
   global state on every command for simpler, faster, and more reliable
   programs.
---

For the past month I had been stuck hunting down subtle bugs that happen when a
particular sequence of commands is entered into a program. Sometimes even
repeating the exact sequence would not be enough to reproduce the bug, since the
program's behavior depends on all commands that have been entered before as well
as some saved state. Such chaos is to be expected when the user commands that a
program exposes each modify one or more global state variables.

The wizards of functional programming counsel us to use pure functions only,
i.e., those whose output depends only on their inputs and that don't change
anything else in the system. That style of coding would have fixed my bugs, but
is strictly speaking impossible. If no function modifies any global state, then
how can it return values? The return values get passed back via the call stack,
which is of course part of the global state and influences the execution of
functions that follow. Even ignoring that, ultimately the program needs to
output the values to the user or manipulate the hardware in some way, which is
also part of the global state.

The real solution indicated in this case is of the type "if you can't beat them,
you join them". If you cannot have perfectly pure functions, then you should
have functions that are *perfectly impure*. In other words, functions that
mutate the global state to the largest extent possible.

In the example from the first paragraphs, my program exposed a range of user
commands: some change system parameters, and others work on one of several
similar output channels of an instrument. The intuitive but buggy approach is
for each command to change only the things it needs to change. The "perfectly
impure" approach is to recompute the entire global state no matter how small the
change that the command actually needs to make.

This results in a tremendous simplification of the possible parameter space. For
every set of user-visible parameter values, there is only one possible state the
system or program can be in. Contrast that to the intuitive/buggy approach where
there is an almost infinite number of system states corresponding to a given set
of parameters!

But isn't this awfully inefficient? If an instrument has ten outputs, and each
output has 25 parameters, then to change one parameter would take 250 times
longer than it needs to! Not really. If all user commands eventually call the
same function to effect a parameter change, that *one* function can do the
optimization to not modify things that haven't changed. In other words, instead
of having to perform the optimization manually in each user-facing command, the
optimization is done at the last possible moment in a single function
automatically. For a reasonably complex program, it's nearly impossible to
manually keep track of this kind of "cache consistency", but pretty easy to do
automatically as described here.

The actual result regarding the mysterious bugs I spent a month chasing? They
were all gone, replaced by relatively shallow issues that were easy to reproduce
and quick to fix. Besides, once I implemented the "inefficient" approach of
updating the whole state on each command, the system became faster and more
responsive, since the automatic optimization did a much better job than my
bug-prone manual ones.

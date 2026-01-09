---
title: Dead Code Elimination is a False Promise
author: Jakob Kastelic
date: 14 Sep 2025
topic: Philosophy
description: >
   Dead code elimination is often promised but rarely delivered. Explore why
   compilers, linkers, and modern package ecosystems fail to remove unused code,
   and why truly maintainable software may require strictly opt-in features and
   separate programs rather than libraries.
---

![](../images/sq.jpg)

Go through the source of any nontrivial program and chances are, most of the
code in there is used very rarely, and a lot if it may never be used. This is
the more so if a program is supposed to be very portable, such as in the Linux
kernel. Of course, compilers will eliminate it, so there's no problem?

### The Problem

Compilers are supposed to detect what's not being used, and remove the code.
They don't do that. For example, processing one "compilation unit" at a time, a
C compiler has no idea which functions will be referenced to from other units
and which are entirely dead. (If the function is declared static, this *does*
work, so declare as many of them static.)

Surely by the time the linker is invoked, all the function calls are clear and
the rest can be stripped away? Also not likely. For example, the function calls
could be computed during runtime as casts of integers into function pointers. If
the linker were to remove them, this mechanism would fail. So long as several
functions are compiled into the same section, the linker will always include all
of them so long as at least one of them is used.

What if we instead explicitly mark which things we would like excluded?

### Conditional Compilation

With conditional compilation, you can include/exclude whatever you want. When a
program has these conditional compilation switches, dead code *does* get
entirely deleted before the compiler even sees it. Most often, the result is a
myriad of poorly-documented (more likely: entirely undocumented) switches that
you don't know what you're allowed to disable.

For example, the Linux kernel provides the amazing menuconfig tool to manage
these inclusions and exclusions. Still, it can take days of work trying out
disabling and re-enabling things, till you give up and wisely conclude that this
"premature optimization" is not worth your time and leave everything turned on
as it is by default.

### "Packages"

The sad reality of modern scripting languages, and even compiled ones like Rust,
is that their robust ecosystems of packages and libraries encourage wholesale
inclusion of code whose size is entirely out of proportion to the task they
perform. (Don't even mention [shared
libraries](https://harmful.cat-v.org/software/dynamic-linking/).)

As an example, let's try out the popular Rust GUI library
[egui](https://github.com/emilk/egui). According to its Readme, it is modular,
so you can use small parts of egui as needed, and comes with "minimal
dependencies". Just what we need to make a tiny app! Okay, first we need Rust
itself:

```
$ curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
$ du -hs .rustup .cargo
1.3G    .rustup
20M     .cargo
```

So far so good---the entire compiler and toolchain fits inside 1.3G, and we
start with 20M of packages. Now let's clone the GUI library and compile its
simple example with a couple really simple widgets:

```
$ git clone git@github.com:emilk/egui.git
$ cd egui/examples/hello_world_simple
$ cargo run -p hello_world_simple
$ cd && du -hs .rustup .cargo
2.6G    .rustup
210M    .cargo
```

Oops! How many gigabytes of code does it take to show a couple characters and
rectangles on the screen? Besides, the above took more than 20 min to complete
on a machine vastly superior to the Cray-2 supercomputer. The compiled program
was 236M in size, or 16M after stripping. Everyday We Stray Further ...

This is far from being a "freak" example; even the simplest tasks in Rust and
Python and pretty much anything else considered "modern" will pull in gigabytes
of "essential" packages.

Packages get inextricably linked with the main program, resulting in an
exponential explosion of complexity (besides the linear growth in size). Once
linked, the program and its libraries/packages are no longer separate modules;
you cannot simply replace a library for a different one, despite the host of
false promises from the OOP crowd.

This is because the interfaces between these modules are very complex: hundreds
or thousands of function calls, complex object operations, &c.

### The Solution

The only way I know of that works is to not have dead code to begin with.
Extra features should be strictly opt-in, not opt-out. These should be
implemented with separate compilation *and* linking; in other words, each
feature is a new program, not a library.

The objection may be raised that we're advocating an extremely inefficient
paradigm, increasing the already significant overhead of function calls with the
much greater one of executing new programs. As an "extreme" example, a typical
Unix shell will parse each command (with few exceptions) as the name of a new
program to execute. How inefficient!?

Maintainable, replaceable code reuse can only happen when the interfaces are
well specified and minimal, such as obtain between cooperating independent
programs in a Unix pipeline.

> The key to problem-solving on the UNIX system is to identify the right
> primitive operations and to put them at the right place. UNIX programs tend to
> solve general problems rather than special cases. In a very loose sense, the
> programs are orthogonal, spanning the space of jobs to be done (although with
> a fair amount of overlap for reasons of history, convenience or efficiency).
> Functions are placed where they will do the most good: there shouldn't be a
> pager in every program that produces output any more than there should be
> filename pattern matching in every program that uses filenames.
>
> One thing that UNIX does not need is more features. It is successful in part
> because it has a small number of good ideas that work well together. Merely
> adding features does not make it easier for users to do things --- it just
> makes the manual thicker.[^design]

[^design]: Pike, Rob, and Brian Kernighan. "Program design in the UNIX
    environment." AT&T Bell Laboratories Technical Journal 63.8 (1984):
    1595-1605. See also [UNIX Style, or cat -v Considered
    Harmful](https://harmful.cat-v.org/cat-v/).

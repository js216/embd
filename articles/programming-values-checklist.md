---
title: A Checklist of Values for Programming
author: Jakob Kastelic
date: 31 Aug 2025
modified: 12 Sep 2025
topic: Philosophy
description: >
   A practical checklist of programming values: simplicity, portability, error
   handling, readability, testing, reusability, robustness, and clean code
   organization. Guidelines for writing minimal, reliable, and maintainable
   software.
---

![](../images/sub.jpg)

### 1. Simplicity and minimalism

Each program does *one* thing only.

> Do not put code in your program that might be used. Do not leave hooks on
> which you can hang extensions. The things you might want to do are infinite;
> that means that each one has 0 probability of realization. If you need an
> extension later, you can code it later - and probably do a better job than if
> you did it now. And if someone else adds the extension, will they notice the
> hooks you left?[^pol]

Do not be tempted to use all the features provided by the language, operating
system, or hardware.

While making full use of the hardware is a nice thing, DO NOT fill up the
available program or data memory more than about 75%, or else future
modifications (or even extra features!) will become *really* difficult to
implement. When the entire system capacity is used up, every functions and
feature becomes entangled with every other one: if you want an extra variable
here, you need to make some other part smaller, etc.

### 2. Portability

Be very strict to only use those of the language features that are guaranteed by
the standard.

Use a simple compile/build process that works on all relevant operating systems
and none, on all relevant combinations of hardware, and with all compilers for
the same language that you have available.

The inevitable non-portable stuff (think the likes of DMA configuration) is to
be minimized, isolated, and documented. The goal of the minimization is not to
make it more "performant", whatever that means, but to make it possible for
someone new to the project or platform to understand.

If the non-portable parts are more than usually obscure, document them in a
literate style.

### 3. Error handling

All functions should return 0 on success and -1 on error. In languages like C
where a function can only return one value, this unfortunately implies that the
data is to be returned via function pointers; these should be the first (few)
arguments of the function.

The error handling should be implemented in multiple levels. At least two are
mandatory:

- Assertions are errors that "cannot happen", which indicate programming errors
  which are to be discovered during testing. Also known as `ERROR`, or `fail`.

- User errors, such as invalid input, which can be recovered from. The error
  codes should be collected all in one place and be associated with
  understandable error messages, which are to be communicated to the user in
  some way.

Both of these should be present from the very beginning of a project. If the
infrastructure is not in place yet, simply make a file like `errors.c` with
empty implementations:

```c
void fail(char *msg) {}
int error(enum err_code err) {}
```

Most likely it will be appropriate to include a way to print the error messages,
or to report them to the user, or trigger a debugger breakpoint when they
happen, etc. That can all easily be added later. What's important is that the
functions be present and used from the very start.

Additional error levels can be added, such as warnings (valid, but unusual and
probably unexpected conditions) and debug information (explaining what the
program is doing at a particular point, to enable crash reconstruction from
these logs).

### 4. Readability

Functions must be very short (ideally less than 25 lines or so).

Use simple control flow. No deeply nested loops and conditional, three
indentation levels inside a function are quite enough.

No multi-cycle recursion, where `f1()` calls `f2()` which calls `f3()` which
calls `f1()` again.

Header inclusions, or the use of modules in general must be a directed acyclic
graph. In particular, two or three modules are not allowed to call each other's
functions, or else these functions should probably be located inside the same
module.

Modules need to be short with the minimal number of functions and data
structures necessary to accomplish their goal.

No function or operator overloading besides what's already provided by the
language. To be very emphatic about it: different functions should not have same
names! (Sorry C++, go away.)

### 5. No side effects

Except in the dream world of functional people, a rule like this is only viable
when its exception is clearly spelled out: the functions with side effects are
to be confined to a small, clearly marked and isolated section of code. Again
like the non-portable code, the amount of code with side effects must be small
in proportion to the main program, perhaps no more than 10% of the entire source
code.

### 6. Tests and tests

There should be an extensive set of tests corresponding to all anticipated use
cases of the program. When new use cases are discovered, more tests are to be
added.

At a minimum, the tests need to cover the "trivial" edge or boundary cases where
most of the bugs hide anyway.

As with the error handling, the testing infrastructure must be present in the
code base from the very beginning, ideally before *any* of the actual
application-specific code is added. Again, this does not need to be complicated.
It is enough to create a directory called "tests" and add a target "test" to the
build system, which compiles and runs a test program. The test program in turn
can be quite minimal, just a list of test functions (function pointer array in
C, or an actual list in Python), and a main function that runs each of these in
turn, checking whether the test function returned 0 (success) or -1 (failure).

As the program grows, if and only if it becomes necessary, more sophisticated
test frameworks can be substituted. But for a small program this may be all that
is needed.

### 7. Reusability

No inheritance! (Sorry C++.)

> I think the lack of reusability comes in object-oriented languages, not
> functional languages. Because the problem with object-oriented languages is
> they've got all this implicit environment that they carry around with them.
> You wanted a banana but what you got was a gorilla holding the banana and the
> entire jungle.
>
> If you have referentially transparent code, if you have pure functions---all
> the data comes in its input arguments and everything goes out and leave no
> state behind---it’s incredibly reusable.[^work]

Functions and modules are to be so reusable that you can copy-paste them from
one program to another without *any* modifications. Inheritance-based programs
require a difficult process to extricate an inherited class, requiring one to
manually resolve the dependencies. (And all functions have the same name, which
does not help.)

Ensure short, simple, minimal dependency chains: short function call chains,
short chains of module inclusions. (It would be nice if there was a tool to
check this mechanically.)

Avoiding side effects in all functions except for a small, isolated set almost
ensures reusability, since one does not have to worry about the changes to the
global state.

In general, when writing functions, modules, and programs, think *tools* rather
than complete systems. General purpose blocks are automatically more reusable
than any specialized system.

### 8. Robustness

The functions, and the completed program, are to handle all corner cases in a
sensible manner. All possible argument values need to be accepted without
crashing the program or causing any other unexpected behavior.

The code should do extensive validation of pre-conditions and post-conditions.
These checks should be added to the code with reckless abandon and disregard for
performance implications, since their performance impact can be easily undone by
toggling a single "debug-mode" switch.

In theory, a program can be proven correct if each module, considered as a black
box, or a box in a flowchart, is ensured to have its pre-conditions met, and if
it makes sure to leave the post-conditions as expected by the modules that come
after.

> if any one of the assertions on the arrows leading into the box is true before
> the operation in that box is performed, then all of the assertions on the
> arrows leading away from the box are true after the operation.
>
> Once [this] has been proved for each box, it follows that all assertions are
> true during any execution of the algorithm.[^taocp]

In practice, such
checks are easy to add, most of the time don't catch major bugs, but when they
do, they are invaluable. The real payoff is that it forces one to think about
all the possible cases the function or program may encounter during its life.
(This knowledge is also useful when writing tests.)

A function should not knowingly trigger any exceptions, interrupts, traps, what
have you. (Probably does not apply in OS design.)

Aim to write complete, finished programs. Do not design products and teams with
the expectation to ship half-broken stuff, and then break it further with
continual "safety" improvement updates which annoy users. A suggestion: do it
right the first time around. If in a rush, get a new job.

### 9. Clean source code organization.

Shallow directory structure: it's enough to have `src`, `tests`, and, for a
library, `include`. In a small C project, there should be a single Makefile, of
no more than 100 lines, covering the entire build process including building and
running tests, and static code analysis.

The buildchain should be standard as much as possible. Do not use special
compiler features. Do not use fancy GUI build tools which generate a deeply
nested directory structure full of entirely illegible garbage code.

The build tools themselves should have a simple build process. Do not torture
future developers with a need to spend two weeks setting up the toolchain,
installing just the right version of each tool that happens to work with the
other tools and your code, etc.

### 10. Clean interfaces

Functions should have a small number of arguments and returned values, certainly
no more than about five.

Modules should expose a small, mostly orthogonal set of public functions.

Ideally, programs should be small, cooperative, and produce their output if
possible in the form of human and machine readable text:

> Write programs to work together. Write programs that handle text streams,
> because that is a universal interface.[^quat]

In particular, there should be no unnecessary output, only what is required for
the communicating processes to talk to each other, or upon explicit user
request.

> Generally a program should say nothing unless and until it has something to
> say.[^tools]

[^pol]: C. Moore: Programming a Problem-Oriented-Language, ca. 1970.

[^work]: J. Armstrong, quoted in P. Seibel: Coders at Work, 2009.

[^taocp]: D. Knuth: The Art of Computer Programming. Volume 1: Fundamental
    Algorithms.

[^quat]: D. McIlroy, quoted in P. Salus: A Quarter Century Of UNIX, 1994.

[^tools]: B. W. Kernighan and P. J. Plauger: Software Tools, Addison-Wesley,
    Reading, Mass., 1976.

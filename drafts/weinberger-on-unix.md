---
title: Weinberger on Unix
author: Jakob Kastelic
date:
topic: Unix
description: >
---

![](../images/pjw.jpg)

Interview with Peter J. Weinberger, Murray Hill, 8 September 1989 Michael S. Mahoney, Interviewer

https://www.tuhs.org/Archive/Documentation/OralHistory/transcripts/weinberger.htm

I’m no longer convinced anybody knows anything about user interface. It’s clear
some things are easier to use and some things are harder to use. That’s okay.
But it’s also clear that people…people…learn a lot.

one of the experiences, I think, of all that sort of computing is that there is
a balance between safety and usefulness and a balance between various flavors of
generality.

I think UNIX was successful because it turned out that a lot of the safety that
people relied on or that academically seemed respectable because you can say
things about it…just…just was pointless. There’s no need for it in many things.

My guess is that there is a modest amount to learn and you can use it. And the
truth is our secretaries use it. We don’t have a special system for secretaries.
They just use it. Now, when you watch them use it you say ‘oh, but there’s so
many easier ways of doing it…there this and this’…but it doesn’t really matter.
They don’t have to use it perfectly.

You can take the manual which was pretty big even in those days and you could
read it once and do some things and you could read it again and read it again
and by the third time through you actually understood how the system worked to a
large extent. All of a sudden things became much less surprising. And then all
the source code was on-line in those days. It wasn’t all that much source code.
And you could look at it. And a large fraction of it had been written by people
with very good style. Right, like, say, Dennis.

What you tell the machine to do, it’s not doing it on the model, it’s doing it
on the mathematical reality. There’s no gap. Which, I think, makes it very
appealing. And one of the…there’s a difference between a computer program and a
theorem, which some people…I think is a fundamental difference, at least to me.
Which is that when you prove a theorem you now sort of know something you didn’t
know before. But when you write a program, the universe has changed. You could
do something you couldn’t do before.

of…there certainly was in the past, a lot of push towards solving the whole
problem. Not that the program solved the whole problem. UNIX is famous for this
theory that it’s best to do 80% because the last 20% is way too hard. But if
there were a big piece you could chop off then you did it.

If you have a theory based program you can believe you got the last bug out. If
you have a hacked up program, all it is, is bugs. Surrounded by, you know,
something that does something. You never get the last bug out. So we’ve got both
kinds. And it’s partly the style of the programmer. Both kinds are useful. But
one kind’s a lot easier to explain and understand even if it’s not more useful.

I also have this feeling that you never want to have to touch the program. So
it’s important to do it right early and that it always be okay. So it always has
to be…it’s not just a problem of the minute, although one writes a lot of code
that’s got to do the problem of the minute, it’s got to fill the niche
permanently (which is completely unrealistic but it’s certainly an attitude).
And I think that matches this other. If it’s just going to be a slipshod
temporary hacked up way of doing it it’s just not going to work long enough. And
you’re going to just have to come back and do it again and it’s just too much
like work. Not that reality actually matches this in any way but I think that’s
the attitude.

A program that’s sufficiently useful can have any number of bad
effects…properties. But people prefer small, clean, easy-to-understand programs.
But they will use big, horrible, grotesque, disgusting, buggy programs if
they’re sufficiently useful. And some will complain louder than others, but it’s
a rare few who will say ‘this is just so awful I won’t use it.’

I think that’s also one of the…a common feel[ing].. that’s common in computing.
The story is if you write the documentation early, it’s likely it’ll be possible
to explain what your program does, whereas if you wait until your program is
completely finished, you may discover that however coherent it looked while you
writing the various pieces, it’s impossible to explain it.

MSM: Because when I got my NeXT coffee cup…for looking at a demonstration...they
had introduced the machine. They talked about this was going to be UNIX but with
a friendly interface. And I said to the guy ‘well, when I think of UNIX and I
think of friendly, I think of pipes and macros. Now, are you telling me I can
pile up icons in a pipeline?’ and he said ‘no, we don’t know how to do that, but
you can open a command window’. I said ‘I can do that in DOS.’ It was part of
making myself friendly. Weinberger: The hell with them. They’re all so
self-satisfied. I don’t like vendors. MSM: Ron knows. He came in with his lowest
common denominator thing, and they were showing the NeXT Interface Builder.
Again I stopped him. I said ‘wait a minute…you’re hooking messages on the
objects. Where did the objects come from? You’re telling me that all the
applications for this have been written in Objective C?’ He said yes. I turned
to our graphics person and he said ‘now, that’s raising the lowest common
denominator.’ Weinberger: It certainly is. And Objective C’s the wrong solution
also.

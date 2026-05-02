---
title: How to Spent Time and Tokens
author: Jakob Kastelic
date: 2 May 2026
topic: Agents
description: >
   Practical techniques for running AI coding agents with minimal supervision:
   close the feedback loop, sandbox aggressively, organize agents into roles,
   break work into mission-driven tasks, lock in progress with automated tests,
   and keep agents productive through short-lived contexts and autonomous
   workflows.
---

![](../images/scr.jpg)

Ask an agent to fix a bug in your code and you'll end up staring at the blinking
prompt, watching it slowly hack away at the task. You can't leave it, since it
stops every couple minutes and asks for guidance, and you can't do other things
either; the constant interruptions fragment your focus. So, you have to sit and
press "Yes" every couple minutes. Or do you?

In this article, I'll show an alternative way. I don't claim it is original nor
will it likely stay useful for very long, but it's the best way to make use of
agents in my work at this time.

### Feedback: Close the Loop

The first order of business is to reduce how often the agents interrupt your
focus. Instead of asking you to run commands or check their work, they need to
be able to run these checks on their own. The idea is simple and powerful in
equal measures: any engineer can set it up so that program output ends up in a
place the agent can read, and once it can read it, it can iterate much more
independently.

How to set it up for a "pure" program (one that takes some input and produces
some output, without significant side effects) is obvious. It's only a little
bit more work when there is physical or remote hardware involved, but the idea
is simple: let the agent program the hardware, write test data to it, read the
outputs. If tests require coordination between multiple devices, say an FPGA and
an oscilloscope, then the test server coordinates between multiple
devices---again nothing exotic. See my
[`test_serv`](https://github.com/js216/test_serv) as a slightly more involved
example.

Closing the loop in this way only helps if the agent is not impeded by misguided
security restrictions. Read on ...

### Sandbox to Grant All Permissions

The security model of current AI coding tools appears to have been devised by
lawyers: simply ask the user for confirmation of all potentially dangerous
actions. You'll automatically press "Yes" to anything, but the AI companies are
safe; after all, you authorized the action so it's your fault if things break or
you lose all your data.

Luckily, the tools also offer the far more sensible alternative: grant the
agents all permissions to do anything whatsoever they want to do:

    claude --dangerously-skip-permissions codex
    --dangerously-bypass-approvals-and-sandbox

I thought it goes without saying that with agents off the leash in this way,
they need to be contained in a restricted environment:

- No access to important or non-public files
- No passwords or cryptographic keys
- No access to corporate databases or shared drives

The easy way to sandbox is to create an unpriviledged account and rely on the
operating system to do its part. Fancier options include containers (which also
rely on OS-level separation), virtual machines, or simply dedicate an old
computer to running AI only.

In my case, I have a dedicated computer with an unpriviledged user set up per
agent team. To make best use of the setup, let's next define agent teams.

### Agent Teams

Progress so far: an all powerful agent has full access to the code and hardware
and will happily work at a task for about half an hour. Big improvement over
every-five-minutes interruptions, but not quite autonomous yet.

While I have no hard evidence for this theory, I've come to believe that the
agents are designed to stop every 15--30 min in order to prevent them from
getting stuck in infinite loops. However, engineering *is* an infinite loop: we
iterate on our jobs forever and so should our agents. Recent models (e.g. GPT
5.5) already offer a big step forward in terms of autonomy, but it's still
useful to be explicit about it when setting up the prompt.

I've been experimenting with different team compositions, but the following set
of agent roles seems to work best:

- **Orchestrator** communicates with me, spawns all other agents, and passes
  messages between them.
- **Worker** does all the hard work: diagnose what causes a bug, design and
  implement a new feature, do a quick test that it works.
- **Verifier** checks that the Worker did not stop halfway, that its work did
  not break something else, that all other tests still work.

With a good "feedback network", this pattern is able to run unsupervised for
hours to days at a time. Even though the Orchestrator is long running, its task
is simple and does not consume much of its "context window". On the other hand,
the Worker needs to read a lot of code, form and test various hypotheses, and
other such tasks which consume a lot of memory. Thus, the Worker needs to be
spawned fresh every half an hour, or wherever it stops. Orchestrator takes care
of that so we don't have to.

The Verifier can run the baseline set of regression tests, or the Orchestrator
can. I have not found a big difference either way.

With some tasks I have found that both Workers and Verifiers become lazy and
dishonest, disabling or "fixing" tests rather than fixing real root causes of
issues. In that case, it may be useful to have a **Police** agent. It's prompt
instructs it to an adversarial review: check that the tests actually test what
they claim to test, check that the other agents did not implement some hidden
"shortcuts". My success with that is mixed; only on a few occasion did the
Police agent uncover shady practices---maybe it's a waste of tokens.

Now that we have a team of agents dedicated to our work we need to ask: who
assigns them the work? The human engineer?

### Manager and Missions

With agentic power at our disposal, we need to give it something to do. A year
back, I'd write a function call signature and outline and ask ChatGPT to fill in
the details. A few months back, I'd give precise instructions describing
program-level behavior to implement, and then steer the agent along the route of
debugging. In almost every case, this resulted in a great deal of anger: "I told
you to not do this, why are you doing that, fix that issue already!?" Lately
I've been settling on a more peaceful approach: the mission file.

Open a new file and write down the key milestones that need to be accomplished.
As a recent example, I have a microcontroller connected to an FPGA via their SPI
interfaces, and I'd like to learn what is the fastest reliable data rate that
can be transmitted between the two. The "mission statement" in the file, for
example, could be: demonstrate that the SPI connection can sustain arbitrary
data patterns and sizes in excess of 100 Mbit/s.

The mission is relatively large in scope: program the microcontroller, program
the FPGA, validate the FPGA code in simulations and formal verification, make it
actually work on hardware. All of that most likely does not fit in the "brain"
of a single Worker. They will happily accept the commission, and then hours
later, hundreds of thousands of tokens wasted, nothing will be done. The task is
simply too large.

Enter the **Manager**: an agent whose role is to study the next unfinished task
in the "mission file", break it down into smaller, testable steps, and pass the
result to the Orchestrator to spawn a fresh Worker with the narrow-scope task.
The Manager writes to the mission file and adds the smaller tasks, and if the
Worker fails at the smaller, it can re-evaluate and perhaps break the work down
even further.

The setup so far---agent teams attacking a big task---will work independently
for hours at a time, churn out volumes of good code and rapidly demonstrate
meaningful progress towards "mission accomplished". Then, something happens that
makes it seem as if the agents all got drunk: previously working code doesn't
work anymore, Verifier starts accepting bogus solutions as "verified", the
Manager is pursuing tasks quite orthogonal to the stated mission objectives.
What to do!?

### Lock in the Progress

Much anger and ALL CAPS SHOUTING will obtain when previously docile agents stage
an apparent mutiny. At first they did a month's work in five minutes, and now
they can't move an image on a website an inch higher!? First they correctly
implemented the JEDEC flash protocol on the FPGA and now they can't get a
"Hello, world!" to compile anymore!? The codebase is a mess, we're 35 commits
ahead of main and 25 behind, and who knows which version of the code works, if
any?

The situation is one that must be avoided from the start rather than fixed after
the fact. The key insight is to connect the "mission file" described in the
previous section directly with the automated tests. There should ideally be a
simple script that mechanically follows a recipe and outputs either a big green
"PASS" or a red "FAIL". On every iteration through the Manager--Worker--Verifier
loop, the script must be run to ensure the prior tests all still succeed. On
every commit to the repository, the full tests suite must pass. Thus, at any
point in the history of the codebase, it should be clear exactly what works and
what does not.

When agents get desperate to get stuff done, they will justify to themselves
(often even  fooling me!) that a certain test must be modified. If they have
direct access to the test routines, they will simply remove the offending test
and claim success. Thus, the tests must be locked in a way that prevents that,
while still allow the agents to add new test cases. One way to do it is to
calculate a SHA256 hash of all passing tests, write these hashes to a file that
agents cannot modify, and add a commit hook that checks that these "locked
tests" are still present and still pass.

### Fresh Agents, Small Tasks

If the Manager has done a good job breaking down the work, the agents will be
wonderfully productive. They work best with a fresh context and when handling
small changes. The testing scheme described above helps to lock this in: each
test demonstrates a small, narrowly scoped feature, and if a test case fails, a
fresh agent can be easily dispatched to address it. If a regression cannot be
fixed, then simply roll back the repository history to a previous snapshot where
that test works, and try again.

### Restart, Don't Steer

Agents are chatty and argumentative and it's very tempting to engage them in
dialogue. They'll complain that the hardware is broken when it's not, they'll
say they're missing some permissions they don't need, and so on. Don't take the
bait.

Instead, take a step back and understand that the agents stopping for a question
before their work is done represents a failure of the work pipeline. They are
supposed to have all the resources they need to implement the task given. If
they do stop, it means that the prompt may have been unclear, the roles
ill-defined, or a supervisory agent either inadequate or missing altogether.

When there is a break, therefore, think what the real underlying issue is. Are
the role descriptions clear that stopping is not allowed? Is the testing
infrastructure really broken? Fix that, clear the agents' context, and restart
the pipeline.

The goal is to have them work independently longer and longer each iteration.
Don't fix their immediate problems; rather, improve the process so the agents
get empowered to fix them without disturbing you.

### How to Spend Time

All the tips above combined allow one to make very good (and quick) work of the
available tokens. But what to do with oneself? Is there still a role for humans
in the creative process?

Plenty of it in fact: read the code produced by the agent when they reach a
natural stopping point, such as "mission accomplished" as per the mission files
described above. I don't like reading the code immediately as it gets produced,
since there's simply too much of it and it'll get changed anyway. But once it's
starting to reach some kind of a final form, it's a good time to review it.

Second task for human is to be the technician on the bench: connect new hardware
devices to the tests, make connections between those devices, create new
hardware for the agents to play with.

Third, if there's still "time and tokens" left over, write new mission files and
get new agentic feedback loops started.

Fourth, inevitably the agents will try and stop for a "questions break". Debug
these breaks in such a way that next time it takes them longer to stop.

Fourth, once a significant milestone is achieved, manually inspect that the
tests do what the agents claim they do. They are (currently) not to be trusted.

Fifth, write about your experiences and share with the world!

--
title: Parameters With Least Overhead
author: Jakob Kastelic
date: 20 Mar 2026
topic: Embedded
description: >
   Comparing shared memory and socket-based designs for managing embedded
   parameters with minimal CPU overhead.
---

![](../images/hw.jpg)

The state of an embedded instrument can be represented as a set of parameters
with names, values, and other attributes. These parameters change in
various ways (user control, programmatically, sensor input) and need to be
accessible on a front panel, remote interface, and in the internal subsystems.
Some never change (serial number), some rarely (firmware version), some
occasionally (user settings), and some need real-time updates (current
measurement value). I'm looking for a way to manage these parameters that
consumes the least processor time, i.e. adds the least overhead.

### One program, bare-metal

If the entire device runs a single program, then the program can use a simple
in-memory array (list, hash map) of parameters and use them as appropriate.
That's a less attractive option for more complex instruments where there's a
GUI, several remote interfaces, a web server perhaps. Maybe better to divide the
firmware into several tasks?

### Several tasks on RTOS

The different application concerns can be implemented as tasks on a real-time
operating system. [FreeRTOS](https://www.freertos.org/), barely more than a
"user-space" threading library, is an attractive option because it's lightweight
and easy to use. The tasks share memory and can access a global array of
parameters, coordinating the access using a mutex to coordinate access.

This solution works for as long as we are happy to keep the whole instrument
firmware compiled into a single executable. But then the smallest change
anywhere requires the whole program to be re-flashed and the instrument
rebooted. When there's a lot of little adjustments this quickly becomes slow and
annoying. It'd be much nicer to have truly independent programs for different
parts of the instrument.

### Programs on a "real" OS

If the instrument supports a full-featured operating system like Linux then we
can divide the work into several programs. One could be in charge of drawing the
graphical user interface, another would serve as a "SCPI shell", fielding the
remote commands received from USB or Ethernet interfaces. Now that the various
programs no longer share the same memory space, the problem arises of sharing
the parameters between the programs. If data is received by the sensor
monitoring program, how can the GUI app access it to display on the LCD panel?

Two solutions come to mind immediately: [POSIX shared
memory](https://man7.org/linux/man-pages/man7/shm_overview.7.html), or a single
central "param server" process that sends/receives data over [Unix-domain
sockets](https://man7.org/linux/man-pages/man7/unix.7.html). The first comes
closest to "zero overhead" and is comparable to the bare-metal and RTOS
solutions; the second separates domains more cleanly but may come with a
performance price. It would be "premature optimization" to discard a
conceptually cleaner solution for fear of overhead, so let's implement both and
see how much they cost.

### Shared memory

In the "shared memory" approach, the parameter list is defined as a header or
library that is compiled into each program that needs access to the parameters.
It defines the memory location, structure, and the synchronization primitives
that make it possible for several programs to share the data.

For concreteness, let's assume that a parameter has a name and a value:

```c
struct param {
   const char *name;
   double val;
   // other attributes as needed
};
```

A header file declares an array of these parameters:

```c
static struct param params[] = {
   {"parameter_name_1", 0.0},
   {"parameter_name_2", 0.0},
   // and so on, about 200 items
}
```

We have a choice of several synchronization methods:

- **No synchronization at all.** If the parameters were simple small numbers,
  the reads and writes are naturally atomic at the hardware level. However, for
  anything larger (such as the struct above), we'd get torn reads. Nonetheless,
  this gives the absolute floor for the overhead measurement.

- **Mutex.**: The straightforward approach: one `pthread_mutex_t` with
  `PTHREAD_PROCESS_SHARED` per table or per parameter. Readers and writers both
  lock/unlock. Simple, correct, but a single global mutex becomes a bottleneck
  when many processes contend — everyone blocks on every access.

- **Read-write lock.** To allow multiple concurrent readers, can use
  [`pthread_rwlock`](https://pubs.opengroup.org/onlinepubs/009696899/functions/pthread_rwlock_rdlock.html).
  Writers take an exclusive lock, readers share. Helps when reads vastly
  outnumber writes, but still blocks readers while a writer holds the lock.

- **Sequence counter.** The writer increments a sequence number before and after
  writing. Readers check the sequence before and after reading. If it changed or
  is odd, they retry. Writers never block on readers, readers never block on
  each other. The writer still needs a mutex if there are multiple writers.
  Seqlocks are cheap for the read path (no syscalls, no atomics beyond loads),
  but require active spinning.

Next, declare the shared memory layout corresponding to the six ways of
synchronizing (mutex, rwlock, seqlock; per-parameter or whole-table locking):

```c
#define MAX_SLOTS 256 // shared memory capacity
#define SHM_NAME "/param_bench"

struct param_slot {
	double val;
#if defined(MUTEX_PARAM)
	pthread_mutex_t lock;
#elif defined(RWLOCK_PARAM)
	pthread_rwlock_t lock;
#elif defined(SEQLOCK_PARAM)
	_Atomic unsigned seq;
#endif
};

struct shared {
#if defined(MUTEX_TABLE)
	pthread_mutex_t lock;
#elif defined(RWLOCK_TABLE)
	pthread_rwlock_t lock;
#elif defined(SEQLOCK_TABLE)
	_Atomic unsigned seq;
#endif
	struct param_slot slots[MAX_SLOTS];
};
```

The actual locking/unlocking functions are very standard, so I'll show only the
per-table mutex case:

```c
#if defined(MUTEX_TABLE)
static inline unsigned _rbegin(struct shared *s, int i) {
	pthread_mutex_lock(&s->lock);
	return 0;
}

static inline int _rend(struct shared *s, int i, unsigned q) {
	pthread_mutex_unlock(&s->lock);
	return 0;
}

static inline void _wlock(struct shared *s, int i) {
	pthread_mutex_lock(&s->lock);
}

static inline void _wunlock(struct shared *s, int i) {
	pthread_mutex_unlock(&s->lock);
}
#endif
```

### Overhead measurements: shared memory

Now we write two programs:

- Randomizer takes any number of command line arguments and runs a loop at about
  60 Hz to write random values for these parameters

- Displayer prints all parameters that change to the standard input, also at 60
  Hz.

We can investigate the potential bottlenecks by varying the synchronization
method and the number of Randomizers and Displayers, and the number of
parameters changed by each Randomizer.

On STM32MP135 eval board, with two Displayers and two Randomizers (on
randomizing all parameters, the other only two parameters) the results are about
the same for all three synchronization primitives, whether per-parameter or per
table:

- The Randomizer, whether randomizing one parameter or all 200, takes about 0.0%
  CPU; i.e., too little to show up in `top`.

- Displayer takes up about 12% if displaying all parameters, which is presumably
  mostly just the printing overhead rather than parameter access.

- Load average varies in the 1.2 to 1.8 range when observed over a few minutes.

In other words, updating 200 parameters at 60 Hz is too light a load to matter!
Any locking method is fine and should be decided based on programming
convenience---but there they are about the same as well.

We can modify the programs to not throttle the update rate and not do
any printing, just count parameter accesses per second. Let's setup the same
configuration as before (two Displayers, two Randomizers: one randomizes all 200
params, the other just 2). Now we can directly report the number of parameter
access in Mops/s (million operations per second) across all synchronization
methods:

| Method  | Granularity| Displayer  | Randomizer 2 | Randomizer 200 | Load Avg |
| ------- | ---------- | ---------- | ------------ | -------------- | -------- |
| mutex   | param      | 1.8        | 1.2          | 0.9            | 3.43     |
| mutex   | table      | 2.2        | 0.7          | 1.3            | 3.61     |
|         |            |            |              |                |          |
| rwlock  | param      | 2.0        | 0.7          | 0.3            | 2.81     |
| rwlock  | table      | 2.6        | 0.3          | 0.6            | 2.55     |
|         |            |            |              |                |          |
| seqlock | param      | 0.0 to 1.5 | 0.8          | 1.4            | 4.03     |
| seqlock | table      | 1.2 to 5.0 | 0.8          | 1.4            | 4.06     |

Now the differences show up. Mutexes appear to be "best behaved": decent overall
performance. Both mutexes and rwlocks seems to prioritize readers with variable
writer performance: if we lock per-param, it's best to write fewer params; if we
lock per-table, it's best to write more params.

Seqlocks are the weirdest: the read performance is highly variable, sometimes
choking to zero read accesses, sometimes outperforming the mutexes and rwlocks.
Strangely, for seqlocks it doesn't matter whether locks are per-table of
per-param. There is a clear explanation: seqlocks have no fairness mechanism, so
a flat-out writer can starve readers indefinitely. When the writer runs
continuously, it increments the sequence counter on every iteration. The reader
captures seq, reads the value, then checks---but by then the writer has already
incremented again. The bursts up to 5.0 happen when the OS scheduler preempts
the writer and the reader gets a few uncontested iterations in.

The unthrottled measurement consumes altogether 100% of the CPU and represents
an upper bound for how many independent parameters the firmware could read and
write. For streaming high-speed data, rather than adding more parameters, one
would most likely consider a different architecture altogether. However, the
firmware designs I have in mind have only tens to hundreds of parameters,
leaving us free to consider a less efficient but perhaps cleaner architecture: a
single parameter server process communicating to clients over sockets.

### Sockets

Let there be three kinds of programs:

- Parameter Server is the keeper of the in-memory parameter list and controls
  read and write access to other programs via Unix domain sockets

- Readers, any number of them, request the values and metadata for some or all
  of the parameters

- Writers, any number of them, modify the value of some of the parameters

Of course some programs will be both readers and writers. The GUI, for example,
displays the latest measurements, and allows the user to change the settings.

For benchmarking, we can again consider the Randomizer / Displayer example.
Unthrottled, each of the two Displayers handle about 0.4 Mops/s, taking up 12%
of the CPU. The 200-param Randomizer handles 0.4 Mops/s and takes up 16% CPU as
well. The 2-param Randomizer handles 0.0036 Mops/s using 12% of the CPU---very
inefficient! Note that 3.6 kops/s is equivalent to 60 parameters updated at 60
Hz. Adding or removing readers and writers slows down or speeds up the system as
expected, but no matter what, the Parameter Server takes up about 45% of the
CPU.

Throttled to 60 Hz, Displayers again take up 12% CPU, most of which is printing.
Randomizers both oscillate between 0.7% and 1.3% CPU, and the Parameter Server
takes up 2.0%. Closing one of the Displayers, the Parameter Server needs only
1.3%. Closing both Displayers, the Server needs between 0.0% and 0.7%. With just
the 200-param Randomizer, the Server and Randomizer both need between 0.0% and
0.7% CPU.

### Conclusion

For high-speed data served one number at a time, sockets would not work. We
could of course try to increase the throughput by sending a lot of data in a
single socket call. If pushing the limits of performance, zero-copy alternatives
using shared memory is the way to go, using one of the locking mechanisms.
Mostly likely mutexes: least confusing (to me), well understood, simple.

For a GUI-throttled set of a few ten or hundred parameters, the client--server
architecture using Unix-domain sockets makes for a very clean design: send all
changed parameters in one request per frame, not one request per parameter. No
need to worry about mutual exclusion; in effect, the Parameter Server *is* the
synchronization mechanism.

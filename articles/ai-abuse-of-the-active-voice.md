---
title: AI Abuse of the Active Voice
author: Jakob Kastelic
date: 28 Oct 2026
topic: Agents
description: >
   Fifteen searchable rules for the grammatical constructions that mark
   machine-written prose, refined until no two rules match the same text.
---

![](../images/f.jpg)

Lacking the grammatical sophistication to describe the symptoms precisely, I was
forced to manually correct the style sentence by sentence---or publish the
material as obviously vibecoded.

In this article, I present a set of rules to aid in automated detection of the
worst of "AI slop"-type grammatical constructions. I started with a loose list
of such rules gathered from various sources and told Claude to rephrase the
rules until no two rules match the same text, over a corpus of my own recent
code. (Is it really mine if agents wrote all of it?)

### Quick Demo

As a quick experiment, choose a vibecoded codebase and ask AI to find some
instances of the following:

> finite object relative clause with an active verb and overt definite noun
> phrase as its subject

Then repeat on something you know was written by hand. In a random sample of
about 3,000 lines taken from the Linux kernel, zero matches. Similar sample
from something I'm working on, 13 matches. Another comparison: original Unix v7
code, one match, in my [port to Arm](https://github.com/js216/unix-v7-c99), more
than ten.

With just that simple rule, we can find some pretty horrible sentences:

- "Writes a setting this daemon decides, keeping it and noting it, by swapping
  it for the value held: true when it stands."

- "The publisher says what the main loop said itself before: the same texts, the
  second's values once per second, rates and levels as they move."

- "A schedule whose values the registers cannot hold spills more than the
  overlap gains: a longer ii holds fewer at once."

Of course, models violate other rules, as spelled out in the next section. You
can use the style sheet below in two ways: run it over an existing text to flag
potential issues, or use it as a commit check to avoid adding more obvious slop
into the existing text. The rules are not intended as a strict gate: they will
flag acceptable text.

### STYLE.md

1. Object relative clause, with or without a relativizer, whose verb is active
   and whose subject is an overt definite noun phrase. "Its `bss`, which `exec`
   clears to zeros"; "what the store writes the next iteration reads".[^clark]

2. Inanimate subject of a verb that, taken literally, needs an animate subject
   (know, want, expect, decide, say, show, owe, own, answer), in a finite clause
   other than an object relative clause. The match is the subject and its verb.
   "As the comment promises"; "the plot says how far a long block has come"; "a
   faulted DSP never answers".[^clark]

3. Copula substitution: a lexical verb in place of "is" ("serves as", "stands
   for"), or "is" in place of a lexical verb, where X means, yields, or
   indicates Y rather than being a kind of Y. The match is the verb with its
   "as" or "for", or the "is" alone. "DEN 0 standing for 2^40"; "EINVAL is a
   driver without blanking"; "Busy is what ran".[^wiki]

4. History narration: an independent clause in the past tense telling what the
   code did before a change, in place of what it does now. The match is the
   clause. "The I register and DB used to sit at bits[26:24] and bit[32]"; "the
   folder answered a different question from the emitted code".

5. Nominalization or gerund as subject or object, doing the work of a finite
   clause, with an object, an of-phrase, or a possessor of its own. The match is
   the noun and its arguments. "The return to the instruction after the `svc`
   restores the user's saved status"; "the averaging takes every
   block".[^reinhart]

6. Non-finite, verbless, or elliptical clause attached to a noun or a clause: a
   participle with a dependent of its own, an absolute construction, or a clause
   with its verb left out. A bare noun phrase labelling a declaration is not a
   clause. "Continues in `swtch`, returning from it into whatever had called
   `swtch`"; "measuring, the span started again; locked, the tag taken a period
   short".[^reinhart][^wiki]

7. Prenominal packing: what an of-phrase would say, put before the noun, as a
   compound of three or more nouns, or an s-genitive with an inanimate
   possessor, its head noun often left out. The match is the premodifier. "The
   process table entry"; "each ADC channel's largest conversion"; "the fit's,
   the seconds' scatter".[^clark]

8. Coordination inside a phrase: two or more nouns, adjectives, or phrases
   joined within one noun phrase or one argument. "The address and cause of a
   data abort"; "with its own phase, filter and gain".[^reinhart][^wiki]

9. Interruption: a subject relative clause, an appositive, a parenthetical, or
   an aside between dashes, set off by commas, dashes, or parentheses, that
   separates a subject from its verb. An object relative clause is rule 1, a
   participle phrase rule 6. The match includes the punctuation. "A process that
   waits for something which is sure to happen soon, such as a disk transfer,
   can sleep"; "The LMX, which clocks the ADC, the CORDIC and the DSP, is
   retuned for every reference".[^clark][^munoz][^wiki]

10. Denominal verb: a verb converted from a noun. "The MMU faults any access
    from user mode"; "one clock synthesizer clocks the ADC"; "one whose last
    round the DMA lapped".[^clark]

11. Exclusion: a negator (not, no, never, nothing, neither), restrictive "only",
    or a contrastive "rather than", "instead of", "unlike", "except", or
    "despite". The match is the operator alone. "Needs no locks against other
    processes, only masked interrupts"; "out now, not at the end of the pass";
    "nulled exactly rather than attenuated".[^wiki][^antislop][^slopbench]

12. Colon apposition: a statement or a bare noun phrase, then a colon and a
    second statement that restates, lists, or explains it, where a full stop,
    "because", or "so" would join them. The match is the colon. "How often the
    capture looks for new blocks: the ring holds seconds"; "the rings start over
    below: what was given out last is the chain's before".

13. Evaluative or intensifying word: a word of the excess-vocabulary lists
    (delve, underscore, ensure, key as an adjective, matters, steady), an
    intensifier (simply, exactly, whole, entirely, at all), or an emphatic
    "own". "Refers to it simply as `u`"; "the outputs remain quiet and steady";
    "the image sends a frame of its
    own".[^kobak][^juzek][^liang][^reinhart][^wiki][^shaib]

14. Sentence that restates an earlier one of the same paragraph. "A process
    running in the kernel is never preempted. It keeps the processor until it
    sleeps or returns to user mode"; "a process acts on its signals only on the
    way back to user mode. ... So a signal takes effect at the next return to
    user mode".[^shaib]

15. Recurring frame: the same opening, closing, or phrase in several sentences
    of one text. "With two processors, ..." closing five paragraphs in a row;
    "Next `main` calls ...", "Next `clkstart` ...", "Next `main` calls ..."
    opening consecutive steps; "From 0 Hz ..." opening sentence after
    sentence.[^slopbench][^templates][^antislop]

[^antislop]: S. Paech et al.: Antislop: A Comprehensive Framework for
    Identifying and Eliminating Repetitive Patterns in Language Models, ICLR
    2026. [arXiv:2510.15061](https://arxiv.org/abs/2510.15061)

[^clark]: T. H. Clark, M. B. Martin, K. Mahowald: Why is AI-generated language
    so hard to understand?, 2026.
    [arXiv:2610.29162](https://arxiv.org/abs/2610.29162)

[^juzek]: T. S. Juzek, Z. B. Ward: Why Does ChatGPT "Delve" So Much? Exploring
    the Sources of Lexical Overrepresentation in Large Language Models, COLING
    2025. [arXiv:2412.11385](https://arxiv.org/abs/2412.11385)

[^kobak]: D. Kobak et al.: Delving into LLM-assisted writing in biomedical
    publications through excess vocabulary, Science Advances 11(27), 2025.
    [arXiv:2406.07016](https://arxiv.org/abs/2406.07016)

[^liang]: W. Liang et al.: Monitoring AI-Modified Content at Scale: A Case
    Study on the Impact of ChatGPT on AI Conference Peer Reviews, ICML 2024.
    [arXiv:2403.07183](https://arxiv.org/abs/2403.07183)

[^munoz]: A. Muñoz-Ortiz, C. Gómez-Rodríguez, D. Vilares: Contrasting
    Linguistic Patterns in Human and LLM-Generated News Text, Artificial
    Intelligence Review, 2024.
    [arXiv:2308.09067](https://arxiv.org/abs/2308.09067)

[^reinhart]: A. Reinhart et al.: Do LLMs write like humans? Variation in
    grammatical and rhetorical styles, PNAS 122(8), 2025.
    [arXiv:2410.16107](https://arxiv.org/abs/2410.16107)

[^shaib]: C. Shaib et al.: Measuring AI "Slop" in Text, 2025.
    [arXiv:2509.19163](https://arxiv.org/abs/2509.19163)

[^slopbench]: D. Roongta et al.: SlopBench: How Well Can We Rank Language
    Models by Slop?, 2026. [arXiv:2609.33905](https://arxiv.org/abs/2609.33905)

[^templates]: C. Shaib et al.: Detection and Measurement of Syntactic Templates
    in Generated Text, EMNLP 2024.
    [arXiv:2407.00211](https://arxiv.org/abs/2407.00211)

[^wiki]: WikiProject AI Cleanup: [Signs of AI
    writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing),
    Wikipedia, October 2026.

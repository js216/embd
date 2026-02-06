---
title: Agent To Read Electronic Datasheets
author: Jakob Kastelic
date: 2 Jan 2026
topic: Agents
description: >
   How to quickly put together a data extraction agent.
---

![](../images/pa.jpg)

When an electronic design company accumulates large amounts of inventory, it can
become overwhelming for engineers to go through the thousands of parts to find
the one needed in a new design. Instead, they are likely to select a new part
from one of the distributors that have a better search engine. This leads to an
ever growing inventory: parts kept in stock and never used, a constant departure
from the ideal of having a "lean" operation.

Nowadays, with everyone creating their own "agent" for just about anything, I
wondered how hard it would be to create my own search engine. This article
represents a day of work, proving that structured data extraction from
semi-unstructured sources like datasheets has become almost a trivial problem.

I took the [Gemma 3](https://deepmind.google/models/gemma/gemma-3/) model (12B
parameters, 3-bit quantization) from Google, ran it in the
[llama.cpp](https://github.com/ggml-org/llama.cpp) inference framework, and fed
it the datasheet for an opamp. To extract the text from the PDFs, I used the
[Docling](https://www.docling.ai/) Python library from IBM research. The output,
generated in about four minutes on a GPU with 8 GB of memory, will be in this
format for now:

```json
"PSRR (Input offset voltage versus power supply)": {
   "min": 65,
   "typ": 100,
   "max": null,
   "unit": "dB"
 },
```

Let's get started!

### Running the model

Obtain and build llama.cpp:

```sh
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -S . -DGGML_CUDA=ON
cmake --build build -j
```

Obtain the [Gemma
3](https://huggingface.co/bartowski/google_gemma-3-12b-it-GGUF) model.

Start the LLM server:

```sh
llama-server -m ~/temp/gemma-3-12b-it-UD-IQ3_XXS.gguf \
   --port 8080 -c 4096 -ngl 999
```

Open `localhost:8080` and feel free to chat with the model. How simple things
have become!

### Get datasheet text

Next, we need to convert the datasheets from the PDF format into plain text that
we can feed to the model. Assuming `docling` is installed (install it with Pip
if not), we can define the following function to convert the documents:

```python
import sys
from pathlib import Path
from docling.document_converter import DocumentConverter

def convert_pdf_to_markdown(pdf_file):
    pdf_path = Path(pdf_file)
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    content = result.document.export_to_markdown()
    print(content)
```

This yields the output in a Markdown format.

### Define agent with a simple prompt

Here's the best part: the "source code" for the agent is in plain English. Here
it is in its entirety:

```
You are a datasheet specification extraction agent. Your
only job is to extract specifications.

OUTPUT FORMAT:
{
  "Full parameter name (short name)": {
    "min": number or null,
    "typ": number or null,
    "max": number or null,
    "unit": "string"
  }
}

EXTRACTION RULES:
- Always include both the full and short spec name in the key.
- Full name goes first, and short name in brackets: "Operating Temperature (T)"
- If a typ value is a range like "-11.5 to 14.5", split it: min=-11.5, max=14.5
- Convert scientific notation: "10 12" → 1e12
- Convert ± values into min/max fields
- Omit parameters with no numeric values (all null)
- Omit footnotes like (1) and (2)
- If no specifications exist, return: {}

CRITICAL OUTPUT RULES:
- Return ONLY valid JSON
- NO explanations
- NO descriptions
- NO phrases like "this section", "no specifications", "I will skip"
- NO text before or after the JSON
- NO markdown code blocks
- Just the raw JSON object
```

The insistence on pure JSON is a hack to make it stop being too chatty. There's
probably a more sophisticated way to do it, but for a first attempt it'll do
just fine.

### "Chunking"

The datasheet conversion from PDF includes lots of unnecessary text like
document version information, copyright, ordering information. For now, we'd
like to get just the electronic specifications. As a first approximation, assume
that the information is always present in tables only.

ChatGPT assures me that the following regex magic will extract tables from a
Markdown document:

```python
import re

def get_chunks(filepath):
    """Return a list of Markdown tables as strings from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    table_pattern = re.compile(
        r"(?:^\|.*\|\s*\n)"           # Header row
        r"(?:^\|[-:\s|]+\|\s*\n)"     # Separator row
        r"(?:^\|.*\|\s*\n?)+",        # Body rows
        re.MULTILINE
    )

    tables = table_pattern.findall(content)
    return [t.strip() for t in tables]
```

### Putting it together

We have all the pieces now: text data in small pieces, a model, the prompt to
define an agent. Now just iterate over all the chunks as defined above, send
them to the model together with the prompt, and observe what comes out. To
automate the process from PDF to the final JSON, I used a Makefile defining the
recipes for the three steps of the transformation. All of this is too
straightforward to be worth including here.

For anyone interested, find the entire code presented above
[here](https://github.com/js216/sfap).


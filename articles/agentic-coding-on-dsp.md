---
title: Agentic Coding on ADSP-2156 Eval Board
author: Jakob Kastelic
date: 13 Apr 2026
topic: DSP
description: >
   A closed-loop system for agentic DSP testing: a simple HTTP server
   distributes binaries, while a Python client flashes an ADSP-21569 board,
   resets it via GPIO, captures UART output, and returns results for automated
   hardware-in-the-loop testing.
---

![](../images/cur.jpg)

In the [previous](https://embd.cc/boot-sharc-dsp-over-uart)
[two](https://embd.cc/sharc-dsp-over-qspi) articles, we compiled a "blink" test
program and started it on the ADSP-21569 eval board. When we observed the
blinking on the board, this signalled success. Now we can "close the loop" by
allowing the computer to read program output from the DSP, allowing automated
testing and agentic coding.

### Python test server

The test setup splits the coding and testing between two separate computers. The
"test" machine obtains a program to test, loads the code on the ADSP-2156 eval
board, and returns the results back to the "code" machine.

The REST API is delightfully simple in Python. The test machine server outline
is as follows:

```python
import os
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    <Get>
    <Post

HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
```

The class defines just two functions. The `<Get>` function selects one of the
files at random from the `inputs/` directory, moves it to `done/`, and sends it
to the remote client. (Return 204 if there's no more test files.)

```python
def do_GET(self):
    names = os.listdir("inputs")
    if not names:
        self.send_response(204)
        self.end_headers()
        return
    name = random.choice(names)
    src = os.path.join("inputs", name)
    data = open(src, "rb").read()
    os.rename(src, os.path.join("done", name))
    self.send_response(200)
    self.end_headers()
    self.wfile.write(data)
```

When the client returns the response, the server just writes it to a filename
determine by the POST endpoint:

```python
def do_POST(self):
    digest = self.path.rsplit("/", 1)[-1]
    n = int(self.headers["Content-Length"])
    with open(os.path.join("outputs", f"{digest}.txt"), "wb") as f:
        f.write(self.rfile.read(n))
    self.send_response(200)
    self.end_headers()
```

On the client side, we likewise need two function. On to get the next load
stream to test:

```python
def get_job(port=8080):
    r = urllib.request.urlopen(f"http://localhost:{port}")
    if r.status == 204:
        return None
    return r.read()
```

And another to submit the response:

```python
def post_resp(ldr, msg, port=8080):
    sha = hashlib.sha256(ldr).hexdigest()
    urllib.request.urlopen(urllib.request.Request(
        f"http://localhost:{port}/{sha}",
        data = msg.encode(),
        method = "POST"
    )).read()
```

For continuous testing/developement use, the client can repeatedly poll for new
jobs. If a job exists, the client tests it and immediately requests a new one.
If there's no more jobs, then the client just polls again in a few seconds or
minutes.

### DSP reset via USB

Blink, as many other programs, runs forever, making it impossible to load any
other program without a hard reset. No obvious "reset over USB" mechanism stands
out to me in the EV-SOMCRR-EZLITE and EV-21569-SOM schematic diagrams.

However, the EZLITE board comes with three LEDs connected to the GPIO expander
that are entirely decorative: DS6, DS7, DS8. We can repurpose one of these (I
chose DS8) to reset the whole board by connecting R172 (expander side) to the S3
RESET pushbutton. Then blinking that LED results in a whole board reset,
allowing us to "re-flash" with new firmware.

### Printf to UART0

To close the loop entirely, the programs should produce some output. If they
print to UART0, then the Python "poller" can capture the output and send it back
via `post_resp()`. Simple, but powerful!

### Conclusion

The point of this exercise is to allow coding agents to test their output on
real hardware without compromising the computer the hardware is connected to.
Thus a single computer could control multiple boards and equipment without
risking inteference between the agents associated with different hardware. Each
set of agents can be separately boxed and run with all permissions granted,
while essentially powerless to escape the confinement.

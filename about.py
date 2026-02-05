#!/usr/bin/env python3
import datetime
import os
import sys
import time

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="author" content="Jakob Kastelic">
<meta name="date" content="{date}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="">
<link rel="stylesheet" href="style.css">
<title>About</title>
</head>
<header class="site-banner">
<div class="logo">
<a href="http://embd.cc"><img src="favicon.ico" alt="logo">embd.cc : About</a>
</div>
<nav class="site-nav">
<a href="archive">Archive</a>
<a href="about">About</a>
</nav>
</header>
<body>
<p>Articles on embedded Linux, STM32 development, low-level programming, and
practical approaches to software productivity. Tutorials, experiments, and
reflections on simplicity in computing.</p>
<p>Contact me at <a href="mailto:contact@embd.cc">contact@embd.cc</a></p>

<pre style="font-family: monospace; margin-top: 3em;">
{uptime_info}
</pre>

<footer class="license-footer">
<p>Content licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
</p>
</footer>

</body>
</html>
"""

def format_uptime():
    """Return full date, time, uptime, and load averages in terminal style."""
    now = datetime.datetime.now()
    # Full date and time
    datetime_str = now.strftime("%a %d %b %Y %H:%M:%S")

    # Uptime
    try:
        with open("/proc/uptime", "r") as f:
            seconds = float(f.readline().split()[0])
        mins, sec = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)

        up_parts = []
        if days:
            up_parts.append(f"{days} days")
        if hours:
            up_parts.append(f"{hours}h")
        if mins:
            up_parts.append(f"{mins} min")
        uptime_str = ", ".join(up_parts) if up_parts else "0 min"
    except FileNotFoundError:
        uptime_str = "uptime unavailable"

    # Load averages
    try:
        load_str = ", ".join(f"{x:.2f}" for x in os.getloadavg())
    except Exception:
        load_str = "0.00, 0.00, 0.00"

    return f"{datetime_str} up {uptime_str},  load average: {load_str}"


def main():
    html = HTML_TEMPLATE.format(
        date="",
        uptime_info="",
    )

    print(html)

if __name__ == "__main__":
    main()


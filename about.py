#!/usr/bin/env python3
import datetime
import os
import sys
import time
import sqlite3

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


def get_averages(db_file):
    if not os.path.exists(db_file):
        return {}

    # Use abbreviated keys directly
    periods = {
        'min': 119,
        'hr': 3600,
        'd': 86400,
        'week': 7*86400,
        'month': 30*86400,
        'yr': 365*86400
    }

    now = int(time.time())
    averages = {}

    # Open the database in read-only mode
    uri = f'file:{db_file}?mode=ro'
    with sqlite3.connect(uri, uri=True) as con:
        cur = con.cursor()
        for name, seconds in periods.items():
            start = now - seconds
            cur.execute("SELECT AVG(mc_2p5) FROM SPS30 WHERE timestamp >= ?", (start,))
            avg = cur.fetchone()[0]
            averages[name] = avg if avg is not None else float('nan')

    return averages


def main():
    now = datetime.datetime.now()
    date_str = now.strftime("%d %b %Y")
    uptime_info = format_uptime()

    db_file = sys.argv[1] if len(sys.argv) > 1 else 'room.db'
    avgs = get_averages(db_file)
    if avgs:
        parts = [f"{k} = {v:.2f}" for k, v in avgs.items()]
        uptime_info += "\n\nPM2.5: " + ", ".join(parts)

    html = HTML_TEMPLATE.format(
        date="",#date_str,
        uptime_info="",#uptime_info
    )

    print(html)

if __name__ == "__main__":
    main()


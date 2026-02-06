#!/usr/bin/env python3

from datetime import date

projects = [
    (
        "Buildroot",
        "Linux as TF-A BL33 on Qemu",
        [
            ("17/09/2025", [
                ("Sub",  "https://lists.buildroot.org/pipermail/buildroot/2025-September/786597.html"),
            ]),
            ("02/03/2026", [
                ("Resp", "https://lists.buildroot.org/pipermail/buildroot/2026-February/796037.html"),
            ]),
            ("02/04/2026", [
                ("Sub",  "https://lists.buildroot.org/pipermail/buildroot/2026-February/796454.html"),
            ]),
        ],
    ),
    (
        "Buildroot",
        "STM32MP135 Without U-Boot",
        [
            ("19/12/2024", [
                ("Sub",  "https://lists.buildroot.org/pipermail/buildroot/2024-December/769250.html"),
            ]),
            ("16/12/2025", [
                ("Resp", "https://lists.buildroot.org/pipermail/buildroot/2025-May/778563.html"),
            ]),
            ("17/09/2025", [
                ("Sub",  "https://lists.buildroot.org/pipermail/buildroot/2025-September/786595.html"),
                ("Sub",  "https://lists.buildroot.org/pipermail/buildroot/2025-September/786596.html"),
                ("Sub",  "https://lists.buildroot.org/pipermail/buildroot/2025-September/786597.html"),
            ]),
            ("02/04/2026", [
                ("Merge",  "https://gitlab.com/buildroot.org/buildroot/-/commit/8e4c663529d135088c78a9c7f4b59354f19d6580"),
            ]),
        ],
    ),
    (
        "sc",
        "rename cmds: left -> mleft, right -> mright",
        [
            ("8/8/2025", [
                ("Sub",  "https://github.com/n-t-roff/sc/commit/26b07f236d1b709c351981c5db5d12c54382bbc7"),
            ]),
            ("8/8/2025", [
                ("Merge",  "https://github.com/n-t-roff/sc/commit/ea7f88fa4256130ccb9ba572f05cfbd485d117b7"),
            ]),
        ],
    ),
    (
        "sc",
        "repeat search in opposite direction",
        [
            ("6/29/2025", [
                ("Sub",  "https://github.com/n-t-roff/sc/commit/08fe9431797bdfd43a8bf2a115b178e7ae898a5a"),
            ]),
            ("6/29/2025", [
                ("Merge",  "https://github.com/n-t-roff/sc/commit/54080300dab84a3b50fde797542845547a600634"),
            ]),
        ],
    ),
    (
        "mc",
        "fix ETA calculation overflow",
        [
            ("12/12/2024", [
                ("Sub/Mege",  "https://github.com/MidnightCommander/mc/issues/4613"),
            ]),
        ],
    ),
    (
        "sc",
        "fix typo in man page",
        [
            ("12/12/2024", [
                ("Sub",  "https://github.com/n-t-roff/sc/commit/5c8bea4b625b84317aec1a927cdc7d1a2c1de502"),
            ]),
            ("12/13/2026", [
                ("Merge",  "https://github.com/n-t-roff/sc/commit/c11a548fcdaddcc5ef005fc409f9826feca28223"),
            ]),
        ],
    ),
    (
        "sc",
        "fix typos in man page",
        [
            ("8/15/2024", [
                ("Sub",  "https://github.com/n-t-roff/sc/commit/3d15ac8fdcd19bf2d21b47603cafc2263387ed3c"),
            ]),
            ("8/15/2024", [
                ("Merge",  "https://github.com/n-t-roff/sc/commit/e029bc0fb5fa29da1fd23b04fa2a97039a96d2ba"),
            ]),
        ],
    ),
]

today = date.today().isoformat()

print(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="author" content="Jakob Kastelic">
<meta name="date" content="{today}">
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
<h3>Contact</h3>
<p>Send an email here: <a href="mailto:contact@embd.cc">contact@embd.cc</a></p>
<h3>Patches</h3>

<table>
  <thead>
    <tr>
      <th>Date</th>
      <th>Project</th>
      <th>Description</th>
      <th>Link(s)</th>
    </tr>
  </thead>
  <tbody>""")

for project, desc, rows in projects:
    first = True
    for date_, links in rows:
        print("    <tr>")
        print(f"      <td>{date_}</td>")
        if first:
            print(f"      <td>{project}</td>")
            print(f"      <td>{desc}</td>")
            first = False
        else:
            print("      <td></td>")
            print("      <td></td>")

        print(
            "      <td>"
            + " ".join(f'<a href="{url}">{label}</a>' for label, url in links)
            + "</td>"
        )
        print("    </tr>")

print("""  </tbody>
</table>

<footer class="license-footer">
<p>Content licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
</p>
</footer>
</body>
</html>""")


#!/usr/bin/env python3
import re, subprocess

out = subprocess.check_output(["claude", "-p", "/usage"], text=True)
pct = re.search(r"^Current session:\s+([\d.]+)% used", out, re.M).group(1)

print(float(pct) / 100)

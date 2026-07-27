"""Drop the dead-channel banner from the overview.

The channel cards already carry a TERMINATED / NOT FOUND / INDEXING badge, so the
banner at the top of the page was saying the same thing twice and greeted every app
launch with a red block. The badges stay; only the banner and its start-up toast go.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")

t = SRC.read_text(encoding="utf-8")
before = len(t)

# 1. the call site in overview()
CALL = "  $(\"#page\").innerHTML=`\n    ${deadAlert()}\n"
assert t.count(CALL) == 1, f"call site not found once ({t.count(CALL)})"
t = t.replace(CALL, "  $(\"#page\").innerHTML=`\n")

# 2. the function itself — from "function deadAlert(){" to the line before statCard
start = t.index("function deadAlert(){")
end = t.index("function statCard(", start)
removed = t[start:end]
assert "terminated by YouTube" in removed and len(removed) < 1400, "unexpected span"
t = t[:start] + t[end:]

# 3. the toast fired on the first probe
TOAST = ('  const gone=ST.channels.filter(c=>c.probe?.status==="terminated");\n'
         '  if(gone.length) toast(`<b>${gone.map(c=>c.label).join(", ")}</b> '
         'terminated by YouTube`,"r");\n')
assert t.count(TOAST) == 1, f"toast not found once ({t.count(TOAST)})"
t = t.replace(TOAST, "")

assert "deadAlert" not in t, "a deadAlert reference survived"
assert 'c.probe?.status==="terminated"?"TERMINATED"' in t or "TERMINATED" in t, \
    "the per-channel badge must stay"

SRC.write_text(t, encoding="utf-8")
print(f"{before:,} -> {len(t):,} chars  (-{before - len(t)})")
print("badge occurrences kept:", t.count("TERMINATED"))

"""Drop the build's "gone alert" injection.

It extended deadAlert(), which no longer exists — the overview banner was removed in
favour of the per-channel badges. The matching "gone card" badge injection stays,
since that is what now carries the information.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = Path(r"C:\Users\Zahid\projects\channel-portal\build.py")

t = P.read_text(encoding="utf-8")
start = t.index("t = sub(t,\n    '  if(term.length) bits.push(")
end = t.index('"gone alert")', start) + len('"gone alert")\n')
removed = t[start:end]
assert "gone alert" in removed and len(removed) < 900, f"unexpected span ({len(removed)})"

t = t[:start] + t[end:]
assert "gone alert" not in t
assert '"gone card")' in t, "the badge injection must stay"
P.write_text(t, encoding="utf-8")
print(f"removed {len(removed)} chars from build.py")

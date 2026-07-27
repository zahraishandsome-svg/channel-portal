"""Stop the breadcrumb from running underneath the toolbar buttons on a phone.

.crumb is a flex row with min-width:0 but its children never shrink, so at phone
widths "Overview - 7 channels" overflowed and rendered behind the search pill.
Ellipsise it, and drop the "Ctrl K" hint — a phone has no Ctrl key and it was eating
50px of a very tight row.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")
MARK = "/* narrow toolbar */"

BLOCK = """
@media(max-width:1000px){
  /* narrow toolbar */
  .crumb{flex:0 1 auto;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;display:block}
  .crumb>*{display:inline}
  .tbar .kbd{display:none}
  .tbar .btn{flex-shrink:0}
}
"""

t = SRC.read_text(encoding="utf-8")
if MARK in t:
    t = re.sub(r"\n@media\(max-width:1000px\)\{\n  " + re.escape(MARK) + r".*?\n\}", "", t, flags=re.S)

anchor = "\n</style>"
assert t.count(anchor) == 1
assert ".crumb{font-size:14px" in t, "crumb rule moved"
t = t.replace(anchor, "\n" + BLOCK.strip() + anchor)
SRC.write_text(t, encoding="utf-8")
print(f"patched: {len(t):,} chars")

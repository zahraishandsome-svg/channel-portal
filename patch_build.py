"""Drop the two safe-area injections from build.py.

Both wrote a padding-top / padding shorthand EARLIER in the sheet than the rules that
reset it, so neither ever took effect on a phone. The source stylesheet now carries a
proper safe-area block as its last rules, which the build inherits for free.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
P = Path(r"C:\Users\Zahid\projects\channel-portal\build.py")

OLD = '''t = sub(t, ".tbar{position:sticky;top:0;z-index:40;",
           ".tbar{position:sticky;top:0;z-index:40;padding-top:max(12px,env(safe-area-inset-top));",
        "tbar safe-area")
t = sub(t, ".page{padding:22px 24px 80px;max-width:1400px;width:100%}",
           ".page{padding:22px 24px calc(80px + env(safe-area-inset-bottom));max-width:1400px;width:100%}",
        "page safe-area")

'''

NEW = '''# Safe-area insets are not patched in here: they live at the END of the source
# stylesheet, because the mobile media query re-sets .tbar's padding shorthand and
# would wipe out anything injected further up.

'''

t = P.read_text(encoding="utf-8")
assert t.count(OLD) == 1, f"injection block not found exactly once ({t.count(OLD)})"
P.write_text(t.replace(OLD, NEW), encoding="utf-8")
print("build.py cleaned")

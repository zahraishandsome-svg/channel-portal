"""Give the toolbar, drawer and page real safe-area insets.

The base rules set `padding` with the shorthand, and the mobile media query sets it
AGAIN (`.tbar{padding:11px 15px}`), so any padding-top written earlier in the sheet is
wiped out. On a Dynamic Island iPhone that left the toolbar buttons underneath the
island. These rules go last in the stylesheet so nothing can override them.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = Path(r"C:\Users\Zahid\YT-Dashboard\dashboard.html")
MARK = "/* safe area — must stay last */"

BLOCK = """
/* safe area — must stay last */
/* The toolbar is sticky at the very top of the viewport and the web app runs
   edge-to-edge (viewport-fit=cover), so on a notch/Dynamic Island phone its
   buttons land underneath the island unless the inset is added here, after every
   padding shorthand that would otherwise reset it. */
.tbar{padding-top:calc(12px + env(safe-area-inset-top,0px));
      padding-left:calc(24px + env(safe-area-inset-left,0px));
      padding-right:calc(24px + env(safe-area-inset-right,0px))}
.sb-head{padding-top:calc(18px + env(safe-area-inset-top,0px))}
.sb{padding-left:env(safe-area-inset-left,0px)}
.page{padding-bottom:calc(80px + env(safe-area-inset-bottom,0px))}
.ovl{padding-top:calc(26px + env(safe-area-inset-top,0px));
     padding-bottom:calc(26px + env(safe-area-inset-bottom,0px))}
.toasts{padding-bottom:env(safe-area-inset-bottom,0px)}
@media(max-width:1000px){
  .tbar{padding-top:calc(11px + env(safe-area-inset-top,0px));
        padding-left:calc(15px + env(safe-area-inset-left,0px));
        padding-right:calc(15px + env(safe-area-inset-right,0px))}
  .page{padding-left:calc(15px + env(safe-area-inset-left,0px));
        padding-right:calc(15px + env(safe-area-inset-right,0px))}
  /* fingers, not cursors */
  .tbar .btn{min-height:40px;padding-left:13px;padding-right:13px}
  .tbar .btn svg{width:19px;height:19px}
  .hamb{min-width:42px;justify-content:center}
}
"""


def main():
    t = SRC.read_text(encoding="utf-8")
    if MARK in t:                      # idempotent: replace the previous block
        t = re.sub(re.escape(MARK) + r".*?(?=\n</style>)", "", t, flags=re.S)
        t = t.replace("\n\n</style>", "\n</style>")

    anchor = "\n</style>"
    assert t.count(anchor) == 1, f"expected one </style>, found {t.count(anchor)}"
    t = t.replace(anchor, "\n" + BLOCK.strip() + anchor)

    # the shorthands this block is here to survive must still be where we think
    for must in [".tbar{padding:11px 15px}", ".tbar{position:sticky"]:
        assert must in t, f"missing anchor: {must}"

    SRC.write_text(t, encoding="utf-8")
    print(f"patched {SRC.name}: {len(t):,} chars")
    print("safe-area rules:", t.count("safe-area-inset"))


main()

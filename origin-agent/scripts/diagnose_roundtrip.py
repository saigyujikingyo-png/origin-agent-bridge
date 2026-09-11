import sys
from pathlib import Path

import originpro as op

path = Path(sys.argv[1]).resolve()
print("input", path.is_file(), path.stat().st_size, flush=True)
try:
    op.set_show(False)
    op.new()
    print("load", op.open(str(path)), flush=True)
    for page in op.pages():
        print("page", page.name, type(page).__name__, flush=True)
    for name in ["Book1", "Book2", "Book3", "Book4"]:
        sheet = op.find_sheet("w", "[" + name + "]Sheet1")
        if sheet:
            print("data", name, [(i, sheet.to_list(i)[:8]) for i in range(min(4, sheet.cols))], flush=True)
finally:
    op.exit()

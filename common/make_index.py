"""Write page/index.html for a codelab: python common/make_index.py <codelab_dir> "<title>" """
import sys
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <link rel="stylesheet" href="/common/genui.css">
</head>
<body>
  <script type="module" src="./app.mjs"></script>
</body>
</html>
"""

if __name__ == "__main__":
    target = Path(sys.argv[1]) / "page" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(TEMPLATE.format(title=sys.argv[2]), encoding="utf-8")
    print("wrote", target)

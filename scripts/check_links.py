"""检查仓库内 markdown 文件的相对链接是否指向真实存在的文件。

仅检查相对路径链接（./ ../ 或无协议路径），外部 URL 不联网验证。
锚点（#...）只校验文件存在，不校验标题锚点。
退出码：有死链时为 1。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def main() -> int:
    broken: list[str] = []
    checked = 0
    for md in sorted(ROOT.rglob("*.md")):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(text):
            target = m.group(1).split()[0].strip("<>")
            if target.startswith(SKIP_PREFIXES):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            checked += 1
            resolved = (md.parent / path_part).resolve()
            if not resolved.exists():
                broken.append(f"{md.relative_to(ROOT)}: {target}")
    print(f"共检查 {checked} 个相对链接")
    if broken:
        print(f"\n发现 {len(broken)} 个死链：")
        for b in broken:
            print(f"  FAIL {b}")
        return 1
    print("未发现死链 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

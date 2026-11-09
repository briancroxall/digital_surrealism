"""Copy the Image maker (web/) for publishing, with a version on its code files.

    python3 tools/stamp_version.py web _site 622036b

Every reference to one of the page's own scripts ("./worker.js",
"./summing.js", ...) gets "?v=<version>" added. Browsers treat a new address
as a new file, so after an update they can't combine a saved copy of an old
script with the new ones (see README, "Browsers caching old code").

Stops with an error, publishing nothing, if any reference is left unstamped.
Uses only the standard library, so GitHub's runner can run it with plain python3.
"""

import re
import shutil
import sys
from pathlib import Path

# "./name.js" or './name.js', as in imports and new Worker(...).
SCRIPT_REF = re.compile(r"""(["'])\./([\w-]+\.js)\1""")


def stamp(source: Path, out: Path, version: str) -> int:
    """Copy source to out, stamping script references. Return how many."""
    if out.exists():
        raise SystemExit(f"{out} already exists. Remove it or choose another folder.")
    shutil.copytree(source, out)
    scripts = {path.name for path in out.glob("*.js")}
    count = 0
    for path in sorted(out.glob("*.html")) + sorted(out.glob("*.js")):
        text = path.read_text(encoding="utf-8")

        def add_version(match: re.Match) -> str:
            nonlocal count
            quote, name = match.groups()
            if name not in scripts:
                raise SystemExit(f"{path.name} refers to ./{name}, which isn't in {source}.")
            count += 1
            return f"{quote}./{name}?v={version}{quote}"

        path.write_text(SCRIPT_REF.sub(add_version, text), encoding="utf-8")

    # Check: no script reference left without a version.
    for path in out.glob("*"):
        if path.suffix in (".html", ".js"):
            text = path.read_text(encoding="utf-8")
            left = re.findall(r"""["']\.?/?[\w-]+\.js["']""", text)
            if left:
                raise SystemExit(f"Unstamped script reference in {path.name}: {left}")
    return count


def main() -> None:
    source, out, version = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    if not re.fullmatch(r"[\w.-]+", version):
        raise SystemExit(f"Unexpected version {version!r}.")
    count = stamp(source, out, version)
    print(f"Stamped {count} script references with v={version} in {out}.")


if __name__ == "__main__":
    main()

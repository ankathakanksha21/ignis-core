import argparse
import sys

from . import build, check, write


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.ingest", description="Rebuild data/processed/ from data/raw/.")
    parser.add_argument("--check", action="store_true", help="do not write; fail if the committed files are stale")
    args = parser.parse_args()

    outputs = build()
    if args.check:
        stale = check(outputs)
        if stale:
            print("out of date: " + ", ".join(stale) + ". Run: python -m app.ingest", file=sys.stderr)
            return 1
        print("data/processed/ is up to date")
        return 0

    write(outputs)
    kinds = {}
    for row in outputs.rows:
        kinds[row["row_kind"]] = kinds.get(row["row_kind"], 0) + 1
    print(f"rows: {kinds}")
    print(f"condition values: {len(outputs.conditions)}")
    print(f"quality flags: {len(outputs.flags)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

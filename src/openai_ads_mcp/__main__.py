"""Entry point. Transport is stdio; stdout belongs to JSON-RPC."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from .server import mcp
    except Exception as exc:  # report configuration errors readably
        print(f"Failed to start: {exc}", file=sys.stderr)
        return 1

    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

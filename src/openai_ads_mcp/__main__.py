"""Einstiegspunkt. Transport ist stdio — stdout gehört dem JSON-RPC."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from .server import mcp
    except Exception as exc:  # Konfigurationsfehler lesbar melden
        print(f"Start fehlgeschlagen: {exc}", file=sys.stderr)
        return 1

    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Rerun the strict native visual integration gate without overwriting v028 evidence."""
from pathlib import Path
import validate_peon_polish_v028 as native

native.OUT = Path(__file__).resolve().parents[1] / 'references/generated/stability_v029/integration'
if __name__ == '__main__':
    native.main()

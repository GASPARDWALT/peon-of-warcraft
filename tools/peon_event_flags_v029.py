#!/usr/bin/env python3
"""Read native saved event IDs, including explicitly reserved v029 flags.

Older validation parsers understand only the sequential const macros. The
three fixed recruitment flags intentionally use numeric DEF EQU statements,
which must not advance that sequence. This helper does not execute assembly
expressions or infer saved indices from object order.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXED_RECRUITMENT_FLAGS = {
    "EVENT_PEON_RECRUIT_IMP1_DONE_V029": 590,
    "EVENT_PEON_RECRUIT_EARTH2_DONE_V029": 591,
    "EVENT_PEON_RECRUIT_GRUNT2_DONE_V029": 592,
}


def _literal(value):
    if value.startswith("$"):
        return int(value[1:], 16)
    if value.startswith("%"):
        return int(value[1:], 2)
    if value.startswith("&"):
        return int(value[1:], 8)
    return int(value, 10)


def event_indices(path=None):
    path = Path(path) if path else ROOT / "constants/event_flags.asm"
    result, index = {}, 0
    for line in path.read_text().splitlines():
        parts = line.split(";", 1)[0].split()
        if not parts:
            continue
        if parts[0] in ("const_def", "const_next"):
            index = _literal(parts[1]) if len(parts) > 1 else 0
        elif parts[0] == "const_skip":
            index += _literal(parts[1]) if len(parts) > 1 else 1
        elif parts[0] == "const":
            result[parts[1]] = index
            index += 1
        elif (len(parts) == 4 and parts[0] == "DEF" and parts[2] == "EQU"
              and parts[1].startswith("EVENT_")):
            try:
                value = _literal(parts[3])
            except ValueError:
                continue  # Nonliteral aliases need the assembler, not eval.
            if parts[1] in result and result[parts[1]] != value:
                raise ValueError(f"Conflicting saved event ID: {parts[1]}")
            result[parts[1]] = value
    return result


def recruitment_flag_indices(path=None):
    flags = event_indices(path)
    actual = {name: flags.get(name) for name in FIXED_RECRUITMENT_FLAGS}
    if actual != FIXED_RECRUITMENT_FLAGS:
        raise AssertionError(("Recruitment flags moved or missing", actual))
    return actual

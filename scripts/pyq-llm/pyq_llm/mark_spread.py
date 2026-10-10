"""CBSE Class XII Chemistry mark spread (mirrors src/generator.ts)."""

from __future__ import annotations

from dataclasses import dataclass

CBSE_70 = {"one": 16, "vsa": 5, "sa": 7, "case": 2, "la": 3}


@dataclass(frozen=True)
class SectionCounts:
    one: int
    vsa: int
    sa: int
    case: int
    la: int


def marks_from_counts(c: SectionCounts) -> int:
    return c.one + c.vsa * 2 + c.sa * 3 + c.case * 4 + c.la * 5


def format_spread(c: SectionCounts) -> str:
    parts: list[str] = []
    if c.one:
        parts.append(f"{c.one}×1")
    if c.vsa:
        parts.append(f"{c.vsa}×2")
    if c.sa:
        parts.append(f"{c.sa}×3")
    if c.case:
        parts.append(f"{c.case}×4")
    if c.la:
        parts.append(f"{c.la}×5")
    return " + ".join(parts)


def cbse_spread_for_total(target_marks: int) -> SectionCounts:
    target = min(70, max(1, int(round(target_marks))))
    if target == 70:
        return SectionCounts(**CBSE_70)

    ratio = target / 70
    c = SectionCounts(
        one=max(1, round(CBSE_70["one"] * ratio)),
        vsa=round(CBSE_70["vsa"] * ratio),
        sa=round(CBSE_70["sa"] * ratio),
        case=round(CBSE_70["case"] * ratio),
        la=round(CBSE_70["la"] * ratio),
    )
    steps = [
        ("one", 1),
        ("vsa", 2),
        ("sa", 3),
        ("case", 4),
        ("la", 5),
    ]

    m = marks_from_counts(c)
    guard = 0
    while m < target and guard < 200:
        guard += 1
        need = target - m
        key, cost = next(((k, co) for k, co in reversed(steps) if co <= need), steps[0])
        c = SectionCounts(
            one=c.one + (1 if key == "one" else 0),
            vsa=c.vsa + (1 if key == "vsa" else 0),
            sa=c.sa + (1 if key == "sa" else 0),
            case=c.case + (1 if key == "case" else 0),
            la=c.la + (1 if key == "la" else 0),
        )
        m += cost

    guard = 0
    while m > target and guard < 200:
        guard += 1
        over = m - target
        pick = None
        for key, cost in steps:
            val = getattr(c, key)
            if val > 0 and cost <= over:
                pick = (key, cost)
                break
        if not pick:
            for key, cost in reversed(steps):
                if getattr(c, key) > 0:
                    pick = (key, cost)
                    break
        if not pick:
            break
        key, cost = pick
        c = SectionCounts(
            one=c.one - (1 if key == "one" else 0),
            vsa=c.vsa - (1 if key == "vsa" else 0),
            sa=c.sa - (1 if key == "sa" else 0),
            case=c.case - (1 if key == "case" else 0),
            la=c.la - (1 if key == "la" else 0),
        )
        m -= cost

    return c

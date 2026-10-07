# EverlongSTK Interface Contract

Version: 0.1
Spec: specV2.md (v0.2)
Last updated: 2026-10-07

## 1. Units Policy

- Energy: Wh
- Power: W
- Data volume: bytes
- Data rate (storage/processing): bytes/s
- Data rate (radio): bits/s
- Time: seconds (simulation), ISO-8601 UTC (wall clock)
- Distance: m
- Angles: deg (config), rad (internal math — documented per function)

## 2. Module Ownership

| Module           | Owns                                        | Must not touch  |
| ---------------- | ------------------------------------------- | --------------- |
| configuration.py | parse/validate/save project JSON            | physics, SQLite |
| models.py        | shared dataclasses                          | IO, physics     |
| orbit.py         | position, sunlight, station access          | power, data     |
| policy.py        | schedule/blocks/python → Actions            | state mutation  |
| power.py         | power allocation + energy ledger (proposed) | SQLite, commit  |
| data.py          | queue/processing/link ledger (proposed)     | SQLite, commit  |
| simulation.py    | ordering, event splits, commit              | IO, GUI         |
| results.py       | SQLite read/write, CSV                      | physics         |
| lifecycle.py     | start/pause/resume/cancel                   | GUI             |

## 3. Frozen Interfaces

<!-- filled in as modules are completed -->

## 4. Invariants

- Battery energy ∈ [0, capacity] at all commits.
- Storage used ∈ [0, capacity] at all commits.
- No module mutates committed state except simulation.py.
- All rates use the unit declared above; no implicit conversion at boundaries.
- Every numeric config field carries value/unit/certainty.

## 5. Open Questions

- (append as we go)

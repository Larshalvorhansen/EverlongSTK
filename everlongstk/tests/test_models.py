"""Immutable cross-module result contracts contain no engine behavior."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from everlong_stk.models import (
    ActionRequest,
    DataLedger,
    EnvironmentSnapshot,
    IntervalResult,
    PowerLedger,
    SatelliteSnapshot,
    SimulationEvent,
)


def test_snapshot_copies_and_protects_queue_mapping():
    queue = {"raw": 12.5}
    state = SatelliteSnapshot(datetime(2027, 1, 1, tzinfo=timezone.utc),
                              0, "idle", 0, 40, queue, 0, 0)
    queue["raw"] = 100
    assert state.queue_bytes["raw"] == 12.5
    with pytest.raises(TypeError):
        state.queue_bytes["raw"] = 42
    with pytest.raises(FrozenInstanceError):
        state.state_id = "survival"


def test_ledgers_copy_all_mappings_and_interval_is_frozen():
    source = {"camera": 2.0}
    power = PowerLedger(source, {}, source, {}, -2.0, 0.0)
    source["camera"] = 9
    assert power.served_wh["camera"] == 2.0
    for name in ("requested_wh", "generated_wh", "served_wh", "curtailed_wh"):
        with pytest.raises(TypeError):
            getattr(power, name)["camera"] = 8
    queues = {"raw": 10.0}
    data = DataLedger(queues, queues, {}, {}, {}, {}, {}, queues)
    queues["raw"] = 99
    for name in data.__dataclass_fields__:
        mapping = getattr(data, name)
        assert mapping.get("raw", 0) in (0, 10)
        with pytest.raises(TypeError):
            mapping["raw"] = 1
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)
    state = SatelliteSnapshot(now, 0, "idle", 0, 40, {}, 0, 0)
    event = SimulationEvent(now, 0, "initial", "Initial snapshot")
    result = IntervalResult(state, power, data, (event,))
    with pytest.raises(FrozenInstanceError):
        result.events = ()
    assert ActionRequest(state_id="idle").processing_enabled is None
    assert EnvironmentSnapshot(now, (1, 2, 3), 0, 0, 550000, False, (), None, 0).time_utc == now

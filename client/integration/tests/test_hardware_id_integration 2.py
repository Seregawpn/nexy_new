import asyncio
import time
import sys
from pathlib import Path

# Ensure 'client' is on sys.path so we can import 'integration.*'
CLIENT_ROOT = Path(__file__).resolve().parents[2]
if str(CLIENT_ROOT) not in sys.path:
    sys.path.append(str(CLIENT_ROOT))

from integration.core.event_bus import EventBus
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler

import importlib


class FakeHardwareIdResult:
    def __init__(self, uuid="FAKE-UUID-1234", source="cache", cached=True, status_value="success"):
        self.uuid = uuid
        self.source = source
        self.cached = cached
        class _S:  # minimal enum-like
            def __init__(self, v):
                self.value = v
        self.status = _S(status_value)


class FakeHardwareIdentifier:
    def __init__(self, *args, **kwargs):
        self._info = {
            "exists": True,
            "size_bytes": 64,
            "created_at": str(time.time()),
            "modified_at": str(time.time()),
            "ttl_remaining": 9999,
            "is_valid": True,
        }

    def get_hardware_id(self, force_regenerate: bool = False):
        return FakeHardwareIdResult()

    def get_cache_info(self):
        return self._info


async def main():
    # Lazy import module to patch its symbol before class instantiation
    hi_mod = importlib.import_module("integration.integrations.hardware_id_integration")

    # Patch HardwareIdentifier used inside integration to fake
    hi_mod.HardwareIdentifier = FakeHardwareIdentifier

    event_bus = EventBus()
    state_manager = ApplicationStateManager()
    error_handler = ErrorHandler(event_bus)

    # Create integration
    HardwareIdIntegration = getattr(hi_mod, "HardwareIdIntegration")
    integration = HardwareIdIntegration(event_bus, state_manager, error_handler, config=None)

    obtained_events = []
    responses = []

    async def on_obtained(event):
        obtained_events.append(event.get("data", {}))

    async def on_response(event):
        responses.append(event.get("data", {}))

    await event_bus.subscribe("hardware.id_obtained", on_obtained)
    await event_bus.subscribe("hardware.id_response", on_response)

    # Init/start integration
    assert await integration.initialize() is True
    assert await integration.start() is True

    # Trigger app.startup to fetch and publish ID
    await event_bus.publish("app.startup", {"test": True})

    # Wait a bit for async handlers
    await asyncio.sleep(0.1)
    assert len(obtained_events) >= 1, "No hardware.id_obtained received"
    assert obtained_events[-1].get("uuid") == "FAKE-UUID-1234"

    # Request ID explicitly and expect response
    req_id = "req-1"
    await event_bus.publish("hardware.id_request", {"request_id": req_id, "wait_ready": True})
    await asyncio.sleep(0.05)
    assert len(responses) >= 1, "No hardware.id_response received"
    assert responses[-1].get("request_id") == req_id
    assert responses[-1].get("uuid") == "FAKE-UUID-1234"

    print("OK: HardwareIdIntegration basic flow works with fake identifier.")


if __name__ == "__main__":
    asyncio.run(main())

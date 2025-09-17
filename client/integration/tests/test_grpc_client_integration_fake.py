import asyncio
import sys
from pathlib import Path
import os

# Ensure 'client' root on path
CLIENT_ROOT = Path(__file__).resolve().parents[2]
if str(CLIENT_ROOT) not in sys.path:
    sys.path.append(str(CLIENT_ROOT))

from integration.core.event_bus import EventBus
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler

import importlib
import tempfile


class FakeAudioChunk:
    def __init__(self, data: bytes, dtype: str = 'int16', shape=None):
        self.audio_data = data
        self.dtype = dtype
        self.shape = shape or [len(data)]


class FakeGrpcClient:
    def __init__(self, *args, **kwargs):
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, *args, **kwargs) -> bool:
        self._connected = True
        return True

    async def cleanup(self):
        self._connected = False

    async def stream_audio(self, prompt: str, screenshot_base64: str, screen_info: dict, hardware_id: str):
        class Resp:
            def __init__(self, text_chunk=None, audio_chunk=None, end_message=None, error_message=None):
                self.text_chunk = text_chunk
                self.audio_chunk = audio_chunk
                self.end_message = end_message
                self.error_message = error_message

        # Simulate small stream: text -> audio -> end
        yield Resp(text_chunk=f"Echo: {prompt}")
        yield Resp(audio_chunk=FakeAudioChunk(b"\x00\x01\x02\x03", dtype='int16', shape=[4]))
        yield Resp(end_message="done")


async def main():
    # Patch integration to use FakeGrpcClient
    integ_mod = importlib.import_module("integration.integrations.grpc_client_integration")
    integ_mod.GrpcClient = FakeGrpcClient

    # Create core
    bus = EventBus()
    state = ApplicationStateManager()
    err = ErrorHandler(bus)

    # Prepare integration
    GrpcClientIntegration = getattr(integ_mod, "GrpcClientIntegration")
    grpc_integration = GrpcClientIntegration(bus, state, err, config=None)

    # Capture published events
    events = {"started": [], "text": [], "audio": [], "done": [], "failed": []}

    async def on_started(e):
        events["started"].append(e.get("data", {}))

    async def on_text(e):
        events["text"].append(e.get("data", {}))

    async def on_audio(e):
        events["audio"].append(e.get("data", {}))

    async def on_done(e):
        events["done"].append(e.get("data", {}))

    async def on_failed(e):
        events["failed"].append(e.get("data", {}))

    await bus.subscribe("grpc.request_started", on_started)
    await bus.subscribe("grpc.response.text", on_text)
    await bus.subscribe("grpc.response.audio", on_audio)
    await bus.subscribe("grpc.request_completed", on_done)
    await bus.subscribe("grpc.request_failed", on_failed)

    # Init/start integration
    assert await grpc_integration.initialize() is True
    assert await grpc_integration.start() is True

    # Seed hardware id and network status
    await bus.publish("hardware.id_obtained", {"uuid": "FAKE-HWID-0001"})
    await bus.publish("network.status_changed", {"new": "connected"})

    # Prepare temp screenshot
    tmp_dir = Path(tempfile.gettempdir()) / "nexy_test"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    shot_path = tmp_dir / "shot_test.jpg"
    shot_path.write_bytes(b"fakejpegdata")

    session_id = 1234.5

    # Publish text and screenshot events
    await bus.publish("voice.recognition_completed", {"session_id": session_id, "text": "open mail"})
    await bus.publish("screenshot.captured", {"session_id": session_id, "image_path": str(shot_path), "width": 100, "height": 50})

    # Allow time for async work
    await asyncio.sleep(0.5)

    # Assertions
    assert events["started"], "No grpc.request_started"
    assert events["text"], "No grpc.response.text"
    assert events["audio"], "No grpc.response.audio"
    assert events["done"], "No grpc.request_completed"
    assert not events["failed"], f"Unexpected failure events: {events['failed']}"

    print("OK: GrpcClientIntegration fake stream end-to-end passed.")


if __name__ == "__main__":
    asyncio.run(main())


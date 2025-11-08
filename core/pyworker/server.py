#!/usr/bin/env python3
import argparse
import asyncio
import logging
import signal
import time
from typing import Optional

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

# Adjust these imports to match where your generated code lands
from protobufs.gen.py.protobufs.apis.services import pyworker_api_pb2 as pb
from protobufs.gen.py.protobufs.apis.services import pyworker_api_pb2_grpc as rpc


# ---------------------------
# Simple TTS queue (no overlap)
# ---------------------------

class TTSQueue:
    """
    Serializes speech so multiple SPEAK tasks don't overlap.
    Replace _speak_impl() with Piper/Coqui/etc. later.
    """
    def __init__(self) -> None:
        self._q: asyncio.Queue[pb.SpeakArgs] = asyncio.Queue()
        self._worker: Optional[asyncio.Task] = None
        self._log = logging.getLogger("TTSQueue")

    async def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None

    async def enqueue(self, speak_args: pb.SpeakArgs) -> None:
        await self._q.put(speak_args)

    async def _run(self) -> None:
        self._log.info("TTS worker started")
        while True:
            args: pb.SpeakArgs = await self._q.get()
            try:
                await self._speak_impl(args)
            except Exception as e:
                self._log.exception("TTS failed: %s", e)

    async def _speak_impl(self, args: pb.SpeakArgs) -> None:
        # DEV placeholder: synchronous print simulates speech latency.
        # Swap with Piper/Coqui wrapper later.
        self._log.info("[TTS]%s%s", f"({args.voice_id}) " if args.voice_id else "", args.text)
        # Simulate short blocking while speaking long phrases (optional)
        await asyncio.sleep(min(0.1 + len(args.text) / 80.0, 2.0))


# ---------------------------
# Idempotency (simple in-mem)
# ---------------------------

class IdempotencyCache:
    """
    Very simple in-memory idempotency cache.
    Stores keys for 'ttl_sec' seconds; purges opportunistically.
    """
    def __init__(self, ttl_sec: float = 300.0) -> None:
        self._seen: dict[str, float] = {}
        self._ttl = ttl_sec

    def check_and_mark(self, key: Optional[str]) -> bool:
        """
        Returns True if this key was seen recently (duplicate),
        otherwise records it and returns False.
        """
        if not key:
            return False
        now = time.monotonic()
        # purge old
        dead = [k for k, ts in self._seen.items() if now - ts > self._ttl]
        for k in dead:
            del self._seen[k]

        if key in self._seen:
            return True
        self._seen[key] = now
        return False


# ---------------------------
# gRPC service implementation
# ---------------------------

class PythonWorkerService(rpc.PythonWorkerServiceServicer):
    def __init__(self, tts: TTSQueue, idem: IdempotencyCache) -> None:
        self._tts = tts
        self._idem = idem
        self._log = logging.getLogger("PythonWorkerService")

    async def RunTask(self, request: pb.RunTaskRequest, context: grpc.aio.ServicerContext) -> pb.RunTaskResponse:
        call: pb.ToolCall = request.call

        # Idempotency: ignore exact duplicates if an idempotency_key is set
        if self._idem.check_and_mark(call.idempotency_key):
            return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_OK)

        # Route by oneof (tool type)
        which = call.WhichOneof("payload")
        try:
            if which == "speak":
                await self._handle_speak(call.speak)
                return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_OK)

            elif which == "play_sound":
                await self._handle_play_sound(call.play_sound)
                return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_OK)

            elif which == "timer":
                # By design, timers are typically handled by the Go scheduler.
                # If one lands here, we can reject or no-op.
                msg = "Timer tool is not handled by Python worker (routed to Go)."
                self._log.warning(msg)
                return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_FAILED, error_message=msg)

            else:
                err = f"Unsupported tool call type: {which or 'None'}"
                self._log.error(err)
                return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_FAILED, error_message=err)

        except Exception as e:
            self._log.exception("RunTask failed")
            return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_FAILED, error_message=str(e))

    # ---- Tool handlers ----

    async def _handle_speak(self, args: pb.SpeakArgs) -> None:
        await self._tts.enqueue(args)

    async def _handle_play_sound(self, args: pb.PlaySoundArgs) -> None:
        # DEV: simple placeholder; integrate an audio player later.
        txt = f"[SOUND] id={args.sound_id or 'ding'} repeat={args.repeat or 1}"
        await self._tts.enqueue(pb.SpeakArgs(text=txt))  # Reuse TTS queue to announce action.


# ---------------------------
# Server bootstrap
# ---------------------------

async def serve(host: str, port: int) -> None:
    server = grpc.aio.server(options=[
        ("grpc.max_send_message_length", 32 * 1024 * 1024),
        ("grpc.max_receive_message_length", 32 * 1024 * 1024),
    ])

    # Health service
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=None,
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    # App services
    tts = TTSQueue()
    await tts.start()
    idem = IdempotencyCache(ttl_sec=300.0)
    worker = PythonWorkerService(tts, idem)
    rpc.add_PythonWorkerServiceServicer_to_server(worker, server)

    bind_addr = f"{host}:{port}"
    server.add_insecure_port(bind_addr)  # For LAN/dev; prefer mTLS in prod
    logging.getLogger("server").info("PythonWorkerService listening on %s", bind_addr)

    # Mark healthy after registration
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("grpc.health.v1.Health", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("assistant.v1.PythonWorkerService", health_pb2.HealthCheckResponse.SERVING)

    await server.start()

    # Graceful shutdown signals
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass  # Windows

    await stop_event.wait()
    logging.getLogger("server").info("Shutting down...")

    # Health: not serving
    health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
    health_servicer.set("assistant.v1.PythonWorkerService", health_pb2.HealthCheckResponse.NOT_SERVING)

    await server.stop(grace=None)  # allow in-flight RPCs to finish
    await tts.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="PythonWorkerService (assistant.v1)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(serve(args.host, args.port))


if __name__ == "__main__":
    main()

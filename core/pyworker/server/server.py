#!/usr/bin/env python3
import asyncio
import logging
from typing import Optional

import grpc

import protobufs.gen.py.protobufs.apis.services.pyserver_api_pb2 as pb
import protobufs.gen.py.protobufs.apis.services.pyserver_api_pb2_grpc as rpc
import protobufs.gen.py.protobufs.apis.models.task_pb2 as models_pb


# ---------------------------
# Simple TTS queue (no overlap)
# ---------------------------

class TTSQueue:
    """
    Serializes speech so multiple SPEAK tasks don't overlap.
    Replace _speak_impl() with Piper/Coqui/etc. later.
    """
    def __init__(self) -> None:
        self._q: asyncio.Queue[models_pb.SpeakArgs] = asyncio.Queue()
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

    async def enqueue(self, speak_args: models_pb.SpeakArgs) -> None:
        await self._q.put(speak_args)

    async def _run(self) -> None:
        self._log.info("TTS worker started")
        while True:
            args: models_pb.SpeakArgs = await self._q.get()
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
# gRPC service implementation
# ---------------------------

class PythonWorkerService(rpc.PythonWorkerServiceServicer):
    def __init__(self, tts: TTSQueue) -> None:
        self._tts = tts
        self._log = logging.getLogger("PythonWorkerService")

    async def RunTask(self, request: pb.RunTaskRequest, context: grpc.aio.ServicerContext) -> pb.RunTaskResponse:
        call: models_pb.ToolCall = request.call

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
                # By design, timers are handled by the Go scheduler.
                # If one lands here we no-op.
                msg = "Timer tool is not handled by the Python worker (routed to Go)."
                self._log.warning(msg)
                return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_UNSPECIFIED, error_message=msg)

            else:
                err = f"Unsupported tool call type: {which or 'None'}"
                self._log.error(err)
                return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_FAILED, error_message=err)

        except Exception as e:
            self._log.exception("RunTask failed")
            return pb.RunTaskResponse(status=pb.RunTaskResponse.STATUS_FAILED, error_message=str(e))

    # ---- Tool handlers ----

    async def _handle_speak(self, args: models_pb.SpeakArgs) -> None:
        await self._tts.enqueue(args)

    async def _handle_play_sound(self, args: models_pb.PlaySoundArgs) -> None:
        # DEV: simple placeholder; integrate an audio player later.
        txt = f"[SOUND] id={args.sound_id or 'ding'} repeat={args.repeat or 1}"
        await self._tts.enqueue(models_pb.SpeakArgs(text=txt))  # Reuse TTS queue to announce action.


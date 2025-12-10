from __future__ import annotations

import asyncio
import enum
import logging
from dataclasses import dataclass
from typing import Optional, Protocol, Tuple, Sequence

# ==== bring your own generated stubs / client / models ====
# Adjust these imports to your repo layout:
# from llm_exec.scheduler_client import SchedulerClient
# from models.plan import PlanModel, ActionModel, ToolCallModel, Priority
# If you haven’t created them as modules yet, paste the small client from earlier.

# Minimal stand-ins so this file is self-contained for now:
class Priority:  # replace with your Enum
    PRIORITY_NORMAL = "PRIORITY_NORMAL"

@dataclass
class ActionModel:
    tool: str
    args: dict
    when: Optional[str] = "now"

@dataclass
class PlanModel:
    actions: list[ActionModel]

class ToolCallModel:
    @staticmethod
    def from_action(tool: str, args: dict) -> "ToolCallModel":
        o = ToolCallModel()
        o.tool = tool
        o.args = args
        return o


class SchedulerClient:
    def __init__(self, address: str, secure: bool = False):
        self.addr = address
        self.secure = secure
        self._started = False

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def start(self):
        self._started = True

    async def close(self):
        self._started = False

    async def schedule_toolcall(self, call: ToolCallModel, *, when="now", priority=Priority.PRIORITY_NORMAL,
                                timezone="Asia/Nicosia", meta=None, task_id=None):
        # Replace with real gRPC call. For now, log.
        logging.getLogger("sched").info("Schedule: tool=%s args=%s when=%s", getattr(call, "tool", "?"), getattr(call, "args", {}), when)
        class Resp: pass
        r = Resp(); r.task_id = "demo-task-id"
        return r
# ==== end minimal stand-ins ====


# ===============================
#           Interfaces
# ===============================

# Raw audio “frames” are opaque here; your concrete impls pick the type (e.g., bytes of PCM16).
AudioFrame = bytes

class WakeDetector(Protocol):
    async def wait_for_hotword(self) -> None:
        """Block until a wake word is detected."""


class VAD(Protocol):
    async def stream_until_eou(self, pre_roll: Sequence[AudioFrame]) -> Sequence[AudioFrame]:
        """
        Consume live audio and return frames covering the utterance,
        including the given pre_roll (small ring buffer captured while idle).
        """


class ASR(Protocol):
    async def transcribe(self, frames: Sequence[AudioFrame]) -> Tuple[str, float]:
        """Return (transcript, confidence in [0,1])."""


class Planner(Protocol):
    async def plan(self, transcript: str, summary_hint: Optional[str] = None) -> PlanModel:
        """Return a plan with actions based on transcript."""


# ===============================
#     Mock implementations
# ===============================

class MockWakeDetector:
    """
    Press ENTER to simulate the wake word.
    Replace with Porcupine/Precise/KWS engine later.
    """
    async def wait_for_hotword(self) -> None:
        print("\n[Wake] Press ENTER to wake…", flush=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input)  # blocks in thread pool


class MockVAD:
    """
    No real audio; just returns a token indicating “frames”.
    Replace with Silero VAD or WebRTC VAD + mic streaming.
    """
    def __init__(self, preroll_ms: int = 2000):
        self.preroll_ms = preroll_ms

    async def stream_until_eou(self, pre_roll: Sequence[AudioFrame]) -> Sequence[AudioFrame]:
        print("[VAD] Simulating capture (type your utterance, ENTER to end): ")
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, input)
        # We encode the text as our “frames” placeholder:
        return [text.encode("utf-8")]


class MockASR:
    """
    Interprets frames from MockVAD (utf-8 text) and returns them as transcript.
    Replace with Whisper.cpp/Vosk streaming decode.
    """
    async def transcribe(self, frames: Sequence[AudioFrame]) -> Tuple[str, float]:
        if not frames:
            return "", 0.0
        try:
            text = frames[0].decode("utf-8").strip()
        except Exception:
            text = ""
        conf = 0.95 if text else 0.0
        logging.getLogger("ASR").info("Transcript: '%s' (conf=%.2f)", text, conf)
        return text, conf


class MockPlanner:
    """
    Very small planner: recognizes “timer” and “play sound”,
    otherwise echoes back a speak action.
    Replace with your LLM call that outputs PlanModel(actions=[...]).
    """
    async def plan(self, transcript: str, summary_hint: Optional[str] = None) -> PlanModel:
        t = transcript.lower()
        actions: list[ActionModel] = []

        if "timer" in t and "minute" in t:
            # naive extract integer minutes
            import re
            m = re.search(r"(\d+)\s*minute", t)
            minutes = int(m.group(1)) if m else 10
            actions.append(ActionModel(tool="speak", args={"text": f"Okay, setting a {minutes} minute timer."}, when="now"))
            actions.append(ActionModel(tool="timer", args={"minutes": minutes, "label": "timer"}, when=f"in {minutes} minutes"))
        elif "play" in t and "sound" in t:
            actions.append(ActionModel(tool="speak", args={"text": "Playing a sound."}, when="now"))
            actions.append(ActionModel(tool="play_sound", args={"sound_id": "ding", "repeat": 1}, when="now"))
        else:
            actions.append(ActionModel(tool="speak", args={"text": f"You said: {transcript}"}, when="now"))

        return PlanModel(actions=actions)


# ===============================
#           FSM Daemon
# ===============================

class State(enum.Enum):
    IDLE = "IDLE"
    CAPTURE = "CAPTURE"
    INTERPRET = "INTERPRET"


@dataclass
class ListenerConfig:
    scheduler_addr: str = "127.0.0.1:50070"
    min_confidence: float = 0.5
    preroll_frames: int = 50   # ring buffer length (frames) while idle (conceptual)
    ack_phrase: str = "Okay."
    timezone: str = "Asia/Nicosia"


class ListenerDaemon:
    def __init__(
        self,
        wake: WakeDetector,
        vad: VAD,
        asr: ASR,
        planner: Planner,
        cfg: ListenerConfig,
    ) -> None:
        self.wake = wake
        self.vad = vad
        self.asr = asr
        self.planner = planner
        self.cfg = cfg
        self._log = logging.getLogger("Listener")
        # Conceptual pre-roll ring buffer (for real audio you’d store last N frames)
        self._ring: list[AudioFrame] = []

    async def run(self) -> None:
        self._log.info("Listener started; connecting to scheduler at %s", self.cfg.scheduler_addr)
        async with SchedulerClient(self.cfg.scheduler_addr) as sched:
            while True:
                # === IDLE ===
                state = State.IDLE
                self._log.debug("State=%s", state.value)
                await self._idle_collect_preroll()  # in real life: continuously fill _ring
                await self.wake.wait_for_hotword()

                # === CAPTURE ===
                state = State.CAPTURE
                self._log.debug("State=%s", state.value)
                frames = await self.vad.stream_until_eou(self._ring)

                # === INTERPRET ===
                state = State.INTERPRET
                self._log.debug("State=%s", state.value)
                transcript, conf = await self.asr.transcribe(frames)

                if not transcript or conf < self.cfg.min_confidence:
                    await self._speak_now(sched, "Sorry, I didn’t catch that.")
                    continue

                plan = await self.planner.plan(transcript)

                # ACK quickly (even if your planner returned its own ack)
                await self._speak_now(sched, self.cfg.ack_phrase)

                # Schedule all actions
                for action in plan.actions:
                    call = ToolCallModel.from_action(action.tool, action.args)
                    when = action.when or "now"
                    await sched.schedule_toolcall(call, when=when, priority=Priority.PRIORITY_NORMAL, timezone=self.cfg.timezone)

    async def _idle_collect_preroll(self) -> None:
        """
        Placeholder for pre-roll. With real audio, keep the last few seconds of frames here.
        In this mock, we don’t collect anything.
        """
        self._ring.clear()

    async def _speak_now(self, sched: SchedulerClient, text: str) -> None:
        call = ToolCallModel.from_action("speak", {"text": text})
        await sched.schedule_toolcall(call, when="now", priority=Priority.PRIORITY_NORMAL, timezone=self.cfg.timezone)


# ===============================
#              main
# ===============================

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = ListenerConfig()
    daemon = ListenerDaemon(
        wake=MockWakeDetector(),
        vad=MockVAD(),
        asr=MockASR(),
        planner=MockPlanner(),
        cfg=cfg,
    )
    await daemon.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

"""Entry point for the personal assistant.

Modes:
  python -m assistant.main --text        Type commands (no audio deps needed)
  python -m assistant.main                Voice mode with wake word (default)
  python -m assistant.main --check        Check Ollama / config and exit
  python -m assistant.main --list-audio   List microphone devices
  python -m assistant.main --list-voices  List TTS voices
"""
from __future__ import annotations

import argparse
import sys

from . import config
from .brain.llm import Brain, check_ollama
from . import skills  # noqa: F401  (importing registers all tools)


def _force_utf8() -> None:
    """Windows consoles default to cp1252 and crash on °, emoji, arrows, etc.
    Reconfigure stdout/stderr to UTF-8 so any reply or tool result prints safely."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def _print_banner() -> None:
    name = config.get("assistant.name", "Computer")
    n_tools = len(__import__("assistant.brain.tools", fromlist=["REGISTRY"]).REGISTRY.tools)
    print(f"\n=== {name} :: personal assistant ===")
    print(f"Model: {config.get('llm.model')}   |   Tools loaded: {n_tools}")


def run_text_mode() -> None:
    """REPL: type commands, see spoken-style replies. Great for testing."""
    _print_banner()
    ok, msg = check_ollama()
    print(msg)
    if not ok:
        print("Fix the above, then retry. (Text mode still works for tool tests once Ollama is up.)")

    def confirm(action: str) -> bool:
        ans = input(f"  [confirm] Run '{action}'? (y/N) ").strip().lower()
        return ans in ("y", "yes")

    brain = Brain(confirm_fn=confirm)
    # In text mode, reminders just print (the default announce already does that).
    print("\nType a command (or 'quit'):")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return
        if text.lower() in ("quit", "exit", "bye"):
            print("Bye.")
            return
        if not text:
            continue
        try:
            reply = brain.ask(text)
        except Exception as exc:
            reply = f"(error talking to the model: {exc})"
        print(f"asst> {reply}\n")


def run_voice_mode() -> None:
    """Wake word -> record -> transcribe -> think -> speak. The full loop."""
    _print_banner()
    ok, msg = check_ollama()
    print(msg)
    if not ok:
        sys.exit(1)

    # Heavy audio imports happen here so text mode never needs them.
    try:
        from .audio.wake_word import make_detector
        from .audio.recorder import record_until_silence
        from .audio.stt import Transcriber
        from .audio.tts import Speaker
    except ImportError as exc:
        print(f"\nVoice mode needs the voice dependencies:\n"
              f"  pip install -r requirements-voice.txt\nMissing: {exc}")
        sys.exit(1)

    print("Loading speech-to-text model (first run downloads it)...")
    stt = Transcriber()
    speaker = Speaker()
    print("Loading wake-word model...")
    # Reuse the STT model for the custom-word spotter: no second load/download.
    detector = make_detector(shared_model=getattr(stt, "model", None))

    def confirm(action: str) -> bool:
        speaker.say(f"Do you want me to {action}? Say yes or no.")
        clip = record_until_silence()
        answer = stt.transcribe(clip).lower()
        return any(w in answer for w in ("yes", "yeah", "yep", "do it", "confirm", "sure"))

    brain = Brain(confirm_fn=confirm)
    # Let reminders/timers speak aloud when they fire.
    from .skills.reminders import set_announcer
    set_announcer(speaker.say)
    print("Warming up the model (first load can take a minute on a small GPU)...")
    brain.warm_up()

    from . import modes
    from .audio.dictation import run_dictation

    follow_up = config.get("assistant.conversation_follow_up", True)
    hands_free = config.get("assistant.hands_free", False)
    stop_words = {"never mind", "nevermind", "stop", "cancel", "that's all",
                  "thank you", "thanks", "go to sleep", "nothing"}

    def handle(text: str) -> None:
        print(f"you> {text}")
        reply = brain.ask(text)
        print(f"asst> {reply}\n")
        speaker.say(reply)
        # A skill may have asked to enter dictation; if so, take over speak-to-type.
        if modes.take_dictation_request():
            run_dictation(record_until_silence, stt.transcribe, speaker.say)

    wake = config.get("assistant.wake_word", "puddles").replace("_", " ")
    name = config.get("assistant.name", "Computer")
    if hands_free:
        print("\nHands-free mode: always listening (no wake word). Ctrl+C to quit.\n")
        speaker.say(f"{name} is listening.")
    else:
        print(f"\nListening. Say '{wake}' to start. Ctrl+C to quit.\n")
        speaker.say(f"{name} is ready.")

    while True:
        try:
            handled_inline = False
            if not hands_free:
                trigger = detector.wait_for_wake()
                # If the wake word and a command were said in one breath, run it now.
                inline = ""
                if hasattr(detector, "split_command") and isinstance(trigger, str):
                    inline = detector.split_command(trigger)
                if inline:
                    handle(inline)
                    handled_inline = True
                else:
                    speaker.say("Yes?")
            # If we already handled a one-breath command and follow-ups are off,
            # go straight back to waiting for the wake word.
            if handled_inline and not (follow_up or hands_free):
                continue
            # Otherwise listen for (further) commands until quiet or a stop word.
            while True:
                print("(listening for your command...)", flush=True)
                clip = record_until_silence()
                text = stt.transcribe(clip).strip()
                if not text:
                    if not handled_inline:
                        print("(no command heard - going back to sleep)", flush=True)
                    break
                if text.lower().strip(" .!?,") in stop_words:
                    speaker.say("Okay.")
                    break
                handle(text)
                if not (follow_up or hands_free):
                    break
        except KeyboardInterrupt:
            print("\nShutting down. Bye.")
            speaker.say("Goodbye.")
            return
        except Exception as exc:
            print(f"(loop error: {exc})")
            continue


def main() -> None:
    _force_utf8()
    parser = argparse.ArgumentParser(description="Local personal assistant")
    parser.add_argument("--text", action="store_true", help="Text REPL mode (no audio)")
    parser.add_argument("--check", action="store_true", help="Check Ollama/config and exit")
    parser.add_argument("--list-audio", action="store_true", help="List microphone devices")
    parser.add_argument("--list-voices", action="store_true", help="List TTS voices")
    args = parser.parse_args()

    if args.check:
        _print_banner()
        ok, msg = check_ollama()
        print(msg)
        sys.exit(0 if ok else 1)
    if args.list_audio:
        try:
            from .audio.recorder import list_devices
            print(list_devices())
        except ImportError:
            print("Audio deps not installed. Run: py -m pip install -r requirements-voice.txt")
        return
    if args.list_voices:
        try:
            from .audio.tts import Speaker
            print(Speaker.list_voices())
        except ImportError:
            print("Audio deps not installed. Run: py -m pip install -r requirements-voice.txt")
        return
    if args.text:
        run_text_mode()
    else:
        run_voice_mode()


if __name__ == "__main__":
    main()

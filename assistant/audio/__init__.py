"""Voice I/O: microphone recording, speech-to-text, text-to-speech, wake word.

These modules import heavy optional dependencies (sounddevice, faster-whisper,
openwakeword, pyttsx3) only when used, so text mode works without them.
"""

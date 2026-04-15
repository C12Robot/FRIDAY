import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os
import threading
import re
import time
import msvcrt
import pyttsx3
from faster_whisper import WhisperModel

print("Loading voice model...")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
print("Voice model ready.")

stop_speaking   = threading.Event()
_stop_interrupt = threading.Event()
_speak_lock     = threading.Lock()

WAKE_WORDS          = ["hey friday", "hey, friday", "hi friday", "okay friday"]
WAKE_CHUNK_DURATION = 2
COMMAND_DURATION    = 6
SAMPLE_RATE         = 16000

_wake_loop_active   = threading.Event()
on_wake_word        = None


def clean_for_speech(text):
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'\*{1,}', '', text)
    text = re.sub(r'_{1,}', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()


def _record_chunk(duration, sample_rate=SAMPLE_RATE):
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.int16
    )
    sd.wait()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        wav.write(temp_path, sample_rate, audio)
    return temp_path


def _transcribe(path):
    segments, _ = model.transcribe(path, language="en")
    text = " ".join([s.text for s in segments])
    os.remove(path)
    return text.strip().lower()


def listen(duration=COMMAND_DURATION, sample_rate=SAMPLE_RATE):
    print("Listening...", flush=True)
    path = _record_chunk(duration, sample_rate)
    segments, _ = model.transcribe(path, language="en")
    text = " ".join([s.text for s in segments])
    os.remove(path)
    result = text.strip()
    if result and len(result) > 2:
        print(f"You said: {result}")
    return result


def _wake_word_loop():
    print("  [Listening for 'Hey FRIDAY'...]", flush=True)
    while _wake_loop_active.is_set():
        if _speak_lock.locked():
            time.sleep(0.3)
            continue
        try:
            path = _record_chunk(WAKE_CHUNK_DURATION)
            text = _transcribe(path)
            if any(ww in text for ww in WAKE_WORDS):
                print("\n  [Hey FRIDAY detected!]", flush=True)
                if on_wake_word:
                    on_wake_word()
        except Exception:
            time.sleep(0.5)


def start_wake_word_listener():
    _wake_loop_active.set()
    t = threading.Thread(target=_wake_word_loop, daemon=True)
    t.start()


def stop_wake_word_listener():
    _wake_loop_active.clear()


def _listen_for_interrupt():
    while not _stop_interrupt.is_set():
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\x1b':  
                stop_speaking.set()
                return
        time.sleep(0.05)


def speak(text):
    if not _speak_lock.acquire(blocking=False):
        return

    try:
        stop_speaking.clear()
        _stop_interrupt.clear()

        text = clean_for_speech(text)
        if not text:
            return

        interrupt_thread = threading.Thread(
            target=_listen_for_interrupt,
            daemon=True
        )
        interrupt_thread.start()

        def _speak_worker():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 170)
                engine.setProperty('volume', 1.0)
                voices = engine.getProperty('voices')
                for v in voices:
                    if 'zira' in v.name.lower():
                        engine.setProperty('voice', v.id)
                        break
                    elif 'english' in v.name.lower():
                        engine.setProperty('voice', v.id)

                engine.say(text)

                engine.startLoop(False)
                while engine.isBusy():
                    if stop_speaking.is_set():
                        engine.stop()
                        break
                    engine.iterate()
                    time.sleep(0.05)
                engine.endLoop()

            except Exception as e:
                print(f"[TTS ERROR] {e}", flush=True)

        speech_thread = threading.Thread(target=_speak_worker, daemon=True)
        speech_thread.start()

        while speech_thread.is_alive():
            if stop_speaking.is_set():
                print("  [interrupted]", flush=True)
                break
            time.sleep(0.1)

        speech_thread.join(timeout=3)
        _stop_interrupt.set()
        time.sleep(0.4)

    finally:
        _speak_lock.release()


def get_input(voice_mode=False):
    if voice_mode:
        return listen()
    else:
        return input("You: ").strip()
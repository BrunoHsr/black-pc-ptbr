"""Trechos com fala (silero VAD do faster-whisper): python vad.py <wav>..."""
import sys, os
from faster_whisper.audio import decode_audio
from faster_whisper.vad import get_speech_timestamps, VadOptions
for w in sys.argv[1:]:
    a = decode_audio(w, sampling_rate=16000)
    ts = get_speech_timestamps(a, VadOptions(min_silence_duration_ms=250, speech_pad_ms=60, threshold=0.5))
    print('==', os.path.basename(w), ' '.join('%.2f-%.2f' % (t['start'] / 16000, t['end'] / 16000) for t in ts))

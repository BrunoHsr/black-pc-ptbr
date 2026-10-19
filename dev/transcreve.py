"""Transcreve WAVs com faster-whisper large-v3 na GPU (precisa de um Python com faster-whisper e as DLLs CUDA dos
pacotes nvidia-*; a variavel WHISPER_MODELS aponta para a pasta dos modelos, senao usa o cache padrao).

uso: python transcreve.py detectar <wav>...                  -> idioma de cada faixa
     python transcreve.py <idioma> <saida_dir> <wav>...      -> <nome>.json com segmentos e palavras
"""
import glob, json, os, sys
from pathlib import Path

nv = Path(sys.prefix) / 'Lib' / 'site-packages' / 'nvidia'
for d in sorted(glob.glob(str(nv / '*' / 'bin'))):
    os.add_dll_directory(d)
    os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')

from faster_whisper import WhisperModel

MODEL_DIR = os.environ.get('WHISPER_MODELS')
PROMPT = ('Interrogation of Sergeant First Class Kellar about Seventh Wave. Lennox, Valencio, McCarver, Solomon, '
          'Division, Naszran, Veblensk, Treneska, Tivliz asylum, Vratska dockyard, Spetriniv gulag, Graznei bridge.')


def model():
    return WhisperModel('large-v3', device='cuda', compute_type='float16', download_root=MODEL_DIR)


def main():
    m = model()
    if sys.argv[1] == 'detectar':
        for w in sys.argv[2:]:
            segs, info = m.transcribe(w, beam_size=1, vad_filter=True)
            first = ' '.join(s.text.strip() for _, s in zip(range(2), segs))
            print('%s\t%s %.2f\t%s' % (os.path.basename(w), info.language, info.language_probability, first[:90]))
        return
    lang, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for w in sys.argv[3:]:
        segs, info = m.transcribe(w, language=lang, beam_size=5, word_timestamps=True, vad_filter=True,
                                  vad_parameters={'min_silence_duration_ms': 300}, initial_prompt=PROMPT,
                                  condition_on_previous_text=False)
        res = [{'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(),
                'words': [[round(x.start, 2), round(x.end, 2), x.word] for x in (s.words or [])]} for s in segs]
        name = Path(w).stem
        json.dump({'audio': os.path.basename(w), 'duration': info.duration, 'segments': res},
                  open(os.path.join(out, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('%s: %d segmentos' % (name, len(res)))


if __name__ == '__main__':
    main()

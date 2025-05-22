import os
import wave
import subprocess
import json
from vosk import Model, KaldiRecognizer
from datetime import timedelta
import urllib.request
import zipfile

# === Téléchargement automatique du modèle Vosk ===
MODEL_DIR = "vosk-model-fr"
MODEL_ZIP = "vosk-model-fr.zip"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip"  # ~40 Mo

def download_model():
    if not os.path.exists(MODEL_DIR):
        print("🔽 Téléchargement du modèle Vosk...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_ZIP)
        print("📦 Décompression...")
        with zipfile.ZipFile(MODEL_ZIP, "r") as zip_ref:
            zip_ref.extractall(".")
        os.rename("vosk-model-small-fr-0.22", MODEL_DIR)
        os.remove(MODEL_ZIP)
        print("✅ Modèle prêt.")

download_model()

# === PARAMÈTRES ===
MODEL_PATH = "vosk-model-fr"
OUTPUT_DIR = "Sortie"
CLIP_DURATION = 65  # secondes
MAX_CLIPS = 10
KEYWORDS = [
    "important", "intéressant", "je pense", "ce qu’il faut retenir",
    "le plus marquant", "clairement", "fondamental", "ce qu’on ne dit pas",
    "en fait", "vraiment", "très puissant", "reellement", "impressionnant", "excellent",
    "ce moment", "essentiel", "Argent", "Business", "ensuite", "second temps",
    "premierement", "danger", "secret", "fou", "dingue", "d’ailleurs"
]
DEBUG = True  # pour afficher les scores

# === OUTILS ===

def format_time(seconds):
    return str(timedelta(seconds=int(seconds)))

def extract_audio(video_path, audio_path="temp.wav"):
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-ar", "16000", "-ac", "1", "-f", "wav", audio_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path

def transcribe_audio(audio_path, model_path):
    wf = wave.open(audio_path, "rb")
    model = Model(model_path)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    results, words = [], []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            results.append(json.loads(rec.Result()))
    results.append(json.loads(rec.FinalResult()))
    for res in results:
        if 'result' in res:
            words.extend(res['result'])
    return words

def get_video_duration(video_path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", video_path
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return float(result.stdout)

def score_segments(words, duration, keywords, clip_length, debug=False):
    segments = []
    for start in range(0, int(duration - clip_length), 5):
        end = start + clip_length
        seg_words = [w for w in words if start <= w['start'] < end]
        kw_count = sum(1 for w in seg_words if w['word'].lower() in keywords)
        score = 0 if len(seg_words) < 10 else kw_count * 2 + len(seg_words)
        segments.append({
            "start": start,
            "end": end,
            "score": score
        })
        if debug:
            print(f"[DEBUG] {format_time(start)} - {format_time(end)} | Score: {score} | KW: {kw_count}")
    return sorted(segments, key=lambda s: s['score'], reverse=True)

def select_best_segments(scored_segments, clip_length, max_clips):
    selected, last_end = [], -999
    for seg in scored_segments:
        if seg['start'] >= last_end + 5:
            selected.append(seg)
            last_end = seg['end']
        if len(selected) >= max_clips:
            break
    return selected

def cut_video_clips(video_path, segments, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for i, seg in enumerate(segments, 1):
        output_file = os.path.join(output_dir, f"clip_{i:02d}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(int(seg["start"])),
            "-t", str(CLIP_DURATION),
            "-c", "copy", output_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Clip {i:02d} : {output_file}")

# === PIPELINE PRINCIPALE ===

def process_video(video_path):
    print(f"🎞️ Fichier vidéo : {video_path}")
    print("🎧 Extraction audio...")
    audio_file = extract_audio(video_path)

    print("🧠 Transcription avec Vosk...")
    words = transcribe_audio(audio_file, MODEL_PATH)

    print("🕒 Récupération durée vidéo...")
    duration = get_video_duration(video_path)

    print("📊 Analyse des segments...")
    segments = score_segments(words, duration, KEYWORDS, CLIP_DURATION, debug=DEBUG)

    print("🎯 Sélection des meilleurs...")
    best = select_best_segments(segments, CLIP_DURATION, MAX_CLIPS)

    print("✂️ Découpage vidéo...")
    cut_video_clips(video_path, best, OUTPUT_DIR)

    print("🎉 Fini.")

if __name__ == "__main__":
    import sys
    video_input = "video_source.mp4"
    if len(sys.argv) > 1:
        video_input = sys.argv[1]
    process_video(video_input)

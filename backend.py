from flask import Flask, render_template, request, send_from_directory
import yt_dlp, os, glob, time, webbrowser
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from gtts import gTTS
from moviepy import VideoFileClip, AudioFileClip

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# MODEL
model = WhisperModel("tiny", compute_type="int8")

# CLEAN
def clean_folder():
    for f in glob.glob(f"{DOWNLOAD_FOLDER}/*"):
        try:
            os.remove(f)
        except:
            pass

# GET VIDEO FILE
def get_video_file(prefix="video"):
    files = glob.glob(f"{DOWNLOAD_FOLDER}/{prefix}.*")
    return os.path.basename(files[0]) if files else None

# DOWNLOAD ORIGINAL VIDEO
def download_video(url):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/original.%(ext)s',
        'format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# EXTRACT AUDIO
def extract_audio():
    video = VideoFileClip(f"{DOWNLOAD_FOLDER}/{get_video_file('original')}")
    video.audio.write_audiofile(f"{DOWNLOAD_FOLDER}/audio.wav")

# SPEECH TO TEXT
def speech_to_text():
    segments, _ = model.transcribe(f"{DOWNLOAD_FOLDER}/audio.wav")
    return list(segments)

# TRANSLATE
def translate_text(text, lang):
    return GoogleTranslator(source='auto', target=lang).translate(text)

# TEXT TO SPEECH
def text_to_speech(text, lang):
    gTTS(text=text, lang=lang).save(f"{DOWNLOAD_FOLDER}/output.mp3")

# MERGE VIDEO
def merge_video():
    video = VideoFileClip(f"{DOWNLOAD_FOLDER}/{get_video_file('original')}")
    audio = AudioFileClip(f"{DOWNLOAD_FOLDER}/output.mp3")

    final = video.with_audio(audio)
    filename = f"translated_{int(time.time())}.mp4"
    final.write_videofile(f"{DOWNLOAD_FOLDER}/{filename}")

    video.close()
    audio.close()

    return filename

# CREATE SUBTITLES
def create_srt(segments):
    with open(f"{DOWNLOAD_FOLDER}/subtitles.srt", "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            f.write(f"{i+1}\n")
            f.write(f"{seg.start:.2f} --> {seg.end:.2f}\n")
            f.write(seg.text.strip() + "\n\n")

# PROCESS
@app.route('/process', methods=['POST'])
def process():
    try:
        url = request.form['url']
        lang = request.form['lang']

        clean_folder()
        download_video(url)

        original_file = get_video_file("original")

        extract_audio()
        segments = speech_to_text()

        full_text = " ".join([seg.text for seg in segments])
        translated = translate_text(full_text, lang)

        create_srt(segments)

        text_to_speech(translated, lang)
        translated_video = merge_video()

        with open(f"{DOWNLOAD_FOLDER}/subtitles.srt", "r", encoding="utf-8") as f:
            subtitles = f.read()

        return render_template(
            "result.html",
            original=original_file,      # ✅ correct
            video=translated_video,      # ✅ correct
            subtitles=subtitles
        )

    except Exception as e:
        return str(e)

# VIDEO STREAM
@app.route('/video/<filename>')
def video_stream(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

# DOWNLOAD
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

# HOME
@app.route('/')
def home():
    return render_template("index.html")

# RUN
if __name__ == "__main__":
    port = 10000
    webbrowser.open(f"http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port)
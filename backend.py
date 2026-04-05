from flask import Flask, render_template, request, send_from_directory
import yt_dlp, os, glob, time, json, webbrowser
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from gtts import gTTS
from moviepy import VideoFileClip, AudioFileClip

app = Flask(__name__)
# test commit

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔥 MODEL
model = WhisperModel("tiny", compute_type="int8")

# 🧹 CLEAN
def clean_folder():
    for f in glob.glob(f"{DOWNLOAD_FOLDER}/*"):
        try:
            os.remove(f)
        except:
            pass

# 📂 GET VIDEO
def get_video_file():
    
    files = glob.glob(f"{DOWNLOAD_FOLDER}/video.*")
    return files[0] if files else None

# 📥 DOWNLOAD
def download_video(url):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/video.%(ext)s',
        'format': 'worst'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# 🔊 EXTRACT
def extract_audio():
    video = VideoFileClip(get_video_file())
    video.audio.write_audiofile(f"{DOWNLOAD_FOLDER}/audio.wav")

# 🧠 SPEECH
def speech_to_text():
    segments, _ = model.transcribe(f"{DOWNLOAD_FOLDER}/audio.wav")
    return list(segments)

# 🌍 TRANSLATE
def translate_text(text, lang):
    chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
    result = ""
    for c in chunks:
        result += GoogleTranslator(source='auto', target=lang).translate(c) + " "
    return result

# 🔊 TTS
def text_to_speech(text, lang):
    gTTS(text=text, lang=lang).save(f"{DOWNLOAD_FOLDER}/output.mp3")

# 🎬 MERGE
def merge_video():
    video = VideoFileClip(get_video_file())
    audio = AudioFileClip(f"{DOWNLOAD_FOLDER}/output.mp3")

    final = video.with_audio(audio)

    filename = f"final_{int(time.time())}.mp4"
    final.write_videofile(f"{DOWNLOAD_FOLDER}/{filename}")

    video.close()
    audio.close()

    return filename

# 📝 SRT
def create_srt(segments):
    with open(f"{DOWNLOAD_FOLDER}/subtitles.srt", "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            f.write(f"{i+1}\n")
            f.write(f"00:00:{int(seg.start):02d},000 --> 00:00:{int(seg.end):02d},000\n")
            f.write(seg.text.strip() + "\n\n")

# 🚀 PROCESS
@app.route('/process', methods=['POST'])
def process():
    try:
        url = request.form['url']
        lang = request.form['lang']
        mode = request.form['mode']

        clean_folder()
        download_video(url)
        extract_audio()

        segments = speech_to_text()
        full_text = " ".join([seg.text for seg in segments])

        translated = translate_text(full_text, lang)
        create_srt(segments)

        # 🔥 READ SUBTITLES (FIX)
        with open(f"{DOWNLOAD_FOLDER}/subtitles.srt", "r", encoding="utf-8") as f:
            subtitles = f.read().split("\n")

        if mode == "text":
            return render_template("result.html",
                                   mode="text",
                                   text=translated,
                                   subtitles=subtitles)

        text_to_speech(translated, lang)
        video = merge_video()

        return render_template("result.html",
                               mode="video",
                               video=video,
                               original=url,
                               subtitles=subtitles)

    except Exception as e:
        return render_template("result.html", mode="error", error=str(e))

# 📥 DOWNLOAD
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

# 🏠 HOME
@app.route('/')
def home():
    return render_template("index.html")

# 🚀 RUN
if __name__ == "__main__":
    port =int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
from flask import Flask, request, jsonify, send_file, Response
import yt_dlp, os, uuid, subprocess, json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup

app = Flask(__name__)
os.makedirs('C:/downloader/hasil', exist_ok=True)

progress_data = {}

@app.route('/')
def home():
    return open('index.html',encoding='utf-8').read()

@app.route('/index.html')
def index():
    return open('index.html',encoding='utf-8').read()

@app.route('/icon.png')
def icon():
    return send_file('icon.png', mimetype='image/png')

@app.route('/manifest.json')
def manifest():
    return send_file('manifest.json', mimetype='application/json')

@app.route('/service-worker.js')
def sw():
    return send_file('service-worker.js',mimetype='application/javascript')
  
@app.route('/info', methods=['POST'])
def get_info():
    url = request.json.get('url', '')
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none':
                formats.append({
                    'format_id': f.get('format_id'),
                    'resolution': f.get('resolution') or f.get('height', 0),
                    'fps': f.get('fps', 0),
                    'filesize': round(f.get('filesize', 0) / 1024 / 1024, 1) if f.get('filesize') else 0,
                    'vcodec': f.get('vcodec', ''),
                    'tbr': round(f.get('tbr', 0)) if f.get('tbr') else 0,
                    'ext': f.get('ext', ''),
                })

        formats = sorted(formats, key=lambda x: x.get('tbr', 0), reverse=True)[:8]

        return jsonify({
            'title': info.get('title', 'Unknown'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'platform': info.get('extractor', 'Unknown'),
            'formats': formats,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query', '')
    results = []

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
            for entry in info.get('entries', []):
                results.append({
                    'title': entry.get('title'),
                    'url': entry.get('url') or entry.get('webpage_url'),
                    'duration': entry.get('duration', 0),
                    'thumbnail': entry.get('thumbnail', ''),
                    'platform': 'YouTube',
                    'channel': entry.get('channel') or entry.get('uploader', ''),
                })
    except:
        pass

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
            info = ydl.extract_info(f"scsearch5:{query}", download=False)
            for entry in info.get('entries', []):
                results.append({
                    'title': entry.get('title'),
                    'url': entry.get('url') or entry.get('webpage_url'),
                    'duration': entry.get('duration', 0),
                    'thumbnail': entry.get('thumbnail', ''),
                    'platform': 'SoundCloud',
                    'channel': entry.get('uploader', ''),
                })
    except:
        pass

    return jsonify({'results': results})
    

NOTES_FILE = 'notes.json'

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, 'r') as f:
            return json.load(f)
    return []

def save_notes(notes):
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f)

@app.route('/notes', methods=['GET'])
def get_notes():
    return jsonify({'notes': load_notes()})

@app.route('/notes', methods=['POST'])
def add_note():
    text = request.json.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Teks kosong'}), 400
    notes = load_notes()
    notes.append({
        'id': str(uuid.uuid4()),
        'text': text,
        'done': False,
    })
    save_notes(notes)
    return jsonify({'success': True, 'notes': notes})

@app.route('/notes/<note_id>', methods=['PUT'])
def toggle_note(note_id):
    notes = load_notes()
    for n in notes:
        if n['id'] == note_id:
            n['done'] = not n['done']
    save_notes(notes)
    return jsonify({'success': True, 'notes': notes})

@app.route('/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    notes = load_notes()
    notes = [n for n in notes if n['id'] != note_id]
    save_notes(notes)
    return jsonify({'success': True, 'notes': notes})
    
@app.route('/websearch', methods=['POST'])
def websearch():
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Query kosong'}), 400

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10)'}
        res = requests.post(
    'https://html.duckduckgo.com/html/',
    data={'q': query},
    headers=headers,
    timeout=10,
    verify=False
)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = []

        for r in soup.select('.result')[:10]:
            title_tag = r.select_one('.result__title a')
            snippet_tag = r.select_one('.result__snippet')
            if title_tag:
                link = title_tag.get('href', '')
                results.append({
                    'title': title_tag.get_text(strip=True),
                    'link': link,
                    'snippet': snippet_tag.get_text(strip=True) if snippet_tag else '',
                })

        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/compress', methods=['POST'])
def compress():
    input_path = request.json.get('input_path', '')
    preset = request.json.get('preset', 'tiktok')
    session_id = str(uuid.uuid4())
    progress_data[session_id] = {'status': 'starting', 'percent': 0}

    presets = {
        'tiktok': {
            'vcodec': 'libx264',
            'resolution': '1080:1920',
            'bitrate': '8000k',
            'fps': '30',
            'audio': '128k',
        },
        'whatsapp': {
            'vcodec': 'libx264',
            'resolution': '-2:720',
            'bitrate': '1500k',
            'fps': '30',
            'audio': '96k',
        },
        'storage': {
            'vcodec': 'libx265',
            'resolution': '-2:720',
            'bitrate': '1000k',
            'fps': '30',
            'audio': '96k',
        },
    }

    p = presets.get(preset, presets['tiktok'])
    filename = os.path.basename(input_path)
    output_path = f'compressed_{filename}'

    def run_compress():
        try:
            progress_data[session_id] = {'status': 'compressing', 'percent': '50%'}
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', f'scale={p["resolution"]}',
                '-c:v', p['vcodec'],
                '-b:v', p['bitrate'],
                '-r', p['fps'],
                '-c:a', 'aac',
                '-b:a', p['audio'],
                '-y', output_path
            ]
            subprocess.run(cmd, capture_output=True)
            progress_data[session_id] = {'status': 'done', 'percent': '100%'}
            subprocess.run([
                'am', 'broadcast',
                '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                '-d', f'file://{output_path}'
            ], capture_output=True)
        except Exception as e:
            progress_data[session_id] = {'status': 'error', 'percent': '0%'}

    import threading
    threading.Thread(target=run_compress).start()

    return jsonify({'success': True, 'session_id': session_id})

@app.route('/progress/<session_id>')
def progress(session_id):
    def generate():
        while True:
            data = progress_data.get(session_id, {})
            yield f"data: {json.dumps(data)}\n\n"
            if data.get('status') in ['done', 'error']:
                break
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download', methods=['POST'])
def download():
    url = request.json.get('url', '')
    quality = request.json.get('quality', 'best')
    session_id = str(uuid.uuid4())
    progress_data[session_id] = {'status': 'starting', 'percent': 0}

    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%').strip()
            speed = d.get('_speed_str', '').strip()
            eta = d.get('_eta_str', '').strip()
            progress_data[session_id] = {
                'status': 'downloading',
                'percent': percent,
                'speed': speed,
                'eta': eta
            }
        elif d['status'] == 'finished':
            progress_data[session_id] = {
                'status': 'processing',
                'percent': '100%',
                'speed': '',
                'eta': ''
            }

    is_audio = quality == 'bestaudio'
    is_pinterest = 'pinterest' in url or 'pin.it' in url
    is_tiktok = 'tiktok' in url or 'vt.tiktok' in url
    is_instagram = 'instagram' in url or 'instagr.am' in url

    def get_cookies(platform):
        paths = {
            'cookies_pinterest.txt',
            'cookies_tiktok.txt',
            'cookies_instagram.txt',
        }
        path = paths.get(platform, '')
        return path if os.path.exists(path) else 'cookies.txt'

    if is_pinterest:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'cookiefile': get_cookies('pinterest'),
            'outtmpl': 'C:/downloader/hasil/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegMetadata', 'add_metadata': True}],
        }
    elif is_tiktok:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'cookiefile': get_cookies('tiktok'),
            'outtmpl': 'C:/downloader/hasil/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegMetadata', 'add_metadata': True}],
        }
    elif is_instagram:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'cookiefile': get_cookies('instagram'),
            'outtmpl': 'C:/downloader/hasil/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegMetadata', 'add_metadata': True}],
        }
    elif is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'cookiefile': 'cookies.txt',
            'outtmpl': 'C:/downloader/hasil/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                {'key': 'FFmpegMetadata', 'add_metadata': True}
            ],
        }
    elif is_tiktok:
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'cookiefile': 'cookies_tiktok.txt',
            'outtmpl': 'C:/downloader/hasil/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',
            'impersonate': 'chrome',
            'postprocessors': [{'key': 'FFmpegMetadata', 'add_metadata': True}],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        progress_data[session_id] = {'status': 'done', 'percent': '100%'}

        import platform
        if platform.system() == 'Android' or os.path.exists('/sdcard'):
            subprocess.run([
              'am', 'broadcast',
              '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
              '-d', 'file:///sdcard/DCIM/Downloader/'
    ], capture_output=True)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'title': info.get('title'),
        })
    except Exception as e:
        progress_data[session_id] = {'status': 'error', 'percent': '0%'}
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
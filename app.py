# app.py - with CAPTCHA solving workflow
import os
import subprocess
import sys
import json
import base64
import webbrowser
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Environment detection
IS_RENDER = os.environ.get('RENDER', False) or os.path.exists('/etc/secrets')

# Download folder
if IS_RENDER:
    DOWNLOAD_FOLDER = Path('/opt/render/project/src/downloads')
else:
    DOWNLOAD_FOLDER = Path(__file__).parent / 'downloads'

DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

print(f"📍 Environment: {'Render' if IS_RENDER else 'Local'}")
print(f"📁 Download folder: {DOWNLOAD_FOLDER}")

def check_deno():
    """Check if Deno is available"""
    deno_paths = [
        'deno',
        r'G:\denoruntime\deno.exe',
        r'C:\Users\PC\.deno\bin\deno.exe',
        r'/root/.deno/bin/deno',
    ]
    
    for deno_path in deno_paths:
        try:
            result = subprocess.run([deno_path, '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Deno found at: {deno_path}")
                return deno_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        except Exception as e:
            print(f"⚠️ Error checking {deno_path}: {e}")
    
    print("⚠️ Deno not found.")
    return None

def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        print(f"✅ yt-dlp: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("📦 Installing yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'])
        return True

def get_cookies_from_browser():
    """Try to get cookies from browser via yt-dlp"""
    try:
        # This will open a browser window for authentication
        cmd = ['yt-dlp', '--cookies-from-browser', 'chrome', '--cookies', 'cookies.txt', '--simulate', 'https://youtube.com']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists('cookies.txt'):
            print("✅ Cookies extracted from browser")
            return ['--cookies', 'cookies.txt']
    except Exception as e:
        print(f"⚠️ Browser cookie extraction failed: {e}")
    return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/open-youtube', methods=['GET'])
def open_youtube():
    """Open YouTube in browser for manual login"""
    youtube_url = "https://www.youtube.com"
    
    if not IS_RENDER:
        # Open browser on local machine
        webbrowser.open(youtube_url)
        return jsonify({
            'success': True,
            'message': 'YouTube opened in your browser. Please log in, then click "Get Cookies" button.',
            'url': youtube_url
        })
    else:
        # On Render, can't open browser - provide instructions
        return jsonify({
            'success': False,
            'message': 'On Render, you cannot open a browser. Please export cookies manually using the extension.',
            'instructions': '1. Install "Get cookies.txt LOCALLY" extension\n2. Log into YouTube\n3. Export cookies\n4. Upload as Secret File'
        })

@app.route('/api/get-cookies', methods=['POST'])
def get_cookies():
    """Get cookies after manual login"""
    try:
        data = request.get_json()
        method = data.get('method', 'browser')
        
        if method == 'browser':
            cookies_arg = get_cookies_from_browser()
            if cookies_arg:
                return jsonify({
                    'success': True,
                    'message': 'Cookies extracted successfully! You can now download videos.',
                    'cookies_obtained': True
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Could not extract cookies. Make sure you are logged into YouTube in your browser.',
                    'instructions': '1. Make sure Chrome is installed\n2. Log into YouTube\n3. Try again'
                })
        else:
            return jsonify({'success': False, 'message': 'Invalid method'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})








@app.route('/api/download', methods=['POST'])
def download():
    """Download video from URL"""
    try:
        data = request.get_json()
        video_url = data.get('url')
        
        if not video_url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        print(f"📥 Downloading: {video_url}")
        
        check_ytdlp()
        
        # Get cookies
        cookies_arg = []
        cookies_path = '/etc/secrets/cookies.txt'
        if os.path.exists(cookies_path):
            cookies_arg = ['--cookies', cookies_path]
            print("✅ Using cookies")
        
        # Simplified command - no --js-runtimes
        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ] + cookies_arg + [video_url]
        
        print("Running download...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        downloaded_files = list(DOWNLOAD_FOLDER.glob('*.mp4'))
        
        if result.returncode == 0 and downloaded_files:
            latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
            file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
            print(f"✅ Downloaded: {latest_file.name} ({file_size} MB)")
            
            return jsonify({
                'success': True,
                'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                'filename': latest_file.name,
                'size_mb': file_size
            })
        
        # Try format 22 as fallback
        print("Trying format 22...")
        cmd2 = [
            'yt-dlp',
            '-f', '22',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
        ] + cookies_arg + [video_url]
        
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
        downloaded_files2 = list(DOWNLOAD_FOLDER.glob('*.mp4'))
        
        if result2.returncode == 0 and downloaded_files2:
            latest_file = max(downloaded_files2, key=lambda f: f.stat().st_mtime)
            file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
            print(f"✅ Downloaded: {latest_file.name} ({file_size} MB)")
            
            return jsonify({
                'success': True,
                'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                'filename': latest_file.name,
                'size_mb': file_size
            })
        
        error_msg = result2.stderr[:500] if result2.stderr else 'Download failed'
        return jsonify({'success': False, 'error': error_msg})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})




def get_existing_cookies():
    """Check for existing cookie files"""
    cookie_paths = ['cookies.txt', '/tmp/cookies.txt', '/etc/secrets/cookies.txt']
    for path in cookie_paths:
        if os.path.exists(path):
            return ['--cookies', path]
    return []

@app.route('/api/list', methods=['GET'])
def list_files():
    """List downloaded files"""
    files = []
    for f in DOWNLOAD_FOLDER.glob('*.mp4'):
        files.append({
            'name': f.name,
            'size_mb': round(f.stat().st_size / (1024 * 1024), 2),
            'path': str(f),
            'modified': f.stat().st_mtime
        })
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'success': True, 'files': files})

@app.route('/api/environment', methods=['GET'])
def environment():
    deno_available = check_deno() is not None
    return jsonify({
        'success': True,
        'is_render': IS_RENDER,
        'download_folder': str(DOWNLOAD_FOLDER),
        'deno_available': deno_available
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 YouTube Downloader Started")
    print("=" * 50)
    print(f"📍 Environment: {'Render' if IS_RENDER else 'Local'}")
    print(f"📁 Download folder: {DOWNLOAD_FOLDER}")
    print(f"🌐 Server: http://localhost:{port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
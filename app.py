# app.py - Hybrid version (Local + Render)
import os
import subprocess
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Detect environment
IS_RENDER = os.environ.get('RENDER', False) or os.path.exists('/etc/secrets')

# Set download folder based on environment
if IS_RENDER:
    # Render - use persistent disk
    DOWNLOAD_FOLDER = Path('/opt/render/project/src/downloads')
    print("📍 Running on Render")
else:
    # Local - use local folder
    DOWNLOAD_FOLDER = Path(__file__).parent / 'downloads'
    print("📍 Running Locally")

# Create download folder
DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

print(f"📁 Download folder: {DOWNLOAD_FOLDER}")

def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        print(f"✅ yt-dlp is installed")
        return True
    except:
        print("📦 Installing yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'])
        return True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def download():
    """Download video from URL"""
    try:
        data = request.get_json()
        video_url = data.get('url')
        
        if not video_url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        print(f"📥 Downloading: {video_url}")
        print(f"📁 Saving to: {DOWNLOAD_FOLDER}")
        
        # Ensure yt-dlp is installed
        check_ytdlp()
        
        # Get cookies if on Render (optional)
        cookies_arg = []
        if IS_RENDER:
            cookies_path = '/etc/secrets/cookies.txt'
            if os.path.exists(cookies_path):
                cookies_arg = ['--cookies', cookies_path]
                print("✅ Using cookies for authentication")
        
        # Try format 18 (360p MP4 - most reliable)
        cmd = [
            'yt-dlp',
            '-f', '18',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
        ] + cookies_arg + [video_url]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Check for downloaded files
        downloaded_files = list(DOWNLOAD_FOLDER.glob('*.mp4'))
        
        if result.returncode == 0 and downloaded_files:
            latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
            file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
            
            return jsonify({
                'success': True,
                'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                'filename': latest_file.name,
                'size_mb': file_size,
                'path': str(latest_file)
            })
        else:
            # Try best format as fallback
            print("Format 18 failed, trying best format...")
            cmd2 = [
                'yt-dlp',
                '-f', 'best[ext=mp4]/best',
                '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
                '--no-playlist',
                '--restrict-filenames',
            ] + cookies_arg + [video_url]
            
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
            downloaded_files2 = list(DOWNLOAD_FOLDER.glob('*.mp4'))
            
            if result2.returncode == 0 and downloaded_files2:
                latest_file = max(downloaded_files2, key=lambda f: f.stat().st_mtime)
                file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
                
                return jsonify({
                    'success': True,
                    'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                    'filename': latest_file.name,
                    'size_mb': file_size,
                    'path': str(latest_file)
                })
            
            return jsonify({
                'success': False,
                'error': result2.stderr[:500] if result2.stderr else 'Download failed'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Download timed out after 5 minutes'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
    # Sort by newest first
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'success': True, 'files': files, 'download_folder': str(DOWNLOAD_FOLDER)})

@app.route('/api/environment', methods=['GET'])
def environment():
    """Get environment info"""
    return jsonify({
        'success': True,
        'is_render': IS_RENDER,
        'download_folder': str(DOWNLOAD_FOLDER),
        'disk_free_gb': DOWNLOAD_FOLDER.free / (1024**3) if hasattr(DOWNLOAD_FOLDER, 'free') else None
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 YouTube Downloader Started")
    print("=" * 50)
    print(f"📍 Environment: {'Render' if IS_RENDER else 'Local'}")
    print(f"📁 Download folder: {DOWNLOAD_FOLDER}")
    try:
        free_gb = DOWNLOAD_FOLDER.free / (1024**3) if hasattr(DOWNLOAD_FOLDER, 'free') else None
        if free_gb:
            print(f"💾 Free space: {free_gb:.2f} GB")
    except:
        pass
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
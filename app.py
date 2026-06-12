# app.py - Docker version
import os
import subprocess
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Environment detection
IS_RENDER = os.environ.get('RENDER', False) or os.path.exists('/.dockerenv')

# Download folder
if IS_RENDER or os.path.exists('/.dockerenv'):
    DOWNLOAD_FOLDER = Path('/opt/render/project/src/downloads')
else:
    DOWNLOAD_FOLDER = Path(__file__).parent / 'downloads'

DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

print(f"📍 Environment: {'Docker/Render' if IS_RENDER else 'Local'}")
print(f"📁 Download folder: {DOWNLOAD_FOLDER}")

def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'], 
                      capture_output=True)
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        print(f"✅ yt-dlp: {result.stdout.strip()}")
        
        # Check Deno
        deno = subprocess.run(['deno', '--version'], capture_output=True, text=True)
        if deno.returncode == 0:
            print(f"✅ Deno: {deno.stdout.strip().split()[1]}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

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
        
        check_ytdlp()
        
        # Use Deno for JavaScript challenges
        cmd = [
            'yt-dlp',
            '--js-runtimes', 'deno',
            '--remote-components', 'ejs:npm',
            '-f', 'best[ext=mp4]/best',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            '--no-warnings',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        # Check for downloaded files
        downloaded_files = list(DOWNLOAD_FOLDER.glob('*.mp4'))
        
        if result.returncode == 0 and downloaded_files:
            latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
            file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
            
            return jsonify({
                'success': True,
                'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                'filename': latest_file.name,
                'size_mb': file_size
            })
        else:
            # Fallback without Deno
            cmd2 = [
                'yt-dlp',
                '-f', '18',
                '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
                '--no-playlist',
                '--restrict-filenames',
                video_url
            ]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
            downloaded_files2 = list(DOWNLOAD_FOLDER.glob('*.mp4'))
            
            if result2.returncode == 0 and downloaded_files2:
                latest_file = max(downloaded_files2, key=lambda f: f.stat().st_mtime)
                file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
                
                return jsonify({
                    'success': True,
                    'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                    'filename': latest_file.name,
                    'size_mb': file_size
                })
            
            return jsonify({
                'success': False,
                'error': result2.stderr[:500] if result2.stderr else 'Download failed'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Download timed out after 10 minutes'})
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
            'path': str(f)
        })
    files.sort(key=lambda x: x['name'], reverse=True)
    return jsonify({'success': True, 'files': files})

@app.route('/api/environment', methods=['GET'])
def environment():
    """Get environment info"""
    return jsonify({
        'success': True,
        'is_docker': True,
        'download_folder': str(DOWNLOAD_FOLDER),
        'deno_installed': subprocess.run(['deno', '--version'], capture_output=True).returncode == 0
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 YouTube Downloader (Docker)")
    print("=" * 50)
    print(f"📁 Download folder: {DOWNLOAD_FOLDER}")
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
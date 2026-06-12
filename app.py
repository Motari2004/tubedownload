# app.py
import os
import subprocess
import sys
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
    """Check if Deno is available - handles PATH issues gracefully"""
    # Possible Deno locations
    deno_paths = [
        'deno',  # Try from PATH
        r'G:\denoruntime\deno.exe',  # Your specific location
        r'C:\Users\PC\.deno\bin\deno.exe',  # Default Deno location
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
    
    print("⚠️ Deno not found. Downloads may fail for some videos.")
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
        
        # Ensure yt-dlp is installed
        check_ytdlp()
        
        # Build command
        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android',
            video_url
        ]
        
        # Add Deno if available (for JavaScript challenges)
        deno_path = check_deno()
        if deno_path:
            # Insert Deno args after yt-dlp
            cmd.insert(1, '--js-runtimes')
            cmd.insert(2, deno_path)
            cmd.insert(3, '--remote-components')
            cmd.insert(4, 'ejs:npm')
            print("✅ Using Deno for JavaScript challenges")
        
        print("Running download...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        # Check for downloaded files
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
        
        # If best format fails, try format 18
        print("Best format failed, trying format 18...")
        cmd2 = [
            'yt-dlp',
            '-f', '18',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            video_url
        ]
        
        if deno_path:
            cmd2.insert(1, '--js-runtimes')
            cmd2.insert(2, deno_path)
            cmd2.insert(3, '--remote-components')
            cmd2.insert(4, 'ejs:npm')
        
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
        print(f"❌ Error: {error_msg}")
        
        return jsonify({
            'success': False,
            'error': error_msg
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
    """Get environment info without causing errors"""
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
    print(f"📁 Download folder: {DOWNLOAD_FOLDER}")
    print(f"🌐 Server: http://localhost:{port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
# app.py
import os
import subprocess
import sys
import json
import base64
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
    deno_paths = [
        'deno',
        r'G:\denoruntime\deno.exe',
        r'C:\Users\PC\.deno\bin\deno.exe',
        r'/root/.deno/bin/deno',  # Render path
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

def get_cookies_arg():
    """Get cookies from various sources (JSON or Netscape format)"""
    
    # Check for Netscape format cookies.txt
    netscape_paths = [
        'cookies.txt',
        '/etc/secrets/cookies.txt',
        '/tmp/cookies.txt',
    ]
    
    for path in netscape_paths:
        if os.path.exists(path):
            print(f"✅ Using Netscape cookies from: {path}")
            return ['--cookies', path]
    
    # Check for JSON cookie files
    json_paths = [
        'www.youtube.com_cookies.json',
        '/etc/secrets/www.youtube.com_cookies.json',
    ]
    
    for json_path in json_paths:
        if os.path.exists(json_path):
            print(f"✅ Found JSON cookies: {json_path}")
            temp_cookie_file = '/tmp/cookies.txt'
            
            try:
                with open(json_path, 'r') as f:
                    cookies = json.load(f)
                
                with open(temp_cookie_file, 'w') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    for cookie in cookies:
                        if cookie.get('domain'):
                            domain = cookie.get('domain', '')
                            flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                            path = cookie.get('path', '/')
                            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                            expiry = int(cookie.get('expirationDate', 0)) if cookie.get('expirationDate') else 0
                            name = cookie.get('name', '')
                            value = cookie.get('value', '')
                            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
                
                print(f"✅ Converted JSON cookies to {temp_cookie_file}")
                return ['--cookies', temp_cookie_file]
            except Exception as e:
                print(f"⚠️ Failed to convert JSON cookies: {e}")
    
    # Check for Base64 encoded cookies in environment variable
    cookies_base64 = os.environ.get('COOKIES_BASE64', '')
    if cookies_base64:
        try:
            temp_cookie_file = '/tmp/cookies.txt'
            cookies_content = base64.b64decode(cookies_base64).decode('utf-8')
            with open(temp_cookie_file, 'w') as f:
                f.write(cookies_content)
            print("✅ Loaded cookies from environment variable")
            return ['--cookies', temp_cookie_file]
        except Exception as e:
            print(f"⚠️ Failed to decode base64 cookies: {e}")
    
    print("⚠️ No cookies found. Downloads may be rate-limited.")
    return []

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
        
        # Get cookies
        cookies_arg = get_cookies_arg()
        
        # Get Deno path
        deno_path = check_deno()
        
        # Try format 18 first (most reliable on Render)
        print("Trying format 18 (360p)...")
        cmd = [
            'yt-dlp',
            '-f', '18',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android',
            '--sleep-requests', '2',
            '--retries', '5',
        ] + cookies_arg + [video_url]
        
        if deno_path:
            cmd.insert(1, '--js-runtimes')
            cmd.insert(2, deno_path)
            cmd.insert(3, '--remote-components')
            cmd.insert(4, 'ejs:npm')
            print("✅ Using Deno for JavaScript challenges")
        
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
                'size_mb': file_size,
                'path': str(latest_file)
            })
        
        # If format 18 fails, try format 22 (720p)
        print("Format 18 failed, trying format 22 (720p)...")
        cmd2 = [
            'yt-dlp',
            '-f', '22',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android',
            '--sleep-requests', '2',
            '--retries', '5',
        ] + cookies_arg + [video_url]
        
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
                'size_mb': file_size,
                'path': str(latest_file)
            })
        
        # If both fail, try best format
        print("Format 22 failed, trying best format...")
        cmd3 = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '-o', f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android',
            '--sleep-requests', '2',
            '--retries', '5',
        ] + cookies_arg + [video_url]
        
        if deno_path:
            cmd3.insert(1, '--js-runtimes')
            cmd3.insert(2, deno_path)
            cmd3.insert(3, '--remote-components')
            cmd3.insert(4, 'ejs:npm')
        
        result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=600)
        downloaded_files3 = list(DOWNLOAD_FOLDER.glob('*.mp4'))
        
        if result3.returncode == 0 and downloaded_files3:
            latest_file = max(downloaded_files3, key=lambda f: f.stat().st_mtime)
            file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
            print(f"✅ Downloaded: {latest_file.name} ({file_size} MB)")
            
            return jsonify({
                'success': True,
                'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                'filename': latest_file.name,
                'size_mb': file_size,
                'path': str(latest_file)
            })
        
        # All formats failed
        error_msg = result3.stderr[:500] if result3.stderr else 'Download failed'
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
            'path': str(f),
            'modified': f.stat().st_mtime
        })
    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify({'success': True, 'files': files, 'download_folder': str(DOWNLOAD_FOLDER)})

@app.route('/api/environment', methods=['GET'])
def environment():
    """Get environment info without causing errors"""
    deno_available = check_deno() is not None
    cookies_available = len(get_cookies_arg()) > 0
    return jsonify({
        'success': True,
        'is_render': IS_RENDER,
        'download_folder': str(DOWNLOAD_FOLDER),
        'deno_available': deno_available,
        'cookies_available': cookies_available
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
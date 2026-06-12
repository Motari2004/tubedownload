# convert_cookies.py
import json
import os
import base64

def convert_json_to_netscape(json_file, output_file):
    """Convert JSON cookies to Netscape format for yt-dlp"""
    
    with open(json_file, 'r') as f:
        cookies = json.load(f)
    
    with open(output_file, 'w') as f:
        # Write header required by yt-dlp
        f.write("# Netscape HTTP Cookie File\n")
        
        for cookie in cookies:
            if not cookie.get('domain'):
                continue
            
            # Extract cookie fields
            domain = cookie.get('domain', '')
            flag = 'TRUE' if domain.startswith('.') else 'FALSE'
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            
            # Expiry (yt-dlp requires a number, use 0 for session)
            expiry = cookie.get('expirationDate', 0)
            if expiry:
                expiry = int(expiry)
            else:
                expiry = 0
            
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            
            # Write line in Netscape format
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
    
    print(f"✅ Converted {json_file} to {output_file}")
    return output_file

def create_base64_for_render(json_file):
    """Create Base64 encoded version for Render environment variable"""
    
    with open(json_file, 'r') as f:
        cookies_content = f.read()
    
    # Encode to Base64
    base64_bytes = base64.b64encode(cookies_content.encode('utf-8'))
    base64_string = base64_bytes.decode('utf-8')
    
    # Save to file
    output_file = 'cookies_base64.txt'
    with open(output_file, 'w') as f:
        f.write(base64_string)
    
    print(f"\n✅ Base64 encoded cookies saved to: {output_file}")
    print("\n📋 Copy this entire string and add to Render as:")
    print("   Environment Variable: COOKIES_BASE64")
    print("\n" + "=" * 50)
    print("BASE64 COOKIES (copy this):")
    print("=" * 50)
    print(base64_string)
    print("=" * 50)
    
    return base64_string

if __name__ == "__main__":
    json_file = 'www.youtube.com_cookies.json'
    
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        print("   Make sure www.youtube.com_cookies.json is in the current directory")
        exit(1)
    
    # Convert to Netscape format for local use
    convert_json_to_netscape(json_file, 'cookies.txt')
    
    # Create Base64 for Render
    create_base64_for_render(json_file)
    
    print("\n" + "=" * 50)
    print("✅ Done! Next steps:")
    print("=" * 50)
    print("1. For LOCAL testing: yt-dlp --cookies cookies.txt <URL>")
    print("2. For RENDER: Add COOKIES_BASE64 environment variable with the value above")
    print("=" * 50)
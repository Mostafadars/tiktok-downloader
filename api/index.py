from flask import Flask, request, jsonify, send_file, render_template
import requests
import os
import re
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from io import BytesIO
from flask_cors import CORS
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.middleware.proxy_fix import ProxyFix
from io import BytesIO
import requests, os, re
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)
app.wsgi_app = ProxyFix(app.wsgi_app)


# Configuration
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>TikTok Video Downloader</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }
        .container {
            background-color: #f9f9f9;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        input[type="text"] {
            width: 70%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            padding: 12px 25px;
            background-color: #25F4EE;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #20D8D2;
        }
        #progress-container {
            margin: 20px 0;
            display: none;
        }
        #progress-bar {
            width: 100%;
            background-color: #f1f1f1;
            border-radius: 5px;
        }
        #progress {
            height: 30px;
            border-radius: 5px;
            background-color: #25F4EE;
            width: 0%;
            transition: width 0.3s;
        }
        #status {
            margin: 10px 0;
            min-height: 20px;
        }
        #result {
            margin-top: 20px;
        }
        .error {
            color: red;
        }
        .success {
            color: green;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>TikTok Video Downloader</h1>
        <p>Paste TikTok video URL below to download</p>
        
        <form id="download-form">
            <input type="text" id="video-url" placeholder="https://www.tiktok.com/@username/video/123456789" required>
            <button type="submit">Download</button>
        </form>
        
        <div id="progress-container">
            <div id="progress-bar">
                <div id="progress"></div>
            </div>
            <div id="status">Processing...</div>
        </div>
        
        <div id="result"></div>
    </div>

    <script>
        document.getElementById('download-form').addEventListener('submit', function(e) {
            e.preventDefault();
            const url = document.getElementById('video-url').value.trim();
            const resultDiv = document.getElementById('result');
            const progressContainer = document.getElementById('progress-container');
            const progressBar = document.getElementById('progress');
            const statusDiv = document.getElementById('status');
            
            if (!url) {
                resultDiv.innerHTML = '<p class="error">Please enter a TikTok URL</p>';
                return;
            }
            
            if (!url.includes('tiktok.com')) {
                resultDiv.innerHTML = '<p class="error">Please enter a valid TikTok URL</p>';
                return;
            }
            
            // Reset UI
            resultDiv.innerHTML = '';
            progressContainer.style.display = 'block';
            progressBar.style.width = '0%';
            statusDiv.textContent = 'Processing URL...';
            
            // Create FormData for the request
            const formData = new FormData();
            formData.append('url', url);
            
            // Create XMLHttpRequest for progress tracking
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/download', true);
            
            xhr.upload.onprogress = function(e) {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    progressBar.style.width = percentComplete + '%';
                    statusDiv.textContent = `Uploading... ${Math.round(percentComplete)}%`;
                }
            };
            
            xhr.onload = function() {
                if (xhr.status === 200) {
                    // Handle the file download
                    const blob = new Blob([xhr.response], {type: 'video/mp4'});
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    
                    // Extract filename from content-disposition or generate one
                    let filename = 'tiktok_video.mp4';
                    const contentDisposition = xhr.getResponseHeader('content-disposition');
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
                        if (filenameMatch) filename = filenameMatch[1];
                    }
                    
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    
                    statusDiv.textContent = 'Download complete!';
                    resultDiv.innerHTML = '<p class="success">Video downloaded successfully!</p>';
                } else {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        resultDiv.innerHTML = `<p class="error">Error: ${error.error || 'Unknown error'}</p>`;
                    } catch {
                        resultDiv.innerHTML = '<p class="error">Error downloading video</p>';
                    }
                    statusDiv.textContent = 'Download failed';
                }
                
                // Hide progress bar after delay
                setTimeout(() => {
                    progressContainer.style.display = 'none';
                }, 3000);
            };
            
            xhr.onerror = function() {
                resultDiv.innerHTML = '<p class="error">Network error occurred</p>';
                statusDiv.textContent = 'Download failed';
                progressContainer.style.display = 'none';
            };
            
            xhr.responseType = 'arraybuffer';
            xhr.send(formData);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/download', methods=['POST'])
def download_video():
    tiktok_url = request.form.get('url')
    
    if not tiktok_url or "tiktok.com" not in tiktok_url:
        return jsonify({'error': 'Invalid TikTok URL'}), 400
    
    try:
        # Get the actual video URL
        video_url = get_video_url(tiktok_url)
        if not video_url:
            return jsonify({'error': 'Could not extract video URL'}), 400
        
        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        elif video_url.startswith('/'):
            video_url = 'https://www.tiktok.com' + video_url
        
        # Generate filename
        video_id = re.search(r'/video/(\d+)', tiktok_url)
        filename = f"tiktok_{video_id.group(1) if video_id else 'video'}.mp4"
        filename = secure_filename(filename)
        save_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Download the video
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
            'Accept': '*/*'
        }
        
        response = requests.get(video_url, headers=headers, stream=True)
        response.raise_for_status()
        
        # Save to file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Return the downloaded file
        return send_file(
            save_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_video_url(tiktok_url):
    try:
        # Method 1: Use TikTok API service
        api_url = f"https://www.tikwm.com/api/?url={tiktok_url}"
        response = requests.get(api_url)
        data = response.json()
        
        if data.get('code') == 0:
            return data['data']['play']
        
        # Method 2: Fallback to web scraping
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(tiktok_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        video_tag = soup.find('video')
        if video_tag:
            return video_tag.get('src')
        
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if script_tag:
            import json
            data = json.loads(script_tag.string)
            return data['props']['pageProps']['videoData']['itemInfos']['video']['urls'][0]
        
        return None
    except Exception as e:
        print(f"Error getting video URL: {e}")
        return None
    
# Required for Vercel
def handler(event, context):
    from flask_lambda import FlaskLambda
    flask_lambda = FlaskLambda(app)
    return flask_lambda(event, context)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
from flask import Flask, render_template, request, redirect, jsonify, Response, stream_with_context
import yt_dlp
import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        # Fetching logs from Supabase
        # .order('created_at', desc=True) sorts them by newest first
        response = supabase.table("download_logs") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({'error': f"Failed to fetch logs: {str(e)}"}), 500
    
@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info.get('formats', []):
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                fmt_url = f.get('url')
                if fmt_url and ((vcodec != 'none' and acodec != 'none') or (vcodec == 'none' and acodec != 'none')):
                    formats.append({
                        'url': fmt_url, 'ext': f.get('ext', 'mp4'), 'height': f.get('height'),
                        'format_note': f.get('format_note'), 'filesize': f.get('filesize'),
                        'vcodec': vcodec, 'acodec': acodec, 'format_id': f.get('format_id')
                    })
            formats.sort(key=lambda x: (x['height'] or 0 if x['vcodec'] != 'none' else 0, x['filesize'] or 0), reverse=True)
            duration = info.get('duration')
            rounded_duration = int(duration) if duration is not None else 0
            return jsonify({
                'title': info.get('title'), 'uploader': info.get('uploader'),
                'duration': rounded_duration, 'thumbnail': info.get('thumbnail'), 'formats': formats
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['GET'])
def proxy_download():
    video_url = request.args.get('url')
    filename = request.args.get('filename', 'video.mp4')
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        supabase.table("download_logs").insert({
            "video_url": video_url,
            "filename": filename
        }).execute()
    except Exception as e:
        app.logger.error(f"Failed to log to Supabase: {str(e)}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Reduce timeout settings if you want it to fail over quickly when a connection hangs
        response = requests.get(video_url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()

        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        return Response(
            stream_with_context(generate()),
            content_type=response.headers.get('Content-Type', 'video/mp4'),
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': response.headers.get('Content-Length')
            }
        )
    except Exception as e:
        # Log the proxy error internally for your debugging records
        app.logger.warning(f"Proxy streaming failed, falling back to direct link redirect. Error: {str(e)}")

        # Redirect the client's browser directly to the media host source link
        return redirect(video_url)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
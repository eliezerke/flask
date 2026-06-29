from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/downloads/<path:filename>')
def download_file(filename):
    # In production, serve from a downloads directory
    downloads_dir = os.path.join(app.root_path, 'downloads')
    return send_from_directory(downloads_dir, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
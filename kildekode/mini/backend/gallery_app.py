import io
from flask import Flask, render_template, Response, send_file

import database
from services.filescanning import get_preview_path

# Initialize the Flask app
app = Flask(__name__)

@app.route('/')
def index():
    """Main gallery page. Fetches the first 100 images and renders the gallery."""
    images = database.get_all_sourcefiles(limit=100)
    return render_template('index.html', images=images)

@app.route('/thumbnail/<int:sourcefile_id>')
def get_thumbnail(sourcefile_id: int):
    """Serves a thumbnail image from the database."""
    source_file = database.get_sourcefile_by_id(sourcefile_id)
    if source_file and source_file.thumbnail:
        return Response(source_file.thumbnail, mimetype='image/jpeg')
    # Return a 404 or a placeholder if not found
    return "Not Found", 404

@app.route('/large/<image_hash>')
def get_large_image(image_hash: str):
    """Serves a large preview image from the filesystem."""
    try:
        # Construct the path to the large preview image
        path = get_preview_path(image_hash)
        # Serve the file
        return send_file(path, mimetype='image/jpeg')
    except FileNotFoundError:
        return "Not Found", 404

if __name__ == '__main__':
    print("Starting the gallery web app!")
    print("Open your browser and go to: http://127.0.0.1:5000")
    app.run(debug=True)

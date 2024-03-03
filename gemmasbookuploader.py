from flask import Flask, render_template, request, redirect, jsonify
import os
from werkzeug.utils import secure_filename
from ebooklib import epub
import base64
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = '/config/'
ALLOWED_EXTENSIONS = {'epub'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_epub_metadata(file_path):
    try:
        book = epub.read_epub(file_path)

        # Extract title and authors
        title = book.get_metadata('DC', 'title')
        authors = book.get_metadata('DC', 'creator')
        title_str = title[0][0] if title else "Unknown Title"
        authors_str = ', '.join([author[0] for author in authors]) if authors else "Unknown Author"

        # Extract cover image
        cover_item = book.get_item_with_id('cover')
        if cover_item:
            cover_bytes = cover_item.content
            cover_image = f"data:image/png;base64,{base64.b64encode(cover_bytes).decode('utf-8')}"
        else:
            cover_image = None

        return {
            'title': title_str,
            'authors': authors_str,
            'cover_image': cover_image,
        }
    except epub.EpubException as e:
        print(f"Error reading ePub file '{file_path}': {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])


# ...

def upload_file():
    metadata = None
    new_path = None

    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            metadata = get_epub_metadata(file_path)

            # If title and authors are provided in the form, update them
            title = request.form.get('title')
            authors = request.form.get('authors')
            if title is not None and authors is not None:
                metadata['title'] = title
                metadata['authors'] = authors

            # Set the destination path for later use
            new_path = os.path.join('/app/downloads', filename)
            print(f"File will be moved to: {new_path}")

            # Ensure we're returning JSON for AJAX requests
            if 'X-Requested-With' in request.headers and request.headers['X-Requested-With'] == 'XMLHttpRequest':
                return jsonify(metadata)

    # Move the file to /app/downloads if new_path is set (button was clicked)
    if new_path:
        shutil.move(file_path, new_path)
        print(f"Moved file to: {new_path}")

    return render_template('upload.html', metadata=metadata)

# ...


if __name__ == '__main__':
    app.run(debug=True, port=8000)
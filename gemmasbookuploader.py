from flask import Flask, render_template, request, redirect, jsonify
import os
from werkzeug.utils import secure_filename
from ebooklib import epub
import shutil
import zipfile

app = Flask(__name__)

UPLOAD_FOLDER = '/config/'
ALLOWED_EXTENSIONS = {'epub'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_epub_metadata(file_path):
    try:
        book = epub.read_epub(file_path)
        title = book.get_metadata('DC', 'title')
        authors = book.get_metadata('DC', 'creator')

        title_str = title[0][0] if title else "Unknown Title"
        authors_str = ', '.join([author[0] for author in authors]) if authors else "Unknown Author"

        return authors_str, title_str
    except epub.EpubException as e:
        print(f"Error reading ePub file '{file_path}': {e}")
        return None, None

def update_epub_metadata(epub_path, new_author, new_title):
    try:
        book = epub.read_epub(epub_path)

        # Update title and authors metadata
        book.set_metadata('DC', 'title', new_title)
        authors = [(new_author, 'aut')]
        book.set_metadata('DC', 'creator', authors)

        # Save changes to a temporary folder
        temp_folder = 'temp_folder'
        os.makedirs(temp_folder, exist_ok=True)
        temp_epub_path = os.path.join(temp_folder, os.path.basename(epub_path))
        epub.write_epub(temp_epub_path, book)

        # Update metadata in ePub file without using OS commands
        with zipfile.ZipFile(epub_path, 'w') as zipf:
            for root, _, files in os.walk(temp_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, temp_folder))

        # Cleanup temporary folder
        shutil.rmtree(temp_folder)

        return True
    except epub.EpubException as e:
        print(f"Error updating ePub metadata for file '{epub_path}': {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
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
            new_title = request.form.get('title')
            new_author = request.form.get('authors')

            if new_title is not None and new_author is not None:
                metadata['title'] = new_title
                metadata['authors'] = new_author

                # Update metadata in the ePub file
                update_success = update_epub_metadata(file_path, new_author, new_title)

                if not update_success:
                    print("Failed to update ePub metadata")

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

if __name__ == '__main__':
    app.run(debug=True, port=8000)

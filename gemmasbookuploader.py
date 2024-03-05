from flask import Flask, render_template, request, redirect, jsonify
import os
from werkzeug.utils import secure_filename
from ebooklib import epub
import shutil
import zipfile
from xml.etree import ElementTree as ET

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
    temp_dir = 'temp_epub_extraction'
    os.makedirs(temp_dir, exist_ok=True)

    # Extract the ePub content to a temporary directory
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Locate the .opf file containing the metadata
    opf_file = None
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.opf'):
                opf_file = os.path.join(root, file)
                break
        if opf_file:
            break

    if not opf_file:
        print("OPF file not found.")
        shutil.rmtree(temp_dir)
        return False

    # Parse the .opf file and update metadata
    tree = ET.parse(opf_file)
    root = tree.getroot()
    namespaces = {'dc': 'http://purl.org/dc/elements/1.1/'}
    
    # Update title
    for title in root.findall('.//dc:title', namespaces):
        title.text = new_title
    
    # Update author
    for creator in root.findall('.//dc:creator', namespaces):
        creator.text = new_author

    tree.write(opf_file)

    # Repack the ePub file
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)

    # Cleanup temporary directory
    shutil.rmtree(temp_dir)
    return True


@app.route('/update-metadata', methods=['POST'])
def update_metadata():
    title = request.form['title']
    authors = request.form['authors']
    epub_path = 'path/to/your/saved/epub/file' # Adjust this to the actual file path

    if update_epub_metadata(epub_path, authors, title):
        return jsonify({'message': 'Metadata updated successfully'}), 200
    else:
        return jsonify({'message': 'Failed to update metadata'}), 500


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

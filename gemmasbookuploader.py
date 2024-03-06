from flask import Flask, render_template, request, redirect, jsonify
import os
import ebooklib
from werkzeug.utils import secure_filename
from ebooklib import epub
import base64
import shutil
import zipfile
from lxml import etree

app = Flask(__name__)

UPLOAD_FOLDER = '/config/'
BOOKS_FOLDER = '/app/books/'
DOWNLOADS_FOLDER = '/app/downloads/'
ALLOWED_EXTENSIONS = {'epub'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['BOOKS_FOLDER'] = BOOKS_FOLDER
app.config['DOWNLOADS_FOLDER'] = DOWNLOADS_FOLDER

import ebooklib
from ebooklib import epub
import base64

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def find_cover_image(book):
    cover_item = None
    
    # Some EPUBs specify the cover image in the metadata
    meta_cover = book.get_metadata('http://www.idpf.org/2007/opf', 'cover')
    if meta_cover:
        cover_id = meta_cover[0][1].get('content')
        cover_item = book.get_item_with_id(cover_id)

    # If not found, try looking for an item with properties="cover-image"
    if not cover_item:
        for item in book.items:
            if item.get_type() == ebooklib.ITEM_IMAGE:
                if 'cover-image' in item.get_name().lower() or 'cover' in item.get_name().lower():
                    cover_item = item
                    break

    # Returning the content of the cover image if found
    if cover_item:
        return cover_item.get_content()

    return None

def get_epub_metadata(file_path):
    try:
        book = epub.read_epub(file_path)

        # Extract title and authors
        title = book.get_metadata('DC', 'title')
        authors = book.get_metadata('DC', 'creator')
        title_str = title[0][0] if title else "Unknown Title"
        authors_str = ', '.join([author[0] for author in authors]) if authors else "Unknown Author"

        # Attempt to extract the cover image
        cover_bytes = find_cover_image(book)
        
        # Use a default cover image if extraction fails
        if cover_bytes:
            cover_image = f"data:image/png;base64,{base64.b64encode(cover_bytes).decode('utf-8')}"
        else:
            # Blank out the cover if extraction fails
            cover_image = None

        return {
            'title': title_str,
            'authors': authors_str,
            'cover_image': cover_image,
        }
    except epub.EpubException as e:
        print(f"Error reading ePub file '{file_path}': {e}")
        # If an error occurs, still provide the rest of the metadata with no cover
        return {
            'title': "Unknown Title",
            'authors': "Unknown Author",
            'cover_image': None,
        }
    except Exception as e:
        print(f"Error reading ePub file '{file_path}': {e}")
        # If an error occurs, still provide the rest of the metadata with no cover
        return {
            'title': "Unknown Title",
            'authors': "Unknown Author",
            'cover_image': None,
        }

   
def update_epub_metadata(epub_file, new_title, new_authors):
    # Temporary directory to extract ePub contents
    temp_dir = "temp_epub_extract"
    os.makedirs(temp_dir, exist_ok=True)

    with zipfile.ZipFile(epub_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    metadata = get_epub_metadata(epub_file)
    title = metadata['title']
    authors = metadata['authors']

    opf_path = None
    # Find the .opf file
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.opf'):
                opf_path = os.path.join(root, file)
                break
        if opf_path:
            break

    if not opf_path:
        raise Exception("OPF file not found in ePub")

    # Parse the .opf file and update metadata
    ns = {'opf': 'http://www.idpf.org/2007/opf', 'dc': 'http://purl.org/dc/elements/1.1/'}
    tree = etree.parse(opf_path)
    title_elem = tree.find('.//dc:title', namespaces=ns)
    if title_elem is not None:
        title_elem.text = new_title
    creator_elems = tree.findall('.//dc:creator', namespaces=ns)
    for creator_elem in creator_elems:
        creator_elem.text = new_authors

    tree.write(opf_path, encoding='utf-8', xml_declaration=True, pretty_print=True)

    # Repackage the ePub file
    with zipfile.ZipFile(epub_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)

    # Clean up the temporary directory
    shutil.rmtree(temp_dir)

    return title, authors

def get_books_in_library():
    books = []
    for root, dirs, files in os.walk(app.config['BOOKS_FOLDER']):
        for file in files:
            if file.endswith('.epub'):
                file_path = os.path.join(root, file)
                metadata = get_epub_metadata(file_path)
                if metadata:
                    metadata['file_path'] = file_path
                    books.append(metadata)
    return books

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    current_metadata = None
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
            current_metadata = get_epub_metadata(file_path)

            # If title and authors are provided in the form, update them
            new_title = request.form.get('new-title')
            new_authors = request.form.get('new-authors')
            if new_title is not None and new_authors is not None:
                current_metadata['title'], current_metadata['authors'] = update_epub_metadata(file_path, new_title, new_authors)

                # Set the destination path for later use
                new_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)
                print(f"File will be moved to: {new_path}")

    # Move the file to /app/books if new_path is set (button was clicked)
    if new_path:
        shutil.move(file_path, new_path)
        print(f"Moved file to: {new_path}")

    # Ensure we're returning JSON for AJAX requests
    if 'X-Requested-With' in request.headers and request.headers['X-Requested-With'] == 'XMLHttpRequest':
        return jsonify(current_metadata)

    # Handle initial page load
    books_in_library = get_books_in_library()
    return render_template('upload.html', current_metadata=current_metadata, books=books_in_library)

@app.route('/library')
def library():
    books_in_library = get_books_in_library()
    return render_template('library.html', books=books_in_library)

if __name__ == '__main__':
    # Start the Flask app
    app.run(debug=True, port=6000)
    
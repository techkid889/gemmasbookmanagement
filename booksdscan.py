import os
import shutil
import time
from ebooklib import epub
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

def get_epub_metadata(epub_path):
    """Extracts the author and title from an ePub file."""
    try:
        book = epub.read_epub(epub_path)
        title = book.get_metadata('DC', 'title')
        authors = book.get_metadata('DC', 'creator')

        title_str = title[0][0] if title else "Unknown Title"
        authors_str = ', '.join([author[0] for author in authors]) if authors else "Unknown Author"

        return authors_str, title_str
    except epub.EpubException as e:
        print(f"Error reading ePub file '{epub_path}': {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected error reading ePub file '{epub_path}': {e}")
        return None, None

def process_directory(root_dir, target_root):
    """Searches directories for ePub files, renames, moves, and deletes the original folder."""
    for subdir, dirs, files in os.walk(root_dir):
        # Process directories
        for directory in dirs:
            directory_path = os.path.join(subdir, directory)
            process_epub_directory(directory_path, target_root)

        # Process files in the root of root_dir
        for file in files:
            if file.endswith('.epub'):
                epub_path = os.path.join(root_dir, file)
                author, title = get_epub_metadata(epub_path)

                if author is not None and title is not None:
                    # Create directories for author and title
                    author_dir = os.path.join(target_root, author.replace("/", "-"))
                    title_dir = os.path.join(author_dir, title.replace("/", "-"))

                    # Create the directories if they don't exist
                    os.makedirs(title_dir, exist_ok=True)

                    # Construct the new filename and path
                    new_filename = f"{author} - {title}.epub".replace("/", "-")  # Avoid path issues
                    new_path = os.path.join(title_dir, new_filename)

                    shutil.move(epub_path, new_path)
                    print(f"Moved: {new_path}")

        # Check if the root directory is empty and delete if true
        if not os.listdir(root_dir):
            shutil.rmtree(root_dir)
            print(f"Deleted empty directory: {root_dir}")

def process_epub_directory(directory_path, target_root):
    """Processes an individual directory for ePub files and moves them to the target location."""
    # Check if there are .epub files within the directory
    epub_files = [file for file in os.listdir(directory_path) if file.endswith('.epub')]

    if epub_files:
        for file in epub_files:
            epub_path = os.path.join(directory_path, file)
            author, title = get_epub_metadata(epub_path)

            if author is not None and title is not None:
                # Create directories for author and title
                author_dir = os.path.join(target_root, author.replace("/", "-"))
                title_dir = os.path.join(author_dir, title.replace("/", "-"))

                # Create the directories if they don't exist
                os.makedirs(title_dir, exist_ok=True)

                # Construct the new filename and path
                new_filename = f"{author} - {title}.epub".replace("/", "-")  # Avoid path issues
                new_path = os.path.join(title_dir, new_filename)

                shutil.move(epub_path, new_path)
                print(f"Moved: {new_path}")

        # Check if the directory is empty and delete if true
        if not os.listdir(directory_path):
            shutil.rmtree(directory_path)
            print(f"Deleted empty directory: {directory_path}")

class BookHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.epub'):
            print(f"New ePub file detected: {event.src_path}")
            process_epub_file(event.src_path, target_directory)
        else:
            print(f"Ignoring non-ePub file: {event.src_path}")

def process_epub_file(epub_path, target_root):
    """Processes an individual ePub file and moves it to the target location."""
    try:
        author, title = get_epub_metadata(epub_path)

        if author is not None and title is not None:
            # Create directories for author and title
            author_dir = os.path.join(target_root, author.replace("/", "-"))
            title_dir = os.path.join(author_dir, title.replace("/", "-"))

            # Create the directories if they don't exist
            os.makedirs(title_dir, exist_ok=True)

            # Construct the new filename and path
            new_filename = f"{author} - {title}.epub".replace("/", "-")  # Avoid path issues
            new_path = os.path.join(title_dir, new_filename)

            shutil.move(epub_path, new_path)
            print(f"Moved: {new_path}")

        # Check if the directory containing the file is empty and delete if true
        containing_directory = os.path.dirname(epub_path)
        if not os.listdir(containing_directory):
            shutil.rmtree(containing_directory)
            print(f"Deleted empty directory: {containing_directory}")

    except Exception as e:
        print(f"Error processing ePub file '{epub_path}': {e}")

# ... (rest of the code remains unchanged)


if __name__ == "__main__":
    # Set the root directory to check for new directories and subdirectories
    root_directory = '/app/downloads/'
    target_directory = '/app/books/'

    # Set up the observer to watch for file creation events using PollingObserver
    event_handler = BookHandler()
    observer = PollingObserver()
    observer.schedule(event_handler, path=root_directory, recursive=True)

    print(f"Watching for new ePub files in: {root_directory}")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

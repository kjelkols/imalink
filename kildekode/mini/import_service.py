import os
import logging
import io
from PIL import Image

# Import the new, clean functions
import database
import exif_service
from config import THUMBNAIL_SIZE

def import_photos(source_dir: str):
    """
    Scans a directory for images, generates thumbnails, cleans EXIF data,
    and saves everything to the database using the modern data access layer.
    """
    logging.info(f"Starting photo import from directory: {source_dir}")
    # Ensure the database and table exist before starting
    database.init_db()

    tags_to_remove = ["thumbnail", "MakerNote", "UserComment"]
    logging.info(f"The following EXIF tags will be removed: {tags_to_remove}")

    processed_files_count = 0
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg")):
                processed_files_count += 1
                full_path = os.path.join(root, file)
                logging.info(f"Processing: {full_path}")

                try:
                    # 1. Create thumbnail
                    thumbnail_bytes = create_thumbnail(full_path)
                    if not thumbnail_bytes:
                        continue  # Skip if thumbnail creation failed

                    # 2. Get raw EXIF data
                    raw_exif = exif_service.get_raw_exif_from_image(full_path)

                    # 3. Clean the EXIF data
                    cleaned_exif = exif_service.clean_exif_data(raw_exif, tags_to_remove)

                    # 4. Add to database using the clean data access function
                    new_id = database.add_sourcefile(
                        filename=full_path,
                        thumbnail=thumbnail_bytes,
                        exif_data=cleaned_exif
                    )
                    logging.info(f'Successfully added "{os.path.basename(full_path)}" with new ID: {new_id}')

                except Exception as e:
                    logging.error(f"Failed to import {full_path}: {e}")

    if processed_files_count == 0:
        logging.warning(f"No .jpg or .jpeg files found in '{source_dir}'.")

    logging.info(f"Photo import process finished. Processed {processed_files_count} files.")


def create_thumbnail(image_path: str) -> bytes | None:
    """Creates a thumbnail for a given image and returns it as bytes."""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return buf.getvalue()
    except Exception as e:
        logging.error(f"Failed to create thumbnail for {image_path}: {e}")
        return None


if __name__ == '__main__':
    # IMPORTANT: Replace this with a real directory on your system.
    photo_directory_to_scan = r"C:\temp\PHOTOS_SRC_TEST_MICRO"

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if os.path.isdir(photo_directory_to_scan):
        import_photos(photo_directory_to_scan)
    else:
        logging.error(f"Directory not found: '{photo_directory_to_scan}'. Please update the variable in import_service.py")


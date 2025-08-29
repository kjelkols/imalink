import os
import logging
import io
from typing import Tuple
from PIL import Image
import imagehash

import database
from services import exif as exif_service
from config import THUMBNAIL_SIZE, LARGE_PATH, LARGE_SIZE

def get_preview_path(image_hash: str) -> str:
    """
    Constructs a nested file path from an image hash to avoid having
    too many files in a single directory.
    Example: 'f068999999996868' -> 'C:/temp/00imalink/large/f0/68/f068999999996868.jpg'
    """
    dir1 = image_hash[0:2]
    dir2 = image_hash[2:4]
    filename = f"{image_hash}.jpg"
    return os.path.join(LARGE_PATH, dir1, dir2, filename)

def create_preview_image(source_path: str, target_path: str, size: Tuple[int, int]):
    """
    Creates a downscaled version of an image, ensuring the target directory exists.
    """
    try:
        target_dir = os.path.dirname(target_path)
        os.makedirs(target_dir, exist_ok=True)

        with Image.open(source_path) as img:
            img.thumbnail(size)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(target_path, "JPEG", quality=85, optimize=True)
        logging.info(f"Successfully created preview: {os.path.basename(target_path)}")
    except Exception as e:
        logging.error(f"Failed to create preview for {source_path}: {e}")

def import_photos(source_dir: str):
    """
    Scans a directory for images, generates thumbnails and previews,
    and saves metadata to the database.
    """
    logging.info(f"Starting photo import from directory: {source_dir}")
    database.init_db()

    tags_to_remove = ["thumbnail", "MakerNote", "UserComment"]
    logging.info(f"The following EXIF tags will be removed: {tags_to_remove}")

    processed_files_count = 0
    duplicates_found_count = 0
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
                        continue

                    # 2. Calculate perceptual hash from thumbnail
                    thumb_image = Image.open(io.BytesIO(thumbnail_bytes))
                    hash_val = imagehash.phash(thumb_image)
                    hash_str = str(hash_val)

                    # 3. Check for duplicates using the hash
                    existing_file = database.get_sourcefile_by_hash(hash_str)
                    if existing_file:
                        logging.warning(f'Duplicate found for "{os.path.basename(full_path)}". Existing file is "{existing_file.filename}". Skipping.')
                        duplicates_found_count += 1
                        continue

                    # 4. Create and save preview image using config values
                    preview_path = get_preview_path(hash_str)
                    create_preview_image(full_path, preview_path, LARGE_SIZE)

                    # 5. Get raw EXIF data
                    raw_exif = exif_service.get_raw_exif_from_image(full_path)

                    # 6. Clean the EXIF data
                    cleaned_exif = exif_service.clean_exif_data(raw_exif, tags_to_remove)

                    # 7. Add to database
                    new_id = database.add_sourcefile(
                        filename=full_path,
                        image_hash=hash_str,
                        thumbnail=thumbnail_bytes,
                        exif_data=cleaned_exif
                    )
                    logging.info(f'Successfully added "{os.path.basename(full_path)}" with new ID: {new_id}')

                except Exception as e:
                    logging.error(f"Failed to import {full_path}: {e}", exc_info=True)

    if processed_files_count == 0:
        logging.warning(f"No .jpg or .jpeg files found in '{source_dir}'.")

    logging.info(f"Photo import process finished. Processed {processed_files_count} files. Found and skipped {duplicates_found_count} duplicates.")

def create_thumbnail(image_path: str) -> bytes | None:
    """Creates a thumbnail for a given image and returns it as bytes."""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            buf = io.BytesIO()
            # Convert to RGB if it's not, to ensure it can be saved as JPEG
            if img.mode != 'RGB':
                img = img.convert('RGB')
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
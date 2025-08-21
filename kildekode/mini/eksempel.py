import os
from PIL import Image
import io
from models import SourceFile

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}

def is_image_file(filename):
    return os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS

def create_thumbnail(image_path, size=(128, 128)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return buf.getvalue()
    except Exception:
        return None

def scan_and_import_images(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if is_image_file(filename):
                full_path = os.path.join(dirpath, filename)
                thumbnail = create_thumbnail(full_path)
                with open(full_path, "rb") as f:
                    image_data = f.read()
                # Her kan du legge inn EXIF-data hvis ønskelig, f.eks. med Pillow
                exif_data = None
                try:
                    with Image.open(full_path) as img:
                        exif_data = img.info.get('exif')
                except Exception:
                    pass
                sourcefile = SourceFile(
                    filename=full_path,
                    thumbnail=thumbnail,
                    exif_data=exif_data
                )
                sourcefile.add()
                print(f"Lagt inn: {full_path}")

if __name__ == "__main__":
    import database
    database.init_db()
    scan_and_import_images(r"C:\temp\PHOTOS_SRC_TEST_MICRO")
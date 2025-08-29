import logging
import os
import sys

# Add the backend directory to the Python path to allow for imports from the services package
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.filescanning import import_photos

def run():
    """
    Runs the photo import process for a specified directory.
    """
    # The directory to scan, as requested by the user.
    photo_directory_to_scan = r"C:\temp\PHOTOS_SRC_TEST_MICRO"

    # Configure logging to print to the console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    logging.info("--- Starting Photo Import Experiment ---")
    logging.info(f"Target directory: {photo_directory_to_scan}")

    if not os.path.isdir(photo_directory_to_scan):
        logging.error(f"Directory not found: '{photo_directory_to_scan}'")
        logging.error("Please ensure the directory exists and the path is correct.")
        return

    try:
        import_photos(photo_directory_to_scan)
        logging.info("--- Experiment Finished Successfully ---")
    except Exception as e:
        logging.error(f"An unexpected error occurred during the experiment: {e}", exc_info=True)
        logging.error("--- Experiment Finished with Errors ---")

if __name__ == "__main__":
    run()

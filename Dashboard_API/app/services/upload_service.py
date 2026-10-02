import os
import time
import pandas as pd
from werkzeug.utils import secure_filename
from flask import current_app
from app.utils.csv_validator import validate_csv_columns

class UploadService:
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

    @staticmethod
    def save_and_validate(file_storage, username):
        if not file_storage or file_storage.filename == '':
            raise ValueError("No file uploaded or file empty.")
            
        if not UploadService.allowed_file(file_storage.filename):
            raise ValueError("Invalid file extension. Only CSV files are accepted.")
            
        # Ensure directories exist
        uploads_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
            
        orig_filename = file_storage.filename
        safe_filename = f"{int(time.time())}_{secure_filename(orig_filename)}"
        filepath = os.path.join(uploads_dir, safe_filename)
        file_storage.save(filepath)
        
        # Read CSV to validate columns
        try:
            # Let's read the first row using pandas to validate columns quickly
            df = pd.read_csv(filepath, nrows=1)
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            raise ValueError(f"Failed to parse CSV file: {e}")
            
        validate_csv_columns(df.columns)
            
        return filepath, safe_filename

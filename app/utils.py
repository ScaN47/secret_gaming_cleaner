import secrets, os
from pathlib import Path
from werkzeug.utils import secure_filename
from encryption import encrypt_file

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = None  # None = accept all, or set set(['png','jpg','pdf'])

def random_id(n=8):
    return secrets.token_urlsafe(n)[:n]

def save_file(file_storage, file_id):
    """
    Save uploaded file with encryption.
    file_id is used for encryption key derivation.
    """
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
    if ALLOWED_EXT and ext.lower() not in ALLOWED_EXT:
        raise ValueError("extension not allowed")
    token = random_id(12)
    stored_name = f"{token}_{filename}"
    path = UPLOAD_FOLDER / stored_name
    file_storage.save(path)
    
    # Encrypt the file
    encrypt_file(str(path), file_id)
    
    return filename, str(path)

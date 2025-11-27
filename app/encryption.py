from cryptography.fernet import Fernet
import base64
import os
import hashlib
import hmac

# Master key for encryption (should be environment variable in production)
MASTER_KEY = os.environ.get('ENCRYPTION_KEY', 'default-master-key-change-in-production')

def derive_key(file_id: str, salt: bytes = None) -> tuple:
    """
    Derive encryption key from file ID and optional salt.
    Returns: (key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    # Use PBKDF2 equivalent with hashlib
    key_material = hashlib.pbkdf2_hmac(
        'sha256',
        (file_id + MASTER_KEY).encode(),
        salt,
        100000
    )
    key = base64.urlsafe_b64encode(key_material)
    
    return key, salt

def encrypt_file(file_path: str, file_id: str) -> bytes:
    """
    Read file, encrypt it, and return encrypted content.
    Also saves metadata (salt) separately.
    """
    # Generate key and salt for this file
    key, salt = derive_key(file_id)
    cipher = Fernet(key)
    
    # Read file
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    # Encrypt
    encrypted_data = cipher.encrypt(file_data)
    
    # Save salt for later decryption
    salt_file = file_path + '.salt'
    with open(salt_file, 'wb') as f:
        f.write(salt)
    
    # Write encrypted data back to file
    with open(file_path, 'wb') as f:
        f.write(encrypted_data)
    
    return encrypted_data

def decrypt_file_content(encrypted_data: bytes, file_id: str) -> bytes:
    """
    Decrypt file content using file_id and stored salt.
    """
    # We need to get the salt - it should be stored somewhere
    # For now, we'll read it from the salt file if available
    return decrypt_file(None, file_id, encrypted_data)

def decrypt_file(file_path: str, file_id: str, encrypted_data: bytes = None) -> bytes:
    """
    Decrypt file using file_id and salt.
    If file_path is provided, reads from file.
    If encrypted_data is provided, uses that instead.
    """
    salt_file = file_path + '.salt' if file_path else None
    
    # Get salt
    if salt_file and os.path.exists(salt_file):
        with open(salt_file, 'rb') as f:
            salt = f.read()
    else:
        # If no salt file, this shouldn't happen in normal operation
        raise ValueError("Salt file not found for decryption")
    
    # Derive same key
    key, _ = derive_key(file_id, salt)
    cipher = Fernet(key)
    
    # Read encrypted data if not provided
    if encrypted_data is None:
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()
    
    # Decrypt
    try:
        decrypted_data = cipher.decrypt(encrypted_data)
        return decrypted_data
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")

def cleanup_salt_file(file_path: str):
    """
    Clean up salt file when original file is deleted.
    """
    salt_file = file_path + '.salt'
    if os.path.exists(salt_file):
        try:
            os.remove(salt_file)
        except Exception:
            pass

import secrets
from flask import Flask, request, jsonify, send_file, abort, render_template
from models import init_db, insert_file, get_file, increment_download, delete_file_record
from utils import save_file
from encryption import decrypt_file, cleanup_salt_file
import time
import os
import io
import qrcode
from threading import Thread
from cleanup import cleanup_expired_files

app = Flask(__name__, template_folder='templates')
init_db()

# Start cleanup thread
def cleanup_thread():
    """Run cleanup every hour"""
    while True:
        time.sleep(3600)  # Run every hour
        cleanup_expired_files()

cleanup_t = Thread(target=cleanup_thread, daemon=True)
cleanup_t.start()

# Configs - tweak
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
DEFAULT_EXPIRE_SECONDS = 24 * 3600

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/qr/<id_>', methods=['GET'])
def get_qr_code(id_):
    """Generate QR code for download link"""
    try:
        link = request.host_url.rstrip('/') + '/d/' + id_
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(link)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/file/<id_>', methods=['GET'])
def get_file_info(id_):
    rec = get_file(id_)
    if not rec:
        return jsonify({"error":"not found"}), 404
    
    # check expiry
    if rec['expire_ts'] and rec['expire_ts'] < int(time.time()):
        # delete file
        try:
            os.remove(rec['stored_path'])
            cleanup_salt_file(rec['stored_path'])
        except Exception:
            pass
        delete_file_record(id_)
        return jsonify({"error":"not found"}), 404
    
    # password check
    pwd = request.args.get('password')
    if rec['password'] and rec['password'] != pwd:
        return jsonify({"error":"password required"}), 403
    
    # max downloads check
    remaining = None
    if rec['max_downloads']:
        remaining = max(0, rec['max_downloads'] - rec['downloads'])
        if remaining == 0:
            return jsonify({"error":"max downloads reached"}), 404
    
    # Calculate remaining time
    remaining_time = None
    if rec['expire_ts']:
        remaining_seconds = rec['expire_ts'] - int(time.time())
        if remaining_seconds > 0:
            remaining_time = remaining_seconds
        else:
            return jsonify({"error":"file expired"}), 404
    
    return jsonify({
        "filename": rec['filename'],
        "downloads": rec['downloads'],
        "remaining": remaining,
        "remaining_time": remaining_time,
        "protected": rec['password'] is not None,
        "encrypted": True
    })

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error":"no file"}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({"error":"empty filename"}), 400
    
    # Generate ID first (needed for encryption)
    id_ = secrets.token_urlsafe(9)
    
    # optional: check content-length header
    filename, stored_path = save_file(f, id_)
    password = request.form.get('password') or None
    expire_seconds = int(request.form.get('expire_seconds') or DEFAULT_EXPIRE_SECONDS)
    max_downloads = int(request.form.get('max_downloads') or 0)  # 0 = unlimited

    meta = {
        'id': id_,
        'filename': filename,
        'stored_path': stored_path,
        'password': password,
        'max_downloads': max_downloads,
        'expire_ts': int(time.time()) + expire_seconds
    }
    insert_file(meta)
    link = request.host_url.rstrip('/') + '/d/' + id_
    return jsonify({"link": link, "id": id_})

@app.route('/d/<id_>', methods=['GET'])
def download(id_):
    rec = get_file(id_)
    if not rec:
        return render_template('download.html'), 404
    
    # check expiry
    if rec['expire_ts'] and rec['expire_ts'] < int(time.time()):
        # delete file
        try:
            os.remove(rec['stored_path'])
            cleanup_salt_file(rec['stored_path'])
        except Exception:
            pass
        delete_file_record(id_)
        return render_template('download.html'), 404
    
    # password check
    pwd = request.args.get('password')
    if rec['password'] and rec['password'] != pwd:
        return render_template('download.html'), 403
    
    # max downloads check
    if rec['max_downloads'] and rec['downloads'] >= rec['max_downloads']:
        # delete
        try: 
            os.remove(rec['stored_path'])
            cleanup_salt_file(rec['stored_path'])
        except: 
            pass
        delete_file_record(id_)
        return render_template('download.html'), 404
    
    # serve file
    increment_download(id_)
    
    # Decrypt file before sending
    try:
        decrypted_data = decrypt_file(rec['stored_path'], id_)
        
        # Send decrypted file
        return send_file(
            io.BytesIO(decrypted_data),
            as_attachment=True,
            download_name=rec['filename']
        )
    except Exception as e:
        return jsonify({"error": f"Decryption failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

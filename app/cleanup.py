import os
import time
from pathlib import Path
from models import get_all_files, delete_file_record
from encryption import cleanup_salt_file

UPLOAD_FOLDER = Path(__file__).parent / "uploads"

def cleanup_expired_files():
    """
    Delete expired files from disk and database.
    Should be called periodically (e.g., via APScheduler).
    """
    try:
        from models import conn
        c = conn.cursor()
        c.execute('SELECT id, stored_path, expire_ts FROM files')
        records = c.fetchall()
        conn.close()
        
        current_time = int(time.time())
        deleted_count = 0
        
        for record in records:
            file_id, stored_path, expire_ts = record
            
            # Check if file is expired
            if expire_ts and expire_ts < current_time:
                try:
                    # Delete file from disk
                    if os.path.exists(stored_path):
                        os.remove(stored_path)
                    cleanup_salt_file(stored_path)
                    
                    # Delete from database
                    delete_file_record(file_id)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_id}: {str(e)}")
        
        print(f"Cleanup completed: {deleted_count} expired files deleted")
        return deleted_count
    except Exception as e:
        print(f"Cleanup error: {str(e)}")
        return 0

def cleanup_orphaned_files():
    """
    Delete files that exist on disk but not in database.
    """
    try:
        from models import get_all_files
        
        # Get all files in database
        db_files = set()
        from models import conn
        c = conn.cursor()
        c.execute('SELECT stored_path FROM files')
        db_records = c.fetchall()
        conn.close()
        
        for record in db_records:
            db_files.add(record[0])
        
        # Check disk
        deleted_count = 0
        if UPLOAD_FOLDER.exists():
            for file_path in UPLOAD_FOLDER.glob('*'):
                if not file_path.name.endswith('.salt'):
                    if str(file_path) not in db_files:
                        try:
                            os.remove(file_path)
                            cleanup_salt_file(str(file_path))
                            deleted_count += 1
                        except Exception as e:
                            print(f"Error deleting orphaned file {file_path}: {str(e)}")
        
        print(f"Orphaned cleanup completed: {deleted_count} files deleted")
        return deleted_count
    except Exception as e:
        print(f"Orphaned cleanup error: {str(e)}")
        return 0

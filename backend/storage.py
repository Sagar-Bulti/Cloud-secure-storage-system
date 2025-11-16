import os, json, datetime
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import resend


# ---------------- Load Environment ----------------
BASE_DIR = os.path.dirname(__file__)   # define BASE_DIR again
load_dotenv()  # loads .env from project root automatically

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")  # Not used anymore, kept for compatibility
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
OTP_EXPIRY = int(os.getenv("OTP_EXPIRY", 180))  # must be OTP_EXPIRY in .env

# Configure Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# ---------------- Paths ----------------
USERS_FILE = os.path.join(BASE_DIR, "..", "db", "users.json")
OTP_FILE = os.path.join(BASE_DIR, "..", "db", "otp.json")
LOG_FILE = os.path.join(BASE_DIR, "..", "db", "access_log.json")
META_FILE = os.path.join(BASE_DIR, "..", "db", "files.json")
LOCAL_STORE = os.path.join(BASE_DIR, "..", "local_store")
TEMP_STORE = os.path.join(BASE_DIR, "..", "temp")
KEY_FILE = os.path.join(BASE_DIR, "..", "db", "secret.key")


# Make sure db directory exists
os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
os.makedirs(os.path.dirname(OTP_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(LOCAL_STORE, exist_ok=True)
os.makedirs(TEMP_STORE, exist_ok=True)

# ---------------- User Helpers ----------------
def load_users():
    """Load users map from JSON file. Returns {} if not present."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# ---------------- OTP Helpers ----------------
def send_email(to_email, subject, message):
    """Send email using Resend API."""
    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY not configured.")
        return False
    if not EMAIL_USER:
        print("❌ EMAIL_USER (from email) not configured.")
        return False
    try:
        params = {
            "from": f"Cloud Storage <{EMAIL_USER}>",
            "to": [to_email],
            "subject": subject,
            "text": message,
        }
        resend.Emails.send(params)
        print(f"📧 Email sent to {to_email} via Resend")
        return True
    except Exception as e:
        print("❌ Email sending failed:", str(e))
        print(f"⚠️ Unable to send OTP email to {to_email} (check SMTP settings).")
        return False

def save_otp(email, otp_code):
    """Save OTP (with created_at) and send it to the user's email."""
    os.makedirs(os.path.dirname(OTP_FILE), exist_ok=True)
    data = {}
    if os.path.exists(OTP_FILE):
        with open(OTP_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}

    # Clean expired OTPs
    now = datetime.datetime.now(datetime.timezone.utc)
    for user, record in list(data.items()):
        try:
            created_at = datetime.datetime.fromisoformat(record.get("created_at"))
            if (now - created_at).total_seconds() > OTP_EXPIRY:
                data.pop(user, None)
        except Exception:
            data.pop(user, None)

    data[email] = {
        "otp": str(otp_code),
        "created_at": now.replace(microsecond=0, tzinfo=None).isoformat() + 'Z'
    }
    with open(OTP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Send OTP via email
    sent = send_email(email, "Your OTP Code", f"Your OTP is: {otp_code}")
    if not sent:
        print(f"⚠️ Unable to send OTP email to {email} (check SMTP settings).")

def verify_otp(email, otp_code):
    """Validate OTP: existence and not expired."""
    if not os.path.exists(OTP_FILE):
        return False

    try:
        with open(OTP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    record = data.get(email)
    if not record:
        return False

    try:
        created_at = datetime.datetime.fromisoformat(record.get("created_at"))
    except Exception:
        return False

    now = datetime.datetime.now(datetime.timezone.utc)
    if (now - created_at).total_seconds() > OTP_EXPIRY:
        return False

    stored_otp = str(record.get("otp", "")).strip()
    input_otp = str(otp_code or "").strip()
    return stored_otp == input_otp

# ---------------- Encryption (Fernet) ----------------
def init_keys():
    """Initialize or load a Fernet key stored at KEY_FILE and return a Fernet instance."""
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        print("🔐 Generated new encryption key")
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    try:
        return Fernet(key)
    except Exception as e:
        print("❌ Failed to initialize Fernet with key:", e)
        raise

# initialize module-level fernet (app can call init_keys() too)
fernet = init_keys()

# ---------------- File Metadata ----------------
def load_metadata():
    """Return metadata dict stored in META_FILE (create if missing)."""
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    if not os.path.exists(META_FILE):
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(META_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_metadata(data):
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------------- File Handling ----------------
def encrypt_file_and_store(filepath, filename, user_email, folder="/"):
    """Encrypt a local file and store it in LOCAL_STORE. Update metadata and return info."""
    os.makedirs(LOCAL_STORE, exist_ok=True)
    safe_name = f"{user_email.replace('@','_at_')}_{filename}"
    save_path = os.path.join(LOCAL_STORE, safe_name)

    with open(filepath, "rb") as f:
        data = f.read()
    encrypted = fernet.encrypt(data)

    with open(save_path, "wb") as f:
        f.write(encrypted)

    # remove the original uploaded temp file if it exists
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print("⚠️ Could not remove temp upload file:", e)

    meta = load_metadata()
    meta[safe_name] = {
        "owner": user_email,
        "original_name": filename,
        "uploaded_at": datetime.datetime.utcnow().isoformat() + 'Z',
        "folder": folder,
        "size": len(data)
    }
    save_metadata(meta)

    return {"stored_as": safe_name, "original": filename, "owner": user_email, "folder": folder}

def decrypt_and_get_file(filename, user_email):
    """
    Decrypt a stored file for the given owner+original name and write to TEMP_STORE.
    Returns the path to the temporary decrypted file (caller should remove it).
    """
    meta = load_metadata()
    record = None
    stored_filename = None
    for stored, details in meta.items():
        if details.get("original_name") == filename and details.get("owner") == user_email:
            record = details
            stored_filename = stored
            break
    if not record:
        return None

    save_path = os.path.join(LOCAL_STORE, stored_filename)
    if not os.path.exists(save_path):
        return None

    with open(save_path, "rb") as f:
        encrypted = f.read()
    try:
        decrypted = fernet.decrypt(encrypted)
    except Exception as e:
        print("❌ Decryption failed:", e)
        return None

    os.makedirs(TEMP_STORE, exist_ok=True)
    out_file = os.path.join(TEMP_STORE, record["original_name"])
    with open(out_file, "wb") as f:
        f.write(decrypted)

    return out_file

def decrypt_and_get_file_by_stored_name(stored_filename, user_email):
    """
    Decrypt a file using the stored filename directly.
    Returns the path to the temporary decrypted file (caller should remove it).
    """
    meta = load_metadata()
    record = meta.get(stored_filename)
    
    if not record or record.get("owner") != user_email:
        return None

    save_path = os.path.join(LOCAL_STORE, stored_filename)
    if not os.path.exists(save_path):
        return None

    with open(save_path, "rb") as f:
        encrypted = f.read()
    try:
        decrypted = fernet.decrypt(encrypted)
    except Exception as e:
        print("❌ Decryption failed:", e)
        return None

    os.makedirs(TEMP_STORE, exist_ok=True)
    out_file = os.path.join(TEMP_STORE, record["original_name"])
    with open(out_file, "wb") as f:
        f.write(decrypted)

    return out_file

def delete_file(filename, user_email):
    """Soft delete file by setting deleted_at timestamp. Returns True if deleted."""
    meta = load_metadata()
    to_delete = None
    
    # Try to find by stored name first, then by original name
    for stored_name, details in meta.items():
        if details["owner"] == user_email:
            if stored_name == filename or details["original_name"] == filename:
                to_delete = stored_name
                break

    if not to_delete:
        return False

    # Soft delete: set timestamp instead of removing
    import datetime
    meta[to_delete]["deleted_at"] = datetime.datetime.utcnow().isoformat() + 'Z'
    save_metadata(meta)
    return True

def restore_file(filename, user_email):
    """Restore a soft-deleted file. Returns True if restored."""
    meta = load_metadata()
    to_restore = None
    
    # Try to find by stored name first, then by original name
    for stored_name, details in meta.items():
        if details["owner"] == user_email:
            if stored_name == filename or details["original_name"] == filename:
                to_restore = stored_name
                break

    if not to_restore or "deleted_at" not in meta[to_restore]:
        return False

    # Remove deleted_at timestamp to restore
    meta[to_restore].pop("deleted_at", None)
    save_metadata(meta)
    return True

def permanently_delete_file(filename, user_email):
    """Permanently delete file and its metadata. Returns True if deleted."""
    meta = load_metadata()
    to_delete = None
    
    # Try to find by stored name first, then by original name
    for stored_name, details in meta.items():
        if details["owner"] == user_email:
            if stored_name == filename or details["original_name"] == filename:
                to_delete = stored_name
                break

    if not to_delete:
        return False

    filepath = os.path.join(LOCAL_STORE, to_delete)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print("⚠️ Could not remove stored file:", e)

    meta.pop(to_delete, None)
    save_metadata(meta)
    return True

def cleanup_old_trash():
    """Permanently delete files in trash older than 30 days."""
    import datetime
    meta = load_metadata()
    now = datetime.datetime.utcnow()
    deleted_count = 0
    
    for stored_name, details in list(meta.items()):
        if "deleted_at" in details:
            deleted_at = datetime.datetime.fromisoformat(details["deleted_at"].replace('Z', ''))
            days_old = (now - deleted_at).days
            if days_old >= 30:
                # Permanently delete
                filepath = os.path.join(LOCAL_STORE, stored_name)
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    meta.pop(stored_name, None)
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️ Failed to cleanup {stored_name}: {e}")
    
    if deleted_count > 0:
        save_metadata(meta)
        print(f"🗑️ Cleaned up {deleted_count} old trash files")
    
    return deleted_count

# ---------------- Email with attachment ----------------
def send_email_with_attachment(receiver_email, filename, filepath, password):
    """
    Send email notification about shared file with password.
    Note: Resend free tier doesn't support attachments, so we send just the password notification.
    """
    if not RESEND_API_KEY:
        print("❌ RESEND_API_KEY not configured.")
        return False
    if not EMAIL_USER:
        print("❌ EMAIL_USER not configured.")
        return False

    body = f"""Hello,

You have received a shared file: {filename}
Password to access it: {password}

Please log in to the cloud storage system to download your file.

- Intelligent Cloud File Sharing System
"""

    try:
        params = {
            "from": f"Cloud Storage <{EMAIL_USER}>",
            "to": [receiver_email],
            "subject": f"Shared File: {filename}",
            "text": body,
        }
        resend.Emails.send(params)
        print(f"📧 Shared file notification sent to {receiver_email} via Resend")
        return True
    except Exception as e:
        print("❌ Failed to send email notification:", e)
        return False
        return False

# ---------------- Access Logs ----------------
def record_access_log(filename, action, user_email, meta=None):
    """
    Record access log entry with standardized schema.
    
    Schema:
        {
            "user": str,
            "action": "upload|download|share|login|logout|delete|share_create|shared_download",
            "file": str,
            "timestamp": ISO8601 string,
            "meta": dict (optional additional metadata)
        }
    
    Creates backup before first write if log file exists.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Create backup on first modification (if file exists and no backup yet)
    backup_dir = os.path.join(BASE_DIR, "..", "db")
    if os.path.exists(LOG_FILE):
        # Check if we need to create a backup (create one per session)
        timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"access_log_backup_{timestamp_str}.json")
        
        # Only create backup if one doesn't exist for this second (prevents multiple backups)
        existing_backups = [f for f in os.listdir(backup_dir) if f.startswith("access_log_backup_")]
        if not existing_backups or not os.path.exists(backup_path):
            try:
                import shutil
                shutil.copy2(LOG_FILE, backup_path)
                print(f"📋 Created backup: {backup_path}")
            except Exception as e:
                print(f"⚠️ Backup creation failed: {e}")
    
    data = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                data = []
    
    # Create standardized entry with new schema
    entry = {
        "user": user_email,
        "action": action,
        "file": filename,
        "timestamp": datetime.datetime.utcnow().isoformat() + 'Z'
    }
    
    # Initialize or preserve metadata
    if meta is None:
        meta = {}
    elif not isinstance(meta, dict):
        meta = {}
    else:
        meta = dict(meta)  # Create a copy to avoid modifying original
    
    # Auto-add file_type if not present and filename is available
    if "file_type" not in meta and filename:
        try:
            file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            meta["file_type"] = file_type
        except Exception:
            meta["file_type"] = "unknown"
    
    # Add metadata to entry
    if meta:
        entry["meta"] = meta
    
    # Quick validation check
    assert "action" in entry, "Log entry must have 'action' field"
    assert "timestamp" in entry, "Log entry must have 'timestamp' field"
    assert isinstance(entry["timestamp"], str), "timestamp must be ISO8601 string"
    
    data.append(entry)
    
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    # Post-write validation
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        verified = json.load(f)
        last_entry = verified[-1]
        assert "action" in last_entry, "Written entry missing 'action'"
        assert "timestamp" in last_entry, "Written entry missing 'timestamp'"


# app.py (complete)
from flask import Flask, request, jsonify, send_file, send_from_directory, after_this_request, render_template
import os, json, datetime, random, uuid
import jwt  # pip install PyJWT
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- Config: load .env early ----------------
BASE_DIR = os.path.dirname(__file__)
ENV_PATH = os.path.join(BASE_DIR, "..", ".env")
load_dotenv(ENV_PATH)  # Ensure environment variables are loaded before importing storage

SECRET = os.getenv("JWT_SECRET", "supersecretjwtkey")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "local_store")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SHARES_FILE = os.path.join(BASE_DIR, "..", "db", "shares.json")

# ---------------- Now import storage and other modules that rely on .env ----------------
from storage import (
    init_keys, encrypt_file_and_store, decrypt_and_get_file, decrypt_and_get_file_by_stored_name,
    record_access_log, load_users, save_users,
    save_otp, verify_otp, load_metadata, save_metadata, delete_file,
    send_email, send_email_with_attachment,
    restore_file, permanently_delete_file, cleanup_old_trash
)

# AI module imports (we assume these functions exist in ai_module.py)
from ai_module import analyze_recent_logs, record_activity, detect_anomalies

# Create the Flask app (set template_folder so render_template finds monitor.html in frontend)
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "../frontend"),
    template_folder=os.path.join(BASE_DIR, "../frontend")
)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- Helper to send security alert by email ----------------
def send_security_alert(user_email, message):
    """
    Use existing send_email(recipient, subject, body) from storage module to notify users.
    """
    if not user_email or not message:
        return False
    try:
        subject = "⚠️ Security Alert — Suspicious Activity Detected"
        body = f"""Hello,

Our monitoring system detected suspicious activity on your account:

{message}

If this wasn't you, please change your password and contact support.

— Intelligent Cloud File Sharing System
"""
        send_email(user_email, subject, body)
        print(f"✅ Sent security alert to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send security alert to {user_email}: {e}")
        return False

# ---------------- Helpers ----------------
def get_user_from_token():
    auth = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not auth:
        return None, jsonify({"error": "missing token"}), 401
    try:
        payload = jwt.decode(auth, SECRET, algorithms=["HS256"])
        return payload["sub"], None, None
    except Exception as e:
        return None, jsonify({"error": "unauthenticated", "detail": str(e)}), 401

def delete_otp(email):
    otp_file = os.path.join(os.path.dirname(__file__), "..", "db", "otp.json")
    if os.path.exists(otp_file):
        with open(otp_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                data = {}
        if email in data:
            data.pop(email)
            with open(otp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

def migrate_metadata_folders():
    """
    Safe migration: ensures all metadata entries have 'folder' field.
    
    - Reads existing metadata from files.json
    - Creates backup before modification
    - Adds 'folder': '/' to entries missing the field
    - Preserves all existing data
    
    This is idempotent - safe to run multiple times.
    """
    try:
        meta_file = os.path.join(BASE_DIR, "..", "db", "files.json")
        
        if not os.path.exists(meta_file):
            print("ℹ️ No metadata file found - skipping migration")
            return
        
        # Load existing metadata
        meta = load_metadata()
        
        if not meta:
            print("ℹ️ Metadata is empty - skipping migration")
            return
        
        # Check if migration is needed
        needs_migration = False
        for stored_name, details in meta.items():
            if "folder" not in details:
                needs_migration = True
                break
        
        if not needs_migration:
            print("✅ Metadata already has folder fields - no migration needed")
            return
        
        # Create backup before migration
        backup_dir = os.path.join(BASE_DIR, "..", "backups", "metadata_migration")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"files_backup_{timestamp}.json")
        
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        
        print(f"📦 Created metadata backup: {backup_file}")
        
        # Migrate: add 'folder' field to entries that don't have it
        migrated_count = 0
        for stored_name, details in meta.items():
            if "folder" not in details:
                details["folder"] = "/"
                migrated_count += 1
        
        # Save updated metadata
        save_metadata(meta)
        
        print(f"✅ Metadata migration complete: {migrated_count} entries updated with default folder '/'")
        print(f"   Backup saved to: {backup_file}")
        
    except Exception as e:
        print(f"❌ Metadata migration failed: {e}")
        print("⚠️ Application will continue, but folder features may not work correctly")

def load_shares():
    if not os.path.exists(SHARES_FILE):
        os.makedirs(os.path.dirname(SHARES_FILE), exist_ok=True)
        with open(SHARES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(SHARES_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_shares(data):
    os.makedirs(os.path.dirname(SHARES_FILE), exist_ok=True)
    with open(SHARES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def find_meta_for_owner_and_name(owner, original_name):
    meta = load_metadata()
    for stored, details in meta.items():
        if details.get("owner") == owner and details.get("original_name") == original_name:
            return stored, details
    return None, None

# ---------------- Log Filtering Helper ----------------
def filter_logs(logs, params):
    """
    Filter log entries based on query parameters.
    
    Args:
        logs: List of log dictionaries
        params: Dict with keys: type, start, end, file_type, file_name, receiver_email
    
    Returns:
        Filtered list of logs
        
    Raises:
        ValueError: If date formats are invalid
    """
    from datetime import datetime
    
    filtered = logs[:]  # Start with copy of all logs
    
    # Filter by action type
    action_type = params.get('type', '').strip().lower()
    if action_type:
        filtered = [l for l in filtered if l.get('action', '').lower() == action_type]
    
    # Filter by date range (inclusive)
    start_date = params.get('start', '').strip()
    end_date = params.get('end', '').strip()
    
    if start_date or end_date:
        start_dt = None
        end_dt = None
        
        if start_date:
            # Support both YYYY-MM-DD and full ISO8601
            if 'T' not in start_date:
                start_date += 'T00:00:00'
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except Exception as e:
                raise ValueError(f"Invalid start date format: {e}")
        
        if end_date:
            if 'T' not in end_date:
                end_date += 'T23:59:59'
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except Exception as e:
                raise ValueError(f"Invalid end date format: {e}")
        
        # Filter logs by timestamp
        filtered_by_date = []
        for log in filtered:
            # Handle both 'timestamp' and 'time' fields
            ts_str = log.get('timestamp') or log.get('time')
            if not ts_str:
                continue  # Skip logs without timestamp
            
            try:
                log_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                # Normalize to naive datetime for comparison
                if log_dt.tzinfo is not None:
                    log_dt = log_dt.replace(tzinfo=None)
                
                # Apply range filters
                if start_dt and start_dt.replace(tzinfo=None) > log_dt:
                    continue
                if end_dt and end_dt.replace(tzinfo=None) < log_dt:
                    continue
                
                filtered_by_date.append(log)
            except Exception:
                # Skip logs with invalid timestamp format
                continue
        
        filtered = filtered_by_date
    
    # Filter by file extension
    file_type = params.get('file_type', '').strip().lower()
    if file_type:
        # Remove leading dot if present
        if file_type.startswith('.'):
            file_type = file_type[1:]
        filtered = [
            l for l in filtered 
            if l.get('file') and l.get('file', '').lower().endswith(f'.{file_type}')
        ]
    
    # Filter by file name substring (case-insensitive)
    file_name = params.get('file_name', '').strip().lower()
    if file_name:
        filtered = [
            l for l in filtered 
            if l.get('file') and file_name in l.get('file', '').lower()
        ]
    
    # Filter by receiver email (for share logs with meta.receiver_emails)
    receiver_email = params.get('receiver_email', '').strip().lower()
    if receiver_email:
        filtered = [
            l for l in filtered
            if (l.get('meta') and 
                isinstance(l.get('meta'), dict) and
                receiver_email in str(l.get('meta', {}).get('receiver_emails', [])).lower())
        ]
    
    return filtered

# ---------------- Monitor data route (returns analysis JSON & emails alert if present) ----------------
@app.route('/api/monitor-data')
def monitor_data():
    """Return last-24h activity stats for the logged-in user and email new alerts once."""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    print(f"\n[MONITOR] Request from: {user_email}")
    
    try:
        # call analyzer for last 24 hours
        stats, alert_message = analyze_recent_logs(
            user_filter=user_email,
            hours=24,
            today_only=False
        )
        print(f"[MONITOR] Stats returned: {stats}")
        print(f"[MONITOR] Alert message: '{alert_message}'")
    except Exception as e:
        print(f"[ERROR] analyze_recent_logs failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"stats": {}, "alert": "analysis error"}), 200

    # Flatten stats for frontend
    user_stats = stats.get(user_email, {}) if isinstance(stats, dict) else {}
    flat_stats = {}
    if isinstance(user_stats, dict):
        flat_stats = {k: int(v) for k, v in user_stats.items() if isinstance(v, (int, float))}

    # Keep track of already-sent alerts so they aren’t resent
    sent_alerts_file = os.path.join(BASE_DIR, "..", "db", "sent_alerts.json")
    sent_alerts = {}
    if os.path.exists(sent_alerts_file):
        try:
            with open(sent_alerts_file, "r", encoding="utf-8") as f:
                sent_alerts = json.load(f)
        except:
            sent_alerts = {}

    last_sent = sent_alerts.get(user_email)

    # ONLY send real alerts (alert_message must be non-empty string returned by ai_module)
    if alert_message:
        print(f"⚠️ Alert detected for {user_email}: {alert_message}")
        # send only if different from last sent
        if alert_message != last_sent:
            print(f"📧 Sending new alert to {user_email} (last sent: {last_sent})")
            try:
                send_security_alert(user_email, alert_message)
                sent_alerts[user_email] = alert_message
                with open(sent_alerts_file, "w", encoding="utf-8") as f:
                    json.dump(sent_alerts, f, indent=2)
                print(f"✅ Alert email sent and logged for {user_email}")
            except Exception as e:
                print(f"❌ send_security_alert failed: {e}")
        else:
            print(f"ℹ️ Alert already sent to {user_email}, skipping duplicate email")
    else:
        print(f"✅ No alerts for {user_email}")

    # Get user's file count
    meta = load_metadata()
    total_files = sum(1 for d in meta.values() if d.get("owner") == user_email)

    # Build anomalies list if there are alerts
    anomalies_list = []
    if alert_message:
        anomalies_list = [{"message": alert_message, "severity": "high"}]

    # Return data in format expected by frontend (includes all activity stats)
    return jsonify({
        "total_files": total_files,
        "total_uploads": flat_stats.get("upload", 0),
        "total_downloads": flat_stats.get("download", 0),
        "anomalies": anomalies_list,
        # Additional stats for timeline/debugging
        "stats": {
            "shares": flat_stats.get("share", 0),
            "deletes": flat_stats.get("delete", 0),
            "failed_logins": flat_stats.get("failed_login", 0),
            "successful_logins": flat_stats.get("login_success", 0),
            "shared_downloads": flat_stats.get("shared_download", 0)
        }
    }), 200




# ---------------- User Management ----------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = (data.get("email") or "").strip().lower()
    pwd = data.get("password")
    username = data.get("username", "").strip()
    dob = data.get("dob", "").strip()
    mobile = data.get("mobile", "").strip()
    address = data.get("address", "").strip()
    
    if not email or not pwd:
        return jsonify({"error": "email & password required"}), 400

    users = load_users()
    if email in users:
        return jsonify({"error": "user already exists"}), 400

    pwd_hash = generate_password_hash(pwd)
    users[email] = {
        "password_hash": pwd_hash,
        "username": username,
        "dob": dob,
        "mobile": mobile,
        "address": address,
        "mfa_enabled": True,
        "created_at": datetime.datetime.utcnow().isoformat() + 'Z'
    }
    save_users(users)
    return jsonify({"message": "registered"}), 201

# ---------------- Login + OTP ----------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = (data.get("email") or "").strip().lower()
    pwd = data.get("password")

    if not email or not pwd:
        return jsonify({"error": "email & password required"}), 400

    users = load_users()
    user = users.get(email)

    # Check if account is locked
    if user and user.get("locked_until"):
        locked_until = datetime.datetime.fromisoformat(user["locked_until"])
        now = datetime.datetime.utcnow()
        if now < locked_until:
            minutes_left = int((locked_until - now).total_seconds() / 60)
            return jsonify({
                "error": "account_locked",
                "message": f"Account locked due to multiple failed login attempts. Try again in {minutes_left} minutes."
            }), 403
        else:
            # Lock expired, clear it
            user["locked_until"] = None
            user["failed_attempts"] = 0
            save_users(users)

    # Track failed login attempts and successes
    try:
        if not user or not check_password_hash(user.get("password_hash", ""), pwd):
            # record failed login for monitoring
            try:
                record_activity(email, "failed_login")
            except Exception:
                pass
            
            # Track failed attempts for lockout
            if user:
                user["failed_attempts"] = user.get("failed_attempts", 0) + 1
                
                # Lock account after 5 failed attempts
                if user["failed_attempts"] >= 5:
                    lockout_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
                    user["locked_until"] = lockout_time.isoformat()
                    save_users(users)
                    
                    # Send security alert
                    send_security_alert(
                        email,
                        f"Your account has been locked for 15 minutes due to {user['failed_attempts']} failed login attempts."
                    )
                    
                    return jsonify({
                        "error": "account_locked",
                        "message": "Account locked for 15 minutes due to multiple failed attempts. Check your email."
                    }), 403
                
                save_users(users)
            
            return jsonify({"error": "invalid credentials"}), 401
        else:
            # successful password check (OTP still required)
            # Reset failed attempts on successful login
            if user:
                user["failed_attempts"] = 0
                user["locked_until"] = None
                save_users(users)
            
            try:
                record_activity(email, "login_success")
            except Exception:
                pass
    except Exception as e:
        print("❌ login monitoring error:", e)

    otp_code = str(random.randint(100000, 999999))
    save_otp(email, otp_code)
    
    send_email(email, "Your OTP Code", f"Your OTP code is: {otp_code}\n\nValid for 3 minutes.")
    return jsonify({"message": "OTP sent to email"}), 200

# ---------------- Verify OTP ----------------
@app.route("/api/verify-otp", methods=["POST"])
def verify_otp_endpoint():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    otp_code = str(data.get("otp") or "").strip()

    if not email or not otp_code:
        return jsonify({"error": "email and otp required"}), 400

    if not verify_otp(email, otp_code):
        return jsonify({"error": "invalid or expired OTP"}), 401

    # OTP is valid, generate JWT token
    token = jwt.encode(
        {"sub": email, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)},
        SECRET,
        algorithm="HS256"
    )
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    # Record successful login in access log
    record_access_log("", "login", email)

    return jsonify({"token": token}), 200

# ---------------- Logout ----------------
@app.route("/api/logout", methods=["POST"])
def logout():
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code
    
    # Record logout in access log
    record_access_log("", "logout", user_email)
    
    return jsonify({"message": "Logged out successfully"}), 200

# ---------------- File Upload ----------------
@app.route("/api/upload", methods=["POST"])
def upload():
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400

    f = request.files["file"]
    folder = request.form.get("folder", "/").strip() or "/"
    filename = secure_filename(f.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(filepath)

    stored = encrypt_file_and_store(filepath, filename, user_email, folder=folder)
    try:
        record_activity(user_email, "upload", filename)
    except Exception:
        pass
    return jsonify({"message": "File uploaded successfully", "stored": stored}), 200

# ---------------- Multiple File Upload (Enhanced) ----------------
@app.route("/api/upload-multiple", methods=["POST"])
def upload_multiple():
    """
    Upload multiple files with validation.
    
    Accepts:
        - files[]: multipart/form-data file array
        - folder: optional folder path (default: "/")
    
    Validates:
        - Max 20 files per request
        - Total size limit: 200MB
        - Authentication required
    
    Returns:
        JSON: { stored: [...], errors: [...] }
    
    TODO: Add unit tests for:
        - Max file count validation
        - Total size limit validation
        - Individual file encryption
        - Error handling for partial failures
    """
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    # Configuration limits
    MAX_FILES = 20
    MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB in bytes

    # Get files from request
    files = request.files.getlist("files[]")
    if not files or len(files) == 0:
        return jsonify({"error": "no files provided"}), 400

    # Validate file count
    if len(files) > MAX_FILES:
        return jsonify({"error": f"too many files (max {MAX_FILES})"}), 400

    # Get folder parameter
    folder = request.form.get("folder", "/").strip() or "/"

    # Calculate total size and validate
    total_size = 0
    for file in files:
        # Seek to end to get size, then reset to beginning
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        total_size += file_size

    if total_size > MAX_TOTAL_SIZE:
        return jsonify({
            "error": f"total size exceeds limit (max 200MB, got {total_size / 1024 / 1024:.2f}MB)"
        }), 400

    # Process each file
    stored_files = []
    errors = []

    for file in files:
        try:
            # Validate filename
            if not file.filename:
                errors.append({"filename": "unknown", "error": "empty filename"})
                continue

            # Secure the filename
            filename = secure_filename(file.filename)
            if not filename:
                errors.append({"filename": file.filename, "error": "invalid filename"})
                continue

            # Save to upload folder
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Encrypt and store
            stored = encrypt_file_and_store(filepath, filename, user_email, folder=folder)
            
            # Log the upload
            record_access_log(filename, "upload", user_email)
            
            # Record activity for monitoring
            try:
                record_activity(user_email, "upload", filename)
            except Exception as e:
                print(f"⚠️ Failed to record activity for {filename}: {e}")

            # Add to successful uploads
            stored_files.append({
                "original_name": filename,
                "stored_name": stored.get("stored_as"),
                "folder": folder
            })

        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
            print(f"❌ Failed to upload {file.filename}: {e}")

    # Record bulk upload summary activity
    if len(stored_files) > 0:
        try:
            record_activity(user_email, "bulk_upload", f"{len(stored_files)} files")
            print(f"📊 Recorded bulk upload activity: {len(stored_files)} files")
        except Exception as e:
            print(f"⚠️ Failed to record bulk upload activity: {e}")

    # Return results
    return jsonify({
        "message": f"Uploaded {len(stored_files)} of {len(files)} files",
        "stored": stored_files,
        "errors": errors
    }), 200 if len(stored_files) > 0 else 400

# ---------------- File List ----------------
@app.route("/api/files", methods=["GET"])
def list_files():
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    folder_path = request.args.get("folder", "/").strip() or "/"
    meta = load_metadata()
    user_files = [
        {
            "filename": k,
            "original_name": d["original_name"], 
            "uploaded_at": d["uploaded_at"],
            "folder": d.get("folder", "/"),
            "size": d.get("size", 0)
        }
        for k, d in meta.items() 
        if d["owner"] == user_email 
        and d.get("folder", "/") == folder_path
        and "deleted_at" not in d  # Filter out soft-deleted files
    ]
    return jsonify(user_files), 200

# ---------------- File Download ----------------
@app.route("/api/download/<filename>", methods=["GET"])
def download(filename):
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    # Try to find file by original name first, then by stored name
    outpath = decrypt_and_get_file(filename, user_email)
    
    # If not found by original name, try stored name
    if not outpath:
        outpath = decrypt_and_get_file_by_stored_name(filename, user_email)
    
    if not outpath:
        return jsonify({"error": "not found"}), 404
    
    try:
        record_activity(user_email, "download", filename)
    except Exception:
        pass

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(outpath):
                os.remove(outpath)
                print(f"🗑️ Deleted temp file: {outpath}")
        except Exception as e:
            print("❌ Temp file cleanup failed:", str(e))
        return response

    return send_file(outpath, as_attachment=True)

# ---------------- Multiple File Download (ZIP) ----------------
@app.route("/api/download-multiple", methods=["POST"])
def download_multiple():
    """
    Download multiple files as a ZIP archive with streaming support.
    
    Accepts JSON body:
        { "filenames": ["file1.txt", "file2.pdf", ...] }
    
    Features:
        - Validates ownership and existence for each file
        - Creates streaming ZIP archive to avoid memory issues
        - Automatic cleanup of temporary decrypted files
        - Logs access for each file downloaded
    
    Returns:
        - ZIP file as attachment (200)
        - Error JSON if validation fails (400/404)
    
    TODO: Add unit tests for:
        - Ownership validation
        - Non-existent file handling
        - Streaming ZIP creation
        - Temp file cleanup verification
    """
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    # Parse request body
    data = request.json or {}
    filenames = data.get("filenames", [])

    if not filenames or not isinstance(filenames, list):
        return jsonify({"error": "filenames array required"}), 400

    if len(filenames) == 0:
        return jsonify({"error": "no files specified"}), 400

    # Validate file limit (reasonable for zip operation)
    MAX_FILES = 50
    if len(filenames) > MAX_FILES:
        return jsonify({"error": f"too many files (max {MAX_FILES})"}), 400

    # Track decrypted files for cleanup
    temp_files = []
    invalid_files = []
    
    try:
        # Decrypt all files first and validate ownership
        for filename in filenames:
            # Decrypt and get file (validates ownership automatically)
            outpath = decrypt_and_get_file(filename, user_email)
            
            if not outpath or not os.path.exists(outpath):
                invalid_files.append(filename)
                continue
            
            temp_files.append({
                "path": outpath,
                "name": filename
            })
            
            # Log access for each file
            record_access_log(filename, "download", user_email)
            try:
                record_activity(user_email, "download", filename)
            except Exception as e:
                print(f"⚠️ Failed to record activity for {filename}: {e}")

        # Check if any files were invalid
        if invalid_files:
            # Cleanup any successfully decrypted files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file["path"]):
                        os.remove(temp_file["path"])
                except Exception:
                    pass
            
            return jsonify({
                "error": "some files not found or access denied",
                "invalid_files": invalid_files
            }), 404

        if not temp_files:
            return jsonify({"error": "no valid files to download"}), 404

        # Create streaming ZIP archive
        import zipfile
        import tempfile
        from io import BytesIO

        # Use temporary file for ZIP to support streaming
        temp_zip_fd, temp_zip_path = tempfile.mkstemp(suffix='.zip')
        os.close(temp_zip_fd)  # Close the file descriptor, we'll open it with zipfile

        try:
            # Create ZIP archive
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for temp_file in temp_files:
                    # Add file to ZIP with original filename
                    zipf.write(temp_file["path"], arcname=temp_file["name"])
            
            # Record bulk download summary activity
            try:
                record_activity(user_email, "bulk_download", f"{len(temp_files)} files")
                print(f"📊 Recorded bulk download activity: {len(temp_files)} files")
            except Exception as e:
                print(f"⚠️ Failed to record bulk download activity: {e}")
            
            # Cleanup handler for both temp decrypted files and zip file
            @after_this_request
            def cleanup(response):
                try:
                    # Remove decrypted temp files
                    for temp_file in temp_files:
                        if os.path.exists(temp_file["path"]):
                            os.remove(temp_file["path"])
                            print(f"🗑️ Cleaned up temp file: {temp_file['name']}")
                    
                    # Remove ZIP file
                    if os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
                        print(f"🗑️ Cleaned up temp ZIP: {temp_zip_path}")
                        
                except Exception as e:
                    print(f"❌ Cleanup failed: {e}")
                
                return response

            # Send ZIP file
            return send_file(
                temp_zip_path,
                as_attachment=True,
                download_name=f"files_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip",
                mimetype='application/zip'
            )

        except Exception as e:
            # Emergency cleanup if ZIP creation fails
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file["path"]):
                        os.remove(temp_file["path"])
                except Exception:
                    pass
            
            if os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except Exception:
                    pass
            
            print(f"❌ ZIP creation failed: {e}")
            return jsonify({"error": f"failed to create archive: {str(e)}"}), 500

    except Exception as e:
        # Emergency cleanup on any error
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file["path"]):
                    os.remove(temp_file["path"])
            except Exception:
                pass
        
        print(f"❌ Download multiple failed: {e}")
        return jsonify({"error": str(e)}), 500

# ---------------- File Delete ----------------
@app.route("/api/delete/<filename>", methods=["DELETE"])
def delete_file_route(filename):
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    success = delete_file(filename, user_email)
    if not success:
        return jsonify({"error": "file not found or not owned by you"}), 404

    # Record activity for AI monitoring (also appears in access logs via merged view)
    record_activity(user_email, "delete", filename)
    print(f"✅ Recorded delete activity for {user_email}: {filename}")
    
    try:
        # Check for unusual deletion activity immediately
        from ai_module import load_sent_alerts, save_sent_alerts
        stats, alert_msg = analyze_recent_logs(user_filter=user_email, hours=24)
        
        print(f"📊 User stats after delete: {stats.get(user_email, {})}")
        print(f"🔔 Alert message: '{alert_msg}'")
        
        if alert_msg and "deletion" in alert_msg.lower():
            # Create unique alert key for this user and alert type
            sent_alerts = load_sent_alerts()
            alert_key = f"{user_email}_unusual_deletion_{datetime.datetime.utcnow().strftime('%Y%m%d')}"
            
            print(f"🔑 Alert key: {alert_key}")
            print(f"📋 Already sent: {sent_alerts.get(alert_key)}")
            
            # Only send if not already sent today
            if not sent_alerts.get(alert_key):
                print(f"📧 Sending unusual deletion alert to {user_email}")
                send_security_alert(user_email, alert_msg)
                sent_alerts[alert_key] = datetime.datetime.utcnow().isoformat() + 'Z'
                save_sent_alerts(sent_alerts)
                print(f"✅ Alert sent and logged")
            else:
                print(f"⏭️ Alert already sent today, skipping")
    except Exception as e:
        print(f"⚠️ Anomaly check failed: {e}")
        import traceback
        traceback.print_exc()

    return jsonify({"message": f"{filename} deleted successfully"}), 200

# ---------------- Trash Bin Management ----------------
@app.route("/api/trash", methods=["GET"])
def get_trash():
    """Get all files in trash (soft-deleted) for current user"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code
    
    meta = load_metadata()
    trash_files = []
    
    for stored_name, details in meta.items():
        if details.get("owner") == user_email and "deleted_at" in details:
            trash_files.append({
                "original_name": details["original_name"],
                "deleted_at": details["deleted_at"],
                "size": details.get("size", 0)
            })
    
    return jsonify({"files": trash_files}), 200

@app.route("/api/trash/restore/<filename>", methods=["POST"])
def restore_file_route(filename):
    """Restore a file from trash"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code
    
    success = restore_file(filename, user_email)
    if not success:
        return jsonify({"error": "file not found in trash"}), 404
    
    record_access_log(filename, "restore", user_email)
    return jsonify({"message": f"{filename} restored successfully"}), 200

@app.route("/api/trash/permanent/<filename>", methods=["DELETE"])
def permanent_delete_route(filename):
    """Permanently delete a file from trash"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code
    
    success = permanently_delete_file(filename, user_email)
    if not success:
        return jsonify({"error": "file not found"}), 404
    
    record_access_log(filename, "permanent_delete", user_email)
    return jsonify({"message": f"{filename} permanently deleted"}), 200

@app.route("/api/trash/empty", methods=["DELETE"])
def empty_trash():
    """Empty entire trash for current user"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code
    
    meta = load_metadata()
    deleted_count = 0
    
    for stored_name, details in list(meta.items()):
        if details.get("owner") == user_email and "deleted_at" in details:
            if permanently_delete_file(details["original_name"], user_email):
                deleted_count += 1
    
    return jsonify({"message": f"Emptied trash ({deleted_count} files deleted)"}), 200

# ---------------- Folder Management Helper ----------------
def load_and_migrate_folders(folders_file):
    """
    Load folders.json and migrate from mixed/list format to dict format.
    
    Handles:
    - Old format: {"email": ["folder1", "folder2"]}
    - New format: {"email:path": {folder_obj}}
    - Mixed format: combination of both
    
    Returns: dict with consistent structure
    """
    os.makedirs(os.path.dirname(folders_file), exist_ok=True)
    
    if not os.path.exists(folders_file):
        with open(folders_file, "w") as f:
            json.dump({}, f)
        return {}
    
    # Handle corrupted/empty JSON file
    try:
        with open(folders_file, "r") as f:
            content = f.read().strip()
            if not content:
                # File is empty, initialize it
                with open(folders_file, "w") as fw:
                    json.dump({}, fw)
                return {}
            data = json.loads(content)
    except json.JSONDecodeError:
        # File is corrupted, backup and reinitialize
        print(f"⚠️ Corrupted folders.json detected, reinitializing...")
        backup_file = folders_file.replace(".json", "_corrupted_backup.json")
        import shutil
        shutil.copy2(folders_file, backup_file)
        with open(folders_file, "w") as f:
            json.dump({}, f)
        return {}
    
    # Check if migration is needed
    needs_migration = False
    migrated_data = {}
    migration_count = 0
    
    for key, value in data.items():
        # If value is a list (old format), convert to dict entries
        if isinstance(value, list):
            needs_migration = True
            # Extract user email from key (it's just the email in old format)
            user_email = key
            for folder_name in value:
                folder_id = f"{user_email}:/{folder_name}"
                migrated_data[folder_id] = {
                    "id": folder_id,
                    "name": folder_name,
                    "path": f"/{folder_name}",
                    "parent": "/",
                    "owner": user_email,
                    "created_at": datetime.datetime.utcnow().isoformat() + 'Z'
                }
                migration_count += 1
        # If value is a dict (new format), keep as-is
        elif isinstance(value, dict):
            migrated_data[key] = value
        else:
            # Unknown format, skip
            print(f"⚠️ Unknown format for key {key}: {type(value)}")
    
    # Save migrated data if changes were made
    if needs_migration:
        # Create timestamped backup
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = folders_file.replace(".json", f"_premigration_{timestamp}.json")
        
        with open(backup_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"📦 Folders migration backup: {backup_file}")
        print(f"🔄 Migrated {migration_count} folder entries from list to dict format")
        
        # Save migrated data
        with open(folders_file, "w") as f:
            json.dump(migrated_data, f, indent=2)
    
    return migrated_data

# ---------------- Folder Management ----------------
@app.route("/api/folders", methods=["GET"])
def list_folders():
    """Get all folders for the current user"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    folders_file = os.path.join(BASE_DIR, "..", "db", "folders.json")
    
    # Load and migrate if needed
    all_folders = load_and_migrate_folders(folders_file)
    
    # Defensive: handle both dict and list returns
    if isinstance(all_folders, dict):
        items = list(all_folders.values())
        data_shape = "dict"
    elif isinstance(all_folders, list):
        items = all_folders
        data_shape = "list"
    else:
        items = []
        data_shape = "unknown"
    
    # Filter for current user
    user_folders = [f for f in items if isinstance(f, dict) and f.get("owner") == user_email]
    
    print(f"📊 list_folders: Loaded {len(items)} total folders (shape: {data_shape}), returning {len(user_folders)} for user {user_email}")
    
    return jsonify(user_folders), 200

@app.route("/api/folders", methods=["POST"])
def create_folder():
    """Create a new folder"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    data = request.json or {}
    folder_name = data.get("name", "").strip()
    parent_path = data.get("parent", "/").strip() or "/"
    
    if not folder_name:
        return jsonify({"error": "Folder name required"}), 400
    
    # Create full folder path
    if parent_path == "/":
        folder_path = f"/{folder_name}"
    else:
        folder_path = f"{parent_path}/{folder_name}"
    
    folders_file = os.path.join(BASE_DIR, "..", "db", "folders.json")
    
    # Load and migrate if needed
    all_folders = load_and_migrate_folders(folders_file)
    
    # Check if folder already exists
    folder_id = f"{user_email}:{folder_path}"
    if folder_id in all_folders:
        return jsonify({"error": "Folder already exists"}), 400
    
    # Create folder
    all_folders[folder_id] = {
        "id": folder_id,
        "name": folder_name,
        "path": folder_path,
        "parent": parent_path,
        "owner": user_email,
        "created_at": datetime.datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(folders_file, "w") as f:
        json.dump(all_folders, f, indent=2)
    
    print(f"✅ Created folder: {folder_id}")
    
    return jsonify(all_folders[folder_id]), 201

@app.route("/api/folders/<path:folder_id>", methods=["PUT"])
def rename_folder(folder_id):
    """Rename a folder"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    data = request.json or {}
    new_name = data.get("name", "").strip()
    
    if not new_name:
        return jsonify({"error": "New folder name required"}), 400
    
    folders_file = os.path.join(BASE_DIR, "..", "db", "folders.json")
    
    # Load and migrate if needed
    all_folders = load_and_migrate_folders(folders_file)
    
    if folder_id not in all_folders or all_folders[folder_id]["owner"] != user_email:
        return jsonify({"error": "Folder not found or access denied"}), 404
    
    old_path = all_folders[folder_id]["path"]
    parent = all_folders[folder_id]["parent"]
    
    # Create new path
    if parent == "/":
        new_path = f"/{new_name}"
    else:
        new_path = f"{parent}/{new_name}"
    
    # Update folder
    new_id = f"{user_email}:{new_path}"
    all_folders[new_id] = all_folders.pop(folder_id)
    all_folders[new_id]["id"] = new_id
    all_folders[new_id]["name"] = new_name
    all_folders[new_id]["path"] = new_path
    
    # Update all child folders and files
    for fid, folder in list(all_folders.items()):
        if folder["owner"] == user_email and folder["parent"].startswith(old_path):
            folder["parent"] = folder["parent"].replace(old_path, new_path, 1)
    
    with open(folders_file, "w") as f:
        json.dump(all_folders, f, indent=2)
    
    # Update files in this folder
    meta = load_metadata()
    for k, v in meta.items():
        if v["owner"] == user_email and v.get("folder", "/").startswith(old_path):
            v["folder"] = v["folder"].replace(old_path, new_path, 1)
    save_metadata(meta)
    
    return jsonify(all_folders[new_id]), 200

@app.route("/api/folders/<path:folder_id>", methods=["DELETE"])
def delete_folder(folder_id):
    """Delete a folder (must be empty)"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    folders_file = os.path.join(BASE_DIR, "..", "db", "folders.json")
    
    # Load and migrate if needed
    all_folders = load_and_migrate_folders(folders_file)
    
    if folder_id not in all_folders or all_folders[folder_id]["owner"] != user_email:
        return jsonify({"error": "Folder not found or access denied"}), 404
    
    folder_path = all_folders[folder_id]["path"]
    
    # Check if folder has files
    meta = load_metadata()
    has_files = any(v["owner"] == user_email and v.get("folder") == folder_path for v in meta.values())
    
    if has_files:
        return jsonify({"error": "Cannot delete folder with files. Move or delete files first."}), 400
    
    # Check if folder has subfolders
    has_subfolders = any(f["owner"] == user_email and f["parent"] == folder_path for f in all_folders.values())
    
    if has_subfolders:
        return jsonify({"error": "Cannot delete folder with subfolders. Delete subfolders first."}), 400
    
    del all_folders[folder_id]
    
    with open(folders_file, "w") as f:
        json.dump(all_folders, f, indent=2)
    
    return jsonify({"message": "Folder deleted successfully"}), 200

@app.route("/api/move-file", methods=["POST"])
def move_file():
    """Move a file to a different folder"""
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    data = request.json or {}
    filename = data.get("filename", "").strip()
    target_folder = data.get("target_folder", "/").strip() or "/"
    
    if not filename:
        return jsonify({"error": "Filename required"}), 400
    
    meta = load_metadata()
    
    if filename not in meta or meta[filename]["owner"] != user_email:
        return jsonify({"error": "File not found or access denied"}), 404
    
    meta[filename]["folder"] = target_folder
    save_metadata(meta)
    
    return jsonify({"message": "File moved successfully"}), 200

# ---------------- Share File (robust) ----------------
@app.route("/api/share", methods=["POST"])
def share_file():
    """
    Accepts JSON:
    {
      "filename": "name",
      "recipients": ["a@x.com","b@y.com"]    OR
      "receiver": "single@x.com"             OR
      "receiver_email": "single@x.com"
      optional: "password": "custompw",
      optional: "expiry_seconds": 3600
    }
    """
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    data = request.json or {}
    filename = (data.get("filename") or "").strip()

    print(f"\n[SHARE] User: {user_email}")
    print(f"[SHARE] Requested filename: '{filename}'")
    print(f"[SHARE] Request data: {data}")

    # accept multiple ways the frontend might send a single recipient
    recipients = data.get("recipients")
    if not recipients:
        single = data.get("receiver") or data.get("receiver_email") or data.get("receiverEmail")
        if single:
            recipients = [single.strip()]
    if isinstance(recipients, str):
        recipients = [r.strip() for r in recipients.split(",") if r.strip()]

    expiry_seconds = int(data.get("expiry_seconds") or 3600)  # 1 hour default

    if not filename or not recipients or len(recipients) == 0:
        return jsonify({"error": "filename and recipients required. Provide 'recipients' (array) or 'receiver' (single)"}), 400

    # Try to find file by original name first
    stored_name, details = find_meta_for_owner_and_name(user_email, filename)
    
    # If not found, check if frontend sent the stored name instead of original name
    if not details:
        meta = load_metadata()
        for stored, d in meta.items():
            if d.get("owner") == user_email and stored == filename:
                # Found by stored name, use it
                stored_name = stored
                details = d
                print(f"✅ Found file by stored name: {stored} -> original: {d.get('original_name')}")
                break
    
    if not details:
        # Debug: show what files user owns
        meta = load_metadata()
        user_files = [d.get("original_name") for k, d in meta.items() if d.get("owner") == user_email]
        print(f"❌ File '{filename}' not found for {user_email}")
        print(f"   Available files: {user_files}")
        return jsonify({
            "error": "file not found or not owned by you",
            "requested": filename,
            "your_files": user_files
        }), 404

    token = uuid.uuid4().hex
    created_at = datetime.datetime.utcnow()
    expires_at = created_at + datetime.timedelta(seconds=expiry_seconds)

    # If sender provided a password, use it; otherwise generate one
    provided_password = data.get("password") or ''.join(random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8))
    password_hash = generate_password_hash(provided_password)

    shares = load_shares()
    shares[token] = {
        "token": token,
        "owner": user_email,
        "original_name": filename,
        "stored_name": stored_name,
        "created_at": created_at.isoformat() + 'Z',
        "expires_at": expires_at.isoformat() + 'Z',
        "password_hash": password_hash,
        "recipients": recipients
    }
    save_shares(shares)

    host = request.host_url.rstrip("/")
    share_link = f"{host}/api/share/{token}"

    # Send the secure link to each recipient
    for r in recipients:
        try:
            print(f"📧 Attempting to send secure link to {r}")

            email_body = f"""
Hello,

A file "{filename}" has been shared with you by {data.get('sender_username', 'a user')}.
You can download it using this secure link (valid for 1 hour):

{share_link}

🔐 IMPORTANT: This file is password-protected. The sender will provide you the password through a separate secure channel (not via email for security reasons).

Once you have the password, click the link above to access the file.

- Intelligent Cloud File Sharing System
"""
            send_email(r, f"Shared File: {filename}", email_body)
            print(f"✅ Secure share link sent to {r}")
        except Exception as e:
            print(f"❌ Email send failed for {r}: {e}")

    # Log share creation with receiver emails in metadata
    record_access_log(filename, "share_create", user_email, meta={"receiver_emails": recipients})
    try:
        record_activity(user_email, "share", filename)
    except Exception:
        pass

    # Return the generated (or provided) password to the sender in the response so the sender can copy it
    return jsonify({
        "message": "Share created successfully",
        "token": token,
        "link": share_link,
        "password": provided_password  # show password to sender in API response
    }), 201

# ---------------- Secure Share Download ----------------
@app.route("/api/share/<token>", methods=["POST"])
def access_shared_file(token):
    """Receiver downloads shared file by entering password."""
    data = request.json or {}
    input_password = (data.get("password") or "").strip()

    shares = load_shares()
    share = shares.get(token)
    if not share:
        return jsonify({"error": "invalid or expired link"}), 404

    # Check expiry
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = datetime.datetime.fromisoformat(share["expires_at"])
    if now > expires_at:
        return jsonify({"error": "link expired"}), 403

    # Check password
    if not check_password_hash(share["password_hash"], input_password):
        return jsonify({"error": "invalid password"}), 401

    stored_path = os.path.join(UPLOAD_FOLDER, share["stored_name"])
    if not os.path.exists(stored_path):
        return jsonify({"error": "file missing"}), 404

    # Use stored_name for decryption since that's the actual encrypted file
    outpath = decrypt_and_get_file_by_stored_name(share["stored_name"], share["owner"])
    if not outpath:
        return jsonify({"error": "file decrypt failed"}), 500

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(outpath):
                os.remove(outpath)
        except:
            pass
        return response

    # Record activity for shared downloads
    try:
        record_activity(share.get("owner"), "shared_download", share["original_name"])
    except Exception as e:
        print(f"⚠️ Failed to record shared download: {e}")

    return send_file(outpath, as_attachment=True, download_name=share["original_name"])

@app.route("/api/share/<token>", methods=["GET"])
def get_share_page(token):
    """Simple landing page for receivers to enter password"""
    return f"""
    <html>
      <body style='font-family:sans-serif; text-align:center; margin-top:50px'>
        <h2>Enter password to download file</h2>
        <form method="post" action="/api/share/{token}" onsubmit="event.preventDefault(); handleSubmit();">
          <input id="pw" type="password" placeholder="Enter password" required style="padding:5px">
          <button type="submit" style="padding:5px 10px">Download</button>
        </form>
        <script>
          async function handleSubmit(){{
            const pw = document.getElementById('pw').value;
            const res = await fetch('/api/share/{token}', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ password: pw }})
            }});
            if (res.ok) {{
              const blob = await res.blob();
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = "shared_file";
              a.click();
            }} else {{
              const data = await res.json().catch(()=>({{}}));
              alert(data.error || 'Invalid password or link expired');
            }}
          }}
        </script>
      </body>
    </html>
    """

# ---------------- Logs ----------------
@app.route("/api/logs", methods=["GET"])
def get_logs():
    """
    Get activity logs for current user with optional filtering.
    
    Query Parameters:
        - type: filter by action type (upload/download/share/login/logout/delete/share_create/shared_download)
        - start: start date (YYYY-MM-DD or ISO8601)
        - end: end date (YYYY-MM-DD or ISO8601)
        - file_type: filter by file extension (e.g., 'pdf', 'jpg')
        - file_name: substring search in filename (case-insensitive)
        - receiver_email: for share logs, filter by receiver email in meta
    
    Returns:
        JSON list of log entries sorted by timestamp descending
    """
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    # Read both activity_log and access_log for comprehensive results
    activity_log_file = os.path.join(os.path.dirname(__file__), "..", "db", "activity_log.json")
    access_log_file = os.path.join(os.path.dirname(__file__), "..", "db", "access_log.json")
    
    all_logs = []
    
    # Load activity logs
    if os.path.exists(activity_log_file):
        try:
            with open(activity_log_file, "r", encoding="utf-8") as f:
                activity_logs = json.load(f)
                print(f"📋 Loaded {len(activity_logs)} entries from activity_log.json")
                all_logs.extend(activity_logs)
        except Exception as e:
            print(f"⚠️ Failed to load activity_log.json: {e}")
    
    # Load access logs
    if os.path.exists(access_log_file):
        try:
            with open(access_log_file, "r", encoding="utf-8") as f:
                access_logs = json.load(f)
                # Normalize old 'time' field to 'timestamp'
                for log in access_logs:
                    if 'time' in log and 'timestamp' not in log:
                        log['timestamp'] = log['time']
                all_logs.extend(access_logs)
        except Exception as e:
            print(f"⚠️ Failed to load access_log.json: {e}")
    
    # Filter by current user only
    user_logs = [l for l in all_logs if l.get("user") == user_email]
    print(f"📊 Total logs for {user_email}: {len(user_logs)} (from {len(all_logs)} total)")
    
    # Debug: Show action types
    action_types = {}
    for log in user_logs:
        action = log.get('action', 'unknown')
        action_types[action] = action_types.get(action, 0) + 1
    print(f"📈 Action breakdown: {action_types}")
    
    # Apply query parameter filters using helper function
    try:
        filter_params = {
            'type': request.args.get('type', ''),
            'start': request.args.get('start', ''),
            'end': request.args.get('end', ''),
            'file_type': request.args.get('file_type', ''),
            'file_name': request.args.get('file_name', ''),
            'receiver_email': request.args.get('receiver_email', '')
        }
        
        user_logs = filter_logs(user_logs, filter_params)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Filter error: {str(e)}"}), 400
    
    # Sort by timestamp descending (newest first)
    def get_timestamp(log):
        ts = log.get('timestamp') or log.get('time') or ''
        return ts
    
    user_logs.sort(key=get_timestamp, reverse=True)
    
    # Apply pagination
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Validate pagination params
        if limit < 1 or limit > 1000:
            limit = 50
        if offset < 0:
            offset = 0
        
        total_count = len(user_logs)
        paginated_logs = user_logs[offset:offset + limit]
        
        # Return with pagination metadata
        return jsonify({
            "logs": paginated_logs,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }), 200
        
    except ValueError:
        # If limit/offset are invalid, return all logs (backward compatibility)
        return jsonify(user_logs), 200

# ---------------- Advanced Search ----------------
# Simple rate limiting storage (in-memory, resets on restart)
_search_rate_limit = {}
_SEARCH_RATE_LIMIT_WINDOW = 60  # seconds
_SEARCH_RATE_LIMIT_MAX = 30  # max requests per window

@app.route("/api/search", methods=["GET"])
def search():
    """
    Advanced search across files metadata and access logs.
    
    Query Parameters:
        - query: search term for filename (case-insensitive, partial match)
        - type: file type filter (e.g., 'pdf', 'jpg', 'txt')
        - from: start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        - to: end date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        - action: filter by action type ('upload', 'download', 'delete', 'share')
        - limit: max results per page (default: 50, max: 100)
        - offset: pagination offset (default: 0)
    
    Returns:
        JSON: {
            "results": [...],
            "total": N,
            "limit": 50,
            "offset": 0
        }
    
    Rate Limit: 30 requests per 60 seconds per user
    
    TODO: Add unit tests for:
        - Date range filtering
        - File type filtering
        - Pagination consistency
        - Rate limit enforcement
        - Invalid parameter handling
    """
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    # --- Rate Limiting ---
    now = datetime.datetime.utcnow().timestamp()
    user_requests = _search_rate_limit.get(user_email, [])
    
    # Clean old requests outside the window
    user_requests = [ts for ts in user_requests if now - ts < _SEARCH_RATE_LIMIT_WINDOW]
    
    if len(user_requests) >= _SEARCH_RATE_LIMIT_MAX:
        return jsonify({
            "error": "rate limit exceeded",
            "message": f"max {_SEARCH_RATE_LIMIT_MAX} requests per {_SEARCH_RATE_LIMIT_WINDOW} seconds"
        }), 429
    
    # Add current request
    user_requests.append(now)
    _search_rate_limit[user_email] = user_requests

    # --- Parse and Validate Parameters ---
    query = request.args.get("query", "").strip().lower()
    file_type = request.args.get("type", "").strip().lower()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    action_filter = request.args.get("action", "").strip().lower()
    
    # Pagination
    try:
        limit = min(int(request.args.get("limit", 50)), 100)  # Max 100
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return jsonify({"error": "invalid limit or offset"}), 400

    # Validate date formats
    date_from_obj = None
    date_to_obj = None
    
    if date_from:
        try:
            # Support both date and datetime formats
            if 'T' in date_from:
                date_from_obj = datetime.datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            else:
                date_from_obj = datetime.datetime.fromisoformat(date_from + 'T00:00:00')
        except ValueError:
            return jsonify({"error": "invalid 'from' date format (use ISO: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"}), 400
    
    if date_to:
        try:
            if 'T' in date_to:
                date_to_obj = datetime.datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            else:
                date_to_obj = datetime.datetime.fromisoformat(date_to + 'T23:59:59')
        except ValueError:
            return jsonify({"error": "invalid 'to' date format (use ISO: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"}), 400

    # Validate action filter
    valid_actions = ['upload', 'download', 'delete', 'share', 'share_create', 'shared_download']
    if action_filter and action_filter not in valid_actions:
        return jsonify({
            "error": "invalid action",
            "message": f"action must be one of: {', '.join(valid_actions)}"
        }), 400

    # --- Search Files Metadata ---
    meta = load_metadata()
    matching_files = []

    for stored_name, details in meta.items():
        # Only search user's own files
        if details.get("owner") != user_email:
            continue
        
        original_name = details.get("original_name", "").lower()
        
        # Filter by query (filename search)
        if query and query not in original_name:
            continue
        
        # Filter by file type
        if file_type:
            file_ext = original_name.split('.')[-1] if '.' in original_name else ''
            if file_ext != file_type:
                continue
        
        # Filter by date range
        if date_from_obj or date_to_obj:
            try:
                uploaded_at = datetime.datetime.fromisoformat(details.get("uploaded_at", ""))
                if date_from_obj and uploaded_at < date_from_obj:
                    continue
                if date_to_obj and uploaded_at > date_to_obj:
                    continue
            except (ValueError, TypeError):
                continue
        
        matching_files.append({
            "type": "file",
            "filename": details.get("original_name"),
            "uploaded_at": details.get("uploaded_at"),
            "folder": details.get("folder", "/"),
            "size": details.get("size", 0),
            "owner": details.get("owner")
        })

    # --- Search Access Logs (if action filter specified) ---
    matching_logs = []
    
    if action_filter:
        log_file = os.path.join(os.path.dirname(__file__), "..", "db", "access_log.json")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                
                for log in logs:
                    # Only user's own logs
                    if log.get("user") != user_email:
                        continue
                    
                    # Filter by action
                    if action_filter and log.get("action") != action_filter:
                        continue
                    
                    # Filter by filename query
                    if query and query not in log.get("file", "").lower():
                        continue
                    
                    # Filter by date range
                    if date_from_obj or date_to_obj:
                        try:
                            log_time = datetime.datetime.fromisoformat(log.get("time", ""))
                            if date_from_obj and log_time < date_from_obj:
                                continue
                            if date_to_obj and log_time > date_to_obj:
                                continue
                        except (ValueError, TypeError):
                            continue
                    
                    matching_logs.append({
                        "type": "log",
                        "filename": log.get("file"),
                        "action": log.get("action"),
                        "time": log.get("time"),
                        "user": log.get("user")
                    })
            
            except Exception as e:
                print(f"⚠️ Failed to read access logs: {e}")

    # --- Combine and Sort Results ---
    all_results = matching_files + matching_logs
    
    # Sort by date (newest first)
    def get_sort_date(item):
        if item["type"] == "file":
            return item.get("uploaded_at", "")
        else:
            return item.get("time", "")
    
    all_results.sort(key=get_sort_date, reverse=True)

    # --- Apply Pagination ---
    total = len(all_results)
    paginated_results = all_results[offset:offset + limit]

    return jsonify({
        "results": paginated_results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total
    }), 200

# ---------------- Analyze Logs ----------------
@app.route("/api/analyze", methods=["GET"])
def analyze():
    try:
        alerts = detect_anomalies()
    except Exception as e:
        print("❌ detect_anomalies error:", e)
        alerts = []
    return jsonify({
        "status": "ok",
        "alerts": alerts
    }), 200

# ---------------- Forgot Password ----------------
@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    email = (data.get("email") or "").strip().lower()
    users = load_users()
    if email not in users:
        return jsonify({"error": "email not registered"}), 400

    otp_code = str(random.randint(100000, 999999))
    save_otp(email, otp_code)

    return jsonify({"message": "Password reset OTP sent to email"}), 200

@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.json
    email = (data.get("email") or "").strip().lower()
    otp_code = str(data.get("otp") or "").strip()
    new_pwd = data.get("new_password")

    if not email or not otp_code or not new_pwd:
        return jsonify({"error": "email, otp, and new_password required"}), 400

    if not verify_otp(email, otp_code):
        return jsonify({"error": "invalid or expired OTP"}), 401

    users = load_users()
    if email not in users:
        return jsonify({"error": "user not found"}), 404

    users[email]["password_hash"] = generate_password_hash(new_pwd)
    save_users(users)

    delete_otp(email)
    return jsonify({"message": "Password reset successful"}), 200

# ---------------- Bulk Upload ----------------
@app.route("/api/bulk-upload", methods=["POST"])
def bulk_upload():
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    files = request.files.getlist("files")
    folder = request.form.get("folder", "").strip() or "/"
    
    if not files:
        return jsonify({"error": "no files provided"}), 400

    uploaded = []
    failed = []

    for f in files:
        try:
            filename = secure_filename(f.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            f.save(filepath)

            stored = encrypt_file_and_store(filepath, filename, user_email, folder=folder)
            record_access_log(filename, "upload", user_email)
            try:
                record_activity(user_email, "upload", filename)
            except Exception:
                pass
            uploaded.append(filename)
        except Exception as e:
            failed.append({"filename": f.filename, "error": str(e)})

    return jsonify({
        "message": f"Uploaded {len(uploaded)} files",
        "uploaded": uploaded,
        "failed": failed
    }), 200

# ---------------- Bulk Download (returns zip) ----------------
@app.route("/api/bulk-download", methods=["POST"])
def bulk_download():
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    data = request.json or {}
    filenames = data.get("filenames", [])

    if not filenames:
        return jsonify({"error": "no filenames provided"}), 400

    import zipfile
    import tempfile

    # Create temporary zip file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_paths = []

    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in filenames:
                outpath = decrypt_and_get_file(filename, user_email)
                if outpath and os.path.exists(outpath):
                    zipf.write(outpath, arcname=filename)
                    temp_paths.append(outpath)
                    try:
                        record_activity(user_email, "download", filename)
                    except Exception:
                        pass

        @after_this_request
        def cleanup(response):
            try:
                for path in temp_paths:
                    if os.path.exists(path):
                        os.remove(path)
                if os.path.exists(temp_zip.name):
                    os.remove(temp_zip.name)
            except Exception as e:
                print("❌ Cleanup failed:", str(e))
            return response

        return send_file(temp_zip.name, as_attachment=True, download_name="files.zip")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- Search & Filter Files ----------------
@app.route("/api/files/search", methods=["POST"])
def search_files():
    user_email, err_resp, code = get_user_from_token()
    if err_resp:
        return err_resp, code

    data = request.json or {}
    query = data.get("query", "").lower()
    folder = data.get("folder", "").strip()
    date_from = data.get("date_from")
    date_to = data.get("date_to")

    meta = load_metadata()
    user_files = []

    for stored_name, details in meta.items():
        if details["owner"] != user_email:
            continue

        # Search by filename
        if query and query not in details["original_name"].lower():
            continue

        # Filter by folder
        file_folder = details.get("folder", "/")
        if folder and file_folder != folder:
            continue

        # Filter by date range
        uploaded_at = details.get("uploaded_at", "")
        if date_from and uploaded_at < date_from:
            continue
        if date_to and uploaded_at > date_to:
            continue

        user_files.append({
            "original_name": details["original_name"],
            "uploaded_at": details["uploaded_at"],
            "folder": details.get("folder", "/")
        })

    return jsonify(user_files), 200

# ---------------- Frontend ----------------
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/monitor')
def monitor_page():
    return render_template('monitor.html')

# ---------------- Run ----------------
if __name__ == "__main__":
    init_keys()
    
    # Run metadata migration to ensure all files have folder field
    print("\n🔄 Running metadata migration...")
    migrate_metadata_folders()
    
    print("\nStarting app; email user from env:", os.getenv("EMAIL_USER"))
    app.run(host="0.0.0.0", port=5000, debug=True)

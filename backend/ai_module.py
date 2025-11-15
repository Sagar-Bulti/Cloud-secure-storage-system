import os
import json
from datetime import datetime, timedelta, timezone
from collections import Counter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------- Paths ----------------
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_DIR = os.path.join(BASE_DIR, "db")
os.makedirs(DB_DIR, exist_ok=True)

ACTIVITY_FILE = os.path.join(DB_DIR, "activity_log.json")
ALERT_LOG_FILE = os.path.join(DB_DIR, "sent_alerts.json")  # track sent alerts (by app.py if needed)


# ---------------- Helper: (kept for possible future use) ----------------
def send_email_alert(to_email, subject, message):
    """(Kept but not used here)"""
    try:
        sender = "yourappemail@gmail.com"
        app_password = "your-app-password"
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))
        import smtplib
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.send_message(msg)
        print(f"✅ Alert email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


# ---------------- Record activity ----------------
def record_activity(user, action, filename=None):
    if not user:
        return
    entry = {
        "user": user,
        "action": action,
        "file": filename,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + 'Z'
    }
    data = []
    if os.path.exists(ACTIVITY_FILE):
        try:
            with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(entry)
    with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------- Sent-alert helpers ----------------
def load_sent_alerts():
    if os.path.exists(ALERT_LOG_FILE):
        try:
            with open(ALERT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_sent_alerts(data):
    with open(ALERT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------- Analyze logs (no emailing) ----------------
def analyze_recent_logs(user_filter=None, hours=24, today_only=False):
    """
    Analyze activity_log.json for a given user within the last N hours.
    Returns (stats, alert_message). If no alert, alert_message is "" (empty).
    """
    from datetime import datetime, timedelta

    if not os.path.exists(ACTIVITY_FILE):
        return {}, ""

    try:
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception:
        logs = []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)

    stats = {}
    alert_message = ""

    for entry in logs:
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", ""))
            # If timezone-naive (old format), assume UTC and make timezone-aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if ts < cutoff:
            continue
        user = entry.get("user")
        if user_filter and user != user_filter:
            continue
        action = entry.get("action", "unknown")
        
        # Handle bulk operations: extract count from filename like "5 files"
        count = 1  # Default count for single actions
        if action in ["bulk_upload", "bulk_download"]:
            filename = entry.get("file", "")
            try:
                # Extract number from "N files" format
                if " files" in filename:
                    count = int(filename.split()[0])
            except (ValueError, IndexError):
                count = 1
            
            # Map bulk actions to their individual equivalents for statistics
            if action == "bulk_upload":
                action = "upload"
            elif action == "bulk_download":
                action = "download"
        
        stats.setdefault(user, {})
        stats[user][action] = stats[user].get(action, 0) + count

    # Basic anomaly rules (only set alert_message when there's a real alert)
    user_stats = stats.get(user_filter, {}) if isinstance(stats, dict) else {}
    
    # Log the stats for debugging
    if user_filter:
        print(f"[STATS] Activity stats for {user_filter}: {user_stats}")
    
    # Check for deletion anomalies first (more urgent)
    if user_stats.get("delete", 0) > 2:
        delete_count = user_stats.get("delete", 0)
        alert_message = f"Unusual number of deletions detected ({delete_count} deletions)."
        print(f"[ALERT] {alert_message} for user {user_filter}")
    elif user_stats.get("failed_login", 0) >= 3:
        failed_count = user_stats.get("failed_login", 0)
        alert_message = f"Multiple failed login attempts detected ({failed_count} attempts)."
        print(f"[ALERT] {alert_message} for user {user_filter}")
    else:
        alert_message = ""   # IMPORTANT: empty when nothing suspicious

    return stats, alert_message


# ---------------- Detect anomalies for dashboard (no emailing) ----------------
def detect_anomalies():
    """Return list of alert messages for the dashboard. Does not send emails."""
    if not os.path.exists(ACTIVITY_FILE):
        return []

    try:
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception:
        logs = []

    user_actions = {}
    for entry in logs:
        user = entry.get("user")
        if not user:
            continue
        user_actions[user] = user_actions.get(user, 0) + 1

    alerts = []
    sent_alerts = load_sent_alerts()

    for user, count in user_actions.items():
        if count > 10:
            alert_key = f"{user}_high_activity_dashboard"
            if not sent_alerts.get(alert_key):
                message = f"⚠️ High activity detected for {user} ({count} actions)"
                alerts.append(message)
                # do NOT call send_email_alert here — app.py will decide when to email
                sent_alerts[alert_key] = True

    save_sent_alerts(sent_alerts)
    return alerts

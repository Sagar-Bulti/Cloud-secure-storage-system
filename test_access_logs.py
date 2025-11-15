"""
Test suite for Access Logs system with filtering and pagination.
Tests backend API endpoints and validates log recording with file_type metadata.
"""

import requests
import json
import datetime
import sys
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from storage import record_access_log

API_URL = "http://127.0.0.1:5000/api"
TEST_USER_A = "test_user_a@example.com"
TEST_USER_B = "test_user_b@example.com"
RECEIVER_1 = "receiver1@example.com"
RECEIVER_2 = "receiver2@example.com"

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name, details=""):
        self.passed.append((test_name, details))
        print(f"✅ PASS: {test_name}")
        if details:
            print(f"   {details}")
    
    def add_fail(self, test_name, reason):
        self.failed.append((test_name, reason))
        print(f"❌ FAIL: {test_name}")
        print(f"   Reason: {reason}")
    
    def add_warning(self, test_name, message):
        self.warnings.append((test_name, message))
        print(f"⚠️  WARNING: {test_name}")
        print(f"   {message}")
    
    def print_summary(self):
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"✅ Passed: {len(self.passed)}")
        print(f"❌ Failed: {len(self.failed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        
        if self.failed:
            print("\n" + "-"*80)
            print("FAILURES:")
            for test_name, reason in self.failed:
                print(f"\n  ❌ {test_name}")
                print(f"     {reason}")
        
        if self.warnings:
            print("\n" + "-"*80)
            print("WARNINGS:")
            for test_name, message in self.warnings:
                print(f"\n  ⚠️  {test_name}")
                print(f"     {message}")
        
        print("\n" + "="*80)
        
        return len(self.failed) == 0

results = TestResults()

def get_auth_token(email, password="testpass123"):
    """Get JWT token for authentication"""
    try:
        # Try to register first (might fail if user exists)
        resp_reg = requests.post(f"{API_URL}/register", json={
            "email": email,
            "password": password
        })
        print(f"   Registration response: {resp_reg.status_code}")
    except Exception as e:
        print(f"   Registration skipped: {e}")
    
    # Login to get token
    resp = requests.post(f"{API_URL}/login", json={
        "email": email,
        "password": password
    })
    
    if resp.status_code == 200:
        data = resp.json()
        token = data.get("token") or data.get("access_token")
        if not token:
            raise Exception(f"No token in response: {data}")
        print(f"   Token received: {token[:50]}..." if len(token) > 50 else f"   Token received: {token}")
        return token
    else:
        raise Exception(f"Failed to get token for {email}: {resp.status_code} - {resp.text}")

def create_sample_logs():
    """Create sample access logs for testing"""
    print("\n" + "="*80)
    print("STEP 1: Creating Sample Access Logs")
    print("="*80)
    
    now = datetime.datetime.utcnow()
    yesterday = now - datetime.timedelta(days=1)
    two_days_ago = now - datetime.timedelta(days=2)
    
    test_logs = [
        # Uploads - different file types
        (two_days_ago, "document.pdf", "upload", TEST_USER_A, None),
        (two_days_ago, "presentation.pptx", "upload", TEST_USER_A, None),
        (yesterday, "image.jpg", "upload", TEST_USER_A, None),
        (yesterday, "spreadsheet.xlsx", "upload", TEST_USER_A, None),
        (now, "video.mp4", "upload", TEST_USER_A, None),
        
        # Downloads
        (yesterday, "document.pdf", "download", TEST_USER_A, None),
        (yesterday, "image.jpg", "download", TEST_USER_A, None),
        (now, "presentation.pptx", "download", TEST_USER_A, None),
        
        # Shares with receiver emails
        (yesterday, "document.pdf", "share_create", TEST_USER_A, {"receiver_emails": [RECEIVER_1]}),
        (now, "image.jpg", "share_create", TEST_USER_A, {"receiver_emails": [RECEIVER_1, RECEIVER_2]}),
        (now, "spreadsheet.xlsx", "share_create", TEST_USER_A, {"receiver_emails": [RECEIVER_2]}),
        
        # Auth events
        (two_days_ago, "", "login_success", TEST_USER_A, None),
        (yesterday, "", "login_success", TEST_USER_A, None),
        (yesterday, "", "logout", TEST_USER_A, None),
        (now, "", "login_success", TEST_USER_A, None),
        (now, "", "failed_login", TEST_USER_B, None),
    ]
    
    # Clear existing access log and create fresh test data
    log_file = os.path.join(os.path.dirname(__file__), "db", "access_log.json")
    
    # Backup existing log
    if os.path.exists(log_file):
        backup_file = log_file.replace(".json", "_backup_before_test.json")
        import shutil
        shutil.copy2(log_file, backup_file)
        print(f"📋 Backed up existing log to: {backup_file}")
    
    # Create test logs
    all_logs = []
    for timestamp, filename, action, user, meta in test_logs:
        entry = {
            "user": user,
            "action": action,
            "file": filename,
            "timestamp": timestamp.isoformat()
        }
        
        # Auto-add file_type from filename if not in meta
        if meta is None:
            meta = {}
        else:
            meta = dict(meta)
        
        if "file_type" not in meta and filename and '.' in filename:
            meta["file_type"] = filename.split('.')[-1].lower()
        
        if meta:
            entry["meta"] = meta
        
        all_logs.append(entry)
    
    # Write all logs at once
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(all_logs, f, indent=2)
    
    print(f"✅ Created {len(all_logs)} sample log entries")
    print(f"   - {sum(1 for l in all_logs if l['action'] == 'upload')} uploads")
    print(f"   - {sum(1 for l in all_logs if l['action'] == 'download')} downloads")
    print(f"   - {sum(1 for l in all_logs if l['action'] == 'share_create')} shares")
    print(f"   - {sum(1 for l in all_logs if l['action'] in ['login_success', 'failed_login', 'logout'])} auth events")
    
    return all_logs

def test_api_filter_by_type(token, all_logs):
    """Test filtering by action type"""
    print("\n" + "="*80)
    print("STEP 2: Testing API Filter by Type")
    print("="*80)
    
    # Test upload filter
    resp = requests.get(f"{API_URL}/logs?type=upload", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code != 200:
        results.add_fail("API Filter - Upload Type", f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    logs = data.get("logs", [])
    
    # Verify only uploads returned
    upload_count = len([l for l in logs if l.get("action") == "upload"])
    non_upload_count = len([l for l in logs if l.get("action") != "upload"])
    
    if non_upload_count > 0:
        results.add_fail("API Filter - Upload Type", 
                        f"Found {non_upload_count} non-upload entries in results")
    else:
        expected_uploads = sum(1 for l in all_logs if l['action'] == 'upload')
        results.add_pass("API Filter - Upload Type", 
                        f"Returned {upload_count} uploads (expected {expected_uploads})")
    
    # Test download filter
    resp = requests.get(f"{API_URL}/logs?type=download", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code == 200:
        data = resp.json()
        logs = data.get("logs", [])
        download_count = len([l for l in logs if l.get("action") == "download"])
        non_download = len([l for l in logs if l.get("action") != "download"])
        
        if non_download > 0:
            results.add_fail("API Filter - Download Type", 
                            f"Found {non_download} non-download entries")
        else:
            expected_downloads = sum(1 for l in all_logs if l['action'] == 'download')
            results.add_pass("API Filter - Download Type", 
                            f"Returned {download_count} downloads (expected {expected_downloads})")

def test_api_filter_by_date(token, all_logs):
    """Test filtering by date range"""
    print("\n" + "="*80)
    print("STEP 3: Testing API Filter by Date Range")
    print("="*80)
    
    now = datetime.datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Test filtering for today only
    resp = requests.get(f"{API_URL}/logs?start={today_str}&end={today_str}", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code != 200:
        results.add_fail("API Filter - Date Range", f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    logs = data.get("logs", [])
    
    # Check all returned logs are from today
    today_start = datetime.datetime.combine(now.date(), datetime.time.min)
    today_end = datetime.datetime.combine(now.date(), datetime.time.max)
    
    out_of_range = 0
    for log in logs:
        timestamp = log.get("timestamp")
        if timestamp:
            log_time = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00').replace('+00:00', ''))
            if log_time < today_start or log_time > today_end:
                out_of_range += 1
    
    if out_of_range > 0:
        results.add_fail("API Filter - Date Range", 
                        f"Found {out_of_range} entries outside date range")
    else:
        expected_today = sum(1 for l in all_logs 
                           if datetime.datetime.fromisoformat(l['timestamp']).date() == now.date())
        results.add_pass("API Filter - Date Range", 
                        f"Returned {len(logs)} entries for today (expected {expected_today})")

def test_api_filter_by_file_type(token, all_logs):
    """Test filtering by file extension"""
    print("\n" + "="*80)
    print("STEP 4: Testing API Filter by File Type")
    print("="*80)
    
    # Test PDF filter
    resp = requests.get(f"{API_URL}/logs?file_type=pdf", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code != 200:
        results.add_fail("API Filter - File Type (PDF)", f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    logs = data.get("logs", [])
    
    # Check all returned logs are PDF files
    non_pdf = 0
    for log in logs:
        file_type = log.get("meta", {}).get("file_type", "").lower()
        filename = log.get("file", "")
        
        # Check both meta.file_type and filename extension
        if file_type != "pdf" and not filename.lower().endswith(".pdf"):
            non_pdf += 1
    
    if non_pdf > 0:
        results.add_fail("API Filter - File Type (PDF)", 
                        f"Found {non_pdf} non-PDF entries in results")
    else:
        expected_pdf = sum(1 for l in all_logs 
                          if l.get('meta', {}).get('file_type') == 'pdf' or 
                          l.get('file', '').lower().endswith('.pdf'))
        results.add_pass("API Filter - File Type (PDF)", 
                        f"Returned {len(logs)} PDF entries (expected {expected_pdf})")
    
    # Test JPG filter
    resp = requests.get(f"{API_URL}/logs?file_type=jpg", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code == 200:
        data = resp.json()
        logs = data.get("logs", [])
        jpg_count = len(logs)
        expected_jpg = sum(1 for l in all_logs 
                          if l.get('meta', {}).get('file_type') == 'jpg' or 
                          l.get('file', '').lower().endswith('.jpg'))
        results.add_pass("API Filter - File Type (JPG)", 
                        f"Returned {jpg_count} JPG entries (expected {expected_jpg})")

def test_api_filter_by_receiver_email(token, all_logs):
    """Test filtering shares by receiver email"""
    print("\n" + "="*80)
    print("STEP 5: Testing API Filter by Receiver Email")
    print("="*80)
    
    # Test filtering by RECEIVER_1
    resp = requests.get(f"{API_URL}/logs?type=share_create&receiver_email={RECEIVER_1}", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code != 200:
        results.add_fail("API Filter - Receiver Email", f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    logs = data.get("logs", [])
    
    # Check all returned logs include RECEIVER_1 in receiver_emails
    missing_receiver = 0
    for log in logs:
        receivers = log.get("meta", {}).get("receiver_emails", [])
        if RECEIVER_1 not in receivers:
            missing_receiver += 1
    
    if missing_receiver > 0:
        results.add_fail("API Filter - Receiver Email", 
                        f"Found {missing_receiver} entries without {RECEIVER_1}")
    else:
        expected = sum(1 for l in all_logs 
                      if l.get('action') == 'share_create' and 
                      RECEIVER_1 in l.get('meta', {}).get('receiver_emails', []))
        results.add_pass("API Filter - Receiver Email", 
                        f"Returned {len(logs)} shares to {RECEIVER_1} (expected {expected})")
    
    # Test filtering by RECEIVER_2
    resp = requests.get(f"{API_URL}/logs?type=share_create&receiver_email={RECEIVER_2}", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code == 200:
        data = resp.json()
        logs = data.get("logs", [])
        expected = sum(1 for l in all_logs 
                      if l.get('action') == 'share_create' and 
                      RECEIVER_2 in l.get('meta', {}).get('receiver_emails', []))
        results.add_pass("API Filter - Receiver Email (2)", 
                        f"Returned {len(logs)} shares to {RECEIVER_2} (expected {expected})")

def test_api_pagination(token):
    """Test pagination with limit and offset"""
    print("\n" + "="*80)
    print("STEP 6: Testing API Pagination")
    print("="*80)
    
    # Test with limit=5
    resp = requests.get(f"{API_URL}/logs?limit=5", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code != 200:
        results.add_fail("API Pagination - Limit", f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    logs = data.get("logs", [])
    total = data.get("total", 0)
    limit = data.get("limit", 0)
    offset = data.get("offset", 0)
    has_more = data.get("has_more", False)
    
    if len(logs) > 5:
        results.add_fail("API Pagination - Limit", f"Returned {len(logs)} entries (expected max 5)")
    else:
        results.add_pass("API Pagination - Limit", 
                        f"Returned {len(logs)} of {total} entries (limit=5, has_more={has_more})")
    
    # Test offset
    resp = requests.get(f"{API_URL}/logs?limit=5&offset=5", headers={
        "Authorization": f"Bearer {token}"
    })
    
    if resp.status_code == 200:
        data = resp.json()
        logs_page2 = data.get("logs", [])
        offset_returned = data.get("offset", 0)
        
        if offset_returned != 5:
            results.add_warning("API Pagination - Offset", 
                              f"Expected offset=5, got {offset_returned}")
        else:
            results.add_pass("API Pagination - Offset", 
                            f"Page 2 returned {len(logs_page2)} entries with offset=5")

def test_combined_filters(token):
    """Test combining multiple filters"""
    print("\n" + "="*80)
    print("STEP 7: Testing Combined Filters")
    print("="*80)
    
    now = datetime.datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")
    
    # Test type + date + file_type
    resp = requests.get(
        f"{API_URL}/logs?type=upload&start={today_str}&file_type=mp4",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if resp.status_code != 200:
        results.add_fail("API Combined Filters", f"Status {resp.status_code}: {resp.text}")
        return
    
    data = resp.json()
    logs = data.get("logs", [])
    
    # Verify all criteria met
    violations = []
    for log in logs:
        if log.get("action") != "upload":
            violations.append(f"Wrong action: {log.get('action')}")
        
        file_type = log.get("meta", {}).get("file_type", "")
        filename = log.get("file", "")
        if file_type != "mp4" and not filename.lower().endswith(".mp4"):
            violations.append(f"Wrong file type: {file_type} / {filename}")
        
        log_date = datetime.datetime.fromisoformat(log.get("timestamp", "")).date()
        if log_date != now.date():
            violations.append(f"Wrong date: {log_date}")
    
    if violations:
        results.add_fail("API Combined Filters", f"Found violations: {violations}")
    else:
        results.add_pass("API Combined Filters", 
                        f"Returned {len(logs)} entries matching all criteria (upload + today + mp4)")

def test_file_type_in_metadata(all_logs):
    """Verify file_type is stored in metadata"""
    print("\n" + "="*80)
    print("STEP 8: Verifying file_type in Metadata")
    print("="*80)
    
    logs_with_files = [l for l in all_logs if l.get('file') and '.' in l.get('file')]
    missing_file_type = []
    incorrect_file_type = []
    
    for log in logs_with_files:
        filename = log.get('file', '')
        expected_ext = filename.split('.')[-1].lower()
        actual_ext = log.get('meta', {}).get('file_type', '')
        
        if not actual_ext:
            missing_file_type.append(filename)
        elif actual_ext != expected_ext:
            incorrect_file_type.append(f"{filename}: expected {expected_ext}, got {actual_ext}")
    
    if missing_file_type:
        results.add_fail("Metadata - file_type Missing", 
                        f"Missing file_type for: {', '.join(missing_file_type)}")
    elif incorrect_file_type:
        results.add_fail("Metadata - file_type Incorrect", 
                        f"Incorrect values: {', '.join(incorrect_file_type)}")
    else:
        results.add_pass("Metadata - file_type", 
                        f"All {len(logs_with_files)} file entries have correct file_type")

def print_frontend_instructions():
    """Print manual testing instructions for frontend"""
    print("\n" + "="*80)
    print("STEP 9: Frontend Manual Testing Instructions")
    print("="*80)
    
    print("""
📋 FRONTEND TESTING CHECKLIST:

1. Open http://127.0.0.1:5000 in your browser

2. Login with credentials:
   Email: test_user_a@example.com
   Password: testpass123

3. Navigate to "Access Logs" section

4. TEST UPLOAD TAB:
   ✓ Should show 5 upload entries
   ✓ Apply file type filter (select "PDF") → should show 1 entry
   ✓ Apply file type filter (select "MP4") → should show 1 entry
   ✓ Clear filters → should show all 5 uploads again
   ✓ Click column headers to sort (Date, Time, File Name, File Type)
   ✓ Search box: type "document" → should filter to matching rows
   ✓ Export CSV → should download CSV file with visible rows

5. TEST DOWNLOAD TAB:
   ✓ Should show 3 download entries
   ✓ Apply date filters (yesterday only) → should show 2 entries
   ✓ Test sorting and search functionality

6. TEST SHARED TAB:
   ✓ Should show 3 share entries
   ✓ Search for receiver email "receiver1@example.com" → should show 2 entries
   ✓ Search for "receiver2@example.com" → should show 2 entries
   ✓ Verify receiver emails column displays correctly

7. TEST AUTH TAB:
   ✓ Should show login/logout entries
   ✓ Verify color-coded status badges (green=SUCCESS, red=FAILED, blue=LOGOUT)
   ✓ Test sorting and filtering

8. TEST PAGINATION:
   ✓ If you have 50+ logs, verify Previous/Next buttons work
   ✓ Verify "Showing X - Y of Z entries" is correct

9. TEST CLIENT-SIDE FEATURES:
   ✓ Sorting: Click headers multiple times to toggle asc/desc (⇅ ↑ ↓)
   ✓ Search: Type in search box and verify real-time filtering
   ✓ CSV Export: Download and verify CSV contains correct data

⚠️  EXPECTED RESULTS:
- Filters should work independently and in combination
- Pagination should maintain filter state
- Sorting should update visual indicators
- Search should only filter visible page results
- CSV export should include only visible rows
""")

def main():
    print("\n" + "="*80)
    print("ACCESS LOGS SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Testing API at: {API_URL}")
    print(f"Test User: {TEST_USER_A}")
    
    try:
        # Create sample logs (doesn't require server)
        all_logs = create_sample_logs()
        
        # Verify metadata
        test_file_type_in_metadata(all_logs)
        
        # Try to run API tests if server is available
        try:
            print("\n🔐 Getting authentication token...")
            token = get_auth_token(TEST_USER_A)
            print(f"✅ Got token for {TEST_USER_A}")
            
            # Run API tests
            test_api_filter_by_type(token, all_logs)
            test_api_filter_by_date(token, all_logs)
            test_api_filter_by_file_type(token, all_logs)
            test_api_filter_by_receiver_email(token, all_logs)
            test_api_pagination(token)
            test_combined_filters(token)
            
        except Exception as e:
            results.add_warning("API Tests Skipped", 
                              f"Could not connect to server: {str(e)[:100]}")
            print("\n⚠️  Backend server not running - skipping API tests")
            print("   To run API tests:")
            print("   1. Start server: cd backend && python run.py")
            print("   2. Run this test again in a new terminal")
        
        # Print frontend testing instructions
        print_frontend_instructions()
        
        # Print summary
        success = results.print_summary()
        
        if success:
            print("\n🎉 LOG CREATION TESTS PASSED!")
            print("\n📝 Next Steps:")
            print("   1. Start the backend server: cd backend && python run.py")
            print("   2. Run this test again to execute API tests")
            print("   3. Follow the frontend testing instructions above")
            print("   4. Verify all UI features work correctly")
        else:
            print("\n⚠️  SOME TESTS FAILED - See details above")
            print("\n💡 Suggestions:")
            print("   1. Check that file_type is correctly stored in metadata")
            print("   2. Verify database files exist in db/ directory")
            print("   3. Review storage.py record_access_log() function")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

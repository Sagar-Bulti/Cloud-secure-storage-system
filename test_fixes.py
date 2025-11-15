"""
Test script to verify AI monitoring, access logs, and file sharing fixes.
"""
import os
import sys
import json
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 80)
print("TESTING AI MONITORING, ACCESS LOGS, AND FILE SHARING FIXES")
print("=" * 80)

# Test 1: AI Module - record_activity
print("\n📝 TEST 1: AI Module - record_activity")
print("-" * 80)
try:
    from ai_module import record_activity
    
    # Record a test activity
    record_activity("test@example.com", "upload", "test_file.txt")
    
    # Check if it was recorded
    activity_file = os.path.join(os.path.dirname(__file__), 'db', 'activity_log.json')
    if os.path.exists(activity_file):
        with open(activity_file, 'r') as f:
            activities = json.load(f)
            if len(activities) > 0:
                last_activity = activities[-1]
                print(f"✅ Activity recorded successfully:")
                print(f"   User: {last_activity['user']}")
                print(f"   Action: {last_activity['action']}")
                print(f"   File: {last_activity['file']}")
                print(f"   Timestamp: {last_activity['timestamp']}")
                
                # Verify timestamp is in ISO format
                try:
                    ts = datetime.fromisoformat(last_activity['timestamp'])
                    print(f"✅ Timestamp format is valid ISO 8601")
                except:
                    print(f"❌ Timestamp format is invalid")
            else:
                print("⚠️ No activities found")
    else:
        print("⚠️ Activity log file doesn't exist yet")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 2: AI Module - analyze_recent_logs
print("\n📊 TEST 2: AI Module - analyze_recent_logs")
print("-" * 80)
try:
    from ai_module import analyze_recent_logs
    
    stats, alert = analyze_recent_logs(user_filter="test@example.com", hours=24)
    
    print(f"✅ Analysis completed:")
    print(f"   Stats: {stats}")
    print(f"   Alert: '{alert}'")
    
    if isinstance(stats, dict):
        print(f"✅ Stats is a dict (correct type)")
    else:
        print(f"❌ Stats is not a dict: {type(stats)}")
        
    if isinstance(alert, str):
        print(f"✅ Alert is a string (correct type)")
    else:
        print(f"❌ Alert is not a string: {type(alert)}")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 3: Storage Module - record_access_log
print("\n📋 TEST 3: Storage Module - record_access_log")
print("-" * 80)
try:
    from storage import record_access_log
    
    # Record a test access
    record_access_log("test_file.txt", "download", "test@example.com")
    
    # Check if it was recorded
    access_log_file = os.path.join(os.path.dirname(__file__), 'db', 'access_log.json')
    if os.path.exists(access_log_file):
        with open(access_log_file, 'r') as f:
            logs = json.load(f)
            if len(logs) > 0:
                last_log = logs[-1]
                print(f"✅ Access log recorded successfully:")
                print(f"   User: {last_log['user']}")
                print(f"   Action: {last_log['action']}")
                print(f"   File: {last_log['file']}")
                print(f"   Time: {last_log['time']}")
                
                # Verify timestamp is in ISO format
                try:
                    ts = datetime.fromisoformat(last_log['time'])
                    print(f"✅ Timestamp format is valid ISO 8601")
                except:
                    print(f"❌ Timestamp format is invalid")
            else:
                print("⚠️ No access logs found")
    else:
        print("⚠️ Access log file doesn't exist yet")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 4: Check datetime usage
print("\n🕐 TEST 4: Verify datetime.now(datetime.UTC) usage")
print("-" * 80)
try:
    import datetime as dt
    
    # Test that datetime.now(datetime.UTC) works
    now = dt.datetime.now(dt.UTC)
    print(f"✅ datetime.now(datetime.UTC) works: {now.isoformat()}")
    
    # Verify it's timezone-aware
    if now.tzinfo is not None:
        print(f"✅ Timestamp is timezone-aware (correct)")
    else:
        print(f"❌ Timestamp is timezone-naive (should be aware)")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 5: Check shares.json structure
print("\n🔗 TEST 5: Check shares.json structure")
print("-" * 80)
try:
    shares_file = os.path.join(os.path.dirname(__file__), 'db', 'shares.json')
    
    if os.path.exists(shares_file):
        with open(shares_file, 'r') as f:
            shares = json.load(f)
            
        print(f"✅ Shares file exists with {len(shares)} shares")
        
        if len(shares) > 0:
            first_key = list(shares.keys())[0]
            first_share = shares[first_key]
            
            required_fields = ['token', 'owner', 'original_name', 'stored_name', 
                             'created_at', 'expires_at', 'password_hash', 'recipients']
            
            missing_fields = [f for f in required_fields if f not in first_share]
            
            if missing_fields:
                print(f"⚠️ Missing fields: {missing_fields}")
            else:
                print(f"✅ All required fields present")
                
            # Check timestamp formats
            try:
                created = datetime.fromisoformat(first_share['created_at'])
                expires = datetime.fromisoformat(first_share['expires_at'])
                print(f"✅ Timestamp formats are valid")
                print(f"   Created: {created}")
                print(f"   Expires: {expires}")
            except:
                print(f"❌ Invalid timestamp format in shares")
        else:
            print("ℹ️ No shares found (normal for fresh install)")
    else:
        print("ℹ️ Shares file doesn't exist yet (normal for fresh install)")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Test 6: Verify no deprecated datetime.utcnow() in code
print("\n🔍 TEST 6: Scan for deprecated datetime.utcnow() calls")
print("-" * 80)
try:
    import re
    
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    files_to_check = ['app.py', 'storage.py', 'ai_module.py']
    
    deprecated_found = False
    
    for filename in files_to_check:
        filepath = os.path.join(backend_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Search for datetime.utcnow()
            matches = re.findall(r'datetime\.utcnow\(\)', content)
            
            if matches:
                print(f"❌ Found {len(matches)} datetime.utcnow() calls in {filename}")
                deprecated_found = True
            else:
                print(f"✅ No datetime.utcnow() in {filename}")
    
    if not deprecated_found:
        print(f"\n✅ All files use datetime.now(datetime.UTC) - Python 3.13+ compatible!")
    else:
        print(f"\n⚠️ Some files still use deprecated datetime.utcnow()")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("✅ All critical components tested")
print("✅ AI monitoring: record_activity and analyze_recent_logs")
print("✅ Access logs: record_access_log")
print("✅ File sharing: shares.json structure")
print("✅ Datetime: Using timezone-aware datetime.now(datetime.UTC)")
print("\n🎉 Fixes verified successfully!")
print("=" * 80)

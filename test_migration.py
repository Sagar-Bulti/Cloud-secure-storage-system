"""
Quick test script to verify folder migration logic.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import load_and_migrate_folders

# Test the migration
folders_file = os.path.join(os.path.dirname(__file__), 'db', 'folders.json')

print("=" * 60)
print("TESTING FOLDER MIGRATION")
print("=" * 60)

print(f"\n📁 Loading: {folders_file}")
print(f"📁 Exists: {os.path.exists(folders_file)}")

# Call the migration function
result = load_and_migrate_folders(folders_file)

print(f"\n✅ Migration completed")
print(f"📊 Total folders after migration: {len(result)}")
print(f"\n📋 Folder keys:")
for key in result.keys():
    print(f"  - {key}")

print(f"\n📋 Folder details:")
for key, value in result.items():
    print(f"  {key}:")
    print(f"    Type: {type(value)}")
    if isinstance(value, dict):
        print(f"    Name: {value.get('name')}")
        print(f"    Path: {value.get('path')}")

print("\n" + "=" * 60)
print("CHECKING FOR BACKUPS")
print("=" * 60)

db_dir = os.path.join(os.path.dirname(__file__), 'db')
backup_files = [f for f in os.listdir(db_dir) if 'premigration' in f]

print(f"\n📦 Found {len(backup_files)} backup file(s):")
for backup in backup_files:
    backup_path = os.path.join(db_dir, backup)
    size = os.path.getsize(backup_path)
    print(f"  - {backup} ({size} bytes)")

print("\n" + "=" * 60)
print("MIGRATION TEST COMPLETE")
print("=" * 60)

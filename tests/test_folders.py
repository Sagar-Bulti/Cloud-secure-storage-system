"""
Test folder management endpoints and migration logic.
"""
import json
import os

def test_list_folders_triggers_migration(client, auth_token, test_dirs):
    """Test that GET /api/folders triggers migration from mixed format."""
    # Create folders.json with MIXED format (old list + new dict)
    folders_file = os.path.join(test_dirs['db'], 'folders.json')
    mixed_data = {
        "test@example.com": ["old_folder"],  # OLD FORMAT: list
        "test@example.com:/new_folder": {    # NEW FORMAT: dict
            "id": "test@example.com:/new_folder",
            "name": "new_folder",
            "path": "/new_folder",
            "parent_path": "/",
            "owner": "test@example.com",
            "created_at": "2024-11-15T00:00:00"
        }
    }
    
    with open(folders_file, 'w') as f:
        json.dump(mixed_data, f)
    
    # Make GET request - should trigger migration
    response = client.get(
        '/api/folders',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    assert response.status_code == 200
    data = response.get_json()
    
    # Should return list of folders
    assert isinstance(data, list)
    
    # Should have migrated the old list entry
    # Now read folders.json to verify migration happened
    with open(folders_file, 'r') as f:
        migrated_data = json.load(f)
    
    # All entries should now be dicts (no lists)
    for key, value in migrated_data.items():
        assert isinstance(value, dict), f"Expected dict for key '{key}', got {type(value)}"
    
    # Old list entry should be converted to dict format
    assert "test@example.com:/old_folder" in migrated_data
    assert migrated_data["test@example.com:/old_folder"]["name"] == "old_folder"
    
    # New entry should still exist
    assert "test@example.com:/new_folder" in migrated_data


def test_create_folder(client, auth_token, test_dirs):
    """Test POST /api/folders creates folder in dict format."""
    folders_file = os.path.join(test_dirs['db'], 'folders.json')
    
    # Start with empty folders
    with open(folders_file, 'w') as f:
        json.dump({}, f)
    
    response = client.post(
        '/api/folders',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={'name': 'test_folder', 'parent_path': '/'}
    )
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'test_folder'
    
    # Verify folders.json has dict format
    with open(folders_file, 'r') as f:
        folders_data = json.load(f)
    
    # Should have exactly one entry in dict format
    assert len(folders_data) == 1
    folder_key = "test@example.com:/test_folder"
    assert folder_key in folders_data
    assert isinstance(folders_data[folder_key], dict)
    assert folders_data[folder_key]['name'] == 'test_folder'


def test_migration_creates_backup(client, auth_token, test_dirs):
    """Test that migration creates a backup file before converting."""
    folders_file = os.path.join(test_dirs['db'], 'folders.json')
    
    # Create file with old format
    old_format = {
        "test@example.com": ["folder1", "folder2"]
    }
    
    with open(folders_file, 'w') as f:
        json.dump(old_format, f)
    
    # Trigger migration via GET request
    response = client.get(
        '/api/folders',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    assert response.status_code == 200
    
    # Check that backup was created
    db_dir = test_dirs['db']
    backup_files = [f for f in os.listdir(db_dir) if f.startswith('folders_premigration_')]
    
    assert len(backup_files) > 0, "Expected backup file to be created"
    
    # Verify backup contains original data
    backup_path = os.path.join(db_dir, backup_files[0])
    with open(backup_path, 'r') as f:
        backup_data = json.load(f)
    
    assert backup_data == old_format


def test_no_migration_on_pure_dict(client, auth_token, test_dirs):
    """Test that pure dict format doesn't trigger migration."""
    folders_file = os.path.join(test_dirs['db'], 'folders.json')
    
    # Create file with pure dict format
    pure_dict = {
        "test@example.com:/folder1": {
            "id": "test@example.com:/folder1",
            "name": "folder1",
            "path": "/folder1",
            "parent_path": "/",
            "owner": "test@example.com",
            "created_at": "2024-11-15T00:00:00"
        }
    }
    
    with open(folders_file, 'w') as f:
        json.dump(pure_dict, f)
    
    # Count backup files before request
    db_dir = test_dirs['db']
    backup_count_before = len([f for f in os.listdir(db_dir) if f.startswith('folders_premigration_')])
    
    # Trigger endpoint
    response = client.get(
        '/api/folders',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    assert response.status_code == 200
    
    # No new backup should be created (no migration needed)
    backup_count_after = len([f for f in os.listdir(db_dir) if f.startswith('folders_premigration_')])
    
    assert backup_count_after == backup_count_before, "No migration backup should be created for pure dict format"

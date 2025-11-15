"""
API Endpoint Tests for SecureCloud Pro

Tests for:
- Bulk upload endpoint
- Bulk download endpoint  
- Search endpoint

Run with: pytest tests/test_api.py -v
"""
import os
import io
import json
import zipfile
import pytest


class TestUploadMultiple:
    """Test suite for POST /api/upload-multiple endpoint."""
    
    def test_upload_multiple_success(self, client, auth_headers, sample_files, test_dirs, monkeypatch):
        """Test successful upload of multiple files."""
        # Mock the storage functions to avoid encryption complexity
        from unittest.mock import MagicMock
        import app
        
        # Mock encrypt_file_and_store
        def mock_encrypt(filepath, filename, user_email, folder="/"):
            return {
                "stored_as": f"test_at_example.com_{filename}",
                "original": filename,
                "owner": user_email,
                "folder": folder
            }
        
        monkeypatch.setattr('app.encrypt_file_and_store', mock_encrypt)
        monkeypatch.setattr('app.record_access_log', MagicMock())
        monkeypatch.setattr('app.record_activity', MagicMock())
        
        # Prepare multipart form data
        data = {
            'files[]': [
                (open(sample_files['file1'], 'rb'), 'test1.txt'),
                (open(sample_files['file2'], 'rb'), 'test2.txt')
            ],
            'folder': '/'
        }
        
        response = client.post(
            '/api/upload-multiple',
            data=data,
            headers={'Authorization': auth_headers['Authorization']},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 200
        result = response.get_json()
        
        # Verify response structure
        assert 'stored' in result
        assert 'errors' in result
        assert 'message' in result
        
        # Verify 2 files were uploaded
        assert len(result['stored']) == 2
        assert 'Uploaded 2 of 2 files' in result['message']
        
        # Verify individual file details
        stored_names = [f['original_name'] for f in result['stored']]
        assert 'test1.txt' in stored_names
        assert 'test2.txt' in stored_names
    
    def test_upload_multiple_no_auth(self, client, sample_files):
        """Test upload without authentication token."""
        data = {
            'files[]': [
                (open(sample_files['file1'], 'rb'), 'test1.txt')
            ]
        }
        
        response = client.post(
            '/api/upload-multiple',
            data=data,
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 401
        assert 'error' in response.get_json()
    
    def test_upload_multiple_no_files(self, client, auth_headers):
        """Test upload with no files provided."""
        response = client.post(
            '/api/upload-multiple',
            data={},
            headers={'Authorization': auth_headers['Authorization']},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        result = response.get_json()
        assert 'error' in result
        assert 'no files' in result['error'].lower()
    
    def test_upload_multiple_exceeds_limit(self, client, auth_headers, sample_files):
        """Test upload exceeding max file count."""
        # Create 21 files (exceeds limit of 20)
        files = [(open(sample_files['file1'], 'rb'), f'test{i}.txt') for i in range(21)]
        
        data = {'files[]': files}
        
        response = client.post(
            '/api/upload-multiple',
            data=data,
            headers={'Authorization': auth_headers['Authorization']},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        result = response.get_json()
        assert 'too many files' in result['error'].lower()


class TestDownloadMultiple:
    """Test suite for POST /api/download-multiple endpoint."""
    
    def test_download_multiple_success(self, client, auth_headers, test_dirs, monkeypatch):
        """Test successful download of multiple files as ZIP."""
        from unittest.mock import MagicMock
        import tempfile
        
        # Create mock decrypted files
        temp_file1 = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file1.write('Test content 1')
        temp_file1.close()
        
        temp_file2 = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file2.write('Test content 2')
        temp_file2.close()
        
        # Mock decrypt_and_get_file to return temp files
        file_map = {
            'test1.txt': temp_file1.name,
            'test2.txt': temp_file2.name
        }
        
        def mock_decrypt(filename, user_email):
            return file_map.get(filename)
        
        monkeypatch.setattr('app.decrypt_and_get_file', mock_decrypt)
        monkeypatch.setattr('app.record_access_log', MagicMock())
        monkeypatch.setattr('app.record_activity', MagicMock())
        
        # Request download
        response = client.post(
            '/api/download-multiple',
            data=json.dumps({'filenames': ['test1.txt', 'test2.txt']}),
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        assert response.content_type == 'application/zip'
        
        # Verify it's a valid ZIP file
        zip_data = io.BytesIO(response.data)
        with zipfile.ZipFile(zip_data, 'r') as zf:
            namelist = zf.namelist()
            assert 'test1.txt' in namelist
            assert 'test2.txt' in namelist
        
        # Cleanup
        try:
            os.remove(temp_file1.name)
            os.remove(temp_file2.name)
        except:
            pass
    
    def test_download_multiple_no_auth(self, client):
        """Test download without authentication."""
        response = client.post(
            '/api/download-multiple',
            data=json.dumps({'filenames': ['test.txt']}),
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 401
    
    def test_download_multiple_no_filenames(self, client, auth_headers):
        """Test download without filenames."""
        response = client.post(
            '/api/download-multiple',
            data=json.dumps({}),
            headers=auth_headers
        )
        
        assert response.status_code == 400
        result = response.get_json()
        assert 'error' in result
    
    def test_download_multiple_invalid_files(self, client, auth_headers, monkeypatch):
        """Test download of non-existent files."""
        from unittest.mock import MagicMock
        
        # Mock decrypt to return None (file not found)
        monkeypatch.setattr('app.decrypt_and_get_file', lambda f, u: None)
        
        response = client.post(
            '/api/download-multiple',
            data=json.dumps({'filenames': ['nonexistent.txt']}),
            headers=auth_headers
        )
        
        assert response.status_code == 404
        result = response.get_json()
        assert 'invalid_files' in result or 'error' in result


class TestSearch:
    """Test suite for GET /api/search endpoint."""
    
    def test_search_basic(self, client, auth_headers, test_dirs, monkeypatch):
        """Test basic search functionality."""
        from unittest.mock import MagicMock
        
        # Mock load_metadata to return test data
        def mock_load_metadata():
            return {
                'test_user_file1.pdf': {
                    'owner': 'test@example.com',
                    'original_name': 'document.pdf',
                    'uploaded_at': '2025-11-15T10:00:00',
                    'folder': '/',
                    'size': 1024
                },
                'test_user_file2.txt': {
                    'owner': 'test@example.com',
                    'original_name': 'notes.txt',
                    'uploaded_at': '2025-11-15T11:00:00',
                    'folder': '/documents',
                    'size': 512
                }
            }
        
        monkeypatch.setattr('app.load_metadata', mock_load_metadata)
        
        response = client.get(
            '/api/search?query=document',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        
        # Verify response structure
        assert 'results' in result
        assert 'total' in result
        assert 'limit' in result
        assert 'offset' in result
        assert 'has_more' in result
        
        # Verify results contain expected fields
        if len(result['results']) > 0:
            first_result = result['results'][0]
            assert 'type' in first_result
            assert 'filename' in first_result
    
    def test_search_with_filters(self, client, auth_headers, monkeypatch):
        """Test search with type and date filters."""
        # Mock metadata
        def mock_load_metadata():
            return {
                'test_file.pdf': {
                    'owner': 'test@example.com',
                    'original_name': 'report.pdf',
                    'uploaded_at': '2025-11-15T10:00:00',
                    'folder': '/',
                    'size': 2048
                }
            }
        
        monkeypatch.setattr('app.load_metadata', mock_load_metadata)
        
        response = client.get(
            '/api/search?type=pdf&from=2025-11-01&to=2025-11-30',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'results' in result
    
    def test_search_pagination(self, client, auth_headers, monkeypatch):
        """Test search pagination."""
        def mock_load_metadata():
            return {
                f'file{i}.txt': {
                    'owner': 'test@example.com',
                    'original_name': f'test{i}.txt',
                    'uploaded_at': '2025-11-15T10:00:00',
                    'folder': '/',
                    'size': 100
                }
                for i in range(100)
            }
        
        monkeypatch.setattr('app.load_metadata', mock_load_metadata)
        
        # Test first page
        response = client.get(
            '/api/search?limit=10&offset=0',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert result['limit'] == 10
        assert result['offset'] == 0
        assert result['has_more'] == True
        assert len(result['results']) <= 10
    
    def test_search_no_auth(self, client):
        """Test search without authentication."""
        response = client.get('/api/search')
        
        assert response.status_code == 401
    
    def test_search_rate_limit(self, client, auth_headers, monkeypatch):
        """Test rate limiting on search endpoint."""
        import app
        
        # Clear rate limit state before test
        app._search_rate_limit.clear()
        
        monkeypatch.setattr('app.load_metadata', lambda: {})
        
        # Make 31 requests (exceeds limit of 30)
        for i in range(31):
            response = client.get('/api/search', headers=auth_headers)
            
            if i < 30:
                assert response.status_code == 200
            else:
                # 31st request should be rate limited
                assert response.status_code == 429
                result = response.get_json()
                assert 'rate limit' in result['error'].lower()
                break


class TestIntegration:
    """Integration tests combining multiple endpoints."""
    
    def test_upload_and_search(self, client, auth_headers, sample_files, monkeypatch):
        """Test uploading files and then searching for them."""
        from unittest.mock import MagicMock
        import app
        
        # Clear rate limit state before test
        app._search_rate_limit.clear()
        
        # Mock storage functions
        stored_metadata = {}
        
        def mock_encrypt(filepath, filename, user_email, folder="/"):
            stored_name = f"{user_email.replace('@', '_at_')}_{filename}"
            stored_metadata[stored_name] = {
                'owner': user_email,
                'original_name': filename,
                'uploaded_at': '2025-11-15T10:00:00',
                'folder': folder,
                'size': 100
            }
            return {
                "stored_as": stored_name,
                "original": filename,
                "owner": user_email,
                "folder": folder
            }
        
        def mock_load_metadata():
            return stored_metadata
        
        monkeypatch.setattr('app.encrypt_file_and_store', mock_encrypt)
        monkeypatch.setattr('app.load_metadata', mock_load_metadata)
        monkeypatch.setattr('app.record_access_log', MagicMock())
        monkeypatch.setattr('app.record_activity', MagicMock())
        
        # Upload files
        upload_data = {
            'files[]': [
                (open(sample_files['file1'], 'rb'), 'test1.txt')
            ]
        }
        
        upload_response = client.post(
            '/api/upload-multiple',
            data=upload_data,
            headers={'Authorization': auth_headers['Authorization']},
            content_type='multipart/form-data'
        )
        
        assert upload_response.status_code == 200
        
        # Search for uploaded file
        search_response = client.get(
            '/api/search?query=test1',
            headers=auth_headers
        )
        
        assert search_response.status_code == 200
        result = search_response.get_json()
        assert result['total'] >= 1

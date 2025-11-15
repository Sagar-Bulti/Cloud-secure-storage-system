"""
Pytest configuration and fixtures for API tests.
"""
import os
import sys
import tempfile
import shutil
import pytest
import json
from datetime import datetime

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

@pytest.fixture(scope='session')
def test_dirs():
    """Create temporary directories for test data."""
    temp_base = tempfile.mkdtemp(prefix='securecloud_test_')
    
    test_paths = {
        'base': temp_base,
        'db': os.path.join(temp_base, 'db'),
        'local_store': os.path.join(temp_base, 'local_store'),
        'temp': os.path.join(temp_base, 'temp'),
        'keys': os.path.join(temp_base, 'keys')
    }
    
    # Create all directories
    for path in test_paths.values():
        os.makedirs(path, exist_ok=True)
    
    # Create empty files.json
    with open(os.path.join(test_paths['db'], 'files.json'), 'w') as f:
        json.dump({}, f)
    
    # Create empty users.json with test user
    with open(os.path.join(test_paths['db'], 'users.json'), 'w') as f:
        from werkzeug.security import generate_password_hash
        json.dump({
            'test@example.com': {
                'password_hash': generate_password_hash('testpass123'),
                'username': 'Test User',
                'mfa_enabled': False
            }
        }, f)
    
    # Create empty access_log.json
    with open(os.path.join(test_paths['db'], 'access_log.json'), 'w') as f:
        json.dump([], f)
    
    yield test_paths
    
    # Cleanup after all tests
    shutil.rmtree(temp_base, ignore_errors=True)


@pytest.fixture
def app(test_dirs):
    """Create Flask app instance with test configuration."""
    # Set environment variables before importing app
    os.environ['JWT_SECRET'] = 'test-secret-key'
    os.environ['EMAIL_USER'] = 'test@example.com'
    os.environ['EMAIL_PASS'] = 'test-password'
    
    # Import app after setting environment
    from app import app as flask_app
    
    # Override paths to use test directories
    flask_app.config['TESTING'] = True
    flask_app.config['UPLOAD_FOLDER'] = test_dirs['local_store']
    
    # Monkey-patch BASE_DIR in the app module
    import app as app_module
    app_module.BASE_DIR = test_dirs['base']
    
    yield flask_app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def auth_token(client):
    """Get a valid JWT token for test user."""
    import jwt
    from datetime import datetime, timedelta
    
    token = jwt.encode(
        {
            'sub': 'test@example.com',
            'exp': datetime.utcnow() + timedelta(hours=2)
        },
        'test-secret-key',
        algorithm='HS256'
    )
    
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    return token


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers with valid token."""
    return {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def sample_files(test_dirs):
    """Create sample test files."""
    files_dir = os.path.join(test_dirs['base'], 'test_files')
    os.makedirs(files_dir, exist_ok=True)
    
    files = {}
    
    # Create small test file 1
    file1_path = os.path.join(files_dir, 'test1.txt')
    with open(file1_path, 'w') as f:
        f.write('This is test file 1')
    files['file1'] = file1_path
    
    # Create small test file 2
    file2_path = os.path.join(files_dir, 'test2.txt')
    with open(file2_path, 'w') as f:
        f.write('This is test file 2')
    files['file2'] = file2_path
    
    yield files
    
    # Cleanup
    shutil.rmtree(files_dir, ignore_errors=True)

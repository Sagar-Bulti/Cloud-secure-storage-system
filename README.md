# 🔐 SecureCloud Pro - AI-Powered File Storage System

A secure, AI-monitored cloud file storage application with end-to-end encryption, multi-factor authentication, and intelligent threat detection.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running Tests](#running-tests)
- [Feature Details](#feature-details)
- [Security Features](#security-features)
- [API Endpoints](#api-endpoints)
- [Usage Guide](#usage-guide)
- [Future Enhancements](#future-enhancements)
- [Contributors](#contributors)

---

## 🎯 Overview

**SecureCloud Pro** is a full-stack web application that provides secure file storage with AI-powered security monitoring. The system encrypts files before storage, implements two-factor authentication via email OTP, and uses machine learning to detect suspicious activities.

### **Core Capabilities:**
- 🔒 **AES-256 Encryption** for all stored files
- 🤖 **AI-Powered Security Monitoring** to detect anomalies
- 📧 **Two-Factor Authentication (2FA)** via email OTP
- 📁 **Folder Organization** with hierarchical structure
- 🔗 **Secure File Sharing** with password protection
- 📊 **Activity Logging** and audit trails
- 📦 **Bulk Operations** for upload/download
- 🔍 **Advanced Search & Filtering**

---

## ✨ Key Features

### 1. **User Authentication & Security**
- User registration with email verification
- Secure login with password hashing (bcrypt)
- Two-Factor Authentication (OTP sent via email)
- Password reset functionality
- Session management with JWT tokens
- Auto-logout for security (no persistent sessions)

### 2. **File Management**
- **Single File Upload**: Upload files to specific folders
- **Bulk Upload**: Upload multiple files at once
- **Download Files**: Secure download with decryption
- **Bulk Download**: Download multiple files as a ZIP archive
- **Delete Files**: Permanent file removal
- **File Sharing**: Share files with other users via encrypted links

### 3. **Folder Organization**
- Create custom folders (e.g., Documents, Photos, Videos)
- Organize files into folders
- Filter files by folder location
- Hierarchical folder structure

### 4. **Search & Filter**
- Search files by name
- Filter files by folder
- Real-time search results
- Case-insensitive search

### 5. **AI Security Monitoring**
- Machine learning-based anomaly detection
- Real-time activity monitoring
- Suspicious activity alerts
- Visual activity charts (Chart.js)
- Detection of unusual patterns:
  - Multiple failed login attempts
  - Excessive file downloads
  - Unusual upload/delete patterns

### 6. **Activity Logs**
- Complete audit trail of all user actions
- Tracks: uploads, downloads, deletions, shares
- Timestamped log entries
- User-specific activity history

### 7. **File Sharing**
- Share files with multiple recipients
- Password-protected share links
- Email notifications to recipients
- Custom or auto-generated passwords
- Secure access control

---

## 🛠️ Technology Stack

### **Backend:**
- **Python 3.x** - Core programming language
- **Flask** - Web framework
- **Flask-CORS** - Cross-Origin Resource Sharing
- **SQLite** - Lightweight database (JSON-based storage)
- **Cryptography (Fernet)** - File encryption/decryption
- **bcrypt** - Password hashing
- **PyJWT** - JSON Web Tokens for authentication
- **scikit-learn** - Machine learning for AI monitoring
- **SMTP (smtplib)** - Email functionality
- **python-dotenv** - Environment variable management

### **Frontend:**
- **HTML5** - Structure
- **CSS3** - Styling with modern design
- **JavaScript (Vanilla)** - Client-side logic
- **Chart.js** - Data visualization
- **Google Fonts (Inter)** - Typography
- **Responsive Design** - Mobile-friendly UI

### **Security:**
- **RSA Encryption** - For key exchange
- **AES-256 Encryption** - File encryption
- **bcrypt** - Password hashing
- **JWT Tokens** - Secure sessions
- **OTP Verification** - Two-factor authentication

### **AI/ML:**
- **Isolation Forest** - Anomaly detection algorithm
- **scikit-learn** - Machine learning library
- **Real-time monitoring** - Activity pattern analysis

---

## 📁 Project Structure

```
Mini project 1/
├── backend/
│   ├── app.py              # Main Flask application with all API routes
│   ├── storage.py          # File encryption/decryption & storage logic
│   ├── ai_module.py        # AI monitoring and anomaly detection
│   └── run.py              # Server launcher script
│
├── frontend/
│   └── index.html          # Complete single-page application UI
│
├── ai/
│   └── train_model.py      # AI model training script
│
├── db/
│   ├── users.json          # User credentials (hashed passwords)
│   ├── files.json          # File metadata
│   ├── folders.json        # User-created folders
│   ├── activity_log.json   # Activity audit trail
│   ├── access_log.json     # Access logs
│   ├── otp.json            # OTP codes with expiry
│   ├── shares.json         # File sharing records
│   ├── sent_alerts.json    # Security alert history
│   └── secret.key          # Encryption secret key
│
├── keys/
│   ├── rsa_priv.pem        # RSA private key
│   └── rsa_pub.pem         # RSA public key
│
├── storage_files/          # Encrypted files storage
├── local_store/            # Local file processing
├── temp/                   # Temporary files
├── venv/                   # Python virtual environment
│
├── .env                    # Environment variables (email config)
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
├── NEW_FEATURES.md         # New features documentation
└── README.md               # This file
```

---

## 🚀 Installation & Setup

### **Prerequisites:**
- Python 3.7 or higher
- pip (Python package manager)
- Email account (Gmail recommended for SMTP)

### **Step 1: Clone or Download the Project**
```bash
cd "Mini project 1"
```

### **Step 2: Create Virtual Environment**
```bash
python -m venv venv
```

### **Step 3: Activate Virtual Environment**

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### **Step 4: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 5: Configure Environment Variables**

Create a `.env` file in the root directory:
```env
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
```

**Note:** For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833):
1. Enable 2FA on your Google account
2. Generate an App Password
3. Use that password in `.env`

### **Step 6: Initialize the Database**

The database files will be created automatically on first run. Ensure the `db/` folder exists.

### **Step 7: Run the Application**

**Option 1: Using run.py**
```bash
cd backend
python run.py
```

**Option 2: Direct Flask run**
```bash
cd backend
python app.py
```

### **Step 8: Access the Application**

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Running Tests

### **Prerequisites**
Ensure you have pytest installed (included in `requirements.txt`).

### **Run All Tests**
```bash
# From project root directory
pytest tests/ -v
```

### **Run Specific Test File**
```bash
pytest tests/test_api.py -v
```

### **Run Specific Test Class**
```bash
pytest tests/test_api.py::TestUploadMultiple -v
```

### **Run with Coverage**
```bash
# Install pytest-cov first
pip install pytest-cov

# Run with coverage report
pytest tests/ --cov=backend --cov-report=html
```

### **Test Structure**

The test suite includes:

1. **Upload Multiple Tests** (`TestUploadMultiple`)
   - ✅ Successful upload of 2 files
   - ✅ Upload without authentication (401)
   - ✅ Upload with no files (400)
   - ✅ Upload exceeding file limit (400)

2. **Download Multiple Tests** (`TestDownloadMultiple`)
   - ✅ Successful ZIP download with 2 files
   - ✅ Download without authentication (401)
   - ✅ Download with no filenames (400)
   - ✅ Download of non-existent files (404)

3. **Search Tests** (`TestSearch`)
   - ✅ Basic search functionality
   - ✅ Search with type and date filters
   - ✅ Pagination (limit/offset)
   - ✅ Search without authentication (401)
   - ✅ Rate limiting (429 after 30 requests)

4. **Integration Tests** (`TestIntegration`)
   - ✅ Upload and search workflow

### **Test Configuration**

Tests use temporary directories for:
- Database files (`files.json`, `users.json`, `access_log.json`)
- Encrypted file storage
- Temporary decrypted files
- Encryption keys

All test data is automatically cleaned up after test execution.

### **Continuous Integration**

To add to CI/CD pipeline:
```yaml
# Example: .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

---

## 📖 Feature Details

### **1. User Registration & Login**

#### **Registration:**
- User provides email and password
- Password is hashed using bcrypt (salt rounds: 12)
- User data stored in `db/users.json`
- Duplicate email prevention

#### **Login Flow:**
1. User enters email and password
2. Backend validates credentials
3. OTP (6-digit code) sent to user's email
4. OTP valid for 5 minutes
5. User enters OTP to verify
6. JWT token issued upon successful verification
7. Token used for all subsequent requests

#### **Security Features:**
- Passwords never stored in plain text
- OTP expires after 5 minutes
- Invalid OTP attempts logged
- Auto-logout on browser refresh (no persistent sessions)

---

### **2. File Upload & Storage**

#### **Single File Upload:**
```
POST /api/upload
- Accepts: file (multipart/form-data), folder (optional)
- Encrypts file using AES-256
- Generates unique encrypted filename
- Stores metadata in files.json
- Returns: success/error message
```

**Process:**
1. User selects file and destination folder
2. File sent to backend
3. Backend encrypts file with Fernet (AES-256)
4. Encrypted file saved in `storage_files/`
5. Metadata (original name, owner, upload time, folder) saved
6. Activity logged

#### **Bulk Upload:**
```
POST /api/bulk-upload
- Accepts: multiple files, folder
- Processes each file individually
- Returns: list of uploaded and failed files
```

**Features:**
- Upload up to 100 files at once
- Progress tracking
- Individual error handling per file
- All files encrypted separately

---

### **3. File Download**

#### **Single Download:**
```
GET /api/download/<filename>
- Retrieves encrypted file
- Decrypts on-the-fly
- Streams to user
- Logs download activity
```

#### **Bulk Download:**
```
POST /api/bulk-download
- Accepts: array of filenames
- Creates temporary ZIP archive
- Decrypts each file
- Adds to ZIP
- Streams ZIP to user
- Cleans up temporary files
```

**Security:**
- Only file owner can download
- Files decrypted in memory (not on disk)
- Temporary files deleted immediately
- Download activity logged

---

### **4. File Sharing**

```
POST /api/share
- Accepts: filename, recipients (array), password (optional)
- Creates secure share record
- Generates password if not provided
- Sends email to all recipients
- Returns: share password
```

**Sharing Process:**
1. User selects file to share
2. Enters recipient email(s)
3. Optionally sets custom password
4. System generates share link
5. Email sent to recipients with:
   - File name
   - Sender information
   - Access password
   - Instructions
6. Recipients use password to access file

**Features:**
- Multi-recipient sharing
- Password-protected access
- Email notifications
- Custom or auto-generated passwords
- Share history tracking

---

### **5. Folder Management**

#### **Create Folder:**
```
POST /api/folders/create
- Accepts: folder name
- Creates virtual folder
- Stores in folders.json
- Returns: success message
```

#### **List Folders:**
```
GET /api/folders
- Returns: all user's folders
- Includes folders from files and folders.json
- Unique folder list
```

**Features:**
- Hierarchical organization
- Virtual folders (no physical directories)
- Folder filtering in file list
- Root folder (/) for default storage

---

### **6. Search & Filter**

```
POST /api/files/search
- Accepts: query (search term), folder (filter)
- Searches file names (case-insensitive)
- Filters by folder if specified
- Returns: matching files
```

**Search Capabilities:**
- Real-time search
- Partial name matching
- Case-insensitive
- Combined with folder filter
- Instant results

---

### **7. Activity Logging**

**Logged Actions:**
- User registration
- Login attempts (success/failure)
- File uploads
- File downloads
- File deletions
- File sharing
- Folder creation

**Log Entry Structure:**
```json
{
  "user": "user@email.com",
  "action": "upload",
  "file": "document.pdf",
  "time": "2025-11-13T10:30:00",
  "ip": "127.0.0.1"
}
```

**Access Logs:**
```
GET /api/logs
- Returns: user's activity history
- Sorted by timestamp (newest first)
- Includes all actions
```

---

### **8. AI Security Monitoring**

#### **How It Works:**

**Data Collection:**
- Monitors all user activities (24-hour window)
- Tracks: uploads, downloads, deletions, shares
- Creates activity vectors for analysis

**Anomaly Detection:**
```python
Algorithm: Isolation Forest
- Unsupervised machine learning
- Detects outliers in activity patterns
- Contamination: 0.1 (10% anomaly threshold)
```

**Detection Patterns:**
- Multiple failed login attempts
- Excessive downloads (> 10 in short time)
- Unusual upload patterns
- Rapid file deletions
- Abnormal sharing behavior

**Alert System:**
```
GET /api/monitor-data
- Returns: activity statistics, alert message
- Alerts stored in sent_alerts.json
- Prevents duplicate alerts (24-hour cooldown)
```

**Alert Types:**
- ⚠️ Multiple failed login attempts detected
- ⚠️ Unusual download activity
- ⚠️ Suspicious file operations
- ✅ No suspicious activity detected

**Visualization:**
- Bar chart showing activity counts
- Real-time statistics
- 24-hour activity window

---

### **9. Password Reset**

**Flow:**
1. User clicks "Forgot Password"
2. Enters email address
3. OTP sent to email
4. User enters OTP + new password
5. Password updated (bcrypt hashed)
6. User can login with new password

```
POST /api/forgot-password
- Sends OTP to email

POST /api/reset-password
- Verifies OTP
- Updates password
```

---

## 🔐 Security Features

### **1. Encryption**

**File Encryption:**
- **Algorithm:** AES-256 (Fernet)
- **Process:** 
  - Unique key generated from `secret.key`
  - Each file encrypted separately
  - Original filename hashed
  - Encrypted content stored

**Password Security:**
- **Algorithm:** bcrypt
- **Salt Rounds:** 12
- **Process:**
  - Password + random salt → hash
  - Hash stored in database
  - Original password never stored

**RSA Keys:**
- Public/private key pair in `keys/`
- Used for secure key exchange
- 2048-bit RSA encryption

### **2. Authentication**

**JWT Tokens:**
- Issued after OTP verification
- Expires after session
- Required for all protected endpoints
- Stored in browser localStorage

**OTP Security:**
- 6-digit random code
- 5-minute expiration
- Single-use only
- Deleted after verification

### **3. Session Management**

**Security Measures:**
- No auto-login (manual sign-in required)
- Credentials cleared on logout
- Session cleared on browser close
- Token validation on every request

### **4. Data Protection**

- All files encrypted at rest
- Passwords hashed (never plain text)
- Secure file deletion
- Activity logging for audit
- Email notifications for shares

---

## 🔌 API Endpoints

### **Authentication:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Register new user |
| POST | `/api/login` | Login and send OTP |
| POST | `/api/verify-otp` | Verify OTP and get token |
| POST | `/api/forgot-password` | Send password reset OTP |
| POST | `/api/reset-password` | Reset password with OTP |

### **File Operations:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload single file |
| POST | `/api/bulk-upload` | Upload multiple files |
| GET | `/api/download/<filename>` | Download file |
| POST | `/api/bulk-download` | Download multiple files as ZIP |
| DELETE | `/api/delete/<filename>` | Delete file |
| GET | `/api/files` | List all user files |
| POST | `/api/files/search` | Search and filter files |

### **Folder Operations:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/folders/create` | Create new folder |
| GET | `/api/folders` | List all folders |

### **Sharing & Logs:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/share` | Share file with users |
| GET | `/api/logs` | Get activity logs |
| GET | `/api/monitor-data` | Get AI monitoring data |

---

## 📱 Usage Guide

### **Getting Started:**

1. **Register:**
   - Click "Register" on home page
   - Enter email and password
   - Account created

2. **Login:**
   - Enter credentials
   - Check email for OTP
   - Enter OTP to verify
   - Access dashboard

### **Uploading Files:**

**Single Upload:**
1. Select folder from dropdown (or create new)
2. Click upload area
3. Select file
4. File uploaded and encrypted

**Bulk Upload:**
1. Select folder
2. Click "Bulk Upload"
3. Select multiple files
4. All files uploaded

### **Managing Files:**

**Download:**
- Click download button (⬇️) on any file
- File decrypted and downloaded

**Share:**
- Click share button (🔗)
- Enter recipient email(s)
- Set password (or auto-generate)
- Recipients receive email

**Delete:**
- Click delete button (🗑️)
- Confirm deletion
- File permanently removed

**Bulk Download:**
1. Check boxes next to files
2. Click "Download Selected"
3. ZIP file downloaded

### **Search & Filter:**
1. Enter filename in search box
2. Select folder filter (optional)
3. Click "Search"
4. Results displayed instantly

### **Creating Folders:**
1. Click "+ New Folder"
2. Enter folder name
3. Folder created and available in dropdown

### **Monitoring Security:**
1. Click "AI Monitor" in sidebar
2. View activity chart
3. Check for security alerts
4. Review statistics

---

## 🚀 Future Enhancements

### **Planned Features:**
- [ ] Cloud deployment (AWS/GCP/Azure)
- [ ] File versioning
- [ ] Collaborative editing
- [ ] Advanced permissions system
- [ ] Mobile app (React Native)
- [ ] File preview (images, PDFs)
- [ ] Storage quota management
- [ ] Advanced AI threat detection
- [ ] Multi-language support
- [ ] Dark mode theme
- [ ] File compression
- [ ] Folder sharing
- [ ] Public share links
- [ ] File comments/annotations
- [ ] Integration with third-party services

### **Possible Improvements:**
- PostgreSQL/MySQL for better scalability
- Redis for caching
- WebSocket for real-time updates
- CDN for faster file delivery
- Advanced search (tags, content search)
- Trash/recycle bin functionality
- File recovery options

---

## 👥 Contributors

**Developer:** [Your Name]  
**Project Type:** Mini Project / Academic Project  
**Date:** November 2025  
**Version:** 1.0.0  

---

## 📄 License

This project is created for educational purposes. Feel free to use and modify for learning.

---

## 🙏 Acknowledgments

- Flask framework and community
- scikit-learn for ML capabilities
- Chart.js for visualizations
- Google Fonts for typography
- All open-source contributors

---

## 📞 Support

For issues, questions, or contributions:
- Check existing documentation in `NEW_FEATURES.md`
- Review code comments in source files
- Test features in development mode first

---

## 🎯 Project Highlights

✅ **Full-stack application** with modern architecture  
✅ **AI-powered security** with machine learning  
✅ **Production-ready encryption** (AES-256)  
✅ **Comprehensive feature set** (upload, download, share, search)  
✅ **Professional UI/UX** with responsive design  
✅ **Complete authentication** with 2FA  
✅ **Activity monitoring** and audit trails  
✅ **Scalable architecture** ready for cloud deployment  

---

**Built with ❤️ using Python, Flask, and JavaScript**

# Deployment Guide - Render.com

## Files Created for Deployment

✅ **requirements.txt** - Added `gunicorn` (production web server)
✅ **render.yaml** - Render configuration with build/start commands
✅ **.gitignore** - Prevents sensitive files from being committed

---

## Step-by-Step Deployment Instructions

### 1️⃣ Push Code to GitHub

**First time setup:**
```bash
cd "c:\Users\Asus\OneDrive\Desktop\Mini project 1"
git init
git add .
git commit -m "Initial commit - Cloud Storage System"
```

**Create GitHub repository:**
- Go to https://github.com/new
- Name: `cloud-storage-system` (or any name)
- Select: **Public** or **Private**
- Don't initialize with README (we already have one)
- Click "Create repository"

**Push your code:**
```bash
git remote add origin https://github.com/YOUR_USERNAME/cloud-storage-system.git
git branch -M main
git push -u origin main
```

---

### 2️⃣ Deploy on Render

**Sign up:**
- Go to https://render.com
- Click "Get Started for Free"
- Sign up with GitHub account (easiest)

**Create Web Service:**
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Render will auto-detect `render.yaml`
4. Click "Apply" to use the configuration

**Manual setup (if render.yaml not detected):**
- **Name:** cloud-storage-app
- **Environment:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `cd backend && gunicorn --bind 0.0.0.0:$PORT run:app`
- **Instance Type:** Free

---

### 3️⃣ Configure Environment Variables

In Render dashboard → Your service → Environment:

Add these secret variables:
- `EMAIL_USER` = `cloudproject.sender2005@gmail.com`
- `EMAIL_PASS` = `tbupjbmpmkuehyme`
- `SMTP_SERVER` = `smtp.gmail.com`
- `SMTP_PORT` = `587`
- `OTP_EXPIRY` = `180`

Click "Save Changes"

---

### 4️⃣ Deploy!

Render will automatically:
- Install dependencies
- Start your Flask app
- Provide a URL like: `https://cloud-storage-app.onrender.com`

**First deploy takes 5-10 minutes** ⏱️

---

## 🔄 Making Changes After Deployment

**Automatic deployment:**
```bash
# Make your changes to code
git add .
git commit -m "Fix bug / Add feature"
git push
```

Render automatically redeploys when you push to GitHub! 🚀

---

## ⚠️ Important Notes

### Free Tier Limitations:
1. **Ephemeral Storage** - Uploaded files will be lost on restart
   - Solution: Upgrade to paid plan + add AWS S3 storage
   
2. **Cold Starts** - Service sleeps after 15 min inactivity
   - First request may take 30-60 seconds
   
3. **Database** - JSON files reset on restart
   - Solution: Add PostgreSQL database (free on Render)

### Security:
- Your `.env` file is NOT uploaded (blocked by .gitignore)
- Environment variables are set securely in Render dashboard
- HTTPS is automatic and free

---

## 🐛 Troubleshooting

**Build fails:**
- Check logs in Render dashboard
- Verify all packages in `requirements.txt` are correct

**App crashes:**
- Check "Logs" tab in Render dashboard
- Ensure environment variables are set correctly

**Frontend can't connect:**
- Update `frontend/index.html` API URLs from `http://localhost:5000` to your Render URL

---

## 📝 Next Steps (Optional Upgrades)

1. **Persistent Storage:** Add AWS S3 for file uploads
2. **Database:** Migrate from JSON to PostgreSQL
3. **Custom Domain:** Add your own domain (free SSL)
4. **Monitoring:** Set up health checks and alerts

---

**Your app will be live at:** `https://YOUR-APP-NAME.onrender.com`

Good luck! 🎉

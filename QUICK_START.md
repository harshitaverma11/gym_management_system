# Gym Management System - Quick Start Guide

## Local Development (Windows/Mac/Linux)

### Backend Setup
```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
# Backend runs on http://localhost:5000
```

### Frontend Setup
```bash
# In a new terminal, navigate to frontend
cd frontend

# Start a simple server
python -m http.server 5500
# Frontend runs on http://localhost:5500
```

**Default Login Credentials:**
- Username: `admin` | Password: `admin123`
- Username: `trainer1` | Password: `trainer123`
- Username: `member1` | Password: `member123`

---

## Deploy to Render (Free Tier)

### Step 1: Prepare GitHub Repository
```bash
git init
git add .
git commit -m "Initial commit for Render"
git remote add origin https://github.com/YOUR_USERNAME/gym-management-system
git push -u origin main
```

### Step 2: Create PostgreSQL Database
1. Go to https://render.com and sign in
2. Click **+ New** → **PostgreSQL**
3. Database name: `gym_management`
4. Leave other settings as default
5. Click **Create Database**
6. Wait for creation (2-3 min), then copy the **Internal Database URL**

### Step 3: Deploy Backend
1. Click **+ New** → **Web Service**
2. Select your GitHub repository
3. Configure:
   - **Name:** `gym-backend`
   - **Root Directory:** `backend`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

4. Add these **Environment Variables:**
   ```
   DATABASE_URL = <paste the PostgreSQL URL from Step 2>
   FLASK_ENV = production
   SECRET_KEY = <generate a random string>
   ALLOWED_ORIGINS = https://<your-frontend-domain>,http://localhost:5500
   ```

5. Click **Create Web Service**
6. Wait 3-5 minutes for deployment
7. Your backend URL: `https://gym-backend.onrender.com`

### Step 4: Deploy Frontend (Static Site)
1. Click **+ New** → **Static Site**
2. Select your GitHub repository
3. Configure:
   - **Name:** `gym-frontend`
   - **Root Directory:** `frontend`
   - Leave **Build Command** empty
   - **Publish Directory:** `.`

4. Click **Create Static Site**
5. Your frontend URL: `https://gym-frontend.onrender.com`

### Step 5: Update Frontend API Endpoint
Edit `frontend/js/script.js` line 6:

**Before:**
```javascript
const API_BASE_URL = 'http://127.0.0.1:5000';
```

**After:**
```javascript
const API_BASE_URL = 'https://gym-backend.onrender.com';
```

Then push the change:
```bash
git add frontend/js/script.js
git commit -m "Update API endpoint for Render deployment"
git push
```

### Step 6: Verify Deployment
1. Open https://gym-frontend.onrender.com
2. Login with: `admin` / `admin123`
3. Check browser console (F12) for any errors

---

## Free Tier Limitations

- ⏰ Web services sleep after 15 min of inactivity (30 sec to wake up)
- 💾 PostgreSQL limited to 256 MB
- 🌐 Static sites are always active
- 📊 Limited build minutes per month

**For production:** Upgrade to paid plan

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to database" | Check `DATABASE_URL` env var in Render dashboard |
| CORS errors | Update `ALLOWED_ORIGINS` to include frontend domain |
| API requests fail | Check backend logs in Render → Logs tab |
| Frontend shows old API URL | Clear browser cache, verify git push succeeded |

---

## Key Files Modified for Render

- ✅ `backend/database.py` - PostgreSQL instead of MySQL
- ✅ `backend/create_users_table.py` - PostgreSQL syntax
- ✅ `backend/create_workouts_table.py` - PostgreSQL queries
- ✅ `backend/requirements.txt` - Added psycopg2, gunicorn
- ✅ `backend/Procfile` - Render deployment config
- ✅ `backend/.env` - Environment variables template
- ✅ `frontend/js/script.js` - Update API_BASE_URL before deploying

---

## Next Steps

- Monitor your apps in Render dashboard
- Set up custom domain (requires paid plan)
- Backup PostgreSQL data regularly
- Update default user passwords in production

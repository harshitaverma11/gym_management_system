# Render Deployment - Step-by-Step Checklist

## Pre-Deployment (Local Setup)

- [ ] Install Python 3.8+ and git
- [ ] Clone or navigate to your project
- [ ] Open terminal in `backend` folder
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate venv:
  - Windows: `.\venv\Scripts\activate`
  - Mac/Linux: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Test backend: `python app.py` (should say "Running on...")
- [ ] Test login at `http://localhost:5000` with credentials:
  - admin / admin123
  - trainer1 / trainer123
  - member1 / member123

## GitHub Preparation

- [ ] Create `.gitignore` file in project root (if needed)
- [ ] `git init`
- [ ] `git add .`
- [ ] `git commit -m "Initial commit - ready for Render"`
- [ ] Create GitHub repository
- [ ] `git remote add origin https://github.com/YOUR_USERNAME/repo-name`
- [ ] `git push -u origin main`

## Render Setup - Database

- [ ] Go to https://render.com and create account
- [ ] Click **+ New** → **PostgreSQL**
- [ ] Fill in:
  - Name: `gym_management_db` (or any name)
  - Region: Choose closest to you
  - Database: `gym_management`
- [ ] Click **Create Database**
- [ ] Wait for "Available" status (~2-3 minutes)
- [ ] Click on database name
- [ ] Copy **Internal Database URL** (looks like: `postgresql://user:pass@host:port/db`)
- [ ] Save this URL for Step 3

## Render Setup - Backend Service

- [ ] In Render dashboard: **+ New** → **Web Service**
- [ ] Select your GitHub repository
- [ ] Fill in:
  - **Name:** `gym-backend`
  - **Root Directory:** `backend`
  - **Environment:** `Python 3`
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn app:app`

- [ ] Click **Add Environment Variable** 4 times:
  1. `DATABASE_URL` = (paste your PostgreSQL URL from Step 2)
  2. `FLASK_ENV` = `production`
  3. `SECRET_KEY` = (run: `python -c "import secrets; print(secrets.token_hex(32))"`)
  4. `ALLOWED_ORIGINS` = (leave as is for now, will update later)

- [ ] Click **Create Web Service**
- [ ] Wait for deployment (~3-5 minutes)
- [ ] Copy your backend URL (will be like: `https://gym-backend.onrender.com`)
- [ ] Note: Service may show "Deploying" for a few minutes

## Render Setup - Frontend

- [ ] In Render dashboard: **+ New** → **Static Site**
- [ ] Select your GitHub repository
- [ ] Fill in:
  - **Name:** `gym-frontend`
  - **Root Directory:** `frontend`
  - Leave **Build Command** empty
  - **Publish Directory:** `.`

- [ ] Click **Create Static Site**
- [ ] Wait for deployment (~2-3 minutes)
- [ ] Copy your frontend URL (will be like: `https://gym-frontend.onrender.com`)

## Update Frontend Configuration

- [ ] Open `frontend/js/script.js` in your editor
- [ ] Find line 6: `const API_BASE_URL = 'http://127.0.0.1:5000';`
- [ ] Replace with: `const API_BASE_URL = 'https://gym-backend.onrender.com';`
- [ ] (Replace with your actual backend URL from previous step)
- [ ] Save file
- [ ] In terminal:
  ```bash
  git add frontend/js/script.js
  git commit -m "Update API endpoint for Render"
  git push
  ```
- [ ] Wait for frontend to redeploy (~1-2 minutes)

## Update Backend ALLOWED_ORIGINS

- [ ] In Render dashboard, click on your backend service
- [ ] Click **Environment**
- [ ] Find `ALLOWED_ORIGINS` variable
- [ ] Update to: `https://gym-frontend.onrender.com,http://localhost:5500`
- [ ] Save changes (service will restart)
- [ ] Wait for restart (~1 minute)

## Final Testing

- [ ] Open your frontend URL in browser
- [ ] You should see login page
- [ ] Try logging in with: `admin` / `admin123`
- [ ] You should be redirected to dashboard
- [ ] Open browser console (F12) → Console tab
- [ ] Should see NO errors (check Network tab for API calls)
- [ ] Try adding a member or viewing workouts
- [ ] Everything working? ✅ Deployment is complete!

## If Something Goes Wrong

1. **Check Render Logs:**
   - Render dashboard → your service → **Logs** tab
   - Look for error messages

2. **Common Issues:**
   - CORS error → Update `ALLOWED_ORIGINS` (Step 8)
   - API returns 404 → Check `API_BASE_URL` in `script.js` (Step 7)
   - Database connection error → Verify `DATABASE_URL` (Step 3)
   - Frontend shows old API URL → Hard refresh browser (Ctrl+Shift+R)

3. **Still Stuck?**
   - Check if backend URL is accessible: visit `https://gym-backend.onrender.com/`
   - Should show: `{"message": "GymPro API Running", "status": "success", "version": "2.0"}`
   - Check backend logs for detailed error messages

## You're Done! 🎉

Your Gym Management System is now live on:
- **Frontend:** https://gym-frontend.onrender.com
- **Backend API:** https://gym-backend.onrender.com

---

## Maintenance Notes

- **Database backups:** Render provides snapshots (check dashboard)
- **Updating code:** Just `git push` and Render auto-redeploys
- **Changing passwords:** Update default users in `create_users_table.py`
- **Service spinning down:** Normal on free tier, service wakes up on first request

Need help? Check `QUICK_START.md` or `RENDER_DEPLOYMENT.md` for more details.

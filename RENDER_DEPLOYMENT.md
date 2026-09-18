# Render Deployment Guide for Gym Management System

## Prerequisites
- Render account (free tier available)
- GitHub repository with your code

## Step 1: Prepare Your Repository
```bash
cd Gym_Management_System
git init
git add .
git commit -m "Initial commit for Render deployment"
git remote add origin <your-github-repo-url>
git push -u origin main
```

## Step 2: Create PostgreSQL Database on Render
1. Go to [render.com](https://render.com)
2. Click **+ New** → **PostgreSQL**
3. Name: `gym-db`
4. Database: `gym_management`
5. Leave region and other settings as default
6. Click **Create Database**
7. Wait for database to be ready (2-3 minutes)
8. Copy the **Internal Database URL** (you'll need this in Step 4)

## Step 3: Deploy Backend Service
1. Click **+ New** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Name:** `gym-backend`
   - **Root Directory:** `backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Add Environment Variables:
   - `DATABASE_URL` = (paste the Internal Database URL from Step 2)
   - `SECRET_KEY` = (create a secure random string)
   - `FLASK_ENV` = `production`
   - `ALLOWED_ORIGINS` = `https://<your-frontend-domain>,http://localhost:5500`
5. Click **Create Web Service**
6. Wait for deployment (3-5 minutes)
7. Your backend URL will be: `https://gym-backend.onrender.com`

## Step 4: Deploy Frontend (Static Site)
1. Click **+ New** → **Static Site**
2. Connect your GitHub repository
3. Configure:
   - **Name:** `gym-frontend`
   - **Root Directory:** `frontend`
   - **Build Command:** (leave empty)
   - **Publish Directory:** `.`
4. Click **Create Static Site**
5. Your frontend URL will be: `https://gym-frontend.onrender.com`

## Step 5: Update Frontend Configuration
Edit `frontend/js/config.js` (if it exists) or update API calls to use:
```javascript
const API_URL = 'https://gym-backend.onrender.com';
```

Or in your HTML files, replace:
- `http://localhost:5000` → `https://gym-backend.onrender.com`

## Step 6: Test the Deployment
1. Open `https://gym-frontend.onrender.com` in your browser
2. Try logging in with default credentials:
   - Username: `admin`, Password: `admin123`
   - Username: `trainer1`, Password: `trainer123`
   - Username: `member1`, Password: `member123`

## Notes on Render Free Tier
- **Limits:**
  - Web service spins down after 15 minutes of inactivity (takes 30 seconds to spin up)
  - Static sites are always active
  - PostgreSQL free tier has 256 MB storage limit
- **For Production:**
  - Upgrade to paid plan for always-on services
  - Increase database storage as needed
  - Use environment-specific configurations

## Troubleshooting
- **Database connection error?** Check `DATABASE_URL` environment variable in Render dashboard
- **CORS error?** Verify `ALLOWED_ORIGINS` includes your frontend domain
- **Service not starting?** Check logs in Render dashboard → Logs tab
- **Need to run migrations?** Use Render Shell to run initialization scripts

## How to Access Render Dashboard
1. Log in to [render.com](https://render.com)
2. Click on your service name
3. View logs, environment variables, and deployment status

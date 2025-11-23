# Render Deployment Guide

## 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/jvybatuto-coder.git
git push -u origin main
```

## 2. Deploy on Render
1. Go to render.com
2. Connect GitHub account
3. Create new Web Service
4. Select your dailyfish repository
5. Configure:
   - Build Command: `./myproject/build.sh`
   - Start Command: `cd myproject && gunicorn myproject.wsgi:application`
   - Environment: Python 3

## 3. Environment Variables
Set in Render dashboard:
- `DEBUG=False`
- `ALLOWED_HOSTS=your-app-name.onrender.com`
- Database variables (auto-configured with PostgreSQL add-on)
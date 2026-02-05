# Savitara - Quick Start Guide

## 🚀 Start Everything (One Command)

### Option 1: PowerShell (Recommended)
```powershell
.\start-all.ps1
```

### Option 2: Command Prompt
```cmd
start-all.bat
```

### Option 3: Double-click
- Just **double-click** `start-all.bat` or `start-all.ps1` in Windows Explorer

## 🛑 Stop Everything

### PowerShell
```powershell
.\stop-all.ps1
```

### Command Prompt
```cmd
stop-all.bat
```

## 📋 What Happens?

When you run the start script:
1. ✅ Backend launches in a separate window (Port 8000)
2. ✅ Frontend launches in a separate window (Port 3000)
3. ✅ Both stay running until you close them
4. ✅ Health check confirms backend is ready

## 🌐 Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔐 Authentication Options

### Manual Sign-Up/Login
1. Go to http://localhost:3000/login
2. Click "Sign Up" tab
3. Enter: Email, Password, Name
4. Select Role: **Grihasta** (user) or **Acharya** (service provider)
5. Complete onboarding

### Google Sign-In ⭐ NEW
1. Go to http://localhost:3000/login
2. Click **"Continue with Google"**
3. Select your Google account
4. Choose your role: **Grihasta** or **Acharya**
5. Automatically redirects to dashboard/onboarding

**Note**: Both methods work identically. Google Sign-In is faster but still requires role selection.

For detailed testing guide, see: [GOOGLE_SIGNIN_TEST.md](GOOGLE_SIGNIN_TEST.md)

## 📝 Manual Start (If Needed)

### Backend Only
```powershell
cd backend
$env:PYTHONPATH = "$PWD"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Only
```powershell
cd savitara-web
npm run dev
```

## 🔧 Troubleshooting

### Port Already in Use
```powershell
# Check what's using port 8000
netstat -ano | Select-String ":8000"

# Stop all services
.\stop-all.ps1
```

### Backend Won't Start
- Ensure `.env` file exists in `backend/` directory
- Check MongoDB connection string in `.env`
- Verify Python dependencies: `pip install -r requirements.txt`

### Frontend Won't Start
- Install dependencies: `cd savitara-web && npm install`
- Clear cache: `npm cache clean --force`

## 💡 Tips

- Each service runs in its own window - you can see logs in real-time
- Close the windows to stop the services
- Or use `stop-all.ps1` / `stop-all.bat` to stop everything at once
- The script checks backend health automatically

## 🎯 Development Workflow

1. Start services: `.\start-all.ps1`
2. Make your changes
3. Services auto-reload on file changes
4. Stop services: `.\stop-all.ps1` or close windows

That's it! 🎉

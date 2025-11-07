# ========================================
# AGNIYA - Quick Start Commands
# ========================================

# FOR POWERSHELL USERS (Recommended):
# Run this single command from G:\agniya:

.\start.ps1

# OR run both servers separately:

# Terminal 1 - Backend:
.\envb\Scripts\Activate.ps1
python api\server_enhanced.py

# Terminal 2 - Frontend:
cd webapp
npm run dev


# FOR COMMAND PROMPT USERS:
# Double-click start.bat
# OR run from cmd:

start.bat


# ========================================
# Manual Start (if scripts don't work)
# ========================================

# Terminal 1 - Backend API:
cd G:\agniya
.\envb\Scripts\Activate.ps1
python api\server_enhanced.py
# Server runs on http://localhost:5000

# Terminal 2 - Frontend:
cd G:\agniya\webapp
npm run dev
# App runs on http://localhost:3000


# ========================================
# Quick Commands Reference
# ========================================

# Check backend health:
curl http://localhost:5000/api/health

# Open dashboard:
start http://localhost:3000/dashboard

# View API documentation:
start http://localhost:5000/api/benchmark

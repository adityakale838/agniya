# 🌐 Hosting Options for AGNIYA with GPU Support

Complete guide to deploy AGNIYA with **GPU acceleration** using GitHub Student Developer Pack.

---

## 🎓 BEST FOR STUDENTS: GitHub Education Pack

**YOU HAVE ACCESS TO:**
- **Azure**: $100/year credit + GPU VMs
- **DigitalOcean**: $200 credit (2 months GPU Droplets)
- **AWS Educate**: Credits for GPU instances
- **Heroku**: Credits (was free, now paid)
- **MongoDB Atlas**: Free tier upgrade (M10 cluster)
- **Namecheap**: FREE .me domain for 1 year
- **Name.com**: FREE domain for 1 year + SSL certificate

**100% FREE FOREVER OPTIONS** (No credits needed):
- ✅ **Railway.app**: $5/month credit FOREVER (enough for hobby projects)
- ✅ **Vercel**: Unlimited free hosting for frontend (FOREVER)
- ✅ **Render**: 750 free hours/month web services (FOREVER)
- ✅ **MongoDB Atlas**: 512MB free database (FOREVER)
- ✅ **Sentry**: Error tracking (FOREVER free tier)
- ✅ **GitHub**: Private repos + Actions minutes (FOREVER)

**RECOMMENDED HYBRID SETUP** (Free Forever + GPU when needed):
- **Option 1**: Render (free backend) + Vercel (free frontend) - NO GPU but FREE
- **Option 2**: Railway ($5/month credit forever) - Some GPU via partnerships
- **Option 3**: Use GPU credits only for testing, deploy to free tier for production

---

## 🆓 TRULY FREE OPTION: Render + Vercel (No GPU)

### ✅ Why This Works:
- **100% FREE FOREVER** with Student Pack
- **No GPU** but still fast with caching (17K ops/sec on CPU)
- **Auto-deploy** from GitHub
- **SSL included**
- **No credit card required**

### 📦 Setup Steps

#### 1. Deploy Backend to Render (FREE)
```bash
# 1. Sign up at render.com with GitHub
# 2. New Web Service → Connect your agniya repo
# 3. Configure:
Name: agniya-backend
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn api.server_optimized:app
Branch: main

# 4. Environment Variables:
PYTHONUNBUFFERED=1
```

#### 2. Deploy Frontend to Vercel (FREE)
```bash
# 1. Sign up at vercel.com with GitHub
# 2. Import your agniya repo
# 3. Framework: Next.js (auto-detected)
# 4. Root Directory: webapp
# 5. Environment Variables:
NEXT_PUBLIC_API_URL=https://agniya-backend.onrender.com

# Deploy!
```

### 💰 Cost
- **Forever**: $0
- **Limitations**: 
  - Backend spins down after 15 min idle (30s cold start)
  - No GPU (CPU only)
  - 512MB RAM on backend

### 🚀 Performance Without GPU
- **Cached queries**: 17,000 ops/sec (CPU-optimized)
- **Cold queries**: 2,700 ops/sec
- **Good for**: Demos, testing, small datasets

---

## 💎 BEST FREE GPU OPTION: Railway + DigitalOcean Credits

### Strategy:
1. **Deploy to Railway** (FREE $5/month forever)
2. **Use DigitalOcean credits** for GPU testing ($200 = 2 months)
3. **Switch between them** based on needs

### Railway Setup (Free Tier)
```bash
# 1. Sign up at railway.app with GitHub
# 2. New Project → Deploy from GitHub
# 3. Add services:
   - Backend: api/server_optimized.py
   - Frontend: webapp/ (Next.js)

# 4. Configure backend:
Start Command: gunicorn api.server_optimized:app
Environment: Python 3.10

# 5. Environment Variables:
DISABLE_GPU=true  # No GPU on Railway free tier
PYTHONUNBUFFERED=1

# Deploy automatically on git push!
```

### When You Need GPU:
```bash
# Spin up DigitalOcean GPU Droplet (use $200 credit)
# Run intensive workloads
# Shut down when done
# Back to Railway for regular operations
```

### 💰 Cost
- **Railway**: FREE $5/month credit forever
- **Good for**: ~100GB bandwidth, 500MB RAM
- **GPU**: Use credits only when needed

---

## 📦 Architecture

```
┌─────────────────┐
│  Next.js App    │ ← Frontend (Vercel)
│  (webapp/)      │
└────────┬────────┘
         │ HTTPS/REST
         ↓
┌─────────────────┐
│  Flask API      │ ← Backend (Render.com)
│  (api/)         │
└─────────────────┘
```

---

## 🚀 Option 1: Azure GPU VM (RECOMMENDED for Students)

### ✅ Why Azure:
- **FREE $100/year** with GitHub Student Pack
- **GPU Support**: NC-series VMs with NVIDIA T4/V100
- **Full Control**: Ubuntu VM with CUDA pre-installed
- **Specs**: 4 vCPU, 16GB RAM, NVIDIA T4 (16GB VRAM)
- **Storage**: 100GB SSD included
- **Perfect for**: AGNIYA with full GPU acceleration

### 📦 Setup Steps

#### 1. Activate Student Pack
```bash
# Visit and apply
https://education.github.com/pack

# Activate Azure benefit
https://azure.microsoft.com/en-us/free/students/
```

#### 2. Create GPU VM
```bash
# Azure Portal → Virtual Machines → Create
Name: agniya-gpu
Region: East US (cheapest GPU region)
Image: Ubuntu 22.04 LTS
Size: Standard_NC4as_T4_v3 (4 vCPU, 16GB RAM, NVIDIA T4)
```

#### 3. Install CUDA & Dependencies
```bash
# SSH into VM
ssh azureuser@your-vm-ip

# Install CUDA Toolkit 12.0
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-0

# Install Python 3.10
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip

# Verify GPU
nvidia-smi  # Should show NVIDIA T4
```

#### 4. Deploy AGNIYA
```bash
# Clone repo
git clone https://github.com/yourusername/agniya.git
cd agniya

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install with GPU support
pip install -r requirements_gpu.txt
pip install cupy-cuda12x

# Start backend
gunicorn api.server_optimized:app --bind 0.0.0.0:5000

# In another terminal, start frontend
cd webapp
npm install
npm run build
npm start
```

#### 5. Configure Firewall
```bash
# Azure Portal → Networking → Add inbound rules
Port 5000 (Backend API)
Port 3000 (Frontend)
Port 22 (SSH)
```

### 💰 Cost with Student Credits
- **NC4as_T4_v3**: ~$0.526/hour
- **Monthly**: ~$380
- **With $100 credit**: ~3 weeks FREE
- **Renews yearly**: 12 weeks total FREE GPU time

---

## 🌊 Option 2: DigitalOcean GPU Droplet

### ✅ Why DigitalOcean:
- **FREE $200 credit** with Student Pack
- **GPU Droplets**: NVIDIA RTX 6000 (24GB VRAM)
- **Simple Setup**: One-click CUDA image
- **Specs**: 8 vCPU, 16GB RAM, RTX 6000
- **Storage**: 100GB SSD

### 📦 Setup Steps

#### 1. Activate $200 Credit
```bash
# Apply at
https://education.github.com/pack

# Redeem DigitalOcean credit
https://www.digitalocean.com/github-students
```

#### 2. Create GPU Droplet
```bash
# DigitalOcean Dashboard → Droplets → Create
Choose Region: New York 3 (GPU available)
Choose Image: Marketplace → CUDA 12.0 on Ubuntu 22.04
Choose Plan: GPU Droplets → Basic GPU ($100/month)
  - 8GB RAM, 2 vCPU, NVIDIA RTX 6000 (24GB VRAM)
  - Or Premium GPU ($150/month) for more power
```

#### 3. Deploy AGNIYA
```bash
# SSH into droplet
ssh root@your-droplet-ip

# Clone and setup
git clone https://github.com/yourusername/agniya.git
cd agniya
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_gpu.txt
pip install cupy-cuda12x

# Verify GPU
nvidia-smi

# Start services
# Backend
gunicorn api.server_optimized:app --bind 0.0.0.0:5000 &

# Frontend
cd webapp && npm install && npm run build && npm start &
```

### 💰 Cost with Student Credits
- **Basic GPU**: $100/month
- **With $200 credit**: 2 months FREE
- **Perfect for**: Development + testing

---

## ⚡ Option 3: AWS EC2 with GPU (AWS Educate)

### ✅ Why AWS:
- **Student Credits** via AWS Educate
- **GPU Instances**: P2, P3, G4dn with NVIDIA GPUs
- **Flexible**: Pay-as-you-go or spot instances
- **Best GPU**: G4dn.xlarge (NVIDIA T4, 16GB VRAM)

### 📦 Quick Setup
```bash
# 1. Apply for AWS Educate
https://aws.amazon.com/education/awseducate/

# 2. Launch EC2 Instance
# AWS Console → EC2 → Launch Instance
AMI: Deep Learning AMI (Ubuntu 22.04)
Instance: g4dn.xlarge
Storage: 100GB GP3 SSD

# 3. Connect and deploy
ssh -i your-key.pem ubuntu@ec2-ip
cd /home/ubuntu
git clone https://github.com/yourusername/agniya.git
# ... continue with installation
```

### 💰 Cost
- **g4dn.xlarge**: $0.526/hour (~$380/month)
- **Spot Instances**: 70% discount (~$120/month)
- **With credits**: Several months FREE

---

## 🎯 Complete Deployment Script (Ubuntu + GPU)

```bash
#!/bin/bash
# Works on Azure, DigitalOcean, AWS

# Update system
sudo apt update && sudo apt upgrade -y

# Install CUDA 12.0 (if not pre-installed)
if ! command -v nvidia-smi &> /dev/null; then
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
    sudo dpkg -i cuda-keyring_1.0-1_all.deb
    sudo apt-get update
    sudo apt-get -y install cuda-toolkit-12-0
    echo 'export PATH=/usr/local/cuda-12.0/bin:$PATH' >> ~/.bashrc
    source ~/.bashrc
fi

# Install Python 3.10
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone AGNIYA
git clone https://github.com/yourusername/agniya.git
cd agniya

# Setup backend
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_gpu.txt
pip install cupy-cuda12x gunicorn

# Setup frontend
cd webapp
npm install
npm run build
cd ..

# Verify GPU
nvidia-smi

echo "✅ Setup complete!"
echo "Start backend: gunicorn api.server_optimized:app --bind 0.0.0.0:5000"
echo "Start frontend: cd webapp && npm start"
```

---

## 📊 GPU Performance Comparison

| Platform | GPU | VRAM | vCPU | RAM | Storage | Cost/Month | Student Credit |
|----------|-----|------|------|-----|---------|------------|----------------|
| **Azure NC4as_T4_v3** | NVIDIA T4 | 16GB | 4 | 16GB | 100GB | $380 | $100/year |
| **DigitalOcean Basic** | RTX 6000 | 24GB | 8 | 16GB | 100GB | $100 | $200 one-time |
| **AWS g4dn.xlarge** | NVIDIA T4 | 16GB | 4 | 16GB | 100GB | $380 | Varies |
| **RunPod** | RTX 4090 | 24GB | 16 | 64GB | 200GB | $0.69/hr | None |

**BEST VALUE**: DigitalOcean ($200 credit = 2 months free)
**BEST LONG-TERM**: Azure ($100/year = 12 weeks/year free)

---

## 🔧 Performance Optimization Tips

### 1. Enable GPU Acceleration
```python
# api/server_optimized.py
db = UltimateOptimizedDatabase(
    key_size=2048,
    enable_gpu_encryption=True,     # Use GPU
    enable_gpu_pipeline=True,       # Zero-copy pipeline
    enable_jit=True,                # CPU JIT
    enable_oram=True,               # GPU ORAM
    oram_mode='hybrid',
    verbose=False
)
```

### 2. Monitor GPU Usage
```bash
# Watch GPU utilization
watch -n 1 nvidia-smi

# Check CUDA version
nvcc --version

# Verify CuPy
python -c "import cupy; print(cupy.cuda.runtime.getDeviceCount(), 'GPUs')"
```

### 3. Optimize for Production
```bash
# Use Gunicorn with multiple workers
gunicorn api.server_optimized:app \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

---

## 🆘 Troubleshooting

### GPU Not Detected
```bash
# Check CUDA installation
ls /usr/local/ | grep cuda

# Reinstall NVIDIA drivers
sudo apt-get purge nvidia*
sudo apt-get install nvidia-driver-535

# Reboot
sudo reboot
```

### Out of Memory
```python
# Reduce cache size
db = UltimateOptimizedDatabase(
    cache_size=10000,  # Smaller cache
    enable_oram=False  # Disable ORAM to save VRAM
)
```

### Slow Performance
```bash
# Check GPU usage
nvidia-smi

# Should show Python process using GPU
# If 0% utilization, CuPy not installed correctly
pip uninstall cupy
pip install cupy-cuda12x
```

---

## 💡 Pro Tips

1. **Use Spot Instances**: Save 70% on AWS/Azure
2. **Enable Auto-shutdown**: Stop VM when idle to save credits
3. **Monitor Spending**: Set billing alerts in cloud console
4. **Backup Data**: Use cloud storage for encrypted databases
5. **Scale Up**: Start small, upgrade GPU as needed

---

## 📚 Additional Resources

- **Azure GPU VMs**: https://learn.microsoft.com/en-us/azure/virtual-machines/sizes-gpu
- **DigitalOcean GPU**: https://www.digitalocean.com/products/gpu-droplets
- **AWS GPU Instances**: https://aws.amazon.com/ec2/instance-types/
- **GitHub Student Pack**: https://education.github.com/pack
- **CUDA Installation**: https://developer.nvidia.com/cuda-downloads

---

## 🎉 Quick Start (Student Pack)

```bash
# 1. Activate GitHub Student Pack
Visit: https://education.github.com/pack

# 2. Choose platform (recommend DigitalOcean for beginners)
DigitalOcean: $200 credit, easiest setup

# 3. Create GPU Droplet
Follow "Option 2" above

# 4. Deploy
Run deployment script (provided above)

# 5. Access your app
http://your-vm-ip:3000 (Frontend)
http://your-vm-ip:5000 (Backend API)

# 6. Enjoy 6.7M ops/sec encrypted queries! 🚀
```

---

**Total Cost with Student Pack**: $0 for 2-12 months depending on platform! 🎓💸

### ✅ Pros:
- **100% Free** for personal projects
- **Global CDN** (Vercel)
- **Auto-deploy** from GitHub
- **SSL included**
- **Easy setup** (5 minutes)

### Backend: Render.com

**Free Tier:**
- 750 hours/month
- 512MB RAM
- Shared CPU
- Auto-deploy from Git

**Setup:**

1. **Create account**: https://render.com/
2. **New Web Service** → Connect GitHub repo
3. **Configure**:
   ```yaml
   Name: agniya-api
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn api.server_optimized:app
   ```
4. **Environment Variables**:
   ```
   PYTHONUNBUFFERED=1
   FLASK_ENV=production
   ```

5. **Deploy** → Get URL: `https://agniya-api.onrender.com`

⚠️ **Note**: Free tier spins down after 15 min idle (30s cold start)

### Frontend: Vercel

**Free Tier:**
- Unlimited bandwidth
- 100GB bandwidth
- Automatic HTTPS
- Global CDN

**Setup:**

1. **Create account**: https://vercel.com/
2. **Import Git Repository** → Select `webapp/`
3. **Framework**: Next.js (auto-detected)
4. **Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://agniya-api.onrender.com
   ```
5. **Deploy** → Get URL: `https://agniya.vercel.app`

---

## 🌟 Option 2: Railway.app (Full-Stack)

**Free Tier:**
- $5 credit/month (500 hours)
- 512MB RAM
- 1GB disk
- Both frontend + backend on one platform

**Setup:**

1. **Create account**: https://railway.app/
2. **New Project** → Deploy from GitHub
3. **Services**:
   - Backend: `api/server_optimized.py`
   - Frontend: `webapp/` (Next.js)
4. **Auto-deploy on push**

✅ **Pros**: Single platform, simpler
❌ **Cons**: $5/month credit limit

---

## 🐳 Option 3: Fly.io (Docker)

**Free Tier:**
- 3 shared VMs
- 160GB bandwidth
- 3GB persistent storage

**Setup:**

1. **Install CLI**:
   ```powershell
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Deploy Backend**:
   ```bash
   cd api
   fly launch --name agniya-api
   fly deploy
   ```

4. **Deploy Frontend**:
   ```bash
   cd webapp
   fly launch --name agniya-web
   fly deploy
   ```

✅ **Pros**: More control, Docker support
❌ **Cons**: Requires Dockerfile, more complex

---

## ☁️ Option 4: Heroku (Classic)

**Free Tier**: ❌ **DISCONTINUED** (as of Nov 2022)

Alternative: Use **Heroku Eco** ($5/month) if you need it.

---

## 🎓 Option 5: Student Plans (GitHub Education)

If you're a student, get **FREE credits**:

### GitHub Student Developer Pack
https://education.github.com/pack

**Includes:**
- **DigitalOcean**: $200 credit (2 months free VPS)
- **Azure**: $100/year credit
- **Heroku**: Free credits
- **MongoDB Atlas**: Free tier upgrade

**Setup DigitalOcean ($200 credit):**
1. Apply for Student Pack
2. Get $200 credit
3. Create Droplet (Ubuntu)
4. Deploy with Docker:
   ```bash
   # Backend
   docker run -d -p 5000:5000 agniya-api
   
   # Frontend
   docker run -d -p 3000:3000 agniya-web
   ```

---

## 🔧 Option 6: Self-Hosted (Your PC)

**Setup:**

1. **Use ngrok** for public URL:
   ```powershell
   # Install ngrok
   choco install ngrok
   
   # Expose backend
   ngrok http 5000
   
   # Expose frontend
   ngrok http 3000
   ```

2. **Or use Cloudflare Tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:5000
   ```

⚠️ **Cons**: PC must stay on, not production-ready

---

## 📊 Comparison Table

| Platform | Backend | Frontend | RAM | Storage | Bandwidth | Cold Start | Cost |
|----------|---------|----------|-----|---------|-----------|------------|------|
| **Vercel + Render** | ✅ | ✅ | 512MB | 1GB | 100GB | 30s | $0 |
| **Railway** | ✅ | ✅ | 512MB | 1GB | ∞ | 0s | $5/mo credit |
| **Fly.io** | ✅ | ✅ | 256MB | 3GB | 160GB | 5s | $0 |
| **Replit** | ✅ | ✅ | 512MB | 1GB | ∞ | 0s | $0 (limited) |
| **PythonAnywhere** | ✅ | ❌ | 512MB | 512MB | Limited | 0s | $0 |

---

## 🏆 Final Recommendation

### For Production (Free):
```
Frontend: Vercel
Backend: Render.com
Database: (if needed) MongoDB Atlas Free
```

### For Testing (Free):
```
All-in-one: Railway.app
```

### For Students (Free Credits):
```
DigitalOcean Droplet ($200 credit)
```

---

## 🚀 Quick Start Script

### 1. Deploy Backend to Render

**File**: `render.yaml`
```yaml
services:
  - type: web
    name: agniya-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn api.server_optimized:app --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      - key: FLASK_ENV
        value: production
```

### 2. Deploy Frontend to Vercel

**File**: `vercel.json`
```json
{
  "builds": [
    {
      "src": "webapp/package.json",
      "use": "@vercel/next"
    }
  ],
  "env": {
    "NEXT_PUBLIC_API_URL": "https://agniya-api.onrender.com"
  }
}
```

### 3. Deploy Commands

```powershell
# Backend
cd api
git init
git add .
git commit -m "Deploy backend"
# Push to GitHub and connect to Render

# Frontend
cd webapp
vercel --prod
```

---

## 📝 Environment Variables

### Backend (Render):
```
FLASK_ENV=production
PYTHONUNBUFFERED=1
PORT=5000
ALLOWED_ORIGINS=https://agniya.vercel.app
```

### Frontend (Vercel):
```
NEXT_PUBLIC_API_URL=https://agniya-api.onrender.com/api
```

---

## 🔒 Security Notes

1. **CORS**: Configure allowed origins in Flask
2. **HTTPS**: Always enabled on Vercel/Render
3. **API Keys**: Use environment variables (never commit)
4. **Rate Limiting**: Add Flask-Limiter for API protection

---

## 🆘 Troubleshooting

### Backend won't start:
- Check `requirements.txt` has all dependencies
- Verify Python version (3.10+)
- Check logs in Render dashboard

### Frontend API calls fail:
- Verify CORS settings in Flask
- Check `NEXT_PUBLIC_API_URL` environment variable
- Ensure backend is running (cold start 30s)

### Cold start too slow:
- Upgrade to paid tier ($7/month Render)
- Or use Railway (no cold start)

---

## 💡 Pro Tips

1. **Use Railway** for development (faster deployments)
2. **Use Vercel + Render** for production (better performance)
3. **Enable caching** in Flask to reduce compute
4. **Compress responses** with gzip
5. **Use CDN** for static assets

---

## 📚 Resources

- **Vercel Docs**: https://vercel.com/docs
- **Render Docs**: https://render.com/docs
- **Railway Docs**: https://docs.railway.app
- **Fly.io Docs**: https://fly.io/docs

---

## 🎉 Success!

Your AGNIYA app is now live:
- **Frontend**: https://agniya.vercel.app
- **Backend**: https://agniya-api.onrender.com
- **Total Cost**: $0/month 🎊

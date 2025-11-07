# AGNIYA Web Application

Professional web interface for homomorphic encryption with 143x speedup.

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌──────────────────┐
│  Next.js App    │ ───> │   Flask API     │ ───> │  Python Backend  │
│  (Port 3000)    │      │   (Port 5000)   │      │  (Encryption)    │
│                 │ <─── │                 │ <─── │                  │
│  - React UI     │      │  - File Upload  │      │  - Paillier-2048 │
│  - Shadcn/ui    │      │  - Encryption   │      │  - AES-256-GCM   │
│  - Tailwind     │      │  - Queries      │      │  - OPE Dual-Mode │
│  - Framer Motion│      │  - Benchmarks   │      │  - GPU Accel     │
└─────────────────┘      └─────────────────┘      └──────────────────┘
```

## Quick Start

### 1. Start Backend API

```powershell
# Navigate to API directory
cd api

# Install dependencies (first time only)
pip install -r requirements.txt

# Start Flask server
python server.py
```

Server will run on `http://localhost:5000`

### 2. Start Frontend

```powershell
# Navigate to webapp directory
cd webapp

# Install dependencies (first time only)
npm install

# Start Next.js dev server
npm run dev
```

App will run on `http://localhost:3000`

### 3. Open Application

Navigate to `http://localhost:3000` in your browser.

## Features

### Landing Page (`/`)
- Hero section with 143x speedup highlight
- Feature cards showing workflow
- Real-time stats display
- Smooth Framer Motion animations

### Dashboard (`/dashboard`)
- **File Upload**: Drag-and-drop CSV interface
- **Schema Designer**: Configure encryption per field
  - Plaintext (identifiers)
  - AES-256 (fast symmetric)
  - Paillier-2048 (homomorphic SUM)
  - OPE+Paillier (range + aggregation)
- **Results Visualization**:
  - Performance charts (143x speedup)
  - Operation latency graphs
  - Benchmark comparison table

## API Endpoints

See full API documentation in main README.

## Tech Stack

**Frontend:** Next.js 16 + TypeScript + Tailwind CSS v4 + Shadcn/ui  
**Backend:** Flask 3.1 + Pandas + NumPy  
**Design:** Linear-inspired, minimal, monochrome

## License

See LICENSE file.

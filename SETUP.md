# HackNYU Monorepo Setup Guide

## Prerequisites

- Python 3.11+ with pip
- Node.js 18+ (for Bun)
- Bun package manager

## Initial Setup

### 1. Install Frontend Dependencies

```bash
# From root directory
bun install
```

### 2. Setup Python Virtual Environment

```bash
# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
.\venv\Scripts\activate   # On Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment example
cp apps/backend/.env.example apps/backend/.env

# Edit the .env file with your configuration
# Or use the root .env file (currently in use)
```

## Development

### Option 1: Run Everything (Recommended)

```bash
# Runs both frontend and backend
bun run dev
```

### Option 2: Run Individually

**Backend only:**
```bash
# Method 1: Using bun scripts
bun run dev:backend

# Method 2: Using shell script
./apps/backend/dev.sh

# Method 3: Direct python
cd apps/backend
python3 app.py --local
```

**Frontend only:**
```bash
bun run dev:web
```

### Option 3: Old Way (Still Supported)

```bash
# Activate venv first
source venv/bin/activate

# Run from root
python3 app.py --local
```

## Testing

```bash
# Run all tests
bun run test

# Backend tests only
bun run test:backend

# With coverage
cd apps/backend
bun run test:coverage
```

## Building for Production

```bash
# Build everything
bun run build

# Build frontend only
bun run build:web
```

## Monorepo Structure

```
hacknyu25/
├── apps/
│   ├── backend/          # Flask API (wrapper)
│   │   ├── app.py        # Entry point
│   │   ├── package.json  # Backend scripts
│   │   └── .env          # Backend env vars
│   └── web/              # React frontend
│       ├── src/          # React source code
│       └── package.json
├── packages/             # Shared code (future)
│   └── shared/           # To be created
├── src/                  # Current Flask code
│   ├── __init__.py
│   ├── database/
│   └── ...
├── package.json          # Root workspace config
└── turbo.json           # Turborepo config
```

## Troubleshooting

### "Module not found" errors

Make sure your virtual environment is activated:
```bash
source venv/bin/activate
```

### Port already in use

Backend runs on port 5001 by default. Kill existing processes:
```bash
lsof -ti:5001 | xargs kill -9
```

### Bun command not found

Install Bun:
```bash
curl -fsSL https://bun.sh/install | bash
```

## Next Steps

See [MIGRATION.md](./MIGRATION.md) for the gradual migration plan.

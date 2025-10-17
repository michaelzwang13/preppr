# Migration Guide: Monorepo Structure

This document tracks the migration from the original Flask app structure to a monorepo structure.

## Migration Status: ✅ COMPLETED

The Flask backend has been successfully migrated from `/src` to `/apps/backend/src`.

## Current Structure

```
hacknyu25/
├── apps/
│   ├── backend/              # Flask backend (MIGRATED)
│   │   ├── src/              # All Flask application code
│   │   │   ├── __init__.py
│   │   │   ├── auth_utils.py
│   │   │   ├── backend/      # API routes and views
│   │   │   ├── config.py
│   │   │   ├── database/     # SQL scripts and migrations
│   │   │   ├── database.py
│   │   │   ├── health.py
│   │   │   ├── services/     # Business logic
│   │   │   ├── static/       # CSS, JS, images
│   │   │   ├── templates/    # Jinja2 templates
│   │   │   └── ...
│   │   ├── app.py            # Entry point
│   │   ├── requirements.txt  # Python dependencies
│   │   ├── Dockerfile        # Docker config
│   │   ├── dev.sh            # Development script
│   │   └── package.json      # Turborepo integration
│   └── web/                  # React frontend
│       ├── src/
│       └── package.json
├── src/                      # OLD: Keep for reference, can be removed
├── app.py                    # OLD: Keep for reference, can be removed
├── requirements.txt          # OLD: Keep for reference, can be removed
├── Dockerfile                # OLD: Keep for reference, can be removed
└── package.json              # Root monorepo config
```

## How to Run

### Development Mode

**Backend only:**
```bash
cd apps/backend
./dev.sh
# or
bun run dev
```

**Both frontend and backend:**
```bash
# From root
bun run dev
# or
./dev-all.sh
```

### Docker Build

**From apps/backend:**
```bash
cd apps/backend
docker build -t preppr-backend .
docker run -p 8080:8080 preppr-backend
```

## What Changed

1. ✅ Moved `/src` → `/apps/backend/src`
2. ✅ Updated `apps/backend/app.py` to import directly from `src`
3. ✅ Copied and updated `requirements.txt` in `apps/backend`
4. ✅ Updated `Dockerfile` to work with new structure
5. ✅ Updated `package.json` test scripts
6. ✅ Database files are in `apps/backend/src/database`

## Old Files (Safe to Remove)

The following root-level files are now duplicated in `apps/backend` and can be removed:

- `/src/` directory
- `/app.py`
- `/requirements.txt` (backend dependencies now in apps/backend/requirements.txt)
- `/Dockerfile` (backend Docker config now in apps/backend/Dockerfile)

**Before removing**, ensure:
1. Install Python dependencies: `cd apps/backend && pip install -r requirements.txt`
2. Test the backend runs: `cd apps/backend && python3 app.py --local`
3. Verify Docker build works: `cd apps/backend && docker build -t test .`

## Next Steps

1. Set up Python virtual environment in `apps/backend` or at root
2. Install dependencies: `pip install -r apps/backend/requirements.txt`
3. Update CI/CD to build from `apps/backend`
4. Remove old root-level files after verification

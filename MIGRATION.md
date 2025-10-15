# Migration Guide: Monorepo Structure

This document explains the gradual migration strategy from the current Flask app to a monorepo structure.

## Current State

- **Old Structure**: Flask app in `/src`, run via `app.py` at root
- **New Structure**: Monorepo with `/apps/backend` and `/apps/web`

## Migration Strategy

### Phase 1: Dual Structure (Current Phase)

Both structures work simultaneously:

**Old way (still works):**
```bash
python app.py --local
```

**New way (recommended):**
```bash
# From root
bun run dev

# Or just backend
cd apps/backend
bun run dev
```

### Phase 2: Gradual Route Migration (Future)

When ready, you can:
1. Start moving routes from `/src` to `/apps/backend/src`
2. Update imports gradually
3. Test both old and new routes work
4. Eventually remove `/src` when fully migrated

### Phase 3: Complete Migration (Future)

Final structure:
```
apps/
  backend/
    src/           # All Flask code
    tests/         # Backend tests
    app.py
    package.json
  web/
    src/           # React code
    package.json
packages/
  shared/          # Shared types/utilities
```

## Current Directory Structure

```
hacknyu25/
├── apps/
│   ├── backend/          # NEW: Backend app wrapper
│   │   ├── app.py        # Entry point (imports from /src)
│   │   ├── package.json  # Turborepo integration
│   │   └── README.md
│   └── web/              # Frontend app
│       ├── src/
│       └── package.json
├── src/                  # CURRENT: Flask application code
│   ├── __init__.py
│   ├── database/
│   ├── services/
│   └── ...
├── app.py                # OLD: Original entry point (still works)
└── package.json          # Root monorepo config
```

## Benefits of This Approach

1. **No Breaking Changes**: Old scripts and deployment continue to work
2. **Gradual Migration**: Move code at your own pace
3. **Testing**: Both structures can be tested in parallel
4. **Rollback**: Easy to revert if needed

## Next Steps

1. Test that both entry points work
2. Update CI/CD to use new structure (while keeping old as fallback)
3. Start moving utility functions to `/packages/shared`
4. Gradually migrate routes to new structure

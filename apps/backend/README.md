# Backend API

Flask backend for HackNYU application.

## Development

```bash
# From the root directory
bun run dev

# Or run only the backend
cd apps/backend
bun run dev
```

## Testing

```bash
# From the root directory
cd apps/backend
bun run test
```

## Structure

The actual Flask application code lives in `/src` at the root level. This allows for gradual migration while maintaining backward compatibility with existing deployment scripts.

## Environment Variables

Create a `.env` file in the root directory with necessary environment variables.

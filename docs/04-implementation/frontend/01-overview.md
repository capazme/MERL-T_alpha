# Frontend Overview

**Status**: Initial Draft
**Location**: `frontend/rlcf-web`

## Technology Stack
- **Framework**: Vite + React
- **Language**: TypeScript
- **State Management**: Zustand, React Query
- **Styling**: Tailwind CSS, Shadcn/UI

## Architecture
The frontend is a Single Page Application (SPA) that interacts with the backend via REST APIs.

### Key Directories
- `src/components`: Reusable UI components.
- `src/pages`: Route components.
- `src/services`: API clients.
- `src/hooks`: Custom React hooks.

## Setup
```bash
cd frontend/rlcf-web
npm install
npm run dev
```

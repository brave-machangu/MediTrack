# MediTrack frontend

React + TypeScript web app for MediTrack. The approved design brief is [DESIGN.md](DESIGN.md); repository rules are in [AGENTS.md](../AGENTS.md) and [prompts/frontend-agent.md](../prompts/frontend-agent.md).

Needs Node 22.22.2 or later (React Router 8 and jsdom require it).

## Commands

| Command | What it does |
|---|---|
| `npm install` | Install dependencies |
| `npm run dev` | Start the app; `/api`, `/healthz` and `/readyz` are proxied to the backend at `http://localhost:8000` |
| `npm run dev:mock` | Start the app against synthetic mock data (MSW), with no backend |
| `npm run gen:api` | Regenerate `src/api/schema.d.ts` from `../api/openapi.yaml`. Never edit that file by hand. |
| `npm run lint` | ESLint (type-aware) |
| `npm run typecheck` | TypeScript, strict |
| `npm run test` | Vitest once, under `TZ=Asia/Tokyo` (AC-35) |
| `npm run build` | Production build into `dist/` (mocks are not included) |
| `npm run screenshots` | Playwright screenshots at 375 px and 1280 px into `screenshots/out/`, plus a 320 px reflow check. Run `npx playwright install chromium` once first. |

## Where things live

- `src/copy.ts`: every user-facing string. `src/copy.test.ts` scans it for unsafe phrases (AC-38); changes need Lead review.
- `src/api/`: generated types, the typed `client.ts` (problem+json, network errors, timeouts) and query hooks.
- `src/components/`, `src/pages/`: UI. Styles are CSS Modules using the tokens in `src/styles/tokens.css`.
- `src/mocks/`: MSW handlers and synthetic data, shared by tests and `dev:mock`.

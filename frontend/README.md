# Frontend – GreenCity AI

React + TypeScript SPA for interactive mapping, priority rankings, and
explainable green-deficiency reports.

## Stack

- React 19
- TypeScript
- Vite
- Leaflet / react-leaflet

## Layout

```
frontend/
├── src/
│   ├── api/            # Backend HTTP clients
│   ├── components/     # Map workspace, rankings, explainability
│   ├── lib/            # Priority colors helpers
│   ├── styles/         # Global design tokens & layout
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json
└── vite.config.ts
```

## Running

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Design notes

Presentation-only layer. Domain scoring and agent logic stay on the backend.

UI:

- Auth gate (register / login)
- Planning workspace: city AOI, then neighborhoods
- Analyze & rank (LangGraph `/run` + cohort ranking)
- Map choropleth by priority band and analysis overlays
- Rankings, explainable report, and optional agent narratives

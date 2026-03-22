# React Frontend

A chat application with an MCP explorer panel, built with React, Tailwind CSS, and shadcn/ui-style components.

## Layout

```
┌────────────────────────────────────────────────┐
│  Header (status bar + connection indicator)      │
├──────────────────────┬─────────────────────────┤
│                      │    MCP Explorer          │
│     Chat Panel       │    ┌─────────────────┐  │
│                      │    │ Tools | Res | Pr │  │
│  User ←→ Claude      │    │                 │  │
│  (auto tool use)     │    │ Browse & test   │  │
│                      │    │ all 3 primitives│  │
│                      │    └─────────────────┘  │
│                      │    ┌─────────────────┐  │
│  [input box] [send]  │    │ Result panel    │  │
├──────────────────────┴────┴─────────────────┴──┤
│  Footer                                         │
└─────────────────────────────────────────────────┘
```

## Components

- **`App.jsx`** — Main layout, health check, header/footer
- **`ChatPanel.jsx`** — Chat interface with message history, tool-use badges
- **`ExplorerPanel.jsx`** — Tabbed explorer for tools, resources, and prompts
- **`ui/`** — shadcn/ui-style components (Button, Card, Badge, Tabs, ScrollArea)

## Running

```bash
# From project root
make frontend

# Or directly
cd frontend && npm run dev
```

Opens at: http://localhost:5173

The Vite dev server proxies `/api/*` requests to the FastAPI backend at `localhost:8000`.

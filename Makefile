# =============================================================================
# MCP Client Demo — Top-level Makefile
# =============================================================================
# Usage:
#   make install     — Install all dependencies (Python + Node)
#   make server      — Run just the MCP server (stdio, for testing)
#   make backend     — Run the FastAPI backend (starts MCP server internally)
#   make frontend    — Run the React dev server
#   make dev         — Run backend + frontend together
#   make clean       — Remove generated files
# =============================================================================

.PHONY: install install-python install-frontend server backend frontend dev clean help

# Default target
help:
	@echo ""
	@echo "  MCP Client Demo"
	@echo "  ==============="
	@echo ""
	@echo "  make install      Install all dependencies"
	@echo "  make backend      Start FastAPI backend (port 8000)"
	@echo "  make frontend     Start React dev server (port 5173)"
	@echo "  make dev          Start both backend and frontend"
	@echo "  make server       Test MCP server standalone (stdio)"
	@echo "  make clean        Remove generated files"
	@echo ""

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

install: install-python install-frontend
	@echo "All dependencies installed!"

install-python:
	pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

server:
	python -m mcp_server.server

backend:
	uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

# Run both backend and frontend (requires two terminals or use this with &)
dev:
	@echo "Starting backend and frontend..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo ""
	@echo "Run in separate terminals:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make frontend"

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/node_modules frontend/dist
	@echo "Cleaned!"

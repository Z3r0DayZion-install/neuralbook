#!/usr/bin/env python3
"""
Example 2: HTTP API Server
===========================
Demonstrates the NeuralBook HTTP API for project management.

This starts a simple HTTP server that handles:
- GET /v1/projects — List all projects
- POST /v1/projects — Create a new project
- GET /v1/projects/:id — Retrieve a project
- PUT /v1/projects/:id — Update a project
- POST /v1/projects/:id/build — Trigger a build

Requirements:
  pip install neuralbook

Usage:
  python 02_api_server.py [--port 8000]

Then in another terminal:
  curl http://localhost:8000/health
  curl -X POST http://localhost:8000/v1/projects \\
    -H "Content-Type: application/json" \\
    -d '{"title": "My Book", "slug": "my-book"}'
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from neuralbook.api_router import route_request


class NeuralBookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for NeuralBook API."""

    def do_GET(self):
        """Handle GET requests."""
        status, response = route_request(
            "GET", self.path, b"", store_path=Path("./api-server-store.json")
        )
        self._send_response(status, response)

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        status, response = route_request(
            "POST", self.path, body, store_path=Path("./api-server-store.json")
        )
        self._send_response(status, response)

    def do_PUT(self):
        """Handle PUT requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        status, response = route_request(
            "PUT", self.path, body, store_path=Path("./api-server-store.json")
        )
        self._send_response(status, response)

    def _send_response(self, status: int, response: dict):
        """Send JSON response."""
        body = json.dumps(response).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def main():
    """Start the HTTP API server."""
    import argparse

    parser = argparse.ArgumentParser(description="NeuralBook HTTP API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")

    args = parser.parse_args()

    server_address = (args.host, args.port)
    server = HTTPServer(server_address, NeuralBookHandler)

    print("=" * 60)
    print("NeuralBook HTTP API Server")
    print("=" * 60)
    print(f"\n📡 Server running at http://{args.host}:{args.port}")
    print("\nEndpoints:")
    print("  GET    /health                 — Health check")
    print("  GET    /v1/projects            — List all projects")
    print("  POST   /v1/projects            — Create new project")
    print("  GET    /v1/projects/{id}       — Get project details")
    print("  PUT    /v1/projects/{id}       — Update project")
    print("  POST   /v1/projects/{id}/build — Trigger build")
    print("\nExample requests:")
    print("  curl http://localhost:8000/health")
    print("  curl http://localhost:8000/v1/projects")
    print(
        """  curl -X POST http://localhost:8000/v1/projects \\
    -H "Content-Type: application/json" \\
    -d '{"title": "My Book", "slug": "my-book"}'"""
    )
    print("\nPress Ctrl+C to stop.")
    print("=" * 60 + "\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())

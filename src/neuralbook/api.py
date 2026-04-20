"""
NeuralBook HTTP API (optional server component).
"""

from typing import Tuple, Dict, Any


def route_request(
    method: str,
    path: str,
    body: bytes,
) -> Tuple[int, Dict[str, Any]]:
    """
    Route HTTP request to appropriate handler.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: Request path
        body: Request body
    
    Returns:
        (status_code, response_dict)
    """
    # Route mapping
    routes = {
        ("GET", "/health"): handle_health,
        ("GET", "/"): handle_root,
        ("POST", "/projects"): handle_create_project,
        ("GET", "/projects"): handle_list_projects,
        ("GET", "/projects/{id}/build"): handle_get_build,
        ("POST", "/projects/{id}/build"): handle_trigger_build,
    }
    
    # Find matching route
    for (route_method, route_path), handler in routes.items():
        if method == route_method and path == route_path:
            return handler(body)
    
    return 404, {"error": "not_found"}


def handle_health(body: bytes) -> Tuple[int, Dict]:
    """Health check endpoint."""
    return 200, {"status": "ok"}


def handle_root(body: bytes) -> Tuple[int, Dict]:
    """Root endpoint."""
    return 200, {"service": "neuralbook", "version": "1.0.0"}


def handle_create_project(body: bytes) -> Tuple[int, Dict]:
    """Create new project."""
    # TODO: Parse body, create project
    return 201, {"id": "project-123", "status": "created"}


def handle_list_projects(body: bytes) -> Tuple[int, Dict]:
    """List projects."""
    return 200, {"projects": []}


def handle_get_build(body: bytes) -> Tuple[int, Dict]:
    """Get build status."""
    return 200, {"status": "success"}


def handle_trigger_build(body: bytes) -> Tuple[int, Dict]:
    """Trigger a build."""
    return 202, {"id": "build-456", "status": "building"}

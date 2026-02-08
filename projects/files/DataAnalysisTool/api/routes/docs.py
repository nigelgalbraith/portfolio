from flask import Blueprint, jsonify

bp = Blueprint("docs", __name__)


def build_openapi_spec():
    """Return an OpenAPI 3.0 spec for the current API surface."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "DataAnalysisTool API",
            "version": "1.0.0",
        },
        "servers": [{"url": "/"}],
        "paths": {
            "/api/pages": {"get": {"summary": "List app pages", "responses": {"200": {"description": "OK"}}}},
            "/api/databases": {
                "get": {"summary": "List databases", "responses": {"200": {"description": "OK"}}},
                "post": {
                    "summary": "Create database",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "properties": {"db": {"type": "string"}}, "required": ["db"]}
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/api/databases/{db}/schema": {
                "get": {
                    "summary": "Database schema (tables + columns)",
                    "parameters": [{"name": "db", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/databases/{db}/tables/{table}/schema": {
                "get": {
                    "summary": "Table schema (rich metadata)",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/databases/{db}/tables/{table}/records/query": {
                "post": {
                    "summary": "Query records",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                                        "offset": {"type": "integer", "minimum": 0},
                                        "filters": {"type": "object"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/databases/{db}/tables/{table}/records/get": {
                "post": {
                    "summary": "Get record by pk",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"pk": {"type": "object"}}, "required": ["pk"]}}},
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/databases/{db}/tables/{table}/records": {
                "post": {
                    "summary": "Create record",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"values": {"type": "object"}}, "required": ["values"]}}},
                    },
                    "responses": {"200": {"description": "OK"}},
                },
                "patch": {
                    "summary": "Update record",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"pk": {"type": "object"}, "changes": {"type": "object"}},
                                    "required": ["pk", "changes"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/api/databases/{db}/tables/{table}/records/delete": {
                "post": {
                    "summary": "Delete record",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"pk": {"type": "object"}}, "required": ["pk"]}}},
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/databases/{db}/tables/{table}/distinct/{column}": {
                "get": {
                    "summary": "Distinct values for a column",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "column", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 500}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/databases/{db}/tables/{table}/lookup": {
                "get": {
                    "summary": "Lookup rows for dropdowns",
                    "parameters": [
                        {"name": "db", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "table", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "value_col", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "label_col", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "search", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 500}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
    }


@bp.get("/api/openapi.json")
def openapi_json():
    """Return the OpenAPI spec as JSON."""
    return jsonify(build_openapi_spec())


@bp.get("/api/docs")
def openapi_docs():
    """Return a Swagger UI HTML page."""
    html = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <title>DataAnalysisTool API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger"></div>
    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: '/api/openapi.json',
        dom_id: '#swagger',
      });
    </script>
  </body>
</html>"""
    return html

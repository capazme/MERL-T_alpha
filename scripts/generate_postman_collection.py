#!/usr/bin/env python3
"""
Generate Postman Collection from OpenAPI Schema

This script exports the MERL-T API OpenAPI schema as a Postman Collection v2.1
for easy API testing and exploration.

Usage:
    python scripts/generate_postman_collection.py

Output:
    - postman/MERL-T_API.postman_collection.json
    - postman/MERL-T_API.postman_environment.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


def load_openapi_schema() -> Dict[str, Any]:
    """
    Load OpenAPI schema from the FastAPI app.

    Note: This requires importing the app, which needs FastAPI installed.
    If FastAPI is not available, we'll use a mock schema.
    """
    try:
        from orchestration.api.main import app
        from orchestration.api.openapi_config import get_custom_openapi_schema
        from orchestration.api.openapi_tags import get_tags_metadata, get_servers_config

        # Generate custom OpenAPI schema
        openapi_schema = get_custom_openapi_schema(
            app=app,
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=get_tags_metadata(),
            servers=get_servers_config()
        )

        print("✅ OpenAPI schema loaded from FastAPI app")
        return openapi_schema

    except ImportError as e:
        print(f"⚠️  Cannot import FastAPI app: {e}")
        print("⚠️  Using mock OpenAPI schema for demonstration")
        return get_mock_openapi_schema()


def get_mock_openapi_schema() -> Dict[str, Any]:
    """
    Provide a mock OpenAPI schema if FastAPI is not available.
    This is a simplified version for testing the script.
    """
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "MERL-T API",
            "version": "0.2.0",
            "description": "AI-powered legal research and analysis system"
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Development server (local)"},
            {"url": "https://api.merl-t.alis.ai", "description": "Production environment"}
        ],
        "paths": {
            "/query/execute": {
                "post": {
                    "summary": "Execute Legal Query",
                    "tags": ["Query Execution"],
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "context": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Success"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        }
    }


def convert_to_postman_collection(openapi_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OpenAPI schema to Postman Collection v2.1 format.

    Args:
        openapi_schema: OpenAPI 3.x schema

    Returns:
        Postman Collection v2.1 JSON
    """
    info = openapi_schema.get("info", {})
    servers = openapi_schema.get("servers", [])
    paths = openapi_schema.get("paths", {})

    # Base collection structure
    collection = {
        "info": {
            "name": info.get("title", "API"),
            "description": info.get("description", ""),
            "version": info.get("version", "1.0.0"),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": "merl-t-api-collection",
        },
        "auth": {
            "type": "apikey",
            "apikey": [
                {"key": "key", "value": "X-API-Key", "type": "string"},
                {"key": "value", "value": "{{api_key}}", "type": "string"},
                {"key": "in", "value": "header", "type": "string"}
            ]
        },
        "item": [],
        "variable": [
            {
                "key": "base_url",
                "value": servers[0]["url"] if servers else "http://localhost:8000",
                "type": "string"
            }
        ]
    }

    # Group endpoints by tag
    tags_map: Dict[str, List[Dict]] = {}

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue

            tags = operation.get("tags", ["Other"])
            tag = tags[0] if tags else "Other"

            # Create Postman request
            request = {
                "name": operation.get("summary", f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}" + path,
                        "host": ["{{base_url}}"],
                        "path": path.strip("/").split("/")
                    },
                    "description": operation.get("description", "")
                }
            }

            # Add request body if present
            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                app_json = content.get("application/json", {})
                examples = app_json.get("examples", {})

                if examples:
                    # Use first example as body
                    first_example = list(examples.values())[0]
                    request["request"]["body"] = {
                        "mode": "raw",
                        "raw": json.dumps(first_example.get("value", {}), indent=2),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }

            # Add to tag group
            if tag not in tags_map:
                tags_map[tag] = []
            tags_map[tag].append(request)

    # Create folder structure by tag
    for tag, requests in tags_map.items():
        folder = {
            "name": tag,
            "item": requests
        }
        collection["item"].append(folder)

    return collection


def create_postman_environment(servers: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Create Postman environment file with different server configurations.

    Args:
        servers: List of server configurations from OpenAPI

    Returns:
        Postman Environment JSON
    """
    # Default to first server or localhost
    default_url = servers[0]["url"] if servers else "http://localhost:8000"

    environment = {
        "id": "merl-t-api-environment",
        "name": "MERL-T API Environment",
        "values": [
            {
                "key": "base_url",
                "value": default_url,
                "type": "default",
                "enabled": True
            },
            {
                "key": "api_key",
                "value": "your-api-key-here",
                "type": "secret",
                "enabled": True
            },
            {
                "key": "dev_url",
                "value": "http://localhost:8000",
                "type": "default",
                "enabled": True
            },
            {
                "key": "staging_url",
                "value": "https://staging-api.merl-t.alis.ai",
                "type": "default",
                "enabled": False
            },
            {
                "key": "prod_url",
                "value": "https://api.merl-t.alis.ai",
                "type": "default",
                "enabled": False
            }
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_at": datetime.utcnow().isoformat() + "Z",
        "_postman_exported_using": "MERL-T OpenAPI Generator"
    }

    return environment


def main():
    """Main function to generate Postman collection and environment."""
    print("=" * 80)
    print("MERL-T API - Postman Collection Generator")
    print("=" * 80)

    # Load OpenAPI schema
    print("\n1. Loading OpenAPI schema...")
    openapi_schema = load_openapi_schema()

    # Convert to Postman collection
    print("\n2. Converting to Postman Collection v2.1...")
    collection = convert_to_postman_collection(openapi_schema)
    print(f"✅ Collection created with {len(collection['item'])} folders")

    # Count total requests
    total_requests = sum(len(folder['item']) for folder in collection['item'])
    print(f"✅ Total requests: {total_requests}")

    # Create environment
    print("\n3. Creating Postman Environment...")
    servers = openapi_schema.get("servers", [])
    environment = create_postman_environment(servers)
    print(f"✅ Environment created with {len(environment['values'])} variables")

    # Create output directory
    output_dir = Path(__file__).parent.parent / "postman"
    output_dir.mkdir(exist_ok=True)

    # Save collection
    collection_path = output_dir / "MERL-T_API.postman_collection.json"
    with open(collection_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Collection saved to: {collection_path}")

    # Save environment
    env_path = output_dir / "MERL-T_API.postman_environment.json"
    with open(env_path, "w", encoding="utf-8") as f:
        json.dump(environment, f, indent=2, ensure_ascii=False)
    print(f"✅ Environment saved to: {env_path}")

    # Print usage instructions
    print("\n" + "=" * 80)
    print("IMPORT INSTRUCTIONS")
    print("=" * 80)
    print("\n1. Open Postman")
    print("2. Click 'Import' button")
    print("3. Select the following files:")
    print(f"   - {collection_path}")
    print(f"   - {env_path}")
    print("\n4. Select the 'MERL-T API Environment' in the top-right dropdown")
    print("5. Edit the environment and set your API key in the 'api_key' variable")
    print("\n6. Start testing the API! 🚀")
    print("\nNote: The collection uses the following variables:")
    print("  - {{base_url}} - API base URL (default: http://localhost:8000)")
    print("  - {{api_key}} - Your API key for authentication")
    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())

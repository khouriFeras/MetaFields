#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch Metafield Definition Structure

This script fetches a metafield definition from Shopify and displays
its complete structure, including validations, options, and allowed values.
"""
import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Shopify API Configuration
SHOPIFY_STORE_DOMAIN = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_ADMIN_ACCESS_TOKEN = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-07").strip()


def graphql_request(query: str, variables: dict = None) -> dict:
    """Make a GraphQL request to Shopify."""
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    result = response.json()
    
    if "errors" in result:
        error_msg = json.dumps(result['errors'], indent=2, ensure_ascii=False)
        raise Exception(f"GraphQL Error: {error_msg}")
    
    return result


def get_metafield_definition_full(namespace: str, key: str) -> dict:
    """Get complete metafield definition with all fields."""
    query = """
    query GetMetafieldDefinition($namespace: String!, $key: String!, $ownerType: MetafieldOwnerType!) {
      metafieldDefinitions(first: 1, ownerType: $ownerType, namespace: $namespace, key: $key) {
        edges {
          node {
            id
            name
            namespace
            key
            description
            type {
              name
            }
            validations {
              name
              value
            }
            pinnedPosition
            access {
              admin
              storefront
            }
            ownerType
          }
        }
      }
    }
    """
    
    try:
        result = graphql_request(query, {
            "namespace": namespace,
            "key": key,
            "ownerType": "PRODUCT"
        })
        
        definitions = result.get("data", {}).get("metafieldDefinitions", {}).get("edges", [])
        if definitions:
            return definitions[0]["node"]
        return None
    except Exception as e:
        print(f"Error fetching definition: {str(e)}")
        return None


def get_all_metafield_definitions(namespace: str = None) -> list:
    """Get all metafield definitions, optionally filtered by namespace."""
    query = """
    query GetMetafieldDefinitions($namespace: String, $first: Int!, $after: String) {
      metafieldDefinitions(first: $first, after: $after, ownerType: PRODUCT, namespace: $namespace) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            name
            namespace
            key
            type {
              name
            }
            validations {
              name
              value
            }
          }
        }
      }
    }
    """
    
    all_definitions = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        variables = {
            "first": 50,
            "after": cursor
        }
        if namespace:
            variables["namespace"] = namespace
        
        try:
            result = graphql_request(query, variables)
            data = result.get("data", {}).get("metafieldDefinitions", {})
            
            page_info = data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
            
            edges = data.get("edges", [])
            for edge in edges:
                all_definitions.append(edge["node"])
        except Exception as e:
            print(f"Error fetching definitions: {str(e)}")
            break
    
    return all_definitions


def extract_allowed_values(definition: dict) -> list:
    """Extract allowed values from validations."""
    allowed_values = []
    validations = definition.get("validations", [])
    
    for validation in validations:
        name = validation.get("name", "")
        value = validation.get("value")
        
        # Different validation types that might contain allowed values
        if name in ["choices", "list", "allowed_values", "enum"]:
            if isinstance(value, list):
                allowed_values = value
            elif isinstance(value, str):
                try:
                    # Try to parse as JSON
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        allowed_values = parsed
                except:
                    # If not JSON, might be comma-separated
                    if "," in value:
                        allowed_values = [v.strip() for v in value.split(",")]
                    else:
                        allowed_values = [value]
    
    return allowed_values


def display_definition(definition: dict):
    """Display metafield definition in a readable format."""
    if not definition:
        print("Definition not found")
        return
    
    print("=" * 60)
    print("METAFIELD DEFINITION")
    print("=" * 60)
    
    print(f"\nBasic Information:")
    print(f"  ID: {definition.get('id', 'N/A')}")
    print(f"  Name: {definition.get('name', 'N/A')}")
    print(f"  Namespace: {definition.get('namespace', 'N/A')}")
    print(f"  Key: {definition.get('key', 'N/A')}")
    print(f"  Description: {definition.get('description', 'N/A')}")
    
    mf_type = definition.get("type", {})
    print(f"\nType:")
    print(f"  Name: {mf_type.get('name', 'N/A')}")
    
    validations = definition.get("validations", [])
    print(f"\nValidations ({len(validations)}):")
    if validations:
        for validation in validations:
            name = validation.get("name", "N/A")
            value = validation.get("value", "N/A")
            print(f"  - {name}: {json.dumps(value, ensure_ascii=False)}")
    else:
        print("  (none)")
    
    # Extract allowed values
    allowed_values = extract_allowed_values(definition)
    print(f"\nAllowed Values (extracted from validations):")
    if allowed_values:
        for i, value in enumerate(allowed_values, 1):
            print(f"  {i}. {value}")
    else:
        print("  (none found)")
    
    access = definition.get("access", {})
    print(f"\nAccess:")
    print(f"  Admin: {access.get('admin', 'N/A')}")
    print(f"  Storefront: {access.get('storefront', 'N/A')}")
    
    print(f"\nMetadata:")
    print(f"  Pinned Position: {definition.get('pinnedPosition', 'N/A')}")
    print(f"  Owner Type: {definition.get('ownerType', 'N/A')}")
    print(f"  Created At: {definition.get('createdAt', 'N/A')}")
    print(f"  Updated At: {definition.get('updatedAt', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("RAW JSON STRUCTURE:")
    print("=" * 60)
    print(json.dumps(definition, indent=2, ensure_ascii=False))


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fetch and display metafield definition structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch a specific metafield definition
  python scripts/fetch_metafield_definition.py \\
    --namespace custom \\
    --key power-source
  
  # List all metafields in a namespace
  python scripts/fetch_metafield_definition.py \\
    --namespace custom \\
    --list-all
  
  # List all metafields (all namespaces)
  python scripts/fetch_metafield_definition.py \\
    --list-all
        """
    )
    
    parser.add_argument('--namespace', help='Metafield namespace')
    parser.add_argument('--key', help='Metafield key')
    parser.add_argument('--list-all', action='store_true', help='List all metafield definitions')
    
    args = parser.parse_args()
    
    if args.list_all:
        print("Fetching all metafield definitions...")
        if args.namespace:
            print(f"Filtering by namespace: {args.namespace}")
        
        definitions = get_all_metafield_definitions(args.namespace)
        
        print(f"\nFound {len(definitions)} metafield definitions:")
        print("=" * 60)
        
        for i, defn in enumerate(definitions, 1):
            namespace = defn.get("namespace", "N/A")
            key = defn.get("key", "N/A")
            name = defn.get("name", "N/A")
            mf_type = defn.get("type", {}).get("name", "N/A")
            allowed_values = extract_allowed_values(defn)
            
            print(f"\n{i}. {namespace}.{key}")
            print(f"   Name: {name}")
            print(f"   Type: {mf_type}")
            if allowed_values:
                print(f"   Allowed Values: {', '.join(str(v) for v in allowed_values[:5])}")
                if len(allowed_values) > 5:
                    print(f"                  ... and {len(allowed_values) - 5} more")
            else:
                print(f"   Allowed Values: (none)")
        
        print("\n" + "=" * 60)
        
    elif args.namespace and args.key:
        print(f"Fetching metafield definition: {args.namespace}.{args.key}")
        definition = get_metafield_definition_full(args.namespace, args.key)
        display_definition(definition)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()


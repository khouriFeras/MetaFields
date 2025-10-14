#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Metafield Definitions in Shopify

This script creates metafield definitions with storefront visibility enabled,
which allows them to be used as filters on collection pages.
"""
import json
import os
import sys
import argparse
import time
from pathlib import Path
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
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10").strip()


def make_graphql_request(query: str, variables: dict = None) -> dict:
    """Make a GraphQL request to Shopify."""
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"HTTP Error {response.status_code}: {response.text}")
        return None
    
    data = response.json()
    
    if "errors" in data:
        print(f"GraphQL Error: {data['errors']}")
        return None
    
    return data.get("data", {})


def check_existing_definitions():
    """Check which metafield definitions already exist."""
    query = """
    query {
      metafieldDefinitions(first: 100, ownerType: PRODUCT) {
        edges {
          node {
            id
            name
            namespace
            key
            type {
              name
            }
            visibleToStorefrontApi
          }
        }
      }
    }
    """
    
    result = make_graphql_request(query)
    if not result:
        return {}
    
    definitions = {}
    for edge in result.get("metafieldDefinitions", {}).get("edges", []):
        node = edge["node"]
        full_key = f"{node['namespace']}.{node['key']}"
        definitions[full_key] = {
            "id": node["id"],
            "name": node["name"],
            "type": node["type"]["name"],
            "visible": node["visibleToStorefrontApi"]
        }
    
    return definitions


def create_metafield_definition(namespace: str, key: str, name: str, metafield_type: str, description: str = ""):
    """Create a metafield definition with storefront visibility."""
    mutation = """
    mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
      metafieldDefinitionCreate(definition: $definition) {
        createdDefinition {
          id
          name
          namespace
          key
          type {
            name
          }
          visibleToStorefrontApi
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "definition": {
            "name": name,
            "namespace": namespace,
            "key": key,
            "type": metafield_type,
            "description": description or f"{name} for product categorization",
            "ownerType": "PRODUCT",
            "visibleToStorefrontApi": True
        }
    }
    
    result = make_graphql_request(mutation, variables)
    
    if not result:
        return False
    
    payload = result.get("metafieldDefinitionCreate", {})
    
    if payload.get("userErrors"):
        print(f"Error: {payload['userErrors']}")
        return False
    
    if payload.get("createdDefinition"):
        return True
    
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Create metafield definitions in Shopify"
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="Path to category mapping JSON file"
    )
    
    args = parser.parse_args()
    
    # Verify file exists
    if not Path(args.mapping).exists():
        print(f"Mapping file not found: {args.mapping}")
        return
    
    print("\nCREATING METAFIELD DEFINITIONS")
    print("=" * 60)
    print(f" Store: {SHOPIFY_STORE_DOMAIN}")
    print(f" API Version: {SHOPIFY_API_VERSION}")
    
    # Load category mapping
    print(f"\nLoading mapping: {args.mapping}")
    with open(args.mapping, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    metafield_defs = mapping.get("metafield_definitions", mapping.get("metafields", []))
    print(f"  Found {len(metafield_defs)} metafield definitions")
    
    # Check existing definitions
    print(f"\nChecking existing definitions...")
    existing = check_existing_definitions()
    print(f"  Found {len(existing)} existing definitions")
    
    # Create missing definitions
    created = 0
    skipped = 0
    failed = 0
    
    print(f"\nCreating metafield definitions...")
    print("=" * 60)
    
    for mf in metafield_defs:
        namespace = mf.get("namespace", "standard")
        key = mf.get("key")
        name = mf.get("name")
        mf_type = mf.get("type")
        
        full_key = f"{namespace}.{key}"
        
        # Check if already exists
        if full_key in existing:
            print(f" Skipped (exists): {name} ({full_key})")
            skipped += 1
            continue
        
        # Create definition
        print(f"Creating: {name} ({full_key}) - {mf_type}...")
        
        success = create_metafield_definition(
            namespace=namespace,
            key=key,
            name=name,
            metafield_type=mf_type,
            description=f"{name} - Product attribute"
        )
        
        if success:
            print(f"Created successfully")
            created += 1
        else:
            print(f"Failed to create")
            failed += 1
        
        # Rate limiting
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total definitions: {len(metafield_defs)}")
    print(f"Created: {created}")
    print(f" Skipped (existed): {skipped}")
    print(f"Failed: {failed}")
    print("=" * 60)
    
    if created > 0:
        print("\n Metafield definitions created with storefront visibility!")
        print(" These can now be used as filters on collection pages.")


if __name__ == "__main__":
    main()


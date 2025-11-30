#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add product IDs to products JSON file by fetching from Shopify using handles.
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
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

PRODUCT_BY_HANDLE_QUERY = """
query GetProductByHandle($query: String!) {
  products(first: 1, query: $query) {
    edges {
      node {
        id
        title
        handle
      }
    }
  }
}
"""


def graphql_request(query: str, variables: Dict = None) -> Dict:
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
    
    return result.get("data", {})


def fetch_product_id_by_handle(handle: str) -> Optional[str]:
    """Fetch product ID by handle."""
    try:
        variables = {"query": f"handle:{handle}"}
        data = graphql_request(PRODUCT_BY_HANDLE_QUERY, variables)
        
        products = data.get("products", {})
        edges = products.get("edges", [])
        if edges:
            return edges[0]["node"]["id"]
        return None
    except Exception as e:
        print(f"    Error fetching ID for handle '{handle}': {str(e)}")
        return None


def add_product_ids(products_file: str, output_file: str = None) -> None:
    """Add product IDs to products JSON by fetching from Shopify."""
    # Validate environment
    if not SHOPIFY_STORE_DOMAIN or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        raise SystemExit("Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN in .env")
    
    products_path = Path(products_file)
    if not products_path.exists():
        raise FileNotFoundError(f"Products file not found: {products_path}")
    
    if output_file is None:
        output_file = products_path.parent / f"{products_path.stem}_with_ids{products_path.suffix}"
    
    print(f"Reading products from: {products_path}")
    with open(products_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"Found {len(products)} products")
    print(f"Fetching product IDs from Shopify...\n")
    
    updated = 0
    not_found = 0
    
    for i, product in enumerate(products, 1):
        handle = product.get("handle", "")
        title = product.get("title", "N/A")
        
        if not handle:
            print(f"[{i}/{len(products)}] {title[:50]}... - No handle, skipping")
            not_found += 1
            continue
        
        print(f"[{i}/{len(products)}] {title[:50]}...")
        print(f"  Handle: {handle}")
        
        # Check if ID already exists
        if product.get("id"):
            print(f"  ID already exists: {product['id']}")
            updated += 1
            continue
        
        # Fetch ID by handle
        product_id = fetch_product_id_by_handle(handle)
        
        if product_id:
            product["id"] = product_id
            print(f"  ✓ Found ID: {product_id}")
            updated += 1
        else:
            print(f"  ✗ Product not found in Shopify")
            not_found += 1
        
        # Rate limiting
        time.sleep(0.3)
    
    # Save updated products
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total products: {len(products)}")
    print(f"  Updated with IDs: {updated}")
    print(f"  Not found: {not_found}")
    print(f"\nSaved to: {output_path}")
    
    if not_found > 0:
        print(f"\n⚠️  Warning: {not_found} product(s) could not be found in Shopify.")
        print(f"   These products will be skipped during upload.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/add_product_ids.py <products_file.json> [output_file.json]")
        sys.exit(1)
    
    products_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        add_product_ids(products_file, output_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


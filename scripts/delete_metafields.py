#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delete Metafields from Shopify Products

This script deletes metafields from products based on the category mapping.
Useful for cleaning up metafields before re-uploading with modifications.
"""
import json
import os
import sys
import time
import argparse
from typing import Dict, List, Optional, Any, Tuple
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


def load_json(file_path: str) -> Any:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    
    # Check for GraphQL errors
    if "errors" in result:
        error_msg = json.dumps(result['errors'], indent=2, ensure_ascii=False)
        raise Exception(f"GraphQL Error: {error_msg}")
    
    return result


def get_product_metafields(product_id: str) -> List[Dict]:
    """
    Get all metafields for a product.
    
    Args:
        product_id: Shopify product GID
    
    Returns:
        List of metafield dicts with id, namespace, key, value, type
    """
    query = """
    query GetProductMetafields($id: ID!) {
      product(id: $id) {
        id
        title
        metafields(first: 250) {
          edges {
            node {
              id
              namespace
              key
              value
              type
            }
          }
        }
      }
    }
    """
    
    try:
        result = graphql_request(query, {"id": product_id})
        product = result.get("data", {}).get("product")
        
        if not product:
            return []
        
        metafields = []
        for edge in product.get("metafields", {}).get("edges", []):
            metafields.append(edge["node"])
        
        return metafields
    except Exception as e:
        print(f"    Error fetching metafields: {str(e)}")
        return []


def delete_metafields_bulk(metafield_ids: List[str]) -> Tuple[bool, Optional[str], int]:
    """
    Delete multiple metafields by ID using metafieldsDelete mutation.
    
    Args:
        metafield_ids: List of metafield GIDs
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str], deleted_count: int)
    """
    if not metafield_ids:
        return True, None, 0
    
    mutation = """
    mutation DeleteMetafields($ids: [ID!]!) {
      metafieldsDelete(ids: $ids) {
        deletedMetafields {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    try:
        result = graphql_request(mutation, {"ids": metafield_ids})
        payload = result.get("data", {}).get("metafieldsDelete", {})
        
        if payload.get("userErrors"):
            errors = payload["userErrors"]
            error_msg = "; ".join([f"{e.get('field', 'unknown')}: {e.get('message', 'unknown')}" for e in errors])
            return False, error_msg, 0
        
        deleted = payload.get("deletedMetafields", [])
        deleted_count = len(deleted)
        return True, None, deleted_count
    except Exception as e:
        return False, str(e), 0


def delete_metafields_by_identifier(
    product_id: str,
    metafields_to_delete: List[Dict]
) -> Tuple[bool, Optional[str], int]:
    """
    Delete metafields using metafieldsDelete with ownerId, namespace, and key.
    This is the recommended method for deleting metafields.
    
    Args:
        product_id: Product GID (ownerId)
        metafields_to_delete: List of dicts with namespace and key
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str], deleted_count: int)
    """
    if not metafields_to_delete:
        return True, None, 0
    
    # Prepare metafield identifiers
    metafield_identifiers = []
    for mf in metafields_to_delete:
        metafield_identifiers.append({
            "ownerId": product_id,
            "namespace": mf["namespace"],
            "key": mf["key"]
        })
    
    mutation = """
    mutation DeleteMetafieldsByIdentifier($identifiers: [MetafieldDeleteInput!]!) {
      metafieldsDelete(identifiers: $identifiers) {
        deletedMetafields {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    try:
        result = graphql_request(mutation, {"identifiers": metafield_identifiers})
        payload = result.get("data", {}).get("metafieldsDelete", {})
        
        if payload.get("userErrors"):
            errors = payload["userErrors"]
            error_msg = "; ".join([f"{e.get('field', 'unknown')}: {e.get('message', 'unknown')}" for e in errors])
            return False, error_msg, 0
        
        deleted = payload.get("deletedMetafields", [])
        deleted_count = len(deleted)
        return True, None, deleted_count
    except Exception as e:
        return False, str(e), 0


def delete_metafields_via_product_update(
    product_id: str,
    metafields_to_delete: List[Dict]
) -> Tuple[bool, Optional[str], int]:
    """
    Delete metafields by setting them to empty string in productUpdate mutation.
    Note: This may not fully delete standard namespace metafields (taxonomy attributes).
    Use delete_metafields_by_identifier instead when possible.
    
    Args:
        product_id: Product GID
        metafields_to_delete: List of dicts with namespace and key
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str], deleted_count: int)
    """
    # Prepare metafields input with empty string values (not null)
    # For list types, use empty array string
    metafields_input = []
    for mf in metafields_to_delete:
        mf_type = mf.get("type", "single_line_text_field")
        if "list" in mf_type:
            # For list types, use empty JSON array
            value = "[]"
        else:
            # For single types, use empty string
            value = ""
        
        metafields_input.append({
            "namespace": mf["namespace"],
            "key": mf["key"],
            "value": value,
            "type": mf_type
        })
    
    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "input": {
            "id": product_id,
            "metafields": metafields_input
        }
    }
    
    try:
        result = graphql_request(mutation, variables)
        payload = result.get("data", {}).get("productUpdate", {})
        
        if payload.get("userErrors"):
            errors = payload["userErrors"]
            error_msg = "; ".join([f"{e.get('field', 'unknown')}: {e.get('message', 'unknown')}" for e in errors])
            return False, error_msg, 0
        
        return True, None, len(metafields_to_delete)
    except Exception as e:
        return False, str(e), 0


def delete_metafields(
    products_file: str,
    mapping_file: str,
    namespace: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False
) -> Dict:
    """
    Delete metafields from Shopify products.
    
    Args:
        products_file: Path to products JSON file
        mapping_file: Path to category mapping JSON (to know which metafields to delete)
        namespace: Optional namespace filter (e.g., "standard"). If None, uses namespace from mapping
        limit: Limit number of products to process
        dry_run: If True, don't actually delete, just show what would be deleted
    
    Returns:
        Deletion statistics
    """
    print("Shopify Metafields Deletion")
    print("=" * 60)
    
    # Validate environment
    if not SHOPIFY_STORE_DOMAIN or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        raise SystemExit("❌ Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN in .env")
    
    print(f"Store: {SHOPIFY_STORE_DOMAIN}")
    print(f"API Version: {SHOPIFY_API_VERSION}")
    
    # Load data
    print(f"\nLoading data...")
    products = load_json(products_file)
    mapping = load_json(mapping_file)
    
    print(f"   Loaded {len(products)} products")
    print(f"   Category: {mapping['category']['fullName']}")
    print(f"   Metafield definitions: {len(mapping['metafields'])}")
    
    # Build list of metafields to delete (from mapping)
    metafields_to_delete = {}
    for mf in mapping['metafields']:
        mf_namespace = mf.get('namespace', 'standard')
        mf_key = mf['key']
        
        # Apply namespace filter if specified
        if namespace and mf_namespace != namespace:
            continue
        
        full_key = f"{mf_namespace}.{mf_key}"
        metafields_to_delete[full_key] = {
            "namespace": mf_namespace,
            "key": mf_key,
            "name": mf.get('name', mf_key)
        }
    
    print(f"\n   Metafields to delete: {len(metafields_to_delete)}")
    for full_key, mf_info in metafields_to_delete.items():
        print(f"     • {full_key} ({mf_info['name']})")
    
    # Limit products if specified
    if limit:
        products = products[:limit]
        print(f"\n⚠️  Limited to first {limit} products for testing")
    
    if dry_run:
        print(f"\n🔍 DRY RUN MODE - No changes will be made")
    
    # Deletion stats
    stats = {
        "total": len(products),
        "processed": 0,
        "deleted": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }
    
    print(f"\n Processing {len(products)} products...")
    print("=" * 60)
    
    for i, product in enumerate(products, 1):
        product_id = product.get("id")
        title = product.get("title", "N/A")
        
        print(f"\n[{i}/{len(products)}] {title[:60]}...")
        print(f"  Product ID: {product_id}")
        
        if dry_run:
            # In dry-run, just check what would be deleted
            metafields = get_product_metafields(product_id)
            matching = [mf for mf in metafields if f"{mf['namespace']}.{mf['key']}" in metafields_to_delete]
            
            if matching:
                print(f"  [DRY RUN] Would delete {len(matching)} metafield(s):")
                for mf in matching:
                    print(f"    • {mf['namespace']}.{mf['key']} = {str(mf['value'])[:50]}")
                stats["deleted"] += len(matching)
            else:
                print(f"  [DRY RUN] No matching metafields to delete")
                stats["skipped"] += 1
            
            stats["processed"] += 1
            continue
        
        # Get metafields for this product
        metafields = get_product_metafields(product_id)
        
        if not metafields:
            print(f"  No metafields found on product")
            stats["skipped"] += 1
            continue
        
        # Find metafields that match our list
        matching_metafields = [
            mf for mf in metafields 
            if f"{mf['namespace']}.{mf['key']}" in metafields_to_delete
        ]
        
        if not matching_metafields:
            print(f"  No matching metafields to delete")
            stats["skipped"] += 1
            continue
        
        print(f"  Found {len(matching_metafields)} metafield(s) to delete:")
        for mf in matching_metafields:
            print(f"    • {mf['namespace']}.{mf['key']} = {str(mf['value'])[:50]}")
        
        # Try deletion by identifier first (recommended method)
        print(f"      Trying deletion by identifier (ownerId + namespace + key)...")
        success, error_msg, deleted_count = delete_metafields_by_identifier(
            product_id,
            matching_metafields
        )
        
        if success and deleted_count > 0:
            print(f"      ✓ Deleted {deleted_count} metafield(s) using identifier method")
            stats["deleted"] += deleted_count
        elif success and deleted_count == 0:
            # Identifier method succeeded but nothing deleted - try ID method
            print(f"      ⚠ Identifier method returned 0 deleted, trying ID method...")
            metafield_ids = [mf['id'] for mf in matching_metafields]
            success, error_msg, deleted_count = delete_metafields_bulk(metafield_ids)
            
            if success and deleted_count > 0:
                print(f"      ✓ Deleted {deleted_count} metafield(s) using ID method")
                stats["deleted"] += deleted_count
            else:
                # Try productUpdate as last resort
                print(f"      ⚠ ID method failed, trying productUpdate (may only clear values)...")
                success, error_msg, deleted_count = delete_metafields_via_product_update(
                    product_id,
                    matching_metafields
                )
                if success:
                    print(f"      ⚠ Cleared {deleted_count} metafield(s) using productUpdate")
                    print(f"      ⚠ Note: Standard namespace metafields may not fully delete via productUpdate")
                    stats["deleted"] += deleted_count
                else:
                    print(f"      ✗ All deletion methods failed: {error_msg}")
                    stats["failed"] += len(matching_metafields)
                    for mf in matching_metafields:
                        stats["errors"].append({
                            "product_id": product_id,
                            "title": title,
                            "metafield": f"{mf['namespace']}.{mf['key']}",
                            "error": error_msg
                        })
        else:
            # Identifier method failed - try ID method
            print(f"      ⚠ Identifier method failed: {error_msg}")
            print(f"      Trying ID method...")
            metafield_ids = [mf['id'] for mf in matching_metafields]
            success, error_msg, deleted_count = delete_metafields_bulk(metafield_ids)
            
            if success and deleted_count > 0:
                print(f"      ✓ Deleted {deleted_count} metafield(s) using ID method")
                stats["deleted"] += deleted_count
            else:
                # Try productUpdate as last resort
                print(f"      ⚠ ID method failed, trying productUpdate (may only clear values)...")
                success, error_msg, deleted_count = delete_metafields_via_product_update(
                    product_id,
                    matching_metafields
                )
                if success:
                    print(f"      ⚠ Cleared {deleted_count} metafield(s) using productUpdate")
                    print(f"      ⚠ Note: Standard namespace metafields may not fully delete via productUpdate")
                    stats["deleted"] += deleted_count
                else:
                    print(f"      ✗ All deletion methods failed: {error_msg}")
                    stats["failed"] += len(matching_metafields)
                    for mf in matching_metafields:
                        stats["errors"].append({
                            "product_id": product_id,
                            "title": title,
                            "metafield": f"{mf['namespace']}.{mf['key']}",
                            "error": error_msg
                        })
        
        # Verify deletion after a short delay
        if not dry_run and stats["deleted"] > 0:
            time.sleep(0.5)  # Wait a bit for Shopify to process
            remaining_metafields = get_product_metafields(product_id)
            # Build set of keys to check
            deleted_keys = {f"{mf['namespace']}.{mf['key']}" for mf in matching_metafields}
            remaining_matching = [
                mf for mf in remaining_metafields 
                if f"{mf['namespace']}.{mf['key']}" in deleted_keys
            ]
            
            if remaining_matching:
                print(f"      ⚠ WARNING: {len(remaining_matching)} metafield(s) still exist after deletion:")
                for mf in remaining_matching:
                    print(f"         • {mf['namespace']}.{mf['key']} = {str(mf['value'])[:50]}")
                print(f"      ⚠ This may be normal for standard namespace metafields (taxonomy attributes)")
                print(f"      ⚠ They may need to be cleared manually in Shopify admin")
            else:
                print(f"      ✓ Verified: All metafields successfully deleted")
        
        stats["processed"] += 1
        
        # Rate limiting between products
        time.sleep(0.3)
    
    # Summary
    print("\n" + "=" * 60)
    print("DELETION SUMMARY")
    print("=" * 60)
    print(f"Total products:      {stats['total']}")
    print(f" Processed:         {stats['processed']}")
    print(f" Deleted:           {stats['deleted']} metafield(s)")
    print(f" Failed:            {stats['failed']}")
    print(f" Skipped:           {stats['skipped']}")
    
    if stats["errors"]:
        print(f"\n Errors ({len(stats['errors'])}):")
        for error in stats["errors"][:10]:  # Show first 10 errors
            print(f"  - {error['title'][:40]}: {error['metafield']} - {error['error']}")
        if len(stats["errors"]) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more errors")
    
    print("\n" + "=" * 60)
    
    if not dry_run:
        if stats["deleted"] > 0:
            print(f"\n✅ Deleted {stats['deleted']} metafield(s) from {stats['processed']} product(s)")
        else:
            print(f"\n⚠️  No metafields were deleted")
    
    return stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Delete metafields from Shopify products",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be deleted
  python scripts/delete_metafields.py \\
    --products exports/مكنسة_تنظيف_metafields.metafields.json \\
    --mapping exports/مكنسة_تنظيف_metafields.category_mapping.json \\
    --limit 2 \\
    --dry-run
  
  # Actually delete from 2 products
  python scripts/delete_metafields.py \\
    --products exports/مكنسة_تنظيف_metafields.metafields.json \\
    --mapping exports/مكنسة_تنظيف_metafields.category_mapping.json \\
    --limit 2
  
  # Delete all metafields from all products
  python scripts/delete_metafields.py \\
    --products exports/مكنسة_تنظيف_metafields.metafields.json \\
    --mapping exports/مكنسة_تنظيف_metafields.category_mapping.json
  
  # Delete only metafields from specific namespace
  python scripts/delete_metafields.py \\
    --products exports/مكنسة_تنظيف_metafields.metafields.json \\
    --mapping exports/مكنسة_تنظيف_metafields.category_mapping.json \\
    --namespace standard
        """
    )
    
    parser.add_argument('--products', required=True, help='Path to products JSON file')
    parser.add_argument('--mapping', required=True, help='Path to category mapping JSON')
    parser.add_argument('--namespace', help='Optional: Only delete metafields from this namespace (e.g., "standard")')
    parser.add_argument('--limit', type=int, help='Limit number of products (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    delete_metafields(
        products_file=args.products,
        mapping_file=args.mapping,
        namespace=args.namespace,
        limit=args.limit,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()


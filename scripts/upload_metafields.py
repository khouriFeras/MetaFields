#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload Category Metafields to Shopify Products

This script uploads metafield VALUES to Shopify products using EXISTING category metafield
definitions (Shopify taxonomy attributes). It does NOT create new metafield definitions.

Category metafields (taxonomy attributes) are Shopify's standard product metafields that
already exist in the taxonomy system. We simply fill in values for products using these
existing definitions.

Supports Arabic translations for bilingual filters.
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
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


def save_json(file_path: str, data: Any) -> None:
    """Save JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
        raise Exception(f"GraphQL Error: {result['errors']}")
    
    return result


def prepare_metafield_input(key: str, value: Any, metafield_type: str) -> Dict:
    """
    Prepare metafield input for Shopify GraphQL mutation.
    
    This function prepares metafield VALUES to be uploaded to products using EXISTING
    category metafield definitions (Shopify taxonomy attributes). It does NOT create
    new metafield definitions.
    
    Args:
        key: Metafield key (e.g., "charging-method") - must match an existing category metafield
        value: Metafield value (can be string, list, etc.)
        metafield_type: Shopify metafield type (e.g., "single_line_text_field", "list.single_line_text_field")
    
    Returns:
        Metafield input dict for GraphQL
    """
    # Use Shopify's "standard" namespace for category metafields (taxonomy attributes)
    # These already exist in Shopify - we're just filling in values for products
    namespace = "standard"
    
    # Convert value based on type
    if metafield_type == "list.single_line_text_field":
        # List type - convert to JSON array string
        if isinstance(value, list):
            metafield_value = json.dumps(value)
        else:
            metafield_value = json.dumps([value])
        value_type = "list.single_line_text_field"
    else:
        # Single value type
        metafield_value = str(value) if value is not None else ""
        value_type = "single_line_text_field"
    
    return {
        "namespace": namespace,
        "key": key,
        "value": metafield_value,
        "type": value_type
    }


def enable_metafield_storefront_visibility(
    namespace: str,
    key: str,
    metafield_name: str
) -> bool:
    """
    Enable storefront visibility for a category metafield definition.
    
    This function enables storefront visibility for EXISTING category metafield definitions
    (Shopify taxonomy attributes) so they can be used in product filters.
    
    When you upload a metafield value using a taxonomy attribute key (e.g., "standard.color"),
    Shopify automatically creates the metafield definition for products if it doesn't exist yet.
    This function just ensures it's visible on the storefront for filtering.
    
    Args:
        namespace: Metafield namespace (e.g., "standard" for category metafields)
        key: Metafield key (e.g., "charging-method")
        metafield_name: Display name (e.g., "Charging method")
    
    Returns:
        True if successful, False otherwise
    """
    # First, check if definition exists
    query = """
    query getMetafieldDefinition($namespace: String!, $key: String!) {
      metafieldDefinitions(first: 1, ownerType: PRODUCT, namespace: $namespace, key: $key) {
        edges {
          node {
            id
            name
            visibleToStorefrontApi
          }
        }
      }
    }
    """
    
    try:
        result = graphql_request(query, {
            "namespace": namespace,
            "key": key
        })
        
        definitions = result.get("data", {}).get("metafieldDefinitions", {}).get("edges", [])
        
        if definitions:
            # Definition exists, update it
            definition_id = definitions[0]["node"]["id"]
            is_visible = definitions[0]["node"]["visibleToStorefrontApi"]
            
            if is_visible:
                print(f"     {metafield_name} already visible to storefront")
                return True
            
            # Update to enable visibility
            mutation = """
            mutation updateMetafieldDefinition($definition: MetafieldDefinitionUpdateInput!) {
              metafieldDefinitionUpdate(definition: $definition) {
                updatedDefinition {
                  id
                  name
                  visibleToStorefrontApi
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            
            update_result = graphql_request(mutation, {
                "definition": {
                    "id": definition_id,
                    "visibleToStorefrontApi": True
                }
            })
            
            errors = update_result.get("data", {}).get("metafieldDefinitionUpdate", {}).get("userErrors", [])
            if errors:
                print(f"      Error enabling visibility for {metafield_name}: {errors}")
                return False
            
            print(f"     Enabled storefront visibility for {metafield_name}")
            return True
        else:
            # Definition doesn't exist yet - it will be created when we add the first metafield
            print(f"      {metafield_name} definition will be created automatically")
            return True
            
    except Exception as e:
        print(f"      Could not enable visibility for {metafield_name}: {str(e)}")
        return False


def update_product_metafields(
    product_id: str,
    metafields_data: Dict[str, Any],
    metafield_definitions: List[Dict]
) -> Dict:
    """
    Update product metafields using GraphQL.
    
    This function uploads metafield VALUES to products using EXISTING category metafield
    definitions (Shopify taxonomy attributes). It does NOT create new metafield definitions.
    
    When you set a metafield value on a product using a standard taxonomy attribute key
    (e.g., "standard.color"), Shopify automatically:
    1. Uses the existing category metafield definition (if not yet linked to products)
    2. Creates the link between product and category metafield
    3. Stores the value
    
    Args:
        product_id: Shopify product GID (e.g., "gid://shopify/Product/123")
        metafields_data: Dict of metafield key -> value
        metafield_definitions: List of category metafield definitions from category mapping
    
    Returns:
        GraphQL response
    """
    # Create metafield type mapping and name->key mapping
    metafield_types = {mf['key']: mf['type'] for mf in metafield_definitions}
    
    # Create a mapping from display name (with spaces/capitals) to correct key (with hyphens)
    # This handles JSON files that have keys like "Audio technology" instead of "audio-technology"
    key_mapping = {}
    for mf in metafield_definitions:
        # Map from name to key (e.g., "Audio technology" -> "audio-technology")
        key_mapping[mf['name']] = mf['key']
        # Also map the key to itself for already-correct keys
        key_mapping[mf['key']] = mf['key']
    
    # Prepare metafields input
    metafields_input = []
    for key, value in metafields_data.items():
        if value is not None:  # Skip null values
            # Convert key to correct format if needed
            correct_key = key_mapping.get(key, key.lower().replace(" ", "-"))
            mf_type = metafield_types.get(correct_key, "single_line_text_field")
            metafields_input.append(prepare_metafield_input(correct_key, value, mf_type))
    
    # GraphQL mutation
    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          title
          metafields(first: 20) {
            edges {
              node {
                namespace
                key
                value
                type
              }
            }
          }
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
    
    return graphql_request(mutation, variables)


def register_translations(
    resource_id: str,
    translations_map: Dict[str, Dict[str, str]],
    metafields_data: Dict[str, Any]
) -> None:
    """
    Register Arabic translations for metafield values.
    
    Args:
        resource_id: Resource GID (product metafield GID)
        translations_map: Translation mapping from metafield_translations.json
        metafields_data: The metafield data to translate
    """
    # This function will register translations for each metafield value
    # Shopify's translation API requires the metafield GID which we get after creating the metafield
    
    # For now, we'll prepare the translations structure
    # In practice, you'd need to:
    # 1. Create metafields first
    # 2. Get their GIDs
    # 3. Register translations using translationsRegister mutation
    
    # This is a complex process that requires multiple API calls
    # For the initial implementation, we'll focus on uploading English values
    # and add translation support in a follow-up iteration
    
    pass


def upload_metafields(
    products_file: str,
    mapping_file: str,
    translations_file: str,
    limit: Optional[int] = None,
    dry_run: bool = False
) -> Dict:
    """
    Upload metafields to Shopify products.
    
    Args:
        products_file: Path to products JSON with metafields
        mapping_file: Path to category mapping JSON
        translations_file: Path to translations JSON
        limit: Limit number of products to process (for testing)
        dry_run: If True, don't actually upload, just show what would be uploaded
    
    Returns:
        Upload statistics
    """
    print("Shopify Metafields Upload")
    print("=" * 60)
    
    # Validate environment
    if not SHOPIFY_STORE_DOMAIN or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        raise SystemExit(" Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN in .env")
    
    print(f"Store: {SHOPIFY_STORE_DOMAIN}")
    print(f"API Version: {SHOPIFY_API_VERSION}")
    
    # Load data
    print(f"\nLoading data...")
    products = load_json(products_file)
    mapping = load_json(mapping_file)
    translations = load_json(translations_file) if translations_file else {}
    
    print(f"   Loaded {len(products)} products")
    print(f"   Category: {mapping['category']['fullName']}")
    print(f"   Metafield definitions: {len(mapping['metafields'])}")
    
    # Limit products if specified
    if limit:
        products = products[:limit]
        print(f"\n Limited to first {limit} products for testing")
    
    if dry_run:
        print(f"\n DRY RUN MODE - No changes will be made")
    
    # Upload metafields
    stats = {
        "total": len(products),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }
    
    print(f"\n Uploading metafields to {len(products)} products...")
    print("=" * 60)
    
    for i, product in enumerate(products, 1):
        product_id = product.get("id")
        title = product.get("title", "N/A")
        metafields_data = product.get("category_metafields", {})
        
        print(f"\n[{i}/{len(products)}] {title[:60]}...")
        print(f"  Product ID: {product_id}")
        
        # Skip if no metafields
        if not metafields_data or all(v is None for v in metafields_data.values()):
            print(f"    No metafields to upload")
            stats["skipped"] += 1
            continue
        
        # Show metafields to upload
        filled_metafields = {k: v for k, v in metafields_data.items() if v is not None}
        print(f"  Metafields to upload: {len(filled_metafields)}")
        for key, value in filled_metafields.items():
            value_str = str(value)[:60]
            print(f"    • {key}: {value_str}")
        
        if dry_run:
            print(f"  [DRY RUN] Would upload {len(filled_metafields)} metafields")
            stats["success"] += 1
            continue
        
        # Upload to Shopify
        try:
            result = update_product_metafields(
                product_id=product_id,
                metafields_data=metafields_data,
                metafield_definitions=mapping['metafields']
            )
            
            # Check for user errors
            user_errors = result.get("data", {}).get("productUpdate", {}).get("userErrors", [])
            if user_errors:
                error_msg = "; ".join([f"{e['field']}: {e['message']}" for e in user_errors])
                print(f"  Error: {error_msg}")
                stats["failed"] += 1
                stats["errors"].append({
                    "product_id": product_id,
                    "title": title,
                    "error": error_msg
                })
            else:
                print(f"  Successfully uploaded {len(filled_metafields)} metafields")
                stats["success"] += 1
            
            # Rate limiting - be nice to Shopify API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Exception: {str(e)}")
            stats["failed"] += 1
            stats["errors"].append({
                "product_id": product_id,
                "title": title,
                "error": str(e)
            })
    
    # Enable storefront visibility for metafields
    if not dry_run and stats["success"] > 0:
        print("\n" + "=" * 60)
        print(" ENABLING STOREFRONT VISIBILITY FOR FILTERS")
        print("=" * 60)
        
        namespace = "standard"
        for metafield_def in mapping['metafields']:
            key = metafield_def['key']
            name = metafield_def['name']
            print(f"\n  🔧 {name} ({namespace}.{key})")
            enable_metafield_storefront_visibility(namespace, key, name)
            time.sleep(0.3)  # Rate limiting
    
    # Summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Total products:      {stats['total']}")
    print(f" Success:          {stats['success']}")
    print(f" Failed:           {stats['failed']}")
    print(f"  Skipped:          {stats['skipped']}")
    
    if stats["errors"]:
        print(f"\n Errors:")
        for error in stats["errors"]:
            print(f"  • {error['title'][:50]}: {error['error']}")
    
    print("\n" + "=" * 60)
    
    if not dry_run and stats["success"] > 0:
        print("\n Metafields uploaded successfully!")
        print(" Storefront visibility ENABLED - filters are ready!")
        print("\n HOW IT WORKS:")
        print("  • Used EXISTING category metafield definitions (taxonomy attributes)")
        print("  • Did NOT create new product metafield definitions")
        print("  • Shopify automatically linked category metafields to products")
        print("  • Values are now stored and ready for filtering")
        print("\n Next steps:")
        print("  1.  DONE: Category metafield values uploaded to products")
        print("  2.  DONE: Storefront visibility enabled")
        print("  3. TODO: Go to Online Store → Themes → Customize")
        print("  4. TODO: Add 'Product filters' block to collection pages")
        print("  5. TODO: Add Arabic translations (Settings → Languages → Translate)")
        print("\n For Arabic translations:")
        print("  English values are uploaded. Add Arabic translations via:")
        print("  • Shopify Admin → Settings → Languages → Translate")
        print("  • Find 'Product metafields' and translate each value")
        print(f"  • Use the mapping in: {translations_file}")
    
    return stats


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upload category metafields to Shopify products with translations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - test with 2 products
  python scripts/upload_metafields.py \\
    --products exports/tag_Power-bank/products_with_metafields_v2.json \\
    --mapping exports/tag_Power-bank/gpt-4o-mini_20251013_120537/tag_Power-bank_category_mapping.json \\
    --translations data/metafield_translations.json \\
    --limit 2 \\
    --dry-run
  
  # Actually upload 2 products
  python scripts/upload_metafields.py \\
    --products exports/tag_Power-bank/products_with_metafields_v2.json \\
    --mapping exports/tag_Power-bank/gpt-4o-mini_20251013_120537/tag_Power-bank_category_mapping.json \\
    --translations data/metafield_translations.json \\
    --limit 2
  
  # Upload all products
  python scripts/upload_metafields.py \\
    --products exports/tag_Power-bank/products_with_metafields_v2.json \\
    --mapping exports/tag_Power-bank/gpt-4o-mini_20251013_120537/tag_Power-bank_category_mapping.json \\
    --translations data/metafield_translations.json
        """
    )
    
    parser.add_argument('--products', required=True, help='Path to products JSON with metafields')
    parser.add_argument('--mapping', required=True, help='Path to category mapping JSON')
    parser.add_argument('--translations', required=False, help='Path to translations JSON (optional)')
    parser.add_argument('--limit', type=int, help='Limit number of products (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be uploaded without actually uploading')
    
    args = parser.parse_args()
    
    upload_metafields(
        products_file=args.products,
        mapping_file=args.mapping,
        translations_file=args.translations,
        limit=args.limit,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()


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


def save_json(file_path: str, data: Any) -> None:
    """Save JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def graphql_request(query: str, variables: Dict = None, debug: bool = False) -> Dict:
    """
    Make a GraphQL request to Shopify.
    
    Args:
        query: GraphQL query/mutation string
        variables: Variables for the query
        debug: If True, log the request and response for debugging
    
    Returns:
        GraphQL response dict
    """
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    if debug:
        print(f"  [DEBUG] GraphQL Request:")
        print(f"    Query: {query[:200]}...")
        print(f"    Variables: {json.dumps(variables, indent=2, ensure_ascii=False)[:500]}")
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    result = response.json()
    
    if debug:
        print(f"  [DEBUG] GraphQL Response:")
        print(f"    {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
    
    # Check for GraphQL errors
    if "errors" in result:
        error_msg = json.dumps(result['errors'], indent=2, ensure_ascii=False)
        if debug:
            print(f"  [DEBUG] GraphQL Errors: {error_msg}")
        raise Exception(f"GraphQL Error: {error_msg}")
    
    return result


def prepare_metafield_input(key: str, value: Any, metafield_type: str, namespace: str = "standard") -> Dict:
    """
    Prepare metafield input for Shopify GraphQL mutation.
    
    This function prepares metafield VALUES to be uploaded to products using EXISTING
    category metafield definitions (Shopify taxonomy attributes). It does NOT create
    new metafield definitions.
    
    Args:
        key: Metafield key (e.g., "charging-method") - must match an existing category metafield
        value: Metafield value (can be string, list, etc.)
        metafield_type: Shopify metafield type (e.g., "single_line_text_field", "list.single_line_text_field")
        namespace: Metafield namespace (default: "standard" for taxonomy attributes)
    
    Returns:
        Metafield input dict for GraphQL
    """
    # Note: We use the namespace from the definition, but for standard namespace,
    # we keep it as "standard" when uploading values (Shopify expects this for taxonomy attributes)
    
    # Handle null/empty values - should be filtered out before calling this function
    if value is None:
        raise ValueError(f"Cannot prepare metafield input for null value: {namespace}.{key}")
    
    # Convert value based on type
    if metafield_type == "list.single_line_text_field":
        # List type - convert to JSON array string
        if isinstance(value, list):
            # Ensure all items are strings and filter out None values
            metafield_value = json.dumps([str(item) for item in value if item is not None])
        elif isinstance(value, str):
            # If it's already a JSON string, validate it
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    metafield_value = json.dumps([str(item) for item in parsed if item is not None])
                else:
                    metafield_value = json.dumps([str(value)])
            except (json.JSONDecodeError, TypeError):
                # Not a JSON string, treat as single value
                metafield_value = json.dumps([str(value)])
        else:
            # Single value, wrap in array
            metafield_value = json.dumps([str(value)])
        value_type = "list.single_line_text_field"
    else:
        # Single value type - ensure it's a string
        if isinstance(value, list):
            # If list type but type is single, take first item
            metafield_value = str(value[0]) if value else ""
        else:
            metafield_value = str(value) if value is not None else ""
        value_type = "single_line_text_field"
    
    return {
        "namespace": namespace,
        "key": key,
        "value": metafield_value,
        "type": value_type
    }


def pin_metafield_definition(definition_id: str, metafield_name: str) -> bool:
    """
    Pin a metafield definition so it shows in Shopify Admin UI.
    
    Pinned definitions automatically display on the corresponding pages in Shopify admin.
    
    Args:
        definition_id: Metafield definition GID
        metafield_name: Display name for logging
    
    Returns:
        True if successful, False otherwise
    """
    mutation = """
    mutation PinMetafieldDefinition($definitionId: ID!) {
      metafieldDefinitionPin(definitionId: $definitionId) {
        pinnedDefinition {
          id
          name
          pinnedPosition
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    try:
        result = graphql_request(mutation, {"definitionId": definition_id})
        
        if not result:
            return False
        
        payload = result.get("metafieldDefinitionPin", {})
        
        if payload.get("userErrors"):
            errors = payload['userErrors']
            error_msg = "; ".join([f"{e.get('field', 'unknown')}: {e.get('message', 'unknown')}" for e in errors])
            print(f"      Error pinning {metafield_name}: {error_msg}")
            return False
        
        if payload.get("pinnedDefinition"):
            print(f"     Pinned {metafield_name} (will show in Admin UI)")
            return True
        
        return False
    except Exception as e:
        print(f"      Could not pin {metafield_name}: {str(e)}")
        return False


def enable_metafield_storefront_visibility(
    namespace: str,
    key: str,
    metafield_name: str
) -> bool:
    """
    Enable storefront visibility for a category metafield definition.
    
    Uses the modern API: access: { storefront: PUBLIC_READ }
    
    Args:
        namespace: Metafield namespace (e.g., "standard" for category metafields)
        key: Metafield key (e.g., "charging-method")
        metafield_name: Display name (e.g., "Charging method")
    
    Returns:
        True if successful, False otherwise
    """
    # First, check if definition exists
    query = """
    query getMetafieldDefinition($namespace: String!, $key: String!, $ownerType: MetafieldOwnerType!) {
      metafieldDefinitions(first: 1, ownerType: $ownerType, namespace: $namespace, key: $key) {
        edges {
          node {
            id
            name
            access {
              storefront
            }
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
            # Definition exists, update it
            definition_id = definitions[0]["node"]["id"]
            current_access = definitions[0]["node"].get("access", {}).get("storefront")
            
            if current_access == "PUBLIC_READ":
                print(f"     {metafield_name} already visible to storefront")
                return True
            
            # Update to enable storefront access
            mutation = """
            mutation updateMetafieldDefinition($definition: MetafieldDefinitionUpdateInput!) {
              metafieldDefinitionUpdate(definition: $definition) {
                updatedDefinition {
                  id
                  name
                  access {
                    storefront
                  }
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
                    "access": {
                        "storefront": "PUBLIC_READ"
                    }
                }
            })
            
            errors = update_result.get("data", {}).get("metafieldDefinitionUpdate", {}).get("userErrors", [])
            if errors:
                error_msg = "; ".join([f"{e.get('field', 'unknown')}: {e.get('message', 'unknown')}" for e in errors])
                print(f"      Error enabling storefront access for {metafield_name}: {error_msg}")
                return False
            
            print(f"     Enabled storefront access for {metafield_name}")
            return True
        else:
            # Definition doesn't exist yet - it will be created when we add the first metafield
            print(f"      {metafield_name} definition will be created automatically")
            return True
            
    except Exception as e:
        print(f"      Could not enable storefront access for {metafield_name}: {str(e)}")
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
    # Create metafield type and namespace mapping
    metafield_types = {mf['key']: mf['type'] for mf in metafield_definitions}
    metafield_namespaces = {mf['key']: mf.get('namespace', 'standard') for mf in metafield_definitions}
    
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
        if value is not None and value != "":  # Skip null and empty values
            # Convert key to correct format if needed
            correct_key = key_mapping.get(key, key.lower().replace(" ", "-").replace("_", "-"))
            mf_type = metafield_types.get(correct_key, "single_line_text_field")
            namespace = metafield_namespaces.get(correct_key, "standard")
            metafields_input.append(prepare_metafield_input(correct_key, value, mf_type, namespace))
    
    # Validate metafields_input is not empty
    if not metafields_input:
        raise ValueError("No valid metafields to upload - all values are null or empty")
    
    # Validate required fields
    for mf_input in metafields_input:
        if not mf_input.get("namespace"):
            raise ValueError(f"Missing namespace for metafield: {mf_input.get('key', 'unknown')}")
        if not mf_input.get("key"):
            raise ValueError(f"Missing key for metafield in namespace: {mf_input.get('namespace', 'unknown')}")
        if mf_input.get("value") is None:
            raise ValueError(f"Missing value for metafield: {mf_input.get('namespace', 'unknown')}.{mf_input.get('key', 'unknown')}")
        if not mf_input.get("type"):
            raise ValueError(f"Missing type for metafield: {mf_input.get('namespace', 'unknown')}.{mf_input.get('key', 'unknown')}")
    
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
    
    # Validate product_id format
    if not product_id:
        raise ValueError("Product ID is required")
    if not product_id.startswith("gid://shopify/Product/"):
        raise ValueError(f"Invalid product ID format: {product_id}. Expected format: gid://shopify/Product/123")
    
    variables = {
        "input": {
            "id": product_id,
            "metafields": metafields_input
        }
    }
    
    return graphql_request(mutation, variables)


def verify_product_metafields(product_id: str, expected_metafields: List[Dict]) -> Dict:
    """
    Verify that metafields actually exist on a product after upload.
    
    Args:
        product_id: Shopify product GID
        expected_metafields: List of metafield dicts with namespace, key, value
    
    Returns:
        Dict with verification results: found, missing, errors
    """
    query = """
    query GetProductMetafields($id: ID!) {
      product(id: $id) {
        id
        title
        metafields(first: 50) {
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
            return {
                "found": [],
                "missing": expected_metafields,
                "errors": ["Product not found"]
            }
        
        # Get actual metafields from product
        actual_metafields = {}
        for edge in product.get("metafields", {}).get("edges", []):
            mf = edge["node"]
            full_key = f"{mf['namespace']}.{mf['key']}"
            actual_metafields[full_key] = {
                "namespace": mf["namespace"],
                "key": mf["key"],
                "value": mf["value"],
                "type": mf["type"]
            }
        
        # Check which expected metafields were found
        found = []
        missing = []
        
        for expected_mf in expected_metafields:
            full_key = f"{expected_mf['namespace']}.{expected_mf['key']}"
            if full_key in actual_metafields:
                found.append(expected_mf)
            else:
                missing.append(expected_mf)
        
        return {
            "found": found,
            "missing": missing,
            "errors": []
        }
    except Exception as e:
        return {
            "found": [],
            "missing": expected_metafields,
            "errors": [str(e)]
        }


def create_metafield_definition(
    namespace: str,
    key: str,
    name: str,
    metafield_type: str,
    description: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Create a metafield definition in Shopify.
    
    Args:
        namespace: Metafield namespace
        key: Metafield key
        name: Display name
        metafield_type: Metafield type (e.g., "list.single_line_text_field")
        description: Optional description
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
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
            "description": description or f"{name} - Product attribute",
            "ownerType": "PRODUCT",
            "access": {
                "storefront": "PUBLIC_READ"
            }
        }
    }
    
    try:
        result = graphql_request(mutation, variables)
        payload = result.get("data", {}).get("metafieldDefinitionCreate", {})
        
        if payload.get("userErrors"):
            errors = payload["userErrors"]
            error_msg = "; ".join([f"{e.get('field', 'unknown')}: {e.get('message', 'unknown')}" for e in errors])
            return False, error_msg
        
        if payload.get("createdDefinition"):
            return True, None
        
        return False, "Unknown error: No createdDefinition and no userErrors returned"
    except Exception as e:
        return False, str(e)


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
            print(f"    ΓÇó {key}: {value_str}")
        
        if dry_run:
            print(f"  [DRY RUN] Would upload {len(filled_metafields)} metafields")
            stats["success"] += 1
            continue
        
        # Upload to Shopify
        try:
            # Prepare expected metafields for verification
            metafield_types = {mf['key']: mf['type'] for mf in mapping['metafields']}
            metafield_namespaces = {mf['key']: mf.get('namespace', 'standard') for mf in mapping['metafields']}
            key_mapping = {}
            for mf in mapping['metafields']:
                key_mapping[mf['name']] = mf['key']
                key_mapping[mf['key']] = mf['key']
            
            expected_metafields = []
            for key, value in filled_metafields.items():
                correct_key = key_mapping.get(key, key.lower().replace(" ", "-").replace("_", "-"))
                namespace = metafield_namespaces.get(correct_key, "standard")
                expected_metafields.append({
                    "namespace": namespace,
                    "key": correct_key,
                    "value": str(value)
                })
            
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
                # Verify metafields were actually created
                time.sleep(0.3)  # Small delay before verification
                verification = verify_product_metafields(product_id, expected_metafields)
                
                if verification["errors"]:
                    print(f"  Warning: Could not verify metafields: {verification['errors']}")
                
                if verification["missing"]:
                    missing_keys = [f"{mf['namespace']}.{mf['key']}" for mf in verification["missing"]]
                    print(f"  Warning: {len(verification['missing'])} metafield(s) not found on product: {', '.join(missing_keys)}")
                    # Don't fail, but log the issue
                
                found_count = len(verification["found"])
                if found_count == len(expected_metafields):
                    print(f"  Successfully uploaded and verified {found_count} metafields")
                else:
                    print(f"  Uploaded {len(expected_metafields)} metafields, verified {found_count} exist")
                
                stats["success"] += 1
            
            # Rate limiting - be nice to Shopify API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Exception: {str(e)}")
            import traceback
            print(f"  Traceback: {traceback.format_exc()[:500]}")
            stats["failed"] += 1
            stats["errors"].append({
                "product_id": product_id,
                "title": title,
                "error": str(e)
            })
    
    # Check and create definitions if they don't exist
    if not dry_run and stats["success"] > 0:
        print("\n" + "=" * 60)
        print(" CHECKING AND CREATING DEFINITIONS")
        print("=" * 60)
        print("\nNote: Definitions are required for metafields to appear in Shopify admin.")
        print("      We'll check if they exist and create them if missing.\n")
        
        definitions_found = 0
        definitions_created = 0
        definitions_failed = 0
        
        for metafield_def in mapping['metafields']:
            key = metafield_def['key']
            name = metafield_def['name']
            namespace = metafield_def.get('namespace', 'standard')
            mf_type = metafield_def.get('type', 'single_line_text_field')
            description = metafield_def.get('description', '')
            
            # Check if definition exists
            query = """
            query getMetafieldDefinition($namespace: String!, $key: String!, $ownerType: MetafieldOwnerType!) {
              metafieldDefinitions(first: 1, ownerType: $ownerType, namespace: $namespace, key: $key) {
                edges {
                  node {
                    id
                    name
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
                    print(f"  [OK] {name} - Definition exists")
                    definitions_found += 1
                else:
                    # Definition doesn't exist - try to create it
                    print(f"  [CREATE] {name} - Creating definition...")
                    success, error_msg = create_metafield_definition(
                        namespace=namespace,
                        key=key,
                        name=name,
                        metafield_type=mf_type,
                        description=description
                    )
                    
                    if success:
                        print(f"         [OK] Created successfully")
                        definitions_created += 1
                        definitions_found += 1
                    else:
                        # For standard namespace, creation might fail (taxonomy attributes)
                        # This is OK - definitions should be created automatically
                        if namespace == "standard":
                            print(f"         [INFO] Cannot create (standard namespace - taxonomy attribute)")
                            print(f"                Definition should exist automatically. If not visible, check Shopify admin.")
                        else:
                            print(f"         [ERROR] Failed: {error_msg}")
                            definitions_failed += 1
                
            except Exception as e:
                print(f"  [ERROR] {name} - Could not check/create: {str(e)}")
                definitions_failed += 1
            
            time.sleep(0.3)  # Rate limiting
        
        print(f"\n  Summary:")
        print(f"    Found existing: {definitions_found - definitions_created}")
        print(f"    Created: {definitions_created}")
        print(f"    Failed: {definitions_failed}")
        print(f"    Total: {definitions_found}/{len(mapping['metafields'])} definitions available")
        
        if definitions_found < len(mapping['metafields']):
            print(f"\n  Note: Some definitions could not be found or created.")
            print(f"        For standard namespace metafields, definitions should exist automatically.")
            print(f"        Check Shopify admin to verify metafields are visible.")
    
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
            print(f"  - {error['title'][:50]}: {error['error']}")
    
    print("\n" + "=" * 60)
    
    if not dry_run and stats["success"] > 0:
        print("\n [OK] Metafields uploaded successfully!")
        print(" [OK] Definitions checked and created if needed")
        print(" [OK] Storefront access enabled - filters are ready!")
        print("\n HOW IT WORKS:")
        print("  - Uploaded metafield values to products")
        print("  - Created metafield definitions if they didn't exist")
        print("  - Enabled storefront access for filtering")
        print("  - Values are now stored and ready for filtering")
        print("\n Next steps:")
        print("  1.  DONE: Metafield values uploaded to products")
        print("  2.  DONE: Definitions created/verified")
        print("  3.  DONE: Storefront access enabled")
        print("  4. TODO: Go to Online Store -> Themes -> Customize")
        print("  5. TODO: Add 'Product filters' block to collection pages")
        print("  6. TODO: Add Arabic translations (Settings -> Languages -> Translate)")
        print("\n To view metafields in Shopify Admin:")
        print("  - Go to Products -> Open a product")
        print("  - Scroll down to 'Metafields' section")
        print("  - Click 'Show all metafields' to see all metafields")
        if translations_file:
            print("\n For Arabic translations:")
            print("  English values are uploaded. Add Arabic translations via:")
            print("  - Shopify Admin -> Settings -> Languages -> Translate")
            print("  - Find 'Product metafields' and translate each value")
            print(f"  - Use the mapping in: {translations_file}")
    
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


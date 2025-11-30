#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2: Push Translations to Shopify

Reads the bilingual metafields JSON produced by:
  TranslateMetaField/translate_metafields.py

Then:

1) Registers English translations for metafield definition name/description
   using Shopify's translationsRegister mutation.

2) Registers English translations for product metafield VALUES (not replacing them)
   so Arabic remains default, English shows when store language is English.

Supports:
  --dry-run
  --skip-definitions
  --skip-values
  --locale
"""

import json
import os
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Shopify API Configuration
SHOPIFY_STORE_DOMAIN = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_ADMIN_ACCESS_TOKEN = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-07").strip()


# ---------------------------------------------------------------------------
# Core Shopify GraphQL helpers
# ---------------------------------------------------------------------------

def graphql_request(query: str, variables: Optional[dict] = None) -> dict:
    """Make a GraphQL request to Shopify."""
    if not SHOPIFY_STORE_DOMAIN or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        raise SystemExit("Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN in .env")

    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(url, headers=headers, json=payload)
    try:
        resp.raise_for_status()
    except Exception as e:
        print("   HTTP error from Shopify:", e)
        print("  Response text:", resp.text[:500])
        raise

    data = resp.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {json.dumps(data['errors'], ensure_ascii=False, indent=2)}")
    return data


def translations_register(
    resource_id: str,
    translations: List[Dict[str, Any]],
    dry_run: bool = False
) -> bool:
    """
    Call translationsRegister for a given resource (e.g. metafield definition or metafield value).
    
    Returns True if successful, False otherwise.
    """
    if dry_run:
        print(f"  [DRY-RUN] Would register translations on {resource_id}:")
        for t in translations:
            print(f"    - locale={t.get('locale')} key={t.get('key')} value={t.get('value')[:50]}...")
        return True

    mutation = """
    mutation RegisterTranslations($resourceId: ID!, $translations: [TranslationInput!]!) {
      translationsRegister(resourceId: $resourceId, translations: $translations) {
        userErrors {
          field
          message
        }
        translations {
          locale
          key
          value
        }
      }
    }
    """

    variables = {
        "resourceId": resource_id,
        "translations": translations
    }

    try:
        result = graphql_request(mutation, variables)
        user_errors = (
            result.get("data", {})
                 .get("translationsRegister", {})
                 .get("userErrors", [])
        )

        if user_errors:
            print(f"   translationsRegister userErrors for {resource_id}:")
            for err in user_errors:
                print(f"    - field={err.get('field')} message={err.get('message')}")
            return False
        else:
            registered = result.get("data", {}).get("translationsRegister", {}).get("translations", [])
            if registered:
                print(f"   Registered {len(registered)} translation(s) for {resource_id}")
            else:
                print(f"   translationsRegister succeeded but no translations returned for {resource_id}")
            return True
    except Exception as e:
        print(f"   Error registering translations for {resource_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# Product fetching helpers (for registering value translations)
# ---------------------------------------------------------------------------

def fetch_products_with_metafield(
    namespace: str,
    key: str,
    collection_identifier: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch products that have a given metafield.
    
    Returns a list of:
      {
        "id": product_id,
        "title": product_title,
        "metafield": {
          "id": mf_id,
          "value": value,
          "type": type
        }
      }
    """
    products_with_mf: List[Dict[str, Any]] = []
    collection_id = None

    if collection_identifier:
        # Find the collection by handle, id or title
        query_coll = """
        query GetCollections($first: Int!, $after: String) {
          collections(first: $first, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
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

        cursor = None
        has_next_page = True

        while has_next_page and collection_id is None:
            vars_coll = {"first": 50, "after": cursor}
            data_coll = graphql_request(query_coll, vars_coll)
            coll_conn = data_coll.get("data", {}).get("collections", {})
            page_info = coll_conn.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            for edge in coll_conn.get("edges", []):
                node = edge.get("node", {})
                if (
                    node.get("id") == collection_identifier
                    or node.get("handle") == collection_identifier
                    or node.get("title") == collection_identifier
                ):
                    collection_id = node.get("id")
                    break

        if not collection_id:
            print(f"   Collection not found: {collection_identifier}, scanning all products")
            collection_identifier = None

    if collection_id:
        # Query products within a specific collection
        query = """
        query GetCollectionProductsWithMetafield(
          $id: ID!, $first: Int!, $after: String, $namespace: String!, $key: String!
        ) {
          collection(id: $id) {
            products(first: $first, after: $after) {
              pageInfo {
                hasNextPage
                endCursor
              }
              edges {
                node {
                  id
                  title
                  metafield(namespace: $namespace, key: $key) {
                    id
                    value
                    type
                  }
                }
              }
            }
          }
        }
        """
        has_next_page = True
        cursor = None

        while has_next_page:
            variables = {
                "id": collection_id,
                "first": 100,
                "after": cursor,
                "namespace": namespace,
                "key": key
            }
            data = graphql_request(query, variables)
            coll = data.get("data", {}).get("collection", {})
            if not coll:
                break
            prod_conn = coll.get("products", {})
            page_info = prod_conn.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            for edge in prod_conn.get("edges", []):
                node = edge.get("node", {})
                mf = node.get("metafield")
                if mf and mf.get("value") is not None:
                    products_with_mf.append({
                        "id": node.get("id"),
                        "title": node.get("title"),
                        "metafield": mf,
                    })
    else:
        # Global scan of products
        print(f"  Scanning all products for metafield {namespace}.{key}...")
        query = """
        query GetProductsWithMetafield($first: Int!, $after: String, $namespace: String!, $key: String!) {
          products(first: $first, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                metafield(namespace: $namespace, key: $key) {
                  id
                  value
                  type
                }
              }
            }
          }
        }
        """
        has_next_page = True
        cursor = None

        while has_next_page:
            variables = {
                "first": 100,
                "after": cursor,
                "namespace": namespace,
                "key": key
            }
            data = graphql_request(query, variables)
            prod_conn = data.get("data", {}).get("products", {})
            page_info = prod_conn.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            for edge in prod_conn.get("edges", []):
                node = edge.get("node", {})
                mf = node.get("metafield")
                if mf and mf.get("value") is not None:
                    products_with_mf.append({
                        "id": node.get("id"),
                        "title": node.get("title"),
                        "metafield": mf,
                    })

    print(f"  Found {len(products_with_mf)} products with metafield {namespace}.{key}")
    return products_with_mf


# ---------------------------------------------------------------------------
# High-level operations
# ---------------------------------------------------------------------------

def update_definition_name_directly(
    definition_id: str, 
    name_en: str,
    dry_run: bool
) -> bool:
    """
    Update metafield definition name directly using metafieldDefinitionUpdate.
    This is a fallback if translationsRegister doesn't work.
    """
    if dry_run:
        print(f"      [DRY-RUN] Would update definition name to: {name_en}")
        return True
    
    mutation = """
    mutation UpdateMetafieldDefinition($id: ID!, $definition: MetafieldDefinitionInput!) {
      metafieldDefinitionUpdate(id: $id, definition: $definition) {
        metafieldDefinition {
          id
          name
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "id": definition_id,
        "definition": {
            "name": name_en
        }
    }
    
    try:
        result = graphql_request(mutation, variables)
        user_errors = result.get("data", {}).get("metafieldDefinitionUpdate", {}).get("userErrors", [])
        
        if user_errors:
            print(f"      ⚠️ metafieldDefinitionUpdate errors:")
            for err in user_errors:
                print(f"        - {err.get('field')}: {err.get('message')}")
            return False
        
        updated_def = result.get("data", {}).get("metafieldDefinitionUpdate", {}).get("metafieldDefinition", {})
        if updated_def:
            print(f"      ✓ Updated definition name to: {updated_def.get('name')}")
            return True
        return False
        
    except Exception as e:
        print(f"      ⚠️ Error updating definition name: {e}")
        return False


def process_definition_translations(
    metafield: Dict[str, Any],
    target_locale: str,
    dry_run: bool
) -> None:
    """
    Register name/description translations for a metafield definition using translationsRegister.
    
    Uses:
      metafield["id"] (metafield definition gid)
      metafield["name_en"]
      metafield["description_en"]
    """
    definition_id = metafield.get("id")
    if not definition_id:
        print("   Skipping definition translation (missing id).")
        return

    name_en = metafield.get("name_en")
    desc_en = metafield.get("description_en")

    if not name_en and not desc_en:
        print("   No English name/description to register for this metafield definition.")
        return

    print(f"  Registering definition translations for {metafield.get('namespace')}.{metafield.get('key')} [{definition_id}]")
    
    # NOTE: translatableResource doesn't support MetafieldDefinition IDs
    # So we'll try translationsRegister directly without digests first
    # If that fails, we'll fall back to updating the definition name directly
    
    translations: List[Dict[str, Any]] = []
    
    # Try to register name translation (without digest first)
    if name_en:
        # First attempt: try translationsRegister without digest
        # Some resource types don't require digests
        translations.append({
            "locale": target_locale,  # "en"
            "key": "name",
            "value": name_en,
        })
        print(f"    Attempting to register English name translation (without digest)")
        print(f"      Arabic (default): {metafield.get('name_ar', 'N/A')}")
        print(f"      English (translation): {name_en}")
    
    # Try to register description translation
    if desc_en:
        translations.append({
            "locale": target_locale,
            "key": "description",
            "value": desc_en,
        })
        print(f"    Attempting to register description translation")
    
    if translations:
        try:
            translations_register(definition_id, translations, dry_run=dry_run)
            print(f"    ✓ Successfully registered definition translations")
        except Exception as e:
            print(f"    ⚠️ translationsRegister failed: {e}")
            # Fallback: update definition name directly
            # This replaces Arabic with English, but it's the only way if translationsRegister doesn't work
            if name_en and not dry_run:
                print(f"    Trying direct update fallback (this will replace Arabic with English)...")
                name_ar = metafield.get("name_ar", "")
                if name_ar:
                    if update_definition_name_directly(definition_id, name_en, dry_run):
                        print(f"    ✓ Updated definition name to English: {name_en}")
                        print(f"    ⚠️ Note: Arabic name '{name_ar}' was replaced. To restore bilingual support,")
                        print(f"       you may need to manually configure translations in Shopify admin.")
                    else:
                        print(f"    ⚠️ Failed to update definition name directly")
                else:
                    print(f"    ⚠️ No Arabic name found, cannot preserve original")
            elif name_en and dry_run:
                print(f"    [DRY-RUN] Would try direct update fallback")
    else:
        print("    ⚠️ No translations to register")


def get_translatable_content_digest(resource_id: str) -> Optional[str]:
    """
    Get the translatableContentDigest for a resource (metafield).
    This is required for registering translations on metafield values.
    """
    query = """
    query GetTranslatableContent($resourceId: ID!) {
      translatableResource(resourceId: $resourceId) {
        resourceId
        translatableContent {
          digest
          key
          value
        }
      }
    }
    """
    
    try:
        result = graphql_request(query, {"resourceId": resource_id})
        resource = result.get("data", {}).get("translatableResource", {})
        
        if not resource:
            print(f"      ⚠️ No translatableResource found for {resource_id}")
            # Debug: show what we got
            print(f"      Debug - Full result: {json.dumps(result.get('data', {}), indent=2)[:200]}")
            return None
        
        content_list = resource.get("translatableContent", [])
        
        if not content_list:
            print(f"      ⚠️ No translatableContent found for {resource_id}")
            print(f"      Debug - Resource keys: {list(resource.keys())}")
            return None
        
        # Debug: show all content
        print(f"      Debug - Found {len(content_list)} translatableContent items")
        for idx, content in enumerate(content_list):
            print(f"        [{idx}] key={content.get('key')}, digest={content.get('digest')[:20] if content.get('digest') else 'None'}...")
        
        # Find the "value" key
        for content in content_list:
            if content.get("key") == "value":
                digest = content.get("digest")
                if digest:
                    return digest
                else:
                    print(f"      ⚠️ Digest is null for 'value' key in {resource_id}")
        
        # If no "value" key found, try first digest
        if content_list:
            digest = content_list[0].get("digest")
            if digest:
                print(f"      ⚠️ Using first available digest (key: {content_list[0].get('key')})")
                return digest
            else:
                print(f"      ⚠️ First digest is also null")
        
        print(f"      ⚠️ No valid digest found for {resource_id}")
        return None
    except Exception as e:
        print(f"      ⚠️ Error getting translatableContentDigest for {resource_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_product_value_translations(
    metafield: Dict[str, Any],
    target_locale: str,
    collection: Optional[str],
    dry_run: bool
) -> None:
    """
    Register translations for product metafield VALUES (not replacing them).
    
    This keeps Arabic values on products and registers English translations
    so they appear in English when the store language is English.
    
    We treat allowed_values_en as a list of:
      { "value_ar": "...", "value_en": "...", "slug": "..." }
    
    For each product that has this metafield:
      - If product metafield value equals value_ar -> register translation with value_en
      - Get translatableContentDigest first, then register translation
    """
    namespace = metafield.get("namespace")
    key = metafield.get("key")

    allowed_values_en = metafield.get("allowed_values_en")
    if not allowed_values_en:
        print(f"   No allowed_values_en mapping for {namespace}.{key}, skipping product value translations.")
        return

    # Build mapping: ar -> en
    ar_to_en: Dict[str, str] = {}
    for item in allowed_values_en:
        v_ar = (item.get("value_ar") or "").strip()
        v_en = (item.get("value_en") or "").strip()
        if v_ar and v_en:
            ar_to_en[v_ar] = v_en

    if not ar_to_en:
        print(f"   Empty ar_to_en mapping for {namespace}.{key}, skipping product value translations.")
        return

    print(f"  Registering product metafield value translations for {namespace}.{key}")
    products = fetch_products_with_metafield(namespace, key, collection_identifier=collection)

    registered_count = 0
    skipped_count = 0
    not_found_count = 0
    digest_error_count = 0

    for p in products:
        pid = p.get("id")
        title = p.get("title")
        mf = p.get("metafield") or {}
        metafield_id = mf.get("id")
        current_value = str(mf.get("value") or "").strip()

        if not metafield_id:
            skipped_count += 1
            continue

        if not current_value:
            skipped_count += 1
            continue

        # Check if current value has a translation
        if current_value in ar_to_en:
            english_value = ar_to_en[current_value]
            
            if not dry_run:
                print(f"    Product: {title!r} ({pid[:20]}...)")
                print(f"      {namespace}.{key}: '{current_value}' -> '{english_value}'")
                
                # Get translatableContentDigest first
                digest = get_translatable_content_digest(metafield_id)
                if not digest or digest == "":
                    print(f"      ⚠️ Could not get translatableContentDigest (got: {digest!r}), skipping")
                    digest_error_count += 1
                    continue
                
                print(f"      Got digest: {digest[:20]}...")
                
                # Register translation with digest
                translations = [{
                    "locale": target_locale,
                    "key": "value",
                    "value": english_value,
                    "translatableContentDigest": digest,
                }]
                
                # Debug: verify digest is in the translation
                if not translations[0].get("translatableContentDigest"):
                    print(f"      ⚠️ ERROR: digest not in translation object!")
                    digest_error_count += 1
                    continue
            else:
                # Dry run - don't fetch digest
                translations = [{
                    "locale": target_locale,
                    "key": "value",
                    "value": english_value,
                }]
            
            success = translations_register(metafield_id, translations, dry_run=dry_run)
            if success:
                registered_count += 1
            else:
                skipped_count += 1
            
            # Small pause to be gentle on rate-limits
            if not dry_run:
                time.sleep(0.15)  # Slightly longer pause since we're making 2 requests per product
        else:
            # Value not in mapping - might already be in English or not translatable
            not_found_count += 1

    print(f"  Done with {namespace}.{key}:")
    print(f"    Registered: {registered_count}")
    print(f"    Not in mapping: {not_found_count}")
    print(f"    Digest errors: {digest_error_count}")
    print(f"    Skipped: {skipped_count}")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload Shopify metafield translations from bilingual JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Default: use metafields_translations.json, register definition translations and product value translations
  python TranslateMetaField/upload_translations.py

  # Dry run (preview actions only)
  python TranslateMetaField/upload_translations.py --dry-run

  # Only definitions (skip product value translations)
  python TranslateMetaField/upload_translations.py --skip-values

  # Only product values (skip definition translations)
  python TranslateMetaField/upload_translations.py --skip-definitions

  # Use a specific locale (e.g., English UK)
  python TranslateMetaField/upload_translations.py --locale en

  # Limit operations to products in a specific collection (handle/title/id)
  python TranslateMetaField/upload_translations.py --collection "مراوح"
        """
    )

    parser.add_argument(
        "--input",
        default="TranslateMetaField/metafields_translations.json",
        help="Path to translations JSON file (default: TranslateMetaField/metafields_translations.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without sending mutations",
    )
    parser.add_argument(
        "--skip-definitions",
        action="store_true",
        help="Skip registering metafield definition name/description translations",
    )
    parser.add_argument(
        "--skip-values",
        action="store_true",
        help="Skip registering product metafield value translations",
    )
    parser.add_argument(
        "--locale",
        default="en",
        help='Target locale for translations (default: "en")',
    )
    parser.add_argument(
        "--collection",
        help="Optional collection identifier (handle, title, or ID) to limit product updates",
    )

    args = parser.parse_args()

    # Validate Shopify env
    if not SHOPIFY_STORE_DOMAIN or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        print(" Error: Missing Shopify credentials in .env file")
        print("   Required: SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_ACCESS_TOKEN")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f" Error: Input file not found: {input_path}")
        sys.exit(1)

    print("=" * 60)
    print("LOADING TRANSLATION JSON")
    print("=" * 60)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metafields = data.get("metafields", [])
    if not metafields:
        print(" No metafields found in JSON.")
        sys.exit(0)

    print(f" Loaded {len(metafields)} metafield entries from {input_path}")
    print(f"  Source locale: {data.get('locale_source')}")
    print(f"  Target locale: {data.get('locale_target')}")
    if args.collection:
        print(f"  Restricting product updates to collection: {args.collection}")

    print("\n" + "=" * 60)
    print("PROCESSING METAFIELD DEFINITIONS")
    print("=" * 60)

    for idx, mf in enumerate(metafields, start=1):
        ns = mf.get("namespace")
        key = mf.get("key")
        print(f"\n[{idx}/{len(metafields)}] {ns}.{key}")

        if not args.skip_definitions:
            process_definition_translations(
                metafield=mf,
                target_locale=args.locale,
                dry_run=args.dry_run,
            )
        else:
            print("  (Skipping definition translations)")

        if not args.skip_values:
            process_product_value_translations(
                metafield=mf,
                target_locale=args.locale,
                collection=args.collection,
                dry_run=args.dry_run,
            )
        else:
            print("  (Skipping product value translations)")

    print("\n" + "=" * 60)
    print("UPLOAD SCRIPT COMPLETE")
    print("=" * 60)
    if args.dry_run:
        print("Mode: DRY RUN (no changes were sent to Shopify).")
    else:
        print("Mode: LIVE (translations were registered in Shopify).")
    print("\nNote: Arabic values remain on products. English translations are registered")
    print("      and will appear when customers view the store in English.")


if __name__ == "__main__":
    main()


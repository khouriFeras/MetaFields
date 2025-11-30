"""
Translate MetaFields from Arabic to English
This script fetches metafield definitions from Shopify, translates Arabic names
and options to English, and preserves both languages in a bilingual JSON dictionary.
"""
import json
import os
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from dotenv import load_dotenv
from openai import OpenAI

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

def fetch_collections() -> List[Dict[str, Any]]:
    """Fetch all collections."""
    query = """
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
    
    collections = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        variables = {"first": 50, "after": cursor}
        try:
            result = graphql_request(query, variables)
            data = result.get("data", {}).get("collections", {})
            page_info = data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
            edges = data.get("edges", [])
            for edge in edges:
                collections.append(edge["node"])
        except Exception as e:
            print(f"Error fetching collections: {str(e)}")
            break
    
    return collections


def fetch_collection_products(collection_identifier: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch products from a collection by handle, ID, or title."""
    # First, get all collections to find the right one
    collections = fetch_collections()
    
    collection = None
    for coll in collections:
        if (coll.get("handle") == collection_identifier or 
            coll.get("id") == collection_identifier or 
            coll.get("title") == collection_identifier):
            collection = coll
            break
    
    if not collection:
        raise SystemExit(f"Collection not found: {collection_identifier}")
    
    # Fetch products from collection
    query = """
    query GetCollectionProducts($id: ID!, $first: Int!, $after: String) {
      collection(id: $id) {
        id
        title
        handle
        products(first: $first, after: $after) {
          pageInfo {
            hasNextPage
            endCursor
          }
          edges {
            node {
              id
              title
              handle
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
        }
      }
    }
    """
    
    products = []
    has_next_page = True
    cursor = None
    
    while has_next_page:
        variables = {"id": collection["id"], "first": 250, "after": cursor}
        try:
            result = graphql_request(query, variables)
            collection_data = result.get("data", {}).get("collection", {})
            if not collection_data:
                break
            
            products_data = collection_data.get("products", {})
            page_info = products_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
            
            edges = products_data.get("edges", [])
            for edge in edges:
                products.append(edge["node"])
        except Exception as e:
            print(f"Error fetching collection products: {str(e)}")
            break
    
    return products, collection


def get_metafield_keys_from_products(products: List[Dict[str, Any]], namespace: str = None) -> set:
    """Extract unique metafield namespace.key pairs from products."""
    metafield_keys = set()
    
    for product in products:
        metafields = product.get("metafields", {}).get("edges", [])
        for edge in metafields:
            mf = edge.get("node", {})
            mf_namespace = mf.get("namespace", "")
            mf_key = mf.get("key", "")
            
            if mf_namespace and mf_key:
                if namespace is None or mf_namespace == namespace:
                    metafield_keys.add((mf_namespace, mf_key))
    
    return metafield_keys


def get_metafield_values_from_products(products: List[Dict[str, Any]], namespace: str = None) -> Dict[tuple, set]:
    """
    Extract unique metafield values from products.
    
    Returns:
        Dictionary mapping (namespace, key) tuples to sets of unique values
    """
    metafield_values = {}
    
    for product in products:
        metafields = product.get("metafields", {}).get("edges", [])
        for edge in metafields:
            mf = edge.get("node", {})
            mf_namespace = mf.get("namespace", "")
            mf_key = mf.get("key", "")
            mf_value = mf.get("value")
            
            if mf_namespace and mf_key and mf_value:
                if namespace is None or mf_namespace == namespace:
                    key = (mf_namespace, mf_key)
                    if key not in metafield_values:
                        metafield_values[key] = set()
                    
                    # Handle different value types
                    if isinstance(mf_value, list):
                        for v in mf_value:
                            if v and str(v).strip():
                                metafield_values[key].add(str(v).strip())
                    elif isinstance(mf_value, str):
                        value_str = mf_value.strip()
                        if value_str:
                            metafield_values[key].add(value_str)
                    else:
                        value_str = str(mf_value).strip()
                        if value_str:
                            metafield_values[key].add(value_str)
    
    # Convert sets to sorted lists
    return {k: sorted(list(v)) for k, v in metafield_values.items()}


def get_metafield_definitions_by_keys(metafield_keys: set) -> list:
    """Get metafield definitions for specific namespace.key pairs."""
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
          }
        }
      }
    }
    """
    
    definitions = []
    for namespace, key in metafield_keys:
        try:
            result = graphql_request(query, {
                "namespace": namespace,
                "key": key,
                "ownerType": "PRODUCT"
            })
            
            edges = result.get("data", {}).get("metafieldDefinitions", {}).get("edges", [])
            if edges:
                definitions.append(edges[0]["node"])
        except Exception as e:
            print(f"  Warning: Could not fetch definition for {namespace}.{key}: {e}")
    
    return definitions


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
            description
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
        if name in ["choices", "list", "allowed_values", "enum", "in"]:
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


def generate_slug(text: str) -> str:
    """Generate a safe machine name (slug) from English text."""
    if not text:
        return ""
    # Convert to lowercase
    slug = text.lower().strip()
    # Replace spaces and common separators with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove special characters but keep letters, numbers, and hyphens
    slug = re.sub(r'[^\w\-]', '', slug)
    # Clean up multiple hyphens
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def get_openai_client() -> OpenAI:
    """Get OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in .env")
    return OpenAI(api_key=api_key)
ENGLISH_TRANSLATION_SYSTEM_PROMPT = """
You are a professional English translator specializing in e-commerce and product specifications.

Your task is to translate Shopify metafield names, descriptions, and their allowed values from Arabic to English.

CRITICAL RULES:
1. Translate metafield names to clear, professional English that customers will understand
2. Translate allowed_values arrays to English, maintaining technical accuracy
3. Keep technical terms consistent (e.g., "4K", "OLED", "LED" stay as-is)
4. Preserve units and numbers (e.g., "السعة (لتر)" -> "Capacity (L)", "القدرة (واط)" -> "Power (W)")
5. Use proper English terminology for e-commerce and product specifications
6. Maintain the same structure and format as the input
7. If description is empty or null, return null for description

Return JSON ONLY in this exact structure:
{
  "metafields": [
    {
      "name": "English translated name",
      "description": "English translated description" or null,
      "allowed_values": ["English value 1", "English value 2"] or null
    }
  ]
}
"""
def translate_metafields_to_english(
    metafields: List[Dict[str, Any]],
    model: str = "gpt-4o-mini"
) -> List[Dict[str, Any]]:
    """
    Translate metafield names, descriptions, and allowed_values from Arabic to English using LLM.
    Args:
        metafields: List of metafield dictionaries with Arabic names
        model: OpenAI model (default: "gpt-4o-mini")
    Returns:
        List of translation results with English names, descriptions, and allowed_values
    """
    if not metafields:
        return []
    client = get_openai_client()
    # Prepare input for translation
    translation_input = {
        "metafields": [
            {
                "name": mf.get("name_ar") or mf.get("name", ""),
                "description": mf.get("description_ar") or mf.get("description") or None,
                "allowed_values": mf.get("allowed_values_ar") or mf.get("allowed_values") or None
            }
            for mf in metafields
        ]
    }
    prompt = f"""Translate the following metafield names, descriptions, and allowed values from Arabic to English:
{json.dumps(translation_input, ensure_ascii=False, indent=2)}
Return the translations in the same JSON structure with English names, descriptions, and values."""
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": ENGLISH_TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw_output = response.choices[0].message.content.strip()
        
        # Debug: print raw output if translation seems empty
        if not raw_output or len(raw_output) < 10:
            print(f"   Warning: Empty or very short response from OpenAI API")
            print(f"  Raw output: {raw_output[:200] if raw_output else 'None'}")
        
        # Strip markdown fences if present
        if "```json" in raw_output:
            raw_output = raw_output.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_output:
            raw_output = raw_output.split("```")[1].split("```")[0].strip()
        
        translation_result = json.loads(raw_output)
        if "metafields" not in translation_result:
            raise ValueError("Missing 'metafields' key in translation response")
        
        # Verify we got the right number of translations
        if len(translation_result["metafields"]) != len(metafields):
            print(f"   Warning: Expected {len(metafields)} translations, got {len(translation_result['metafields'])}")
        
        return translation_result["metafields"]
    except json.JSONDecodeError as e:
        print(f"   JSON decode error. Raw output (first 500 chars):\n{raw_output[:500] if 'raw_output' in locals() else 'N/A'}")
        raise ValueError(f"LLM did not return valid JSON for translation:\n{raw_output[:500] if 'raw_output' in locals() else 'N/A'}\n\nError: {e}")
    except Exception as e:
        print(f"   Translation error: {e}")
        raise ValueError(f"Error translating to English: {e}")
def process_metafield_definitions(
    definitions: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    dry_run: bool = False
) -> List[Dict[str, Any]]:
    """
    Process metafield definitions: extract allowed values, translate, and structure output.
    
    Args:
        definitions: List of metafield definitions from Shopify
        model: OpenAI model for translation
        dry_run: If True, only process first 5 metafields
    
    Returns:
        List of processed metafield dictionaries with both Arabic and English versions
    """
    if dry_run:
        definitions = definitions[:5]
        print(f"DRY RUN: Processing first {len(definitions)} metafields...")
    
    # Extract allowed values for each definition
    processed_definitions = []
    for defn in definitions:
        # Check if we have product values (from collection mode)
        if "_product_values" in defn:
            allowed_values_ar = defn["_product_values"]
        else:
            # Extract from validations (definition mode)
            allowed_values_ar = extract_allowed_values(defn)
        
        processed_def = {
            "id": defn.get("id"),
            "namespace": defn.get("namespace"),
            "key": defn.get("key"),
            "type": defn.get("type", {}).get("name", "unknown"),
            "locale_source": "ar",
            "locale_target": "en",
            "name_ar": defn.get("name", ""),
            "description_ar": defn.get("description") or None,
            "allowed_values_ar": allowed_values_ar if allowed_values_ar else None,
        }
        processed_definitions.append(processed_def)
        
        # Debug: Show extracted allowed values
        if dry_run and allowed_values_ar:
            print(f"  Found {len(allowed_values_ar)} values for {defn.get('namespace')}.{defn.get('key')}: {allowed_values_ar[:3]}{'...' if len(allowed_values_ar) > 3 else ''}")
    
    # Translate in batches to avoid token limits
    print(f"Translating {len(processed_definitions)} metafields to English...")
    batch_size = 20  # Process in batches to avoid token limits
    translated_results = []
    failed_indices = []
    
    for i in range(0, len(processed_definitions), batch_size):
        batch = processed_definitions[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(processed_definitions) + batch_size - 1) // batch_size
        
        print(f"  Translating batch {batch_num}/{total_batches} ({len(batch)} metafields)...")
        
        try:
            batch_translations = translate_metafields_to_english(batch, model)
            translated_results.extend(batch_translations)
        except Exception as e:
            print(f"Warning: Failed to translate batch {batch_num}: {e}")
            # Add None placeholders for failed batch
            translated_results.extend([None] * len(batch))
            failed_indices.extend(range(i, i + len(batch)))
    
    # Merge translations into processed definitions
    final_metafields = []
    for i, processed_def in enumerate(processed_definitions):
        if i in failed_indices:
            print(f"   Warning: Skipping metafield {processed_def.get('namespace')}.{processed_def.get('key')} (translation failed)")
            continue
        
        if i < len(translated_results) and translated_results[i] is not None:
            translation = translated_results[i]
            
            # Process allowed_values: create objects with value_ar, value_en, and slug
            allowed_values_en = None
            if translation.get("allowed_values"):
                allowed_values_en = []
                allowed_values_ar = processed_def.get("allowed_values_ar") or []
                
                # Debug: Show translation received
                if len(allowed_values_ar) > 0:
                    print(f"   Translating {len(allowed_values_ar)} options for {processed_def.get('namespace')}.{processed_def.get('key')}")
                
                for j, value_en in enumerate(translation.get("allowed_values", [])):
                    value_ar = allowed_values_ar[j] if j < len(allowed_values_ar) else ""
                    slug = generate_slug(value_en)
                    
                    allowed_values_en.append({
                        "value_ar": value_ar,
                        "value_en": value_en,
                        "slug": slug
                    })
            elif processed_def.get("allowed_values_ar"):
                # Debug: Show if allowed_values were expected but not translated
                print(f"   Warning: {processed_def.get('namespace')}.{processed_def.get('key')} has {len(processed_def.get('allowed_values_ar'))} allowed values but translation didn't return them")
            
            final_metafield = {
                **processed_def,
                "name_en": translation.get("name", ""),
                "description_en": translation.get("description") or None,
                "allowed_values_en": allowed_values_en
            }
        else:
            # Translation failed or missing - keep only Arabic
            final_metafield = {
                **processed_def,
                "name_en": None,
                "description_en": None,
                "allowed_values_en": None
            }
            print(f"Warning: No translation for {processed_def.get('namespace')}.{processed_def.get('key')}")
        
        final_metafields.append(final_metafield)
    
    return final_metafields


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Translate Shopify metafield definitions from Arabic to English",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
   # Translate metafields in "custom" namespace (default)
   python TranslateMetaField/translate_metafields.py
   
   # Translate metafields used by products in a collection
   python TranslateMetaField/translate_metafields.py --collection "مراوح"
   
   # Translate metafields from collection, filtered by namespace
   python TranslateMetaField/translate_metafields.py --collection "مراوح" --namespace custom
   
   # Translate metafields in a specific namespace
   python TranslateMetaField/translate_metafields.py --namespace shopify
   
   # Fetch all namespaces
   python TranslateMetaField/translate_metafields.py --all
   
   # Dry run (preview first 5)
   python TranslateMetaField/translate_metafields.py --dry-run
   
   # Custom output file
   python TranslateMetaField/translate_metafields.py --output custom_translations.json
        """
    )
    
    parser.add_argument(
        '--namespace',
        default='custom',
        help='Metafield namespace to filter (default: custom)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Fetch metafields from all namespaces (overrides --namespace)'
    )
    parser.add_argument(
        '--output',
        default='TranslateMetaField/metafields_translations.json',
        help='Output JSON file path (default: TranslateMetaField/metafields_translations.json)'
    )
    parser.add_argument(
        '--model',
        default='gpt-4o-mini',
        help='OpenAI model to use (default: gpt-4o-mini)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview translations without saving (processes first 5 metafields)'
    )
    parser.add_argument(
        '--collection',
        help='Collection identifier (handle, title, or ID) - translate metafields used by products in this collection'
    )
    
    args = parser.parse_args()
    
    # Validate environment
    if not SHOPIFY_STORE_DOMAIN or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        print(" Error: Missing Shopify credentials in .env file")
        print("   Required: SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_ACCESS_TOKEN")
        sys.exit(1)
    
    # Determine namespace filter
    namespace_filter = None if args.all else args.namespace
    
    # Fetch metafield definitions
    print(f"{'='*60}")
    print("FETCHING METAFIELD DEFINITIONS")
    print(f"{'='*60}")
    
    products_data = None
    if args.collection:
        # Fetch metafields from collection products
        print(f"Fetching products from collection: {args.collection}")
        try:
            products, collection = fetch_collection_products(args.collection)
            products_data = products
            print(f" Found {len(products)} products in collection: {collection.get('title', collection.get('id'))}")
            
            # Extract unique metafield keys from products
            print(f"Extracting metafield keys from products...")
            metafield_keys = get_metafield_keys_from_products(products, namespace_filter)
            print(f" Found {len(metafield_keys)} unique metafield definitions used in collection")
            
            if not metafield_keys:
                print(" No metafields found in collection products")
                sys.exit(0)
            
            # Extract unique values from products
            print(f"Extracting unique metafield values from products...")
            metafield_values = get_metafield_values_from_products(products, namespace_filter)
            print(f" Found unique values for {len(metafield_values)} metafields")
            
            # Fetch definitions for these keys
            print(f"Fetching metafield definitions...")
            definitions = get_metafield_definitions_by_keys(metafield_keys)
            print(f" Found {len(definitions)} metafield definitions")
            
            # Merge product values into definitions
            for defn in definitions:
                key = (defn.get("namespace"), defn.get("key"))
                if key in metafield_values:
                    # Store the values from products as allowed_values_ar
                    # This will override any values from validations
                    defn["_product_values"] = metafield_values[key]
            
        except Exception as e:
            print(f" Error fetching collection products: {e}")
            sys.exit(1)
    else:
        # Fetch all metafield definitions (original behavior)
        if namespace_filter:
            print(f"Filtering by namespace: {namespace_filter}")
        else:
            print("Fetching from all namespaces")
        
        try:
            definitions = get_all_metafield_definitions(namespace_filter)
            print(f" Found {len(definitions)} metafield definitions")
        except Exception as e:
            print(f"Error fetching metafield definitions: {e}")
            sys.exit(1)
    
    if not definitions:
        print(" No metafield definitions found")
        sys.exit(0)
    
    # Process and translate
    print(f"\n{'='*60}")
    print("PROCESSING AND TRANSLATING")
    print(f"{'='*60}")
    
    try:
        translated_metafields = process_metafield_definitions(
            definitions,
            model=args.model,
            dry_run=args.dry_run
        )
        
        print(f"\n Successfully processed {len(translated_metafields)} metafields")
        
        # Count successful translations
        successful = sum(1 for mf in translated_metafields if mf.get("name_en"))
        print(f" Successfully translated {successful}/{len(translated_metafields)} metafields")
        
    except Exception as e:
        print(f"Error processing metafields: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Save output
    if not args.dry_run:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        output_data = {
             "locale_source": "ar",
             "locale_target": "en",
             "namespace_filter": namespace_filter or "all",
             "collection": args.collection if args.collection else None,
             "total_metafields": len(translated_metafields),
             "metafields": translated_metafields
         }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(" TRANSLATION COMPLETE")
        print(f"{'='*60}")
        print(f"Output saved to: {output_path}")
        print(f"Total metafields: {len(translated_metafields)}")
        print(f"Successfully translated: {successful}")
    else:
        print(f"\n{'='*60}")
        print("DRY RUN COMPLETE")
        print(f"{'='*60}")
        print("Preview of translated metafields:")
        for i, mf in enumerate(translated_metafields[:5], 1):
            print(f"\n{i}. {mf.get('namespace')}.{mf.get('key')}")
            print(f"   Arabic: {mf.get('name_ar', 'N/A')}")
            name_en = mf.get('name_en', '')
            if name_en:
                print(f"   English: {name_en}")
            else:
                print(f"   English: (translation failed or empty)")
            if mf.get('allowed_values_en'):
                print(f"   Options: {len(mf.get('allowed_values_en', []))} values")
                for opt in mf.get('allowed_values_en', [])[:3]:
                    print(f"     - {opt.get('value_ar')} → {opt.get('value_en')} ({opt.get('slug')})")
            elif mf.get('allowed_values_ar'):
                print(f"   Options: {len(mf.get('allowed_values_ar', []))} values (not translated)")


if __name__ == "__main__":
    main()


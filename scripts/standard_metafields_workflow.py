#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standard Metafields Workflow
1. Fetches products from Shopify
2. Automatically matches to Shopify categories using AI
3. Gets metafields from Shopify taxonomy
4. Asks user if they want to add more metafields (LLM-generated)
5. Translates all metafields to Arabic
6. Fills metafields with values
7. Creates Excel output
"""
import json
import os
import sys
import argparse
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fetch_products import (
    fetch_products_by_tag, 
    fetch_collection_products, 
    fetch_all_products
)
from scripts.generate_basic_metafields import (
    generate_collection_metafields,
    translate_metafields_to_arabic
)
from scripts.fill_category_metafields import fill_metafields_parallel
from scripts.create_metafields_excel import create_excel_report

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def load_json(file_path: str) -> Any:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: str, data: Any) -> None:
    """Save JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_taxonomy() -> Dict:
    """Load Shopify taxonomy data."""
    taxonomy_file = Path("data/shopify_taxonomy_full.json")
    if not taxonomy_file.exists():
        raise SystemExit("Taxonomy file not found. Please run: python scripts/fetch_shopify_taxonomy.py")
    
    return load_json(str(taxonomy_file))


def match_category_using_llm(products: List[Dict], taxonomy: Dict) -> Optional[Dict]:
    """
    Use LLM to match products to a Shopify category.
    Returns the best matching category with its metafields.
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Sample a few products to understand the collection
    sample_products = products[:min(5, len(products))]
    sample_text = "\n".join([
        f"- {p.get('title', 'N/A')} ({p.get('productType', 'N/A')})"
        for p in sample_products
    ])
    
    # Get list of common categories (leaf categories with attributes, prioritize those)
    all_cats = taxonomy.get("all_categories", [])
    categories_with_attrs = [
        cat for cat in all_cats
        if cat.get("isLeaf") and cat.get("attributes")
    ]
    
    # Also include some popular categories without attributes
    categories_without_attrs = [
        cat for cat in all_cats
        if cat.get("isLeaf") and not cat.get("attributes")
    ][:50]
    
    # Combine and limit to 150 categories for the prompt
    candidate_categories = (categories_with_attrs[:100] + categories_without_attrs[:50])[:150]
    
    categories_list = "\n".join([
        f"- {cat.get('fullName', cat.get('name', ''))}"
        for cat in candidate_categories
    ])
    
    prompt = f"""You are matching products to Shopify's product taxonomy categories.

Sample products:
{sample_text}

Available Shopify categories:
{categories_list}

Find the BEST matching Shopify category for these products. Return ONLY the full category path (e.g., "Home & Garden > Household Appliances > Water Heaters").

If no good match exists, return "CUSTOM"."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": "You are an expert at matching products to Shopify's product taxonomy. Return only the category path or 'CUSTOM'. Do not include any explanation."},
                {"role": "user", "content": prompt},
            ],
        )
        
        category_path = response.choices[0].message.content.strip()
        
        # Clean up the response (remove quotes, extra text)
        if '"' in category_path:
            category_path = category_path.split('"')[1]
        if category_path.startswith("Category:"):
            category_path = category_path.replace("Category:", "").strip()
        
        if category_path.upper() == "CUSTOM" or not category_path:
            return None
        
        # Find the category in taxonomy (try fullName first, then name)
        for cat in all_cats:
            if cat.get("fullName") == category_path:
                return cat
            if cat.get("name") == category_path:
                return cat
        
        # Try partial match
        for cat in all_cats:
            if category_path in cat.get("fullName", "") or cat.get("fullName", "").endswith(category_path):
                return cat
        
        print(f"⚠️ Category '{category_path}' not found in taxonomy")
        return None
        
    except Exception as e:
        print(f"⚠️ Error matching category: {e}")
        return None


def normalize_value_to_allowed(value: Any, metafield: Dict) -> Any:
    """
    Normalize a value to match one of the allowed_values from the metafield definition.
    Returns the exact allowed value if found, otherwise returns the original value.
    """
    if value is None:
        return None
    
    allowed_values = metafield.get("allowed_values") or metafield.get("values", [])
    if not allowed_values:
        # No allowed values, return as-is
        return value
    
    # Convert to string for comparison
    value_str = str(value).strip()
    if not value_str:
        return None
    
    # Try exact match first
    for allowed in allowed_values:
        if str(allowed).strip() == value_str:
            return allowed
    
    # Try case-insensitive match
    value_lower = value_str.lower()
    for allowed in allowed_values:
        if str(allowed).lower().strip() == value_lower:
            return allowed
    
    # Try partial match (contains)
    for allowed in allowed_values:
        allowed_str = str(allowed).lower()
        if value_lower in allowed_str or allowed_str in value_lower:
            # Only match if reasonable length
            if len(value_lower) >= 2 and len(allowed_str) >= 2:
                return allowed
    
    # Try with normalized spaces and special chars
    normalized_value = re.sub(r'[_\-\s]+', ' ', value_lower).strip()
    for allowed in allowed_values:
        normalized_allowed = re.sub(r'[_\-\s]+', ' ', str(allowed).lower()).strip()
        if normalized_value == normalized_allowed:
            return allowed
        if normalized_value in normalized_allowed or normalized_allowed in normalized_value:
            if len(normalized_value) >= 2:
                return allowed
    
    # If no match found, return original value
    return value


def normalize_product_metafields(product: Dict, metafield_definitions: List[Dict]) -> Dict:
    """
    Normalize all metafield values in a product to match allowed_values.
    """
    product_copy = product.copy()
    metafields = product_copy.get("category_metafields", {})
    
    if not metafields:
        return product_copy
    
    normalized_metafields = {}
    for key, value in metafields.items():
        # Find the metafield definition
        mf_def = None
        for mf in metafield_definitions:
            if mf.get("key") == key:
                mf_def = mf
                break
        
        if not mf_def:
            normalized_metafields[key] = value
            continue
        
        # Normalize the value
        if isinstance(value, list):
            normalized_list = []
            for item in value:
                normalized_item = normalize_value_to_allowed(item, mf_def)
                if normalized_item is not None:
                    normalized_list.append(normalized_item)
            normalized_metafields[key] = normalized_list if normalized_list else None
        else:
            normalized_metafields[key] = normalize_value_to_allowed(value, mf_def)
    
    product_copy["category_metafields"] = normalized_metafields
    return product_copy


def get_metafields_from_category(category: Dict) -> List[Dict]:
    """Extract metafield definitions from a Shopify taxonomy category."""
    metafields = []
    attributes = category.get("attributes", [])
    
    # Load attribute details from YAML file
    attributes_file = Path("data/shopify_attributes.yml")
    attr_details = {}
    if attributes_file.exists():
        with open(attributes_file, 'r', encoding='utf-8') as f:
            attr_data = yaml.safe_load(f) or {}
            base_attrs = attr_data.get("base_attributes", [])
            for attr in base_attrs:
                handle = attr.get("handle", "").replace("_", "-")
                attr_details[handle] = attr
    
    # Load values from YAML file
    values_file = Path("data/shopify_values.yml")
    value_map = {}
    if values_file.exists():
        with open(values_file, 'r', encoding='utf-8') as f:
            values_data = yaml.safe_load(f) or []
            for val in values_data:
                friendly_id = val.get("friendly_id", "")
                if "__" in friendly_id:
                    attr_handle = friendly_id.split("__")[0].replace("_", "-")
                    if attr_handle not in value_map:
                        value_map[attr_handle] = []
                    value_map[attr_handle].append(val.get("name", ""))
    
    for attr in attributes:
        handle = attr.get("handle", "").replace("_", "-")
        attr_info = attr_details.get(handle, {})
        
        # Determine type
        mf_type = attr_info.get("type", "single_line_text_field")
        if not mf_type or mf_type == "text":
            # Check if it has values - if yes, it's a list type
            if handle in value_map or attr.get("values"):
                mf_type = "list.single_line_text_field"
            else:
                mf_type = "single_line_text_field"
        
        mf = {
            "namespace": "standard",
            "key": handle,
            "name": attr.get("name", ""),
            "type": mf_type,
            "description": attr.get("description", "") or attr_info.get("description", ""),
        }
        
        # Add values if available
        if handle in value_map:
            mf["values"] = value_map[handle]
            mf["allowed_values"] = value_map[handle]
        elif attr.get("values"):
            mf["values"] = [v.get("name", "") if isinstance(v, dict) else str(v) for v in attr.get("values", [])]
            mf["allowed_values"] = mf["values"]
        
        metafields.append(mf)
    
    return metafields


def ask_for_more_metafields(existing_metafields: List[Dict], category_name: str) -> List[Dict]:
    """Ask user if they want to add more metafields - either via LLM or manually."""
    print(f"\n{'='*60}")
    print("CURRENT METAFIELDS")
    print(f"{'='*60}")
    if existing_metafields:
        for i, mf in enumerate(existing_metafields, 1):
            mf_name = mf.get('name', 'Unknown')
            mf_key = mf.get('key', 'unknown')
            mf_type = mf.get('type', 'unknown')
            print(f"{i}. {mf_name} ({mf_key}) - {mf_type}")
            # Show allowed values if present
            allowed = mf.get('allowed_values') or mf.get('values', [])
            if allowed and len(allowed) > 0:
                values_preview = ", ".join(str(v) for v in allowed[:5])
                if len(allowed) > 5:
                    values_preview += f" (and {len(allowed) - 5} more)"
                print(f"   Values: {values_preview}")
        print(f"\nTotal: {len(existing_metafields)} metafields")
    else:
        print("No metafields found.")
    
    print(f"\n{'='*60}")
    print("ADD MORE METAFIELDS")
    print(f"{'='*60}")
    print("Options:")
    print("  1. Let LLM generate additional metafields automatically")
    print("  2. Manually specify metafields to add")
    print("  3. Skip (use current metafields)")
    
    response = input("\nEnter your choice (1/2/3): ").strip()
    
    if response == '3' or response.lower() == 'n' or response.lower() == 'skip':
        print("  Skipping additional metafields.")
        return []
    
    new_metafields = []
    
    if response == '1' or response.lower() == 'y' or response.lower() == 'yes':
        # LLM generation
        print("\nGenerating additional metafields using LLM...")
        try:
            additional_result = generate_collection_metafields(category_name)
            additional_metafields = additional_result.get("metafields", [])
            
            # Filter out duplicates
            existing_keys = {mf.get("key") for mf in existing_metafields}
            new_metafields = [
                mf for mf in additional_metafields
                if mf.get("key") not in existing_keys
            ]
            
            if new_metafields:
                print(f"\n✓ Generated {len(new_metafields)} additional metafields:")
                for i, mf in enumerate(new_metafields, 1):
                    print(f"  {i}. {mf.get('name', 'Unknown')} ({mf.get('key', 'unknown')})")
            else:
                print("  No new metafields generated (all duplicates)")
                
        except Exception as e:
            print(f"⚠️ Error generating additional metafields: {e}")
    
    elif response == '2' or response.lower() == 'm' or response.lower() == 'manual':
        # Manual specification
        print("\nManual Metafield Addition")
        print("Enter metafields one by one. For each metafield, provide:")
        print("  - Name (e.g., 'Power (W)')")
        print("  - Key (e.g., 'power-watts') - will be auto-generated if not provided")
        print("  - Type (single_line_text_field, number_integer, number_decimal, list.single_line_text_field)")
        print("  - Allowed values (comma-separated, or press Enter for none)")
        print("\nType 'done' when finished, or 'cancel' to skip.")
        
        existing_keys = {mf.get("key") for mf in existing_metafields}
        
        while True:
            print(f"\n{'─'*60}")
            name = input("Metafield name (or 'done'/'cancel'): ").strip()
            
            if name.lower() == 'done':
                break
            if name.lower() == 'cancel':
                new_metafields = []
                break
            
            if not name:
                print("  Name is required. Skipping...")
                continue
            
            # Auto-generate key from name
            key_input = input(f"Key (press Enter to auto-generate from '{name}'): ").strip()
            if not key_input:
                # Auto-generate key: lowercase, replace spaces with hyphens, remove special chars
                # Handle Arabic characters by transliterating or using a fallback
                key = name.lower().strip()
                # Replace spaces and common separators with hyphens
                key = re.sub(r'[\s_]+', '-', key)
                # Remove special characters but keep Arabic/Latin letters and numbers
                key = re.sub(r'[^\w\-]', '', key)
                # Clean up multiple hyphens
                key = re.sub(r'-+', '-', key).strip('-')
                
                # If key is still empty or only special chars, use a fallback
                if not key or len(key) < 2:
                    # Create a simple key from first few characters
                    key = ''.join(c for c in name.lower() if c.isalnum())[:20]
                    if not key:
                        key = f"metafield-{len(existing_keys) + 1}"
            else:
                key = key_input.replace('_', '-').replace(' ', '-').lower()
                # Clean the key
                key = re.sub(r'[^\w\-]', '', key)
                key = re.sub(r'-+', '-', key).strip('-')
            
            # Validate key is not empty
            if not key or len(key.strip()) < 1:
                print(f"  ⚠️ Could not generate valid key. Please provide a key manually.")
                key_input = input("Key (required): ").strip()
                if not key_input:
                    print("  Skipping this metafield (key is required)")
                    continue
                key = key_input.replace('_', '-').replace(' ', '-').lower()
                key = re.sub(r'[^\w\-]', '', key).strip('-')
            
            # Check for duplicates
            if key in existing_keys:
                print(f"  ⚠️ Key '{key}' already exists. Please use a different key.")
                key_input = input(f"New key (or press Enter to skip): ").strip()
                if not key_input:
                    print("  Skipping this metafield")
                    continue
                key = key_input.replace('_', '-').replace(' ', '-').lower()
                key = re.sub(r'[^\w\-]', '', key).strip('-')
                if key in existing_keys:
                    print(f"  ⚠️ Key still exists. Skipping...")
                    continue
            
            # Get type
            print("\nAvailable types:")
            print("  1. single_line_text_field (text)")
            print("  2. number_integer (whole numbers)")
            print("  3. number_decimal (decimal numbers)")
            print("  4. list.single_line_text_field (dropdown with options)")
            
            type_input = input("Type (1/2/3/4 or type name): ").strip()
            type_map = {
                '1': 'single_line_text_field',
                '2': 'number_integer',
                '3': 'number_decimal',
                '4': 'list.single_line_text_field',
            }
            mf_type = type_map.get(type_input, type_input)
            if mf_type not in ['single_line_text_field', 'number_integer', 'number_decimal', 'list.single_line_text_field']:
                mf_type = 'single_line_text_field'
            
            # Get allowed values if list type
            allowed_values = None
            if mf_type == 'list.single_line_text_field':
                values_input = input("Allowed values (comma-separated, or press Enter for none): ").strip()
                if values_input:
                    allowed_values = [v.strip() for v in values_input.split(',') if v.strip()]
            
            # Validate key
            if not key or len(key.strip()) == 0:
                print(f"  ⚠️ Invalid key generated. Please provide a key manually.")
                continue
            
            # Create metafield
            new_mf = {
                "namespace": "shopify",
                "key": key,
                "name": name,
                "type": mf_type,
                "description": "",
            }
            
            if allowed_values:
                new_mf["allowed_values"] = allowed_values
                new_mf["values"] = allowed_values
            else:
                new_mf["allowed_values"] = None
                new_mf["values"] = []
            
            new_metafields.append(new_mf)
            existing_keys.add(key)
            print(f"  ✓ Added: {name} ({key}) - {mf_type}")
            if allowed_values:
                print(f"    Values: {', '.join(str(v) for v in allowed_values[:5])}")
    
    if new_metafields:
        print(f"\n{'─'*60}")
        print(f"✓ Successfully added {len(new_metafields)} metafield(s):")
        for i, mf in enumerate(new_metafields, 1):
            print(f"  {i}. {mf.get('name')} ({mf.get('key')}) - {mf.get('type')}")
    
    return new_metafields


def main():
    parser = argparse.ArgumentParser(description="Standard Metafields Workflow")
    parser.add_argument("--tag", type=str, help="Fetch products by tag")
    parser.add_argument("--collection", type=str, help="Fetch products by collection")
    parser.add_argument("--products", type=str, help="Use existing products JSON file")
    parser.add_argument("--output", type=str, required=True, help="Output directory path")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip fetching products")
    
    args = parser.parse_args()
    
    # Step 1: Fetch or load products
    if args.products:
        print(f"Loading products from: {args.products}")
        products = load_json(args.products)
    elif args.skip_fetch:
        raise ValueError("Must provide --products file when using --skip-fetch")
    elif args.tag:
        print(f"Fetching products by tag: {args.tag}")
        products = fetch_products_by_tag(args.tag)
    elif args.collection:
        print(f"Fetching products by collection: {args.collection}")
        products = fetch_collection_products(args.collection)
    else:
        print("Fetching all products...")
        products = fetch_all_products()
    
    print(f"✓ Found {len(products)} products")
    
    # Step 2: Match to Shopify category
    print(f"\n{'='*60}")
    print("MATCHING TO SHOPIFY CATEGORY")
    print(f"{'='*60}")
    taxonomy = load_taxonomy()
    category = match_category_using_llm(products, taxonomy)
    
    if not category:
        print("⚠️ Could not match to Shopify category. Using custom metafields...")
        category_name = input("Enter category name for custom metafields: ").strip()
        if not category_name:
            category_name = "Custom Category"
        metafields = []
    else:
        category_name = category.get("fullName") or category.get("name", "Unknown")
        print(f"✓ Matched to category: {category_name}")
        metafields = get_metafields_from_category(category)
        print(f"✓ Found {len(metafields)} metafields from taxonomy")
    
    # Step 3: Generate or get metafields, then ask if they want more
    if not metafields:
        # No metafields from taxonomy - ask if they want to generate some
        print(f"\n{'='*60}")
        print("NO METAFIELDS FROM SHOPIFY TAXONOMY")
        print(f"{'='*60}")
        print(f"Category: {category_name}")
        print("\nNo metafields found in Shopify taxonomy for this category.")
        response = input("\n❓ Do you want to generate metafields using LLM? (y/n): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            print(f"\nGenerating metafields for: {category_name}")
            result = generate_collection_metafields(category_name)
            metafields = result.get("metafields", [])
            print(f"✓ Generated {len(metafields)} metafields")
        else:
            print("  Skipping metafield generation. You can add them manually later.")
            metafields = []
    
    # Now show the metafields (whether from taxonomy or generated) and ask if they want more
    if metafields:
        print(f"\nCurrent metafields before asking for more: {len(metafields)}")
        additional_metafields = ask_for_more_metafields(metafields, category_name)
        if additional_metafields:
            print(f"\nAdding {len(additional_metafields)} manually added metafields:")
            for mf in additional_metafields:
                print(f"  - {mf.get('name', 'Unknown')} ({mf.get('key', 'unknown')})")
            metafields.extend(additional_metafields)
            print(f"✓ Total metafields: {len(metafields)}")
        else:
            print("  No additional metafields added.")
    else:
        # Even if no metafields exist, allow manual addition
        print(f"\nNo existing metafields. You can add them manually.")
        additional_metafields = ask_for_more_metafields([], category_name)
        if additional_metafields:
            print(f"\nAdding {len(additional_metafields)} manually added metafields:")
            for mf in additional_metafields:
                print(f"  - {mf.get('name', 'Unknown')} ({mf.get('key', 'unknown')})")
            metafields.extend(additional_metafields)
            print(f"✓ Total metafields: {len(metafields)}")
    
    # Step 3.5: Validate and clean metafields
    # Remove any metafields with empty keys and ensure required fields
    print(f"\nValidating metafields (before: {len(metafields)})...")
    original_count = len(metafields)
    cleaned_metafields = []
    removed_keys = []
    
    for mf in metafields:
        key = mf.get("key", "").strip() if mf.get("key") else ""
        if not key:
            removed_keys.append(mf.get("name", "Unknown"))
            print(f"  ⚠️ Removing metafield with empty key: {mf.get('name', 'Unknown')}")
            continue
        
        # Ensure required fields exist
        if "values" not in mf:
            mf["values"] = mf.get("allowed_values", []) or []
        if "allowed_values" not in mf:
            mf["allowed_values"] = mf.get("values", []) or None
        
        # Ensure namespace exists
        if "namespace" not in mf:
            mf["namespace"] = "shopify"
        
        cleaned_metafields.append(mf)
    
    metafields = cleaned_metafields
    if len(metafields) < original_count:
        print(f"⚠️ Removed {original_count - len(metafields)} invalid metafields")
        if removed_keys:
            print(f"  Removed keys: {', '.join(removed_keys)}")
    
    if not metafields:
        print("⚠️ ERROR: No valid metafields to process!")
        print("  Please add metafields and try again.")
        sys.exit(1)
    
    print(f"✓ Validated {len(metafields)} metafields ready for filling")
    print(f"  Metafield keys: {[mf.get('key') for mf in metafields]}")
    
    # Step 4: Translate to Arabic
    print(f"\n{'='*60}")
    print("TRANSLATING METAFIELDS TO ARABIC")
    print(f"{'='*60}")
    metafields_before_translation = len(metafields)
    metafield_keys_before = [mf.get("key") for mf in metafields]
    
    try:
        metafields = translate_metafields_to_arabic(metafields)
        metafields_after_translation = len(metafields)
        metafield_keys_after = [mf.get("key") for mf in metafields]
        
        if metafields_before_translation != metafields_after_translation:
            print(f"⚠️ WARNING: Metafield count changed during translation!")
            print(f"  Before: {metafields_before_translation}, After: {metafields_after_translation}")
            missing_keys = set(metafield_keys_before) - set(metafield_keys_after)
            if missing_keys:
                print(f"  Missing keys: {missing_keys}")
        
        print(f"✓ Translated {len(metafields)} metafields to Arabic")
    except Exception as e:
        print(f"⚠️ Warning: Failed to translate to Arabic: {e}")
        print("  Continuing with English names...")
        import traceback
        traceback.print_exc()
    
    # Step 5: Create category mapping
    print(f"\n{'='*60}")
    print("FINAL METAFIELDS SUMMARY")
    print(f"{'='*60}")
    print(f"Total metafields to save: {len(metafields)}")
    for i, mf in enumerate(metafields, 1):
        print(f"  {i}. {mf.get('name', 'Unknown')} ({mf.get('key', 'unknown')}) - {mf.get('type', 'unknown')}")
    print(f"{'='*60}\n")
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    mapping = {
        "tag": args.tag or args.collection or "all",
        "category": {
            "id": category.get("id", "custom") if category else "custom",
            "name": category_name,
            "fullName": category_name,
            "confidence": "ai-matched" if category else "custom",
            "reasoning": "Matched using AI" if category else "Custom category"
        },
        "metafields": metafields
    }
    
    mapping_file = output_dir / "category_mapping.json"
    save_json(str(mapping_file), mapping)
    print(f"✓ Saved category mapping: {mapping_file}")
    print(f"  Contains {len(metafields)} metafields")
    
    # Step 6: Fill metafields
    print(f"\n{'='*60}")
    print("FILLING METAFIELDS")
    print(f"{'='*60}")
    
    if not metafields:
        print("⚠️ WARNING: No metafields to fill! Skipping fill step.")
        filled_products = products
    else:
        print(f"Filling {len(metafields)} metafields for {len(products)} products...")
        print(f"Metafield keys: {[mf.get('key', 'unknown') for mf in metafields]}")
        
        # Verify metafields structure
        for mf in metafields:
            if not mf.get("key"):
                print(f"⚠️ WARNING: Metafield missing key: {mf}")
            if not mf.get("name"):
                print(f"⚠️ WARNING: Metafield missing name: {mf}")
            if not mf.get("type"):
                print(f"⚠️ WARNING: Metafield missing type: {mf}")
        
        try:
            filled_products = fill_metafields_parallel(
                products,
                metafields,
                category_name,
                model="gpt-4o-mini",
                max_workers=3
            )
            
            # Check if any products got filled
            filled_count = sum(1 for p in filled_products if p.get("category_metafields"))
            values_count = sum(
                len([v for v in (p.get("category_metafields", {})).values() if v not in (None, "", [])])
                for p in filled_products
            )
            print(f"\n✓ Fill complete: {filled_count}/{len(products)} products have metafields")
            print(f"✓ Total metafield values filled: {values_count}")
            
        except Exception as e:
            print(f"⚠️ ERROR during metafield filling: {e}")
            import traceback
            traceback.print_exc()
            print("  Using products without filled metafields...")
            filled_products = products
    
    # Step 6.5: Normalize values to match allowed_values
    print(f"\nNormalizing values to match allowed values...")
    normalized_count = 0
    for product in filled_products:
        original_metafields = product.get("category_metafields", {})
        normalized_product = normalize_product_metafields(product, metafields)
        normalized_metafields = normalized_product.get("category_metafields", {})
        
        # Check if any values were normalized
        if original_metafields != normalized_metafields:
            normalized_count += 1
            product["category_metafields"] = normalized_metafields
    
    if normalized_count > 0:
        print(f"✓ Normalized values for {normalized_count} products")
    else:
        print("✓ All values already normalized")
    
    products_file = output_dir / "products_with_metafields.json"
    save_json(str(products_file), filled_products)
    print(f"✓ Saved products with metafields: {products_file}")
    
    # Step 7: Create Excel
    print(f"\n{'='*60}")
    print("CREATING EXCEL REPORT")
    print(f"{'='*60}")
    excel_file = output_dir / "metafields_report.xlsx"
    create_excel_report(filled_products, mapping, str(excel_file))
    
    print(f"\n{'='*60}")
    print("✓ WORKFLOW COMPLETE")
    print(f"{'='*60}")
    print(f"Products: {products_file}")
    print(f"Mapping: {mapping_file}")
    print(f"Excel: {excel_file}")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update category_mapping.json to only include metafields that are actually used in products.
This syncs the mapping file with what's actually in the products after Excel editing.
"""
import json
import sys
from pathlib import Path
from collections import Counter

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def update_mapping_from_products(mapping_file: str, products_file: str, output_file: str = None) -> None:
    """Update mapping file to only include metafields actually used in products."""
    
    print("Updating Category Mapping from Products")
    print("=" * 60)
    
    # Load mapping
    print(f"\nLoading mapping: {mapping_file}")
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    original_metafields = mapping.get('metafields', [])
    print(f"  Original metafields: {len(original_metafields)}")
    
    # Load products
    print(f"\nLoading products: {products_file}")
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"  Products: {len(products)}")
    
    # Find all metafield keys actually used in products
    used_keys = set()
    key_counts = Counter()
    
    for product in products:
        category_metafields = product.get('category_metafields', {})
        for key in category_metafields.keys():
            used_keys.add(key)
            key_counts[key] += 1
    
    print(f"\n  Metafields actually used: {len(used_keys)}")
    for key, count in key_counts.most_common():
        print(f"    • {key}: used in {count} products")
    
    # Filter mapping to only include used metafields
    used_metafields = []
    for mf in original_metafields:
        mf_key = mf.get('key', '')
        if mf_key in used_keys:
            used_metafields.append(mf)
        else:
            print(f"  Removing unused metafield: {mf.get('name', 'Unknown')} ({mf_key})")
    
    # Update mapping
    mapping['metafields'] = used_metafields
    
    # Save updated mapping
    if output_file is None:
        output_file = mapping_file
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print("MAPPING UPDATED")
    print(f"{'='*60}")
    print(f"✓ Updated mapping file: {output_path}")
    print(f"✓ Metafields: {len(original_metafields)} → {len(used_metafields)}")
    print(f"✓ Removed {len(original_metafields) - len(used_metafields)} unused metafields")
    
    if len(used_metafields) != len(used_keys):
        print(f"\n⚠️ Warning: {len(used_keys) - len(used_metafields)} metafield keys in products")
        print(f"   don't have definitions in the mapping file.")
        missing_keys = used_keys - {mf.get('key') for mf in used_metafields}
        print(f"   Missing keys: {', '.join(missing_keys)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update category_mapping.json to match metafields actually used in products",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update mapping to match products
  python scripts/update_mapping_from_products.py \\
    --mapping exports/مراوح_workflow/category_mapping.json \\
    --products exports/مراوح_workflow/products_ready_for_upload.json
  
  # Save to a new file
  python scripts/update_mapping_from_products.py \\
    --mapping exports/مراوح_workflow/category_mapping.json \\
    --products exports/مراوح_workflow/products_ready_for_upload.json \\
    --output exports/مراوح_workflow/category_mapping_updated.json
        """
    )
    
    parser.add_argument('--mapping', required=True, help='Path to category_mapping.json')
    parser.add_argument('--products', required=True, help='Path to products JSON file')
    parser.add_argument('--output', help='Output file path (default: overwrites mapping file)')
    
    args = parser.parse_args()
    
    try:
        update_mapping_from_products(args.mapping, args.products, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



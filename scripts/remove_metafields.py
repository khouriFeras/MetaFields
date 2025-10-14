#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove Specific Metafields from JSON

This script removes specified metafields from all products in a JSON file.
Useful for cleaning up unwanted metafields before uploading.
"""
import json
import argparse
from pathlib import Path
from typing import List


def remove_metafields(json_path: str, output_path: str, metafield_keys: List[str]):
    """Remove specified metafields from all products."""
    print("\nREMOVING METAFIELDS")
    print("=" * 60)
    
    # Load JSON
    print(f"\nLoading JSON: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    print(f"  Loaded {len(products)} products")
    
    # Count removals
    total_removed = 0
    products_affected = 0
    
    # Remove metafields
    for product in products:
        if 'metafields' not in product:
            continue
        
        removed_from_product = 0
        for key in metafield_keys:
            if key in product['metafields']:
                del product['metafields'][key]
                removed_from_product += 1
                total_removed += 1
        
        if removed_from_product > 0:
            products_affected += 1
    
    # Save updated JSON
    print(f"\n💾 Saving updated JSON: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("REMOVAL COMPLETED!")
    print("=" * 60)
    print(f" Total products: {len(products)}")
    print(f" Products affected: {products_affected}")
    print(f"  Total metafields removed: {total_removed}")
    print(f"\n Removed metafield keys:")
    for key in metafield_keys:
        print(f"  • {key}")
    print(f"\n Output: {output_path}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Remove specific metafields from JSON file"
    )
    parser.add_argument(
        "--json",
        required=True,
        help="Path to JSON file"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output JSON file"
    )
    parser.add_argument(
        "--keys",
        required=True,
        nargs='+',
        help="Metafield keys to remove (space-separated)"
    )
    
    args = parser.parse_args()
    
    # Verify file exists
    if not Path(args.json).exists():
        print(f" JSON file not found: {args.json}")
        return
    
    remove_metafields(args.json, args.output, args.keys)


if __name__ == "__main__":
    main()

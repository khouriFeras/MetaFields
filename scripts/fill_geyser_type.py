#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fill geyser_type metafield based on product titles
Products with "فوري" (instant) in title = "instant"
All others (كيزر/storage) = "storage"
"""
import json
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def fill_geyser_type(json_path: str) -> None:
    """Fill geyser_type metafield for all products."""
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    print(f"Reading JSON file: {json_path}")
    
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if "Products" not in data:
        raise ValueError("JSON file does not contain a 'Products' sheet")
    
    products = data["Products"]
    metafield_key = "Metafield: shopify.geyser_type [list.single_line_text_field]"
    
    instant_count = 0
    storage_count = 0
    
    print(f"\nProcessing {len(products)} products...")
    
    for product in products:
        title = product.get("Title", "").lower()
        handle = product.get("Handle", "").lower()
        
        # Check if product title or handle contains "فوري" (instant)
        if "فوري" in title or "فوري" in handle:
            product[metafield_key] = "instant"
            instant_count += 1
        else:
            # Default to storage for all other products
            product[metafield_key] = "storage"
            storage_count += 1
    
    print(f"\n✓ Filled geyser_type values:")
    print(f"  - Instant: {instant_count} products")
    print(f"  - Storage: {storage_count} products")
    
    # Save updated JSON
    print(f"\nSaving updated JSON file: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Successfully updated JSON file")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fill_geyser_type.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    try:
        fill_geyser_type(json_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


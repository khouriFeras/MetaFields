#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
clean_processed_data.py
- Cleans processed product data by removing unnecessary meta fields
- Removes price, user_preferences, and ratings from all products
"""

import json
from pathlib import Path


def clean_processed_data(input_file: str, output_file: str = None) -> None:
    """Clean processed product data by removing unnecessary meta fields."""
    
    # Load processed data
    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"📥 Loaded {len(products)} products")
    
    # Fields to remove from metafields
    fields_to_remove = ['price', 'user_preferences', 'ratings']
    
    # Clean each product's metafields
    cleaned_count = 0
    for product in products:
        if 'metafields' in product:
            original_count = len(product['metafields'])
            
            # Remove unwanted fields
            for field in fields_to_remove:
                product['metafields'].pop(field, None)
            
            new_count = len(product['metafields'])
            if original_count != new_count:
                cleaned_count += 1
    
    # Save cleaned data
    if output_file is None:
        output_file = input_file.replace('.json', '_cleaned.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Cleaned product data:")
    print(f"  - Products processed: {len(products)}")
    print(f"  - Products with removed fields: {cleaned_count}")
    print(f"  - Removed fields: {fields_to_remove}")
    print(f"  - Saved to: {output_file}")
    
    # Show sample of cleaned metafields
    if products:
        sample_product = products[0]
        if 'metafields' in sample_product:
            print(f"\n📋 Sample cleaned metafields:")
            for key, value in sample_product['metafields'].items():
                print(f"  - {key}: {value}")
    
    return output_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean processed product data")
    parser.add_argument('--input-file', required=True, help='Processed product data JSON file')
    parser.add_argument('--output-file', help='Output file for cleaned data')
    
    args = parser.parse_args()
    
    clean_processed_data(args.input_file, args.output_file)

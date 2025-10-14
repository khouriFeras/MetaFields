#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Excel Changes Back to JSON

This script syncs manual changes made in Excel back to the JSON file.
Matches products by Title (since Excel may not have Product IDs).
"""
import json
import argparse
from pathlib import Path
import pandas as pd


def sync_excel_to_json(excel_path: str, json_path: str, output_path: str):
    """Sync Excel changes to JSON file."""
    print("\n SYNCING EXCEL TO JSON")
    print("=" * 60)
    
    # Load Excel
    print(f"\n Loading Excel: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name="Products")
    print(f"   Loaded {len(df)} products from Excel")
    
    # Load JSON
    print(f"\n Loading JSON: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    print(f"   Loaded {len(products)} products from JSON")
    
    # Get metafield columns (exclude product info columns)
    exclude_cols = ['Title', 'Product Type', 'Vendor', 'Price Range', 'Status', 'Product ID']
    metafield_cols = [col for col in df.columns if col not in exclude_cols]
    print(f"\n Found {len(metafield_cols)} metafield columns in Excel")
    
    # Match products by title and update metafields
    matched = 0
    updated = 0
    total_metafields = 0
    
    for idx, row in df.iterrows():
        title = row['Title']
        
        # Find matching product in JSON by title
        product = next((p for p in products if p.get('title') == title), None)
        
        if product:
            matched += 1
            
            # Clear existing metafields
            product['metafields'] = {}
            
            # Add metafields from Excel
            for col in metafield_cols:
                value = row[col]
                
                # Skip empty values
                if pd.isna(value) or value == '' or value == 'N/A':
                    continue
                
                # Handle list values (stored as comma-separated in Excel)
                if isinstance(value, str) and ',' in value:
                    # This might be a list - keep as string for now
                    product['metafields'][col] = value
                else:
                    product['metafields'][col] = value
                
                total_metafields += 1
            
            updated += 1
    
    # Save updated JSON
    print(f"\n Saving updated JSON: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(" SYNC COMPLETED!")
    print("=" * 60)
    print(f" Excel products: {len(df)}")
    print(f" JSON products: {len(products)}")
    print(f" Matched products: {matched}")
    print(f" Updated products: {updated}")
    print(f" Total metafields: {total_metafields}")
    print(f" Output: {output_path}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Excel changes back to JSON file"
    )
    parser.add_argument(
        "--excel",
        required=True,
        help="Path to Excel file"
    )
    parser.add_argument(
        "--json",
        required=True,
        help="Path to original JSON file"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output JSON file"
    )
    
    args = parser.parse_args()
    
    # Verify files exist
    if not Path(args.excel).exists():
        print(f" Excel file not found: {args.excel}")
        return
    
    if not Path(args.json).exists():
        print(f" JSON file not found: {args.json}")
        return
    
    sync_excel_to_json(args.excel, args.json, args.output)


if __name__ == "__main__":
    main()

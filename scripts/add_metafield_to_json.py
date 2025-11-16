#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add a new metafield column to all products in the JSON file
Preserves all existing metafields and adds the new one.
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def add_metafield_to_json(
    json_path: str,
    namespace: str,
    key: str,
    metafield_type: str,
    default_value: str = "",
    update_metafield_definitions: bool = True
) -> None:
    """
    Add a new metafield column to all products in the JSON file.
    
    Args:
        json_path: Path to the JSON file
        namespace: Metafield namespace (e.g., 'shopify')
        key: Metafield key (e.g., 'warranty-period')
        metafield_type: Metafield type (e.g., 'single_line_text_field', 'number_integer', etc.)
        default_value: Default value to set for all products (empty string by default)
        update_metafield_definitions: Whether to add the metafield to the Metafield Definitions sheet
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    print(f"Reading JSON file: {json_path}")
    
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check if Products sheet exists
    if "Products" not in data:
        raise ValueError("JSON file does not contain a 'Products' sheet")
    
    products = data["Products"]
    if not products:
        print("Warning: No products found in the Products sheet")
        return
    
    # Create the metafield column name
    metafield_column = f"Metafield: {namespace}.{key} [{metafield_type}]"
    
    print(f"\nAdding metafield: {metafield_column}")
    print(f"Default value: '{default_value}'")
    
    # Check if metafield already exists
    overwrite = False
    if metafield_column in products[0]:
        print(f"Warning: Metafield column '{metafield_column}' already exists!")
        response = input("Do you want to overwrite existing values? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Cancelled. No changes made.")
            return
        overwrite = True
    
    # Add the metafield to all products
    updated_count = 0
    for product in products:
        if metafield_column not in product:
            product[metafield_column] = default_value
            updated_count += 1
        elif overwrite:
            product[metafield_column] = default_value
            updated_count += 1
    
    print(f"✓ Added metafield to {updated_count} products")
    
    # Update Metafield Definitions if requested
    if update_metafield_definitions and "Metafield Definitions" in data:
        print("\nUpdating Metafield Definitions sheet...")
        definitions = data["Metafield Definitions"]
        
        # Check if definition already exists
        existing_def = None
        for def_item in definitions:
            if (def_item.get("Namespace", "").lower() == namespace.lower() and 
                def_item.get("Key", "").lower() == key.lower()):
                existing_def = def_item
                break
        
        if existing_def:
            print(f"  Metafield definition already exists: {namespace}.{key}")
            print(f"  Current type: {existing_def.get('Type', 'N/A')}")
            if existing_def.get('Type', '') != metafield_type:
                response = input(f"  Update type from '{existing_def.get('Type')}' to '{metafield_type}'? (yes/no): ").strip().lower()
                if response == 'yes':
                    existing_def["Type"] = metafield_type
                    print(f"  ✓ Updated type to {metafield_type}")
        else:
            # Add new definition
            new_def = {
                "Name": key.replace('-', ' ').replace('_', ' ').title(),
                "Key": key,
                "Namespace": namespace,
                "Type": metafield_type,
                "Description": ""
            }
            definitions.append(new_def)
            print(f"  ✓ Added new metafield definition: {namespace}.{key}")
    
    # Save updated JSON
    print(f"\nSaving updated JSON file: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Successfully updated JSON file")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python add_metafield_to_json.py <json_file> <namespace> <key> <type> [default_value]")
        print("\nExample:")
        print('  python add_metafield_to_json.py "exports/كيزر_metafields.json" shopify warranty-period single_line_text_field ""')
        print('  python add_metafield_to_json.py "exports/كيزر_metafields.json" shopify weight number_decimal "0"')
        print("\nCommon metafield types:")
        print("  - single_line_text_field")
        print("  - number_integer")
        print("  - number_decimal")
        print("  - list.single_line_text_field")
        print("  - boolean")
        sys.exit(1)
    
    json_file = sys.argv[1]
    namespace = sys.argv[2]
    key = sys.argv[3]
    metafield_type = sys.argv[4]
    default_value = sys.argv[5] if len(sys.argv) > 5 else ""
    
    try:
        add_metafield_to_json(json_file, namespace, key, metafield_type, default_value)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


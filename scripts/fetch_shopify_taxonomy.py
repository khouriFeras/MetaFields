#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch Shopify's Product Taxonomy
Downloads the taxonomy directly from Shopify's open-source GitHub repository.
Source: https://github.com/Shopify/product-taxonomy
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# GitHub repository URLs
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Shopify/product-taxonomy/main"
TAXONOMY_JSON_URL = f"{GITHUB_RAW_BASE}/dist/en/categories.json"
ATTRIBUTES_JSON_URL = f"{GITHUB_RAW_BASE}/dist/en/attributes.json"
VALUES_JSON_URL = f"{GITHUB_RAW_BASE}/dist/en/values.json"

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def download_json_file(url: str, description: str) -> Dict:
    """Download and parse a JSON file from GitHub."""
    print(f"Downloading {description}...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"Downloaded successfully")
        return data
    except requests.RequestException as e:
        raise SystemExit(f"Failed to download {description}: {e}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Failed to parse {description}: {e}")


def flatten_categories(data: List, parent_categories: List = None) -> List[Dict]:
    """
    Recursively flatten nested category structure.
    
    Args:
        data: Nested category data
        parent_categories: List of parent category names for building full path
        
    Returns:
        Flat list of all categories
    """
    if parent_categories is None:
        parent_categories = []
    
    categories = []
    
    for item in data:
        if isinstance(item, dict):
            # Process this category
            cat_info = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "fullName": item.get("full_name", ""),
                "level": item.get("level", 0),
                "isLeaf": not item.get("children", []),
                "isRoot": item.get("level", 0) == 0,
                "attributes": item.get("attributes", [])
            }
            
            categories.append(cat_info)
            
            # Recursively process children
            children = item.get("children", [])
            if children:
                child_categories = flatten_categories(children, parent_categories + [item.get("name", "")])
                categories.extend(child_categories)
        
        elif isinstance(item, list):
            # If item is a list, recursively process it
            nested_categories = flatten_categories(item, parent_categories)
            categories.extend(nested_categories)
    
    return categories


def process_taxonomy_data(taxonomy_json: Dict, attribute_type_map: Dict[str, Dict]) -> Dict:
    """
    Process categories from GitHub taxonomy.
    
    Args:
        taxonomy_json: Raw taxonomy JSON from GitHub (contains version and verticals)
        attribute_type_map: Mapping of attribute handle to metadata (type, values, description)
        
    Returns:
        Processed categories with metafields
    """
    print(f"\nProcessing taxonomy data...")
    print(f"Taxonomy version: {taxonomy_json.get('version', 'Unknown')}")
    
    verticals = taxonomy_json.get('verticals', [])
    print(f"Processing {len(verticals)} verticals...")
    
    all_categories = []
    
    # Process each vertical
    for vertical in verticals:
        vertical_name = vertical.get('name', 'Unknown')
        categories = vertical.get('categories', [])
        
        # Flatten categories in this vertical
        vertical_categories = flatten_categories(categories)
        all_categories.extend(vertical_categories)
    
    print(f"Processed {len(all_categories)} total categories")
    
    # Separate leaf categories
    leaf_categories = [cat for cat in all_categories if cat["isLeaf"]]
    print(f" Found {len(leaf_categories)} leaf categories (most specific)")
    
    # Process metafields for categories that have attributes
    # Include ALL categories (not just leaf) if they have attributes
    categories_with_metafields = []
    
    for category in all_categories:
        attributes = category.get("attributes", [])
        
        if attributes:
            # Convert attributes to our metafield format
            metafields = []
            for attr in attributes:
                handle = attr.get("handle", "")
                
                # Get the metadata from attribute map
                attr_metadata = attribute_type_map.get(handle, {})
                attr_type = attr_metadata.get("type", "single_line_text_field")
                attr_values = attr_metadata.get("values", [])
                
                metafield = {
                    "id": attr.get("id", ""),
                    "name": attr.get("name", ""),
                    "namespace": "standard",  # Shopify standard attributes
                    "key": handle if handle else attr.get("name", "").lower().replace(" ", "_"),
                    "type": attr_type,  # Use actual type inferred from attributes.json
                    "description": attr.get("description", "") or attr_metadata.get("description", ""),
                    "extended": attr.get("extended", False),
                    "values": [v.get("name") for v in attr_values] if attr_values else []
                }
                metafields.append(metafield)
            
            categories_with_metafields.append({
                "id": category["id"],
                "name": category["name"],
                "fullName": category["fullName"],
                "metafields": metafields
            })
    
    print(f" {len(categories_with_metafields)} categories have metafields")
    
    return {
        "all_categories": all_categories,
        "leaf_categories": leaf_categories,
        "categories_with_metafields": categories_with_metafields,
        "statistics": {
            "total_categories": len(all_categories),
            "leaf_categories": len(leaf_categories),
            "categories_with_metafields": len(categories_with_metafields)
        }
    }


def build_attribute_type_map(attributes_data: Dict) -> Dict[str, Dict]:
    """
    Build a map of attribute handle -> metadata from attributes JSON.
    
    Args:
        attributes_data: Raw attributes JSON from GitHub (contains version and attributes)
        
    Returns:
        Dictionary mapping attribute handle to its metadata (type, values, etc.)
    """
    print("Building attribute type map...")
    
    attributes = attributes_data.get("attributes", [])
    attr_map = {}
    
    for attr in attributes:
        handle = attr.get("handle", "")
        values = attr.get("values", [])
        
        if handle:
            # Infer type based on whether it has predefined values
            if values and len(values) > 0:
                # Has predefined values - use list type
                attr_type = "list.single_line_text_field"
            else:
                # No predefined values - free text
                attr_type = "single_line_text_field"
            
            attr_map[handle] = {
                "type": attr_type,
                "values": values,
                "description": attr.get("description", "")
            }
    
    print(f"Mapped types for {len(attr_map)} attributes")
    return attr_map


def fetch_taxonomy_from_github() -> Dict:
    """
    Fetch taxonomy from Shopify's GitHub repository.
    
    Returns:
        Complete taxonomy with categories and attributes
    """
    print("🔍 Fetching Shopify product taxonomy from GitHub...")
    print(f"   Source: {GITHUB_RAW_BASE}\n")
    
    # Download both files
    taxonomy_json = download_json_file(TAXONOMY_JSON_URL, "categories")
    attributes_json = download_json_file(ATTRIBUTES_JSON_URL, "attributes")
    
    # Build attribute type map
    attribute_type_map = build_attribute_type_map(attributes_json)
    
    # Process the taxonomy with type information
    taxonomy_data = process_taxonomy_data(taxonomy_json, attribute_type_map)
    
    return taxonomy_data


def save_taxonomy(taxonomy_data: Dict, output_dir: str = "data") -> None:
    """Save taxonomy data to JSON files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save full taxonomy with metafields
    full_file = output_path / "shopify_taxonomy_full.json"
    with open(full_file, 'w', encoding='utf-8') as f:
        json.dump(taxonomy_data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved full taxonomy: {full_file}")
    
    # Save simplified category list (for easier searching)
    simple_categories = [
        {
            "id": cat["id"],
            "name": cat["name"],
            "fullName": cat["fullName"]
        }
        for cat in taxonomy_data["categories_with_metafields"]
    ]
    
    simple_file = output_path / "shopify_categories_simple.json"
    with open(simple_file, 'w', encoding='utf-8') as f:
        json.dump(simple_categories, f, ensure_ascii=False, indent=2)
    print(f"Saved simple category list: {simple_file}")
    
    # Save statistics
    stats_file = output_path / "shopify_taxonomy_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(taxonomy_data["statistics"], f, ensure_ascii=False, indent=2)
    print(f"Saved statistics: {stats_file}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fetch Shopify's product taxonomy from GitHub repository",
        epilog="Source: https://github.com/Shopify/product-taxonomy"
    )
    parser.add_argument(
        '--output-dir',
        default='data',
        help='Output directory (default: data)'
    )
    
    args = parser.parse_args()
    
    print("Shopify Taxonomy Fetcher")
    print("Source: Shopify's Open Source Product Taxonomy")
    print(f" {GITHUB_RAW_BASE}\n")
    
    # Fetch taxonomy from GitHub
    taxonomy_data = fetch_taxonomy_from_github()
    
    # Save to files
    save_taxonomy(taxonomy_data, args.output_dir)
    
    # Print summary
    stats = taxonomy_data["statistics"]
    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60)
    print(f"Total categories:                {stats['total_categories']}")
    print(f"Leaf categories:                 {stats['leaf_categories']}")
    print(f"Categories with metafields:      {stats['categories_with_metafields']}")
    print("="*60)
    print("\n Done! Use these files for category matching and metafield population.")
    print(" Files saved to:", Path(args.output_dir).absolute())


if __name__ == "__main__":
    main()


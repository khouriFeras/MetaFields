#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a guide for creating metafield definitions manually in Shopify Admin.
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


def generate_definitions_guide(mapping_file: str, output_file: str = None, products_file: str = None) -> None:
    """Generate a guide for creating metafield definitions."""
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    metafields = mapping.get('metafields', [])
    
    # If products file is provided, filter to only show metafields that are actually used
    used_keys = set()
    if products_file and Path(products_file).exists():
        with open(products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        for product in products:
            category_metafields = product.get('category_metafields', {})
            used_keys.update(category_metafields.keys())
        
        # Filter metafields to only those being used
        if used_keys:
            metafields = [mf for mf in metafields if mf.get('key') in used_keys]
            print(f"Found {len(used_keys)} metafields in use: {', '.join(sorted(used_keys))}")
            print()
    
    print("=" * 60)
    print("METAFIELD DEFINITIONS GUIDE")
    print("=" * 60)
    print("\nCreate these definitions in Shopify Admin:")
    print("Settings → Custom data → Products → Add definition\n")
    
    guide_lines = []
    guide_lines.append("=" * 60)
    guide_lines.append("METAFIELD DEFINITIONS TO CREATE IN SHOPIFY ADMIN")
    guide_lines.append("=" * 60)
    guide_lines.append("\nGo to: Settings → Custom data → Products → Add definition\n")
    guide_lines.append("Create the following definitions:\n")
    
    for i, mf in enumerate(metafields, 1):
        namespace = mf.get('namespace', 'custom')
        if namespace == 'shopify':
            namespace = 'custom'
        
        key = mf.get('key', '')
        name = mf.get('name', '')
        mf_type = mf.get('type', 'single_line_text_field')
        
        # Map type to Shopify admin type
        type_map = {
            'single_line_text_field': 'Single line text',
            'number_integer': 'Number (integer)',
            'number_decimal': 'Number (decimal)',
            'list.single_line_text_field': 'List of single line text',
        }
        admin_type = type_map.get(mf_type, 'Single line text')
        
        print(f"{i}. {name}")
        print(f"   Namespace: {namespace}")
        print(f"   Key: {key}")
        print(f"   Type: {admin_type}")
        print(f"   Full identifier: {namespace}.{key}")
        print()
        
        guide_lines.append(f"{i}. {name}")
        guide_lines.append(f"   Namespace: {namespace}")
        guide_lines.append(f"   Key: {key}")
        guide_lines.append(f"   Type: {admin_type}")
        guide_lines.append(f"   Full identifier: {namespace}.{key}")
        guide_lines.append("")
    
    guide_lines.append("=" * 60)
    guide_lines.append("INSTRUCTIONS:")
    guide_lines.append("=" * 60)
    guide_lines.append("1. Go to Shopify Admin → Settings → Custom data → Products")
    guide_lines.append("2. Click 'Add definition'")
    guide_lines.append("3. For each metafield above:")
    guide_lines.append("   - Enter the Name (display name)")
    guide_lines.append("   - Enter the Namespace and Key exactly as shown")
    guide_lines.append("   - Select the Type")
    guide_lines.append("4. Save each definition")
    guide_lines.append("5. After creating all definitions, the metafield values")
    guide_lines.append("   will appear in your product pages!")
    guide_lines.append("")
    
    # Save to file
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(guide_lines))
        print(f"\n✓ Guide saved to: {output_file}")
    else:
        # Save to default location
        default_output = Path(mapping_file).parent / "metafield_definitions_guide.txt"
        with open(default_output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(guide_lines))
        print(f"\n✓ Guide saved to: {default_output}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate guide for creating metafield definitions manually"
    )
    
    parser.add_argument('--mapping', required=True, help='Path to category_mapping.json')
    parser.add_argument('--products', help='Path to products JSON file (to filter only used metafields)')
    parser.add_argument('--output', help='Output file path (default: same directory as mapping)')
    
    args = parser.parse_args()
    
    try:
        generate_definitions_guide(args.mapping, args.output, args.products)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


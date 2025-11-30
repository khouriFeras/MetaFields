#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Arabic characters in metafield keys by converting them to English equivalents.
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

# Mapping from Arabic keys to English keys
ARABIC_TO_ENGLISH_KEYS = {
    "حجم-المروحة": "fan-size",
    "مستويات-السرعة": "speed-levels",
    "نوع-المروحة": "fan-type",
    "عدد-الشفرات": "blade-count"
}


def fix_mapping_file(mapping_file: str, output_file: str = None) -> None:
    """Fix Arabic keys in mapping file."""
    mapping_path = Path(mapping_file)
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")
    
    if output_file is None:
        output_file = mapping_path.parent / f"{mapping_path.stem}_fixed{mapping_path.suffix}"
    
    print(f"Reading mapping file: {mapping_path}")
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    print(f"Fixing Arabic keys in metafield definitions...")
    updated_count = 0
    
    for mf in mapping.get('metafields', []):
        old_key = mf.get('key', '')
        if old_key in ARABIC_TO_ENGLISH_KEYS:
            new_key = ARABIC_TO_ENGLISH_KEYS[old_key]
            print(f"  {old_key} → {new_key}")
            mf['key'] = new_key
            updated_count += 1
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Updated {updated_count} metafield keys")
    print(f"✓ Saved to: {output_path}")
    
    return output_path


def fix_products_file(products_file: str, mapping_file: str, output_file: str = None) -> None:
    """Fix Arabic keys in products file using the mapping."""
    products_path = Path(products_file)
    mapping_path = Path(mapping_file)
    
    if not products_path.exists():
        raise FileNotFoundError(f"Products file not found: {products_path}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")
    
    if output_file is None:
        output_file = products_path.parent / f"{products_path.stem}_fixed{products_path.suffix}"
    
    print(f"\nReading products file: {products_path}")
    with open(products_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"Reading mapping file: {mapping_path}")
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    # Create key mapping from Arabic to English
    key_mapping = {}
    for mf in mapping.get('metafields', []):
        old_key = mf.get('key', '')
        if old_key in ARABIC_TO_ENGLISH_KEYS:
            new_key = ARABIC_TO_ENGLISH_KEYS[old_key]
            key_mapping[old_key] = new_key
    
    print(f"\nFixing Arabic keys in products...")
    updated_products = 0
    
    for product in products:
        metafields = product.get('category_metafields', {})
        if not metafields:
            continue
        
        # Create new metafields dict with English keys
        new_metafields = {}
        updated = False
        
        for old_key, value in metafields.items():
            if old_key in key_mapping:
                new_key = key_mapping[old_key]
                new_metafields[new_key] = value
                updated = True
            else:
                # Keep keys that don't need fixing
                new_metafields[old_key] = value
        
        if updated:
            product['category_metafields'] = new_metafields
            updated_products += 1
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Updated {updated_products} products")
    print(f"✓ Saved to: {output_path}")
    
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python scripts/fix_arabic_keys.py <mapping_file.json> <products_file.json> [output_mapping.json] [output_products.json]")
        print("\nExample:")
        print("  python scripts/fix_arabic_keys.py \\")
        print("    exports/مراوح_workflow/category_mapping.json \\")
        print("    exports/مراوح_workflow/products_from_excel_with_ids.json")
        sys.exit(1)
    
    mapping_file = sys.argv[1]
    products_file = sys.argv[2]
    output_mapping = sys.argv[3] if len(sys.argv) > 3 else None
    output_products = sys.argv[4] if len(sys.argv) > 4 else None
    
    try:
        # Fix mapping file
        fixed_mapping = fix_mapping_file(mapping_file, output_mapping)
        
        # Fix products file using original mapping (before fix) to get the key mapping
        # Actually, we need to use the fixed mapping, so let's do it differently
        # We'll create the key mapping from the original file
        import json
        with open(mapping_file, 'r', encoding='utf-8') as f:
            original_mapping = json.load(f)
        
        # Create reverse mapping for products fix
        key_mapping = {}
        for mf in original_mapping.get('metafields', []):
            old_key = mf.get('key', '')
            if old_key in ARABIC_TO_ENGLISH_KEYS:
                new_key = ARABIC_TO_ENGLISH_KEYS[old_key]
                key_mapping[old_key] = new_key
        
        # Now fix products
        products_path = Path(products_file)
        if output_products is None:
            output_products = products_path.parent / f"{products_path.stem}_fixed{products_path.suffix}"
        
        print(f"\nReading products file: {products_path}")
        with open(products_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        print(f"\nFixing Arabic keys in products...")
        updated_products = 0
        
        for product in products:
            metafields = product.get('category_metafields', {})
            if not metafields:
                continue
            
            # Create new metafields dict with English keys
            new_metafields = {}
            updated = False
            
            for old_key, value in metafields.items():
                if old_key in key_mapping:
                    new_key = key_mapping[old_key]
                    new_metafields[new_key] = value
                    updated = True
                else:
                    # Keep keys that don't need fixing
                    new_metafields[old_key] = value
            
            if updated:
                product['category_metafields'] = new_metafields
                updated_products += 1
        
        output_products_path = Path(output_products)
        output_products_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_products_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Updated {updated_products} products")
        print(f"✓ Saved to: {output_products_path}")
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Fixed mapping: {fixed_mapping}")
        print(f"  Fixed products: {output_products_path}")
        print(f"\nNext step: Upload with fixed files")
        print(f"  python scripts/upload_metafields.py \\")
        print(f"    --products \"{output_products_path}\" \\")
        print(f"    --mapping \"{fixed_mapping}\"")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)






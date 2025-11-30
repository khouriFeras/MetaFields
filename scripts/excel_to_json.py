#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Excel metafields file to JSON format
Reads an Excel file and converts it to JSON matching the expected format.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def process_products_sheet(df: pd.DataFrame, mapping_file: str = None) -> List[Dict]:
    """
    Process Products sheet and convert to product JSON format with category_metafields.
    Maps metafield columns to category_metafields structure, preserving "NA" values.
    """
    import json
    
    # Load mapping if provided to get metafield keys
    metafield_key_map = {}
    if mapping_file and Path(mapping_file).exists():
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
            for mf in mapping.get('metafields', []):
                # Map Arabic name to key
                mf_name = mf.get('name', '')
                mf_key = mf.get('key', '')
                if mf_name and mf_key:
                    metafield_key_map[mf_name] = mf_key
    
    products = []
    base_columns = ['Handle', 'Title', 'Product Type', 'Vendor', 'Status']
    
    for _, row in df.iterrows():
        product = {}
        
        # Get base fields
        for col in base_columns:
            if col in df.columns:
                value = row[col]
                # Preserve "NA" values
                if isinstance(value, str) and value.strip().upper() == 'NA':
                    product[col.lower().replace(' ', '_')] = 'NA'
                elif pd.isna(value) or value == '':
                    product[col.lower().replace(' ', '_')] = ''
                else:
                    product[col.lower().replace(' ', '_')] = str(value)
        
        # Get metafields (all columns except base columns)
        category_metafields = {}
        for col in df.columns:
            if col not in base_columns:
                value = row[col]
                
                # Preserve "NA" values
                if isinstance(value, str) and value.strip().upper() == 'NA':
                    # Map column name (Arabic name) to metafield key
                    mf_key = metafield_key_map.get(col, col)  # Use mapping or column name as fallback
                    category_metafields[mf_key] = 'NA'
                elif pd.isna(value) or value == '':
                    # Skip empty values
                    pass
                else:
                    # Map column name to metafield key
                    mf_key = metafield_key_map.get(col, col)
                    # Try to parse as JSON if it looks like a list
                    str_value = str(value).strip()
                    if str_value.startswith('[') and str_value.endswith(']'):
                        try:
                            category_metafields[mf_key] = json.loads(str_value)
                        except:
                            category_metafields[mf_key] = str_value
                    else:
                        category_metafields[mf_key] = str_value
        
        if category_metafields:
            product['category_metafields'] = category_metafields
        
        products.append(product)
    
    return products


def excel_to_json(excel_path: str, output_path: str = None, sheet_name: str = None, mapping_file: str = None, process_products: bool = False) -> None:
    """
    Convert Excel file to JSON format.
    Supports multiple sheets - converts all sheets to a single JSON object.
    
    Args:
        excel_path: Path to the Excel file
        output_path: Optional path for output JSON file. If None, uses same name as Excel file.
        sheet_name: Optional sheet name to convert. If None, converts all sheets.
    """
    excel_path = Path(excel_path)
    
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    print(f"Reading Excel file: {excel_path}")
    
    # Open Excel file to get sheet names
    xl_file = pd.ExcelFile(excel_path, engine='openpyxl')
    sheet_names = xl_file.sheet_names
    print(f"Found sheets: {sheet_names}")
    
    # If specific sheet requested, only process that one
    if sheet_name:
        if sheet_name not in sheet_names:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {sheet_names}")
        sheet_names = [sheet_name]
    
    # Convert each sheet
    result = {}
    
    for sheet in sheet_names:
        print(f"\nProcessing sheet: {sheet}")
        df = pd.read_excel(excel_path, sheet_name=sheet, engine='openpyxl')
        
        print(f"  Found {len(df)} rows and {len(df.columns)} columns")
        print(f"  Columns: {list(df.columns)[:10]}...")  # Show first 10 columns
        
        # Preserve "NA" values - replace NaN with empty string, but keep "NA" strings
        # First, convert all values to string to preserve "NA"
        for col in df.columns:
            # Check if column contains "NA" strings
            df[col] = df[col].astype(str)
            # Replace pandas NaN string representation with empty string
            df[col] = df[col].replace('nan', '', regex=False)
            df[col] = df[col].replace('<NA>', '', regex=False)
            df[col] = df[col].replace('NaT', '', regex=False)
            # Keep "NA" as-is (case-insensitive check)
            df[col] = df[col].apply(lambda x: 'NA' if str(x).strip().upper() == 'NA' else x)
        
        # Replace any remaining NaN values with empty string
        df = df.fillna('')
        
        # Convert to list of dictionaries
        data = df.to_dict('records')
        
        # Post-process to ensure "NA" strings are preserved
        for record in data:
            for key, value in record.items():
                # Convert pandas NaN/None to empty string, but preserve "NA"
                if pd.isna(value) or value is None:
                    record[key] = ''
                elif isinstance(value, str) and value.strip().upper() == 'NA':
                    record[key] = 'NA'
                elif isinstance(value, str) and value.strip() == '':
                    record[key] = ''
        
        result[sheet] = data
        
        print(f"  Converted {len(data)} rows")
    
    # Determine output path
    if output_path is None:
        output_path = excel_path.with_suffix('.json')
    else:
        output_path = Path(output_path)
    
    # Write JSON file
    print(f"\nWriting JSON file: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f" Successfully converted all sheets to JSON")
    print(f" Output saved to: {output_path}")


def process_excel_for_upload(excel_path: str, mapping_file: str, output_path: str) -> None:
    """
    Process Excel Products sheet and convert to upload-ready JSON format.
    Maps metafield columns to category_metafields structure using mapping file.
    """
    excel_path = Path(excel_path)
    mapping_path = Path(mapping_file)
    
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")
    
    # Load mapping to get metafield definitions
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    # Create name to key mapping
    metafield_key_map = {}
    for mf in mapping.get('metafields', []):
        mf_name = mf.get('name', '')
        mf_key = mf.get('key', '')
        if mf_name and mf_key:
            metafield_key_map[mf_name] = mf_key
    
    print(f"Reading Excel file: {excel_path}")
    print(f"Using mapping: {mapping_path}")
    
    # Read Products sheet
    df = pd.read_excel(excel_path, sheet_name='Products', engine='openpyxl')
    print(f"Found {len(df)} products")
    
    # Process products
    products = process_products_sheet(df, str(mapping_path))
    
    # Save to JSON
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Processed {len(products)} products")
    print(f"✓ Saved to: {output_path}")
    print(f"\nNext step: Fetch product IDs and upload to Shopify")
    print(f"  python scripts/fetch_products.py collection --title \"مراوح\" --output exports/مراوح_workflow/products_with_ids.json")
    print(f"  Then merge the IDs with this file before uploading")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Convert Excel to JSON:")
        print("    python excel_to_json.py <excel_file> [output_json_file] [sheet_name]")
        print("  Process Excel for upload (requires mapping file):")
        print("    python excel_to_json.py --upload <excel_file> --mapping <mapping_file> --output <output_json>")
        sys.exit(1)
    
    # Check if --upload flag is used
    if '--upload' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--upload', action='store_true')
        parser.add_argument('--excel', '--excel_file', dest='excel_file', required=True)
        parser.add_argument('--mapping', required=True)
        parser.add_argument('--output', required=True)
        args = parser.parse_args()
        
        try:
            process_excel_for_upload(args.excel_file, args.mapping, args.output)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        excel_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        sheet_name = sys.argv[3] if len(sys.argv) > 3 else None
        
        try:
            excel_to_json(excel_file, output_file, sheet_name)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


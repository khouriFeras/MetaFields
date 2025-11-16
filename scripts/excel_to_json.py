#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Excel metafields file to JSON format
Reads an Excel file and converts it to JSON matching the expected format.
"""
import json
import sys
import os
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


def excel_to_json(excel_path: str, output_path: str = None, sheet_name: str = None) -> None:
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
        
        # Replace NaN values with None/empty strings
        df = df.fillna('')
        
        # Convert to list of dictionaries
        data = df.to_dict('records')
        result[sheet] = data
        
        print(f"  ✓ Converted {len(data)} rows")
    
    # Determine output path
    if output_path is None:
        output_path = excel_path.with_suffix('.json')
    else:
        output_path = Path(output_path)
    
    # Write JSON file
    print(f"\nWriting JSON file: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Successfully converted all sheets to JSON")
    print(f"✓ Output saved to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python excel_to_json.py <excel_file> [output_json_file] [sheet_name]")
        print("  If sheet_name is provided, only that sheet will be converted")
        print("  Otherwise, all sheets will be converted to a JSON object with sheet names as keys")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    sheet_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        excel_to_json(excel_file, output_file, sheet_name)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


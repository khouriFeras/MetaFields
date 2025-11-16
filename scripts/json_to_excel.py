#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert JSON file back to Excel format with multiple sheets
Reads a JSON file with sheet structure and converts it back to Excel.
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


def json_to_excel(json_path: str, output_path: str = None) -> None:
    """
    Convert JSON file back to Excel format with multiple sheets.
    
    Args:
        json_path: Path to the JSON file
        output_path: Optional path for output Excel file. If None, uses same name as JSON file.
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    print(f"Reading JSON file: {json_path}")
    
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Determine output path
    if output_path is None:
        output_path = json_path.with_suffix('.xlsx')
    else:
        output_path = Path(output_path)
    
    print(f"Writing Excel file: {output_path}")
    
    # Create Excel writer
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # If data is a dict with sheet names as keys
        if isinstance(data, dict):
            for sheet_name, sheet_data in data.items():
                if isinstance(sheet_data, list) and len(sheet_data) > 0:
                    print(f"  Writing sheet: {sheet_name} ({len(sheet_data)} rows)")
                    df = pd.DataFrame(sheet_data)
                    # Replace empty strings with NaN for cleaner Excel output
                    df = df.replace('', None)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    print(f"  Skipping empty sheet: {sheet_name}")
        # If data is a list, write to single sheet
        elif isinstance(data, list):
            print(f"  Writing single sheet: Sheet1 ({len(data)} rows)")
            df = pd.DataFrame(data)
            df = df.replace('', None)
            df.to_excel(writer, sheet_name='Sheet1', index=False)
        else:
            raise ValueError("JSON structure not recognized. Expected dict with sheet names or list.")
    
    print(f"\n✓ Successfully converted JSON to Excel")
    print(f"✓ Output saved to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_excel.py <json_file> [output_excel_file]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        json_to_excel(json_file, output_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


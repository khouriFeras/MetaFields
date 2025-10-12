#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Excel Report for Category Metafields
Generates a comprehensive Excel file with products and their filled metafields.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def load_json(file_path: str) -> Any:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_summary_sheet(wb: Workbook, products: List[Dict], mapping: Dict) -> None:
    """Create summary sheet with overview information."""
    ws = wb.create_sheet("Summary", 0)
    
    # Header style
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    
    # Title
    ws['A1'] = "Category Metafields Analysis"
    ws['A1'].font = Font(bold=True, size=16)
    ws.merge_cells('A1:D1')
    
    # Category Information
    row = 3
    ws[f'A{row}'] = "CATEGORY INFORMATION"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = header_font
    ws.merge_cells(f'A{row}:B{row}')
    
    row += 1
    category_info = [
        ("Tag:", mapping.get("tag", "N/A")),
        ("Shopify Category:", mapping["category"]["fullName"]),
        ("Category ID:", mapping["category"]["id"]),
        ("Confidence:", mapping["category"]["confidence"].upper()),
        ("Reasoning:", mapping["category"]["reasoning"]),
    ]
    
    for label, value in category_info:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = value
        row += 1
    
    # Products Statistics
    row += 1
    ws[f'A{row}'] = "PRODUCTS STATISTICS"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = header_font
    ws.merge_cells(f'A{row}:B{row}')
    
    row += 1
    total_products = len(products)
    products_with_metafields = sum(1 for p in products if p.get("category_metafields"))
    
    products_stats = [
        ("Total Products:", total_products),
        ("Products with Metafields:", products_with_metafields),
        ("Coverage:", f"{(products_with_metafields/total_products*100):.1f}%"),
    ]
    
    for label, value in products_stats:
        ws[f'A{row}'] = label
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'] = value
        row += 1
    
    # Top Vendors
    row += 1
    ws[f'A{row}'] = "TOP VENDORS"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = header_font
    ws.merge_cells(f'A{row}:B{row}')
    
    row += 1
    vendors = [p.get('vendor', 'Unknown') for p in products]
    top_vendors = Counter(vendors).most_common(10)
    
    for vendor, count in top_vendors:
        ws[f'A{row}'] = vendor
        ws[f'B{row}'] = count
        row += 1
    
    # Metafields Statistics
    row += 1
    ws[f'A{row}'] = "METAFIELDS STATISTICS"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'A{row}'].fill = header_fill
    ws[f'A{row}'].font = header_font
    ws.merge_cells(f'A{row}:B{row}')
    
    row += 1
    ws[f'A{row}'] = "Metafield"
    ws[f'B{row}'] = "Filled Count"
    ws[f'C{row}'] = "Coverage %"
    for col in ['A', 'B', 'C']:
        ws[f'{col}{row}'].font = Font(bold=True)
        ws[f'{col}{row}'].fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    
    row += 1
    metafield_stats = {}
    for mf in mapping["metafields"]:
        key = mf["key"]
        filled_count = sum(
            1 for p in products 
            if p.get("category_metafields", {}).get(key) is not None
        )
        metafield_stats[mf["name"]] = {
            "filled": filled_count,
            "percentage": (filled_count / total_products * 100) if total_products > 0 else 0
        }
    
    for metafield_name, stats in sorted(metafield_stats.items(), key=lambda x: x[1]["filled"], reverse=True):
        ws[f'A{row}'] = metafield_name
        ws[f'B{row}'] = stats["filled"]
        ws[f'C{row}'] = f"{stats['percentage']:.1f}%"
        row += 1
    
    # Auto-adjust column widths
    for col in ['A', 'B', 'C', 'D']:
        ws.column_dimensions[col].width = 40


def create_products_sheet(wb: Workbook, products: List[Dict], mapping: Dict) -> None:
    """Create products sheet with all products and their metafields."""
    ws = wb.create_sheet("Products", 1)
    
    # Header style
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Define columns
    base_columns = [
        "Title",
        "Product Type",
        "Vendor",
        "Price Range",
        "Status"
    ]
    
    # Add metafield columns
    metafield_columns = [mf["name"] for mf in mapping["metafields"]]
    all_columns = base_columns + metafield_columns
    
    # Write headers
    for col_idx, header in enumerate(all_columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
    
    # Write product data
    for row_idx, product in enumerate(products, 2):
        # Base data
        ws.cell(row=row_idx, column=1, value=product.get('title', ''))
        ws.cell(row=row_idx, column=2, value=product.get('productType', ''))
        ws.cell(row=row_idx, column=3, value=product.get('vendor', ''))
        ws.cell(row=row_idx, column=4, value=product.get('priceRange', ''))
        ws.cell(row=row_idx, column=5, value=product.get('status', ''))
        
        # Metafield data
        category_metafields = product.get('category_metafields', {})
        for col_idx, mf in enumerate(mapping["metafields"], len(base_columns) + 1):
            value = category_metafields.get(mf["key"])
            
            # Format value based on type
            if value is None:
                display_value = ""
            elif isinstance(value, list):
                display_value = ", ".join(str(v) for v in value)
            elif isinstance(value, dict):
                display_value = json.dumps(value)
            else:
                display_value = str(value)
            
            cell = ws.cell(row=row_idx, column=col_idx, value=display_value)
            
            # Highlight empty metafields
            if not display_value:
                cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    
    # Auto-adjust column widths
    for col_idx in range(1, len(all_columns) + 1):
        column_letter = get_column_letter(col_idx)
        max_length = 0
        
        for row_idx in range(1, len(products) + 2):
            cell_value = ws.cell(row=row_idx, column=col_idx).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))
        
        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
    
    # Freeze first row
    ws.freeze_panes = "A2"


def create_metafields_sheet(wb: Workbook, mapping: Dict) -> None:
    """Create metafields definition sheet."""
    ws = wb.create_sheet("Metafield Definitions", 2)
    
    # Header style
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    # Headers
    headers = ["Name", "Key", "Namespace", "Type", "Description"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Write metafield definitions
    for row_idx, mf in enumerate(mapping["metafields"], 2):
        ws.cell(row=row_idx, column=1, value=mf["name"])
        ws.cell(row=row_idx, column=2, value=mf["key"])
        ws.cell(row=row_idx, column=3, value=mf["namespace"])
        ws.cell(row=row_idx, column=4, value=mf["type"])
        ws.cell(row=row_idx, column=5, value=mf.get("description", ""))
    
    # Auto-adjust column widths
    for col_idx in range(1, 6):
        column_letter = get_column_letter(col_idx)
        max_length = 0
        
        for row_idx in range(1, len(mapping["metafields"]) + 2):
            cell_value = ws.cell(row=row_idx, column=col_idx).value
            if cell_value:
                max_length = max(max_length, len(str(cell_value)))
        
        ws.column_dimensions[column_letter].width = min(max_length + 2, 60)


def create_excel_report(products: List[Dict], mapping: Dict, output_file: str) -> None:
    """Create complete Excel report."""
    print(f"\n📊 Creating Excel report...")
    
    wb = Workbook()
    
    # Remove default sheet
    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])
    
    # Create sheets
    print("  📄 Creating Summary sheet...")
    create_summary_sheet(wb, products, mapping)
    
    print("  📄 Creating Products sheet...")
    create_products_sheet(wb, products, mapping)
    
    print("  📄 Creating Metafield Definitions sheet...")
    create_metafields_sheet(wb, mapping)
    
    # Save workbook
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_file)
    
    print(f"  ✅ Excel report saved: {output_file}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create Excel report for category metafields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/create_metafields_excel.py \\
    --products exports/tag_water-pump/products_with_metafields.json \\
    --mapping exports/tag_water-pump/tag_water-pump_category_mapping.json \\
    --output exports/tag_water-pump/water-pump_metafields_final.xlsx
        """
    )
    
    parser.add_argument('--products', required=True, help='Path to products JSON file with metafields')
    parser.add_argument('--mapping', required=True, help='Path to category mapping JSON file')
    parser.add_argument('--output', required=True, help='Output Excel file path')
    
    args = parser.parse_args()
    
    # Load data
    print(f"📂 Loading products from: {args.products}")
    products = load_json(args.products)
    print(f"  ✅ Loaded {len(products)} products")
    
    print(f"\n📂 Loading category mapping from: {args.mapping}")
    mapping = load_json(args.mapping)
    print(f"  ✅ Category: {mapping['category']['fullName']}")
    print(f"  ✅ Metafields: {len(mapping['metafields'])}")
    
    # Create Excel report
    create_excel_report(products, mapping, args.output)
    
    print("\n✅ Excel report creation complete!")
    print(f"\n📊 Review the file: {args.output}")
    print("   - Summary: Overview and statistics")
    print("   - Products: All products with filled metafields")
    print("   - Metafield Definitions: Field specifications")


if __name__ == "__main__":
    main()


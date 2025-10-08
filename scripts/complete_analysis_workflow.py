#!/usr/bin/env python3
"""
Complete analysis workflow for ANY collection.
One script to rule them all!
"""

import subprocess
import sys
from pathlib import Path

def run_complete_analysis(identifier: str, output_dir: str = "exports", mode: str = "collection") -> str:
    """
    Run complete analysis workflow for any collection or tag.
    
    Args:
        identifier: Name of the collection or tag to analyze
        output_dir: Directory to save outputs
        mode: "collection" or "tag"
    Returns:
        Path to final Excel file
    """
    print(f" Starting Complete Analysis for: {identifier} (mode: {mode})")
    print("=" * 60)
    
    # Step 1: Fetch products
    print(f" Step 1: Fetching products from Shopify by {mode}...")
    
    # Create safe name for folder and files
    safe_name = identifier.replace(' ', '_').replace('/', '_')
    
    if mode == "tag":
        fetch_cmd = [
            sys.executable, "scripts/fetch_products.py", 
            "tag", "--name", identifier
        ]
        filename_prefix = f"products_tag_{safe_name}"
        subfolder = f"tag_{safe_name}"
    else:  # collection mode
        fetch_cmd = [
            sys.executable, "scripts/fetch_products.py", 
            "collection", "--title", identifier
        ]
        filename_prefix = f"collection_{safe_name}"
        subfolder = safe_name
    
    try:
        result = subprocess.run(fetch_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        print(" Products fetched successfully!")
    except subprocess.CalledProcessError as e:
        print(f" Error fetching products: {e}")
        print(f"\nCommand output:\n{e.stdout}")
        print(f"\nError output:\n{e.stderr}")
        return None
    
    # All files will be in the subfolder
    subfolder_path = f"{output_dir}/{subfolder}"
    
    # Determine input file based on mode
    input_file = f"{subfolder_path}/{filename_prefix}_with_lang.json"
    
    # Step 2: Dynamic analysis
    print("\nStep 2: Running dynamic meta field discovery...")
    analysis_file = f"{subfolder_path}/{safe_name}_analysis.json"
    analysis_cmd = [
        sys.executable, "scripts/dynamic_product_analyzer.py",
        input_file,
        "-o", analysis_file
    ]
    
    try:
        result = subprocess.run(analysis_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        print(" Dynamic analysis completed!")
    except subprocess.CalledProcessError as e:
        print(f" Error in dynamic analysis: {e}")
        print(f"\nCommand output:\n{e.stdout}")
        print(f"\nError output:\n{e.stderr}")
        return None
    
    # Step 3: Universal field population
    print("\n Step 3: Populating fields with universal script...")
    populated_file = f"{subfolder_path}/{safe_name}_complete.json"
    populate_cmd = [
        sys.executable, "scripts/universal_field_population.py",
        analysis_file, "-o", populated_file
    ]
    
    try:
        result = subprocess.run(populate_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        print(" Field population completed!")
    except subprocess.CalledProcessError as e:
        print(f"Error in field population: {e}")
        print(f"\nCommand output:\n{e.stdout}")
        print(f"\nError output:\n{e.stderr}")
        return None
    
    # Step 4: Create Excel
    print("\nStep 4: Creating Excel output...")
    excel_file = f"{subfolder_path}/{safe_name}_final.xlsx"
    excel_cmd = [
        sys.executable, "scripts/create_dynamic_excel.py",
        populated_file, "-o", excel_file
    ]
    
    try:
        result = subprocess.run(excel_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        print(" Excel file created!")
    except subprocess.CalledProcessError as e:
        print(f" Error creating Excel: {e}")
        print(f"\nCommand output:\n{e.stdout}")
        print(f"\nError output:\n{e.stderr}")
        return None
    
    print("\n" + "=" * 60)
    print(f"COMPLETE ANALYSIS FINISHED!")
    print(f"Final Excel file: {excel_file}")
    print(f"Complete JSON: {populated_file}")
    print("=" * 60)
    
    return excel_file

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Complete Analysis Workflow',
        epilog="""
Examples:
  # By collection:
  python complete_analysis_workflow.py "طعام قطط"
  
  # By tag:
  python complete_analysis_workflow.py --tag "cat_food"
        """
    )
    parser.add_argument('identifier', help='Collection title or tag name to analyze')
    parser.add_argument('-t', '--tag', action='store_true', help='Fetch by tag instead of collection')
    parser.add_argument('-o', '--output-dir', default='exports', help='Output directory')
    
    args = parser.parse_args()
    
    # Determine mode
    mode = "tag" if args.tag else "collection"
    
    try:
        # Run complete analysis
        excel_file = run_complete_analysis(args.identifier, args.output_dir, mode)
        
        if excel_file:
            print(f"\n Success! Analysis complete: {excel_file}")
        else:
            print("\n Analysis failed!")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

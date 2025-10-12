#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Category Metafields Workflow
End-to-end process: fetch products → match category → fill metafields → create Excel
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f" {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"\n {description} - Complete!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n {description} - Failed!")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"\n {description} - Error!")
        print(f"Error: {e}")
        return False


def check_taxonomy_exists(taxonomy_file: str = "data/shopify_taxonomy_full.json") -> bool:
    """Check if taxonomy file exists, raise error if not."""
    path = Path(taxonomy_file)
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy file not found at: {taxonomy_file}")
    return Path(taxonomy_file).exists()


def main():
    """Main workflow function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Complete workflow for category metafields analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script runs the complete workflow:
1. Fetch products by tag from Shopify
2. Match tag to best Shopify category
3. Fill category metafields using LLM
4. Create Excel report for review

Examples:
  # Complete workflow for water-pump products
  python scripts/category_metafields_workflow.py --tag water-pump
  
  # With custom model
  python scripts/category_metafields_workflow.py --tag tv --model gpt-4o
  
  # Skip fetching if products already exist
  python scripts/category_metafields_workflow.py --tag cat-food --skip-fetch
  
  # Fetch taxonomy first (only needed once)
  python scripts/category_metafields_workflow.py --fetch-taxonomy-only
        """
    )
    
    parser.add_argument('--tag', help='Product tag to analyze')
    parser.add_argument('--model', default='gpt-4o', help='OpenAI model to use (default: gpt-4o)')
    parser.add_argument('--mode', choices=['batch', 'single'], default='batch', 
                       help='Metafield filling mode (default: batch)')
    parser.add_argument('--batch-size', type=int, default=10, 
                       help='Batch size for batch mode (default: 10)')
    parser.add_argument('--skip-fetch', action='store_true', 
                       help='Skip fetching products (use existing data)')
    parser.add_argument('--fetch-taxonomy-only', action='store_true',
                       help='Only fetch Shopify taxonomy and exit')
    parser.add_argument('--taxonomy-sample', type=int,
                       help='Sample size for taxonomy fetching (for testing)')
    parser.add_argument('--output-dir', default='exports', 
                       help='Output directory (default: exports)')
    
    args = parser.parse_args()
    
    # Check if we're only fetching taxonomy
    if args.fetch_taxonomy_only:
        print(" Fetching Shopify Product Taxonomy\n")
        cmd = ["python", "scripts/fetch_shopify_taxonomy.py"]
        if args.taxonomy_sample:
            cmd.extend(["--sample", str(args.taxonomy_sample)])
        
        run_command(cmd, "Fetch Shopify Taxonomy")
        print("\nTaxonomy fetching complete!")
        print("You can now run the workflow with --tag to analyze products.")
        return
    
    # Validate tag is provided for regular workflow
    if not args.tag:
        parser.error("--tag is required (or use --fetch-taxonomy-only)")
    
    # Validate environment
    if not os.getenv("SHOPIFY_STORE_DOMAIN") or not os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN"):
        raise SystemExit(
            " Missing Shopify credentials.\n"
            "Please set SHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN in .env"
        )
    
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(" Missing OPENAI_API_KEY in .env")
    
    # Check if taxonomy exists
    if not check_taxonomy_exists():
        print("Shopify taxonomy not found!")
        print("Fetching taxonomy first (this only needs to be done once)...\n")
        
        cmd = ["python", "scripts/fetch_shopify_taxonomy.py"]
        if not run_command(cmd, "Fetch Shopify Taxonomy"):
            raise SystemExit(" Failed to fetch taxonomy. Please try again.")
    
    # Setup paths
    safe_tag = args.tag.replace(' ', '_').replace('/', '_')
    tag_dir = Path(args.output_dir) / f"tag_{safe_tag}"
    tag_dir.mkdir(parents=True, exist_ok=True)
    
    products_file = tag_dir / f"products_tag_{safe_tag}_with_lang.json"
    mapping_file = tag_dir / f"tag_{safe_tag}_category_mapping.json"
    metafields_file = tag_dir / f"products_with_metafields.json"
    excel_file = tag_dir / f"{safe_tag}_metafields_final.xlsx"
    
    print("\n" + "="*60)
    print(" CATEGORY METAFIELDS WORKFLOW")
    print("="*60)
    print(f"Tag: {args.tag}")
    print(f"Model: {args.model}")
    print(f"Mode: {args.mode}")
    print(f"Output directory: {tag_dir}")
    print("="*60)
    
    # Step 1: Fetch products from Shopify
    if not args.skip_fetch or not products_file.exists():
        cmd = [
            "python", "scripts/fetch_products.py",
            "--output-dir", args.output_dir,
            "tag", "--name", args.tag
        ]
        
        if not run_command(cmd, "Step 1: Fetch Products from Shopify"):
            raise SystemExit(" Workflow failed at Step 1")
    else:
        print(f"\n⏭Skipping Step 1: Using existing products file: {products_file}")
    
    # Verify products file exists
    if not products_file.exists():
        raise SystemExit(f"Products file not found: {products_file}")
    
    # Step 2: Match tag to Shopify category
    if not mapping_file.exists():
        cmd = [
            "python", "scripts/match_tag_to_category.py",
            "--tag", args.tag,
            "--products", str(products_file),
            "--model", args.model
        ]
        
        if not run_command(cmd, "Step 2: Match Tag to Shopify Category"):
            raise SystemExit(" Workflow failed at Step 2")
    else:
        print(f"\n⏭️  Skipping Step 2: Using existing category mapping: {mapping_file}")
    
    # Verify mapping file exists
    if not mapping_file.exists():
        raise SystemExit(f" Category mapping file not found: {mapping_file}")
    
    # Step 3: Fill metafields for all products
    cmd = [
        "python", "scripts/fill_category_metafields.py",
        "--products", str(products_file),
        "--mapping", str(mapping_file),
        "--output", str(metafields_file),
        "--model", args.model,
        "--mode", args.mode
    ]
    
    if args.mode == 'batch':
        cmd.extend(["--batch-size", str(args.batch_size)])
    
    if not run_command(cmd, "Step 3: Fill Category Metafields"):
        raise SystemExit(" Workflow failed at Step 3")
    
    # Step 4: Create Excel report
    cmd = [
        "python", "scripts/create_metafields_excel.py",
        "--products", str(metafields_file),
        "--mapping", str(mapping_file),
        "--output", str(excel_file)
    ]
    
    if not run_command(cmd, "Step 4: Create Excel Report"):
        raise SystemExit(" Workflow failed at Step 4")
    
    # Success!
    print("\n" + "="*60)
    print(" WORKFLOW COMPLETE!")
    print("="*60)
    print(f"\n All files saved to: {tag_dir}")
    print(f"\n Final Excel Report: {excel_file}")
    print("\nGenerated files:")
    print(f"  1. {products_file.name} - Raw products from Shopify")
    print(f"  2. {mapping_file.name} - Category mapping")
    print(f"  3. {metafields_file.name} - Products with filled metafields")
    print(f"  4. {excel_file.name} -  FINAL REPORT (Review this!)")
    print("\n" + "="*60)
    print("\n Next steps:")
    print("   1. Open the Excel file and review the metafields")
    print("   2. Make any necessary adjustments")
    print("   3. Use the data to create metafields in Shopify")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()


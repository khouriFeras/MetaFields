#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
smart_workflow.py
- Complete smart workflow: fetch → LLM discover meta fields → create definitions → LLM fill values → update Shopify → export
- Designed for Arabic product recommendation bot integration
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Import our existing modules
sys.path.append(str(Path(__file__).parent))
from fetch_products import (
    fetch_all_products, fetch_product_by_handle, fetch_product_by_id,
    fetch_products_by_tag, fetch_collection_products, add_language_markers,
    write_json, write_csv, write_xlsx, ensure_output_dir
)
from smart_meta_discovery import discover_and_create_meta_fields
from llm_meta_filler import process_products_with_llm

# Environment variables
SHOPIFY_STORE_DOMAIN: str = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_ADMIN_ACCESS_TOKEN: str = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
TARGET_LANGUAGE: str = os.getenv("TARGET_LANGUAGE", "en").strip()
ORIGINAL_LANGUAGE: str = os.getenv("ORIGINAL_LANGUAGE", "ar").strip()
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "data").strip()


def validate_environment() -> None:
    """Validate required environment variables."""
    missing: List[str] = []
    if not SHOPIFY_STORE_DOMAIN:
        missing.append("SHOPIFY_STORE_DOMAIN")
    if not SHOPIFY_ADMIN_ACCESS_TOKEN:
        missing.append("SHOPIFY_ADMIN_ACCESS_TOKEN")
    if missing:
        raise SystemExit(
            f"Missing required environment variables: {', '.join(missing)}.\n"
            "Set them in .env or your environment and try again."
        )


def detect_product_type(products: List[Dict]) -> Optional[str]:
    """Detect product type from products."""
    if not products:
        return None
    
    # Check product types and tags
    product_types = set()
    all_tags = set()
    
    for product in products:
        if product.get("productType"):
            product_types.add(product["productType"].lower())
        if product.get("tags"):
            for tag in product["tags"]:
                all_tags.add(tag.lower())
    
    # Check for specific product types
    type_mapping = {
        "blender": ["blender", "blenders", "خلاط", "خلاطات"],
        "hair_dryer": ["hair dryer", "hair dryers", "مجفف شعر", "مجففات الشعر"],
        "drill": ["drill", "drills", "دريل", "دريلات"],
        "tv": ["tv", "television", "شاشة", "تلفزيون", "تلفاز"],
        "air_conditioner": ["air conditioner", "ac", "مكيف", "تكييف"],
        "dog_food": ["dog food", "كلاب", "طعام كلاب", "أكل كلاب"]
    }
    
    for detected_type, keywords in type_mapping.items():
        for keyword in keywords:
            if keyword in product_types or any(keyword in tag for tag in all_tags):
                return detected_type
    
    return None


def fetch_products_by_command(command: str, args: Dict) -> List[Dict]:
    """Fetch products based on command and arguments."""
    if command == 'all':
        return fetch_all_products()
    elif command == 'single':
        if args.get('handle'):
            product = fetch_product_by_handle(args['handle'])
            return [product] if product else []
        elif args.get('id'):
            product = fetch_product_by_id(args['id'])
            return [product] if product else []
    elif command == 'tag':
        return fetch_products_by_tag(args['name'])
    elif command == 'collection':
        return fetch_collection_products(args['identifier'])
    
    return []


def export_smart_results(products: List[Dict], discovery_results: Dict, 
                        filename_prefix: str, output_dir: Path, 
                        no_csv: bool = False, no_xlsx: bool = False) -> None:
    """Export products and discovery results."""
    print(f"📁 Exporting {len(products)} products with smart meta fields...")
    
    # Products with smart meta fields
    processed_file = output_dir / f"{filename_prefix}_smart_processed.json"
    write_json(processed_file, products)
    print(f"  - Products: {processed_file}")
    
    # Discovery results
    discovery_file = output_dir / f"{filename_prefix}_meta_discovery.json"
    write_json(discovery_file, discovery_results)
    print(f"  - Discovery: {discovery_file}")
    
    # CSV (unless disabled)
    if not no_csv:
        csv_file = output_dir / f"{filename_prefix}_smart_processed.csv"
        write_csv(csv_file, products)
        print(f"  - CSV: {csv_file}")
    
    # XLSX (unless disabled)
    if not no_xlsx:
        xlsx_file = output_dir / f"{filename_prefix}_smart_processed.xlsx"
        write_xlsx(xlsx_file, products)
        print(f"  - Excel: {xlsx_file}")
    
    print(f"✅ Export complete!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart workflow: fetch → LLM discover → create → LLM fill → update → export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Complete smart workflow for all products
  python smart_workflow.py all
  
  # Smart workflow for collection
  python smart_workflow.py collection --handle blenders
  
  # Custom sample percentage for discovery
  python smart_workflow.py all --sample-percentage 0.15
  
  # Discovery only (don't create or update)
  python smart_workflow.py all --discovery-only
  
  # Skip Shopify updates (test without updating)
  python smart_workflow.py all --skip-shopify-update
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Fetch method')
    
    # Smart workflow options (add to all subparsers)
    common_args = [
        ('--output-dir', {'default': OUTPUT_DIR, 'help': 'Output directory'}),
        ('--no-csv', {'action': 'store_true', 'help': 'Skip CSV export'}),
        ('--no-xlsx', {'action': 'store_true', 'help': 'Skip XLSX export'}),
        ('--sample-percentage', {'type': float, 'default': 0.1, 'help': 'Sample percentage for discovery (default: 0.1)'}),
        ('--category', {'help': 'Override detected category for meta field discovery'}),
        ('--discovery-only', {'action': 'store_true', 'help': 'Only discover meta fields, do not create or fill'}),
        ('--skip-llm-fill', {'action': 'store_true', 'help': 'Skip LLM value filling'}),
        ('--skip-shopify-update', {'action': 'store_true', 'help': 'Skip Shopify updates'}),
        ('--verbose', {'action': 'store_true', 'help': 'Verbose output'})
    ]
    
    # All products command
    all_parser = subparsers.add_parser('all', help='Fetch all products')
    for arg_name, arg_kwargs in common_args:
        all_parser.add_argument(arg_name, **arg_kwargs)
    
    # Single product command
    single_parser = subparsers.add_parser('single', help='Fetch single product')
    single_group = single_parser.add_mutually_exclusive_group(required=True)
    single_group.add_argument('--handle', help='Product handle')
    single_group.add_argument('--id', help='Product ID')
    for arg_name, arg_kwargs in common_args:
        single_parser.add_argument(arg_name, **arg_kwargs)
    
    # Tag command
    tag_parser = subparsers.add_parser('tag', help='Fetch products by tag')
    tag_parser.add_argument('--name', required=True, help='Tag name')
    for arg_name, arg_kwargs in common_args:
        tag_parser.add_argument(arg_name, **arg_kwargs)
    
    # Collection command
    collection_parser = subparsers.add_parser('collection', help='Fetch products from collection')
    collection_group = collection_parser.add_mutually_exclusive_group(required=True)
    collection_group.add_argument('--handle', help='Collection handle')
    collection_group.add_argument('--title', help='Collection title')
    collection_group.add_argument('--id', help='Collection ID')
    for arg_name, arg_kwargs in common_args:
        collection_parser.add_argument(arg_name, **arg_kwargs)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    validate_environment()
    output_dir = ensure_output_dir(args.output_dir)
    
    print("🚀 Starting smart workflow with LLM-powered meta field discovery...")
    print("=" * 70)
    
    # Step 1: Fetch products
    print("📥 Step 1: Fetching products...")
    
    if args.command == 'all':
        products = fetch_all_products()
        filename_prefix = "products"
    elif args.command == 'single':
        if args.handle:
            product = fetch_product_by_handle(args.handle)
            products = [product] if product else []
            filename_prefix = f"single_product_{args.handle}"
        elif args.id:
            product = fetch_product_by_id(args.id)
            products = [product] if product else []
            filename_prefix = f"single_product_{args.id.replace('gid://shopify/Product/', '')}"
    elif args.command == 'tag':
        products = fetch_products_by_tag(args.name)
        safe_name = args.name.replace(' ', '_').replace('/', '_')
        filename_prefix = f"products_tag_{safe_name}"
    elif args.command == 'collection':
        if args.handle:
            products = fetch_collection_products(args.handle)
            safe_name = args.handle.replace(' ', '_').replace('/', '_')
            filename_prefix = f"collection_{safe_name}"
        elif args.title:
            products = fetch_collection_products(args.title)
            safe_name = args.title.replace(' ', '_').replace('/', '_')
            filename_prefix = f"collection_{safe_name}"
        elif args.id:
            products = fetch_collection_products(args.id)
            filename_prefix = f"collection_{args.id.replace('gid://shopify/Collection/', '')}"
    
    if not products:
        print("❌ No products found.")
        sys.exit(1)
    
    print(f"✅ Fetched {len(products)} products")
    
    # Add language markers
    products_with_lang = add_language_markers(products)
    
    # Step 2: Smart meta field discovery
    print(f"\n🔍 Step 2: Smart meta field discovery...")
    
    category = args.category or detect_product_type(products)
    if not category:
        print("❌ Could not detect product category for meta field discovery")
        sys.exit(1)
    
    print(f"📊 Detected category: {category}")
    
    try:
        discovery_results = discover_and_create_meta_fields(
            products_with_lang,
            category,
            sample_percentage=args.sample_percentage,
            create_definitions=not args.discovery_only,
            verbose=args.verbose
        )
        
        if "error" in discovery_results:
            print(f"❌ Discovery failed: {discovery_results['error']}")
            sys.exit(1)
        
        print(f"✅ Discovered {len(discovery_results['discovered_fields'])} meta fields")
        if not args.discovery_only:
            print(f"✅ Created {discovery_results['success_count']} meta field definitions")
        
        # Store discovered fields for LLM processing
        discovered_meta_fields = discovery_results['discovered_fields']
        
    except Exception as e:
        print(f"❌ Discovery error: {e}")
        sys.exit(1)
    
    # Step 3: LLM value filling (if not discovery-only)
    if not args.discovery_only and not args.skip_llm_fill:
        print(f"\n🤖 Step 3: LLM-powered value extraction...")
        
        try:
            processed_products = process_products_with_llm(
                products_with_lang,
                category,
                update_shopify=not args.skip_shopify_update,
                verbose=args.verbose
            )
            products_with_lang = processed_products
            
        except Exception as e:
            print(f"❌ LLM filling error: {e}")
            if args.skip_shopify_update:
                print("⚠️  Continuing with original products...")
            else:
                sys.exit(1)
    else:
        print(f"\n⏭️  Step 3: Skipping LLM value filling")
    
    # Step 4: Export results
    print(f"\n📁 Step 4: Exporting results...")
    export_smart_results(
        products_with_lang, 
        discovery_results,
        filename_prefix, 
        output_dir,
        no_csv=args.no_csv,
        no_xlsx=args.no_xlsx
    )
    
    print("\n🎉 Smart workflow complete!")
    print("=" * 70)
    print(f"📊 Summary:")
    print(f"  - Products processed: {len(products)}")
    print(f"  - Category: {category}")
    print(f"  - Meta fields discovered: {len(discovery_results['discovered_fields'])}")
    print(f"  - Meta fields created: {discovery_results.get('success_count', 0)}")
    print(f"  - LLM value filling: {'✅ Completed' if not args.discovery_only and not args.skip_llm_fill else '⏭️ Skipped'}")
    print(f"  - Shopify updates: {'✅ Completed' if not args.discovery_only and not args.skip_shopify_update else '⏭️ Skipped'}")
    print(f"  - Export: ✅ Completed")
    print(f"  - Output directory: {output_dir}")
    
    # Show bot integration info
    if discovery_results.get('discovered_fields'):
        print(f"\n🤖 Bot Integration Ready:")
        print(f"  - Meta fields optimized for Arabic recommendation bot")
        print(f"  - Fields support filtering, searching, and comparison")
        print(f"  - Ready for slot-filling and user preference matching")


if __name__ == "__main__":
    main()

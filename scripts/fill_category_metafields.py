#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fill Category Metafields for Products
Uses LLM to intelligently fill Shopify category metafields for all products.
"""
import json
import os
import sys
import re
import html
from pathlib import Path
from typing import Dict, List, Optional, Any
import openai
from dotenv import load_dotenv

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


def clean_html(html_text: str) -> str:
    """Clean HTML text by removing tags and decoding entities."""
    if not html_text:
        return ""
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', ' ', html_text)
    # Decode HTML entities
    clean_text = html.unescape(clean_text)
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text)
    return clean_text.strip()


def load_json(file_path: str) -> Any:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: str, data: Any) -> None:
    """Save JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_product_info(product: Dict) -> str:
    """Extract relevant product information for LLM analysis."""
    title = product.get('title', 'N/A')
    product_type = product.get('productType', 'N/A')
    vendor = product.get('vendor', 'N/A')
    tags = ', '.join(product.get('tags', []))
    
    # Clean description
    description_html = product.get('descriptionHtml', '')
    description = clean_html(description_html)
    if len(description) > 500:
        description = description[:500] + "..."
    
    # Get variant information
    variants_info = []
    variants = product.get('variants', [])
    for variant in variants[:3]:  # Max 3 variants
        v_title = variant.get('title', 'Default')
        v_price = variant.get('price', 'N/A')
        options = variant.get('selected_options', [])
        options_str = ", ".join([f"{opt['name']}: {opt['value']}" for opt in options])
        if options_str:
            variants_info.append(f"{v_title} - {options_str} - {v_price}")
        else:
            variants_info.append(f"{v_title} - {v_price}")
    
    variants_text = "\n  ".join(variants_info) if variants_info else "No variants"
    
    product_info = f"""
Title: {title}
Type: {product_type}
Vendor: {vendor}
Tags: {tags}
Description: {description}
Variants:
  {variants_text}
"""
    
    return product_info.strip()


def fill_metafields_batch(
    products: List[Dict],
    metafield_definitions: List[Dict],
    category_name: str,
    model: str = "gpt-4o",
    batch_size: int = 10
) -> List[Dict]:
    """
    Fill metafields for a batch of products using LLM.
    Args:
        products: List of products to process
        metafield_definitions: List of metafield definitions from category
        category_name: Name of the Shopify category
        model: OpenAI model to use
        batch_size: Number of products to process in each batch
    Returns:
        List of products with filled metafields
    """
    print(f"\n Filling metafields for {len(products)} products using {model}...")
    print(f" Category: {category_name}")
    print(f"  Metafields to fill: {len(metafield_definitions)}")
    # Prepare metafield definitions for prompt
    metafield_descriptions = []
    for mf in metafield_definitions:
        validations = ""
        if mf.get('validations'):
            val_list = [f"{v['name']}: {v['value']}" for v in mf['validations']]
            validations = f" (Validations: {', '.join(val_list)})"
        desc = mf.get('description', '')
        metafield_descriptions.append(
            f"- {mf['name']} (key: {mf['key']}, type: {mf['type']}){validations}\n"
            f"  Description: {desc if desc else 'No description'}"
        )
    metafields_text = "\n".join(metafield_descriptions)
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    results = []
    total_batches = (len(products) + batch_size - 1) // batch_size
    
    for batch_idx in range(0, len(products), batch_size):
        batch = products[batch_idx:batch_idx + batch_size]
        current_batch = (batch_idx // batch_size) + 1
        
        print(f"\n  Batch {current_batch}/{total_batches} ({len(batch)} products)...")
        
        # Prepare batch product info
        batch_products_info = []
        for i, product in enumerate(batch, 1):
            product_info = extract_product_info(product)
            batch_products_info.append(f"PRODUCT {i}:\n{product_info}")
        
        products_text = "\n\n".join(batch_products_info)
        
        # Create prompt
        prompt = f"""You are filling Shopify category metafields for products.

CATEGORY: {category_name}

METAFIELDS TO FILL:
{metafields_text}

PRODUCTS:
{products_text}

INSTRUCTIONS:
1. Analyze each product carefully
2. Fill ALL metafields with appropriate values based on product information
3. Extract values from title, description, variants, and tags
4. If a value cannot be determined, use null
5. For single_line_text_field: use short text (max 100 chars)
6. For list.single_line_text_field: use array of strings
7. Follow all validations and constraints
8. Be accurate and consistent

Return ONLY valid JSON in this EXACT format:
{{
  "products": [
    {{
      "product_index": 1,
      "metafields": {{
        "metafield_key1": "value1",
        "metafield_key2": ["value1", "value2"],
        "metafield_key3": null
      }}
    }},
    ...
  ]
}}

Return only the JSON, no other text."""
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a product data expert. You analyze products and extract metafield values accurately. You always return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            batch_result = json.loads(result_text)
            
            # Merge metafields back to products
            for i, product_data in enumerate(batch_result.get("products", [])):
                if i < len(batch):
                    product = batch[i].copy()
                    product["category_metafields"] = product_data.get("metafields", {})
                    results.append(product)
            
            print(f"    Processed {len(batch)} products")
            
        except Exception as e:
            print(f"    Error processing batch: {e}")
            # Add products without metafields
            for product in batch:
                product_copy = product.copy()
                product_copy["category_metafields"] = {}
                results.append(product_copy)
    
    return results


def fill_metafields_single(
    products: List[Dict],
    metafield_definitions: List[Dict],
    category_name: str,
    model: str = "gpt-4o"
) -> List[Dict]:
    """
    Fill metafields for products one at a time (slower but more accurate).
    
    Args:
        products: List of products to process
        metafield_definitions: List of metafield definitions from category
        category_name: Name of the Shopify category
        model: OpenAI model to use
        
    Returns:
        List of products with filled metafields
    """
    print(f"\n Filling metafields for {len(products)} products (single mode) using {model}...")
    print(f" Category: {category_name}")
    print(f"  Metafields to fill: {len(metafield_definitions)}")
    
    # Prepare metafield definitions for prompt
    metafield_descriptions = []
    for mf in metafield_definitions:
        validations = ""
        if mf.get('validations'):
            val_list = [f"{v['name']}: {v['value']}" for v in mf['validations']]
            validations = f" (Validations: {', '.join(val_list)})"
        
        desc = mf.get('description', '')
        metafield_descriptions.append(
            f"- {mf['name']} (key: {mf['key']}, type: {mf['type']}){validations}\n"
            f"  Description: {desc if desc else 'No description'}"
        )
    
    metafields_text = "\n".join(metafield_descriptions)
    
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    results = []
    
    for i, product in enumerate(products, 1):
        print(f"  [{i}/{len(products)}] {product.get('title', 'N/A')[:50]}...")
        
        product_info = extract_product_info(product)
        
        # Create prompt
        prompt = f"""You are filling Shopify category metafields for a product.

CATEGORY: {category_name}

METAFIELDS TO FILL:
{metafields_text}

PRODUCT:
{product_info}

INSTRUCTIONS:
1. Analyze the product carefully
2. Fill ALL metafields with appropriate values based on product information
3. Extract values from title, description, variants, and tags
4. If a value cannot be determined, use null
5. For single_line_text_field: use short text (max 100 chars)
6. For list.single_line_text_field: use array of strings
7. Follow all validations and constraints
8. Be accurate and specific

Return ONLY valid JSON in this EXACT format:
{{
  "metafields": {{
    "metafield_key1": "value1",
    "metafield_key2": ["value1", "value2"],
    "metafield_key3": null
  }}
}}

Return only the JSON, no other text."""
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a product data expert. You analyze products and extract metafield values accurately. You always return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            product_copy = product.copy()
            product_copy["category_metafields"] = result.get("metafields", {})
            results.append(product_copy)
            
            # Show filled metafields count
            filled_count = sum(1 for v in result.get("metafields", {}).values() if v is not None)
            print(f"    ✅ Filled {filled_count}/{len(metafield_definitions)} metafields")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            product_copy = product.copy()
            product_copy["category_metafields"] = {}
            results.append(product_copy)
    
    return results


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fill category metafields for products using LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fill metafields for water-pump products (batch mode)
  python scripts/fill_category_metafields.py \\
    --products exports/tag_water-pump/products_tag_water-pump_with_lang.json \\
    --mapping exports/tag_water-pump/tag_water-pump_category_mapping.json \\
    --output exports/tag_water-pump/products_with_metafields.json
  
  # Single product mode (slower but more accurate)
  python scripts/fill_category_metafields.py \\
    --products exports/tag_tv/products_tag_tv_with_lang.json \\
    --mapping exports/tag_tv/tag_tv_category_mapping.json \\
    --output exports/tag_tv/products_with_metafields.json \\
    --mode single
        """
    )
    
    parser.add_argument('--products', required=True, help='Path to products JSON file')
    parser.add_argument('--mapping', required=True, help='Path to category mapping JSON file')
    parser.add_argument('--output', required=True, help='Output file path for products with metafields')
    parser.add_argument('--model', default='gpt-4o', help='OpenAI model to use (default: gpt-4o)')
    parser.add_argument('--mode', choices=['batch', 'single'], default='batch', help='Processing mode (default: batch)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for batch mode (default: 10)')
    
    args = parser.parse_args()
    
    # Validate OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(" Missing OPENAI_API_KEY in .env")
    
    # Load products
    print(f"Loading products from: {args.products}")
    products = load_json(args.products)
    print(f"  Loaded {len(products)} products")
    
    # Load category mapping
    print(f"\n Loading category mapping from: {args.mapping}")
    mapping = load_json(args.mapping)
    category_name = mapping["category"]["fullName"]
    metafield_definitions = mapping["metafields"]
    print(f"  Category: {category_name}")
    print(f"  Metafields: {len(metafield_definitions)}")
    
    if not metafield_definitions:
        raise SystemExit("No metafield definitions found in mapping file")
    
    # Fill metafields
    if args.mode == 'single':
        results = fill_metafields_single(
            products=products,
            metafield_definitions=metafield_definitions,
            category_name=category_name,
            model=args.model
        )
    else:
        results = fill_metafields_batch(
            products=products,
            metafield_definitions=metafield_definitions,
            category_name=category_name,
            model=args.model,
            batch_size=args.batch_size
        )
    
    # Save results
    print(f"\nSaving results to: {args.output}")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(args.output, results)
    
    # Statistics
    total_products = len(results)
    products_with_metafields = sum(1 for p in results if p.get("category_metafields"))
    total_metafields_filled = sum(
        sum(1 for v in p.get("category_metafields", {}).values() if v is not None)
        for p in results
    )
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total products processed:     {total_products}")
    print(f"Products with metafields:     {products_with_metafields}")
    print(f"Total metafields filled:      {total_metafields_filled}")
    print(f"Average per product:          {total_metafields_filled/total_products:.1f}")
    print("="*60)
    print("\nMetafield filling complete!")
    print(f"\nNext step: Create Excel file for review")


if __name__ == "__main__":
    main()


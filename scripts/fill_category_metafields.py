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
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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
    
    # Clean description (full description for complete spec extraction)
    description_html = product.get('descriptionHtml', '')
    description = clean_html(description_html)
    # No truncation - send full description to capture all specs
    # Important for fields like Energy efficiency class (HDR/SDR)
    
    # Get variant information (ALL variants for complete spec extraction)
    variants_info = []
    variants = product.get('variants', [])
    for variant in variants:  # All variants (captures all sizes, colors, options)
        v_title = variant.get('title', 'Default')
        v_price = variant.get('price', 'N/A')
        options = variant.get('selected_options', [])
        options_str = ", ".join([f"{opt['name']}: {opt['value']}" for opt in options])
        if options_str:
            variants_info.append(f"{v_title} - {options_str} - {v_price}")
        else:
            variants_info.append(f"{v_title} - {v_price}")
    
    variants_text = "\n  ".join(variants_info) if variants_info else "No variants"
    
    # Get existing metafields (might have additional context)
    existing_metafields = product.get('metafields', {})
    metafields_text = ""
    if existing_metafields and len(existing_metafields) > 0:
        mf_items = [f"{k}: {v}" for k, v in list(existing_metafields.items())[:5]]
        metafields_text = f"\nExisting Metafields: {', '.join(mf_items)}"
    
    # Get pricing info
    pricing = product.get('pricing', {})
    price_info = product.get('priceRange', 'N/A')
    
    product_info = f"""
Title: {title}
Type: {product_type}
Vendor: {vendor}
Price Range: {price_info}
Tags: {tags}
Description: {description}
Variants:
  {variants_text}{metafields_text}
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
    # Prepare metafield definitions for prompt (with available values for better selection)
    metafield_descriptions = []
    for mf in metafield_definitions:
        validations = ""
        if mf.get('validations'):
            val_list = [f"{v['name']}: {v['value']}" for v in mf['validations']]
            validations = f" (Validations: {', '.join(val_list)})"
        
        # Include available values for list fields to help AI choose correctly
        values_info = ""
        if mf.get('values') and len(mf['values']) > 0:
            # Show first 15 values (keep prompt reasonable)
            value_sample = mf['values'][:15]
            values_str = ', '.join(value_sample)
            if len(mf['values']) > 15:
                values_str += f" (and {len(mf['values'])-15} more)"
            values_info = f"\n  Available values: {values_str}"
        
        desc = mf.get('description', '')
        metafield_descriptions.append(
            f"- {mf['name']} (key: {mf['key']}, type: {mf['type']}){validations}\n"
            f"  Description: {desc if desc else 'No description'}{values_info}"
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
1. READ THE ENTIRE DESCRIPTION CAREFULLY - Technical specs are often mentioned throughout
2. For list.single_line_text_field: SELECT from "Available values" provided above
3. Extract values from: Title, FULL Description (read all of it!), Variants, Tags
4. Look for technical specifications like:
   - Energy efficiency, HDR/SDR ratings (often in descriptions)
   - Screen size, resolution (often in variants or title)
   - Color, material (often in variants)
   - Audio technology, connectivity (in descriptions)
5. For fields with available values: ONLY use values from the list
6. IMPORTANT: Avoid selecting "Other" - try to find the closest specific match
7. Match variations to standard values (e.g., "Ultra HD" = "4K", "Stereo" might match a specific audio tech)
8. If truly cannot determine a value, use null (NOT "Other")
9. Only use "Other" if the product explicitly has a unique feature not in the list
10. Be thorough and read ALL product information before deciding

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
            # GPT-5 models have different API parameters than GPT-4
            api_params = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a product data expert. You analyze products and extract metafield values accurately. You always return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ]
            }
            
            # GPT-5 models use max_completion_tokens and don't support custom temperature
            if model.startswith('gpt-5'):
                # GPT-5 uses reasoning tokens + output tokens, so we need more
                # For gpt-5-nano: reasoning (~4000) + output (~2000) = 6000+ total
                api_params["max_completion_tokens"] = 12000
                # temperature=1 is default for GPT-5, don't set it
            else:
                api_params["max_tokens"] = 4000
                api_params["temperature"] = 0.2
            
            response = client.chat.completions.create(**api_params)
            
            result_text = response.choices[0].message.content
            
            # Handle empty responses (GPT-5 reasoning token issue)
            if not result_text or len(result_text.strip()) == 0:
                print(f"    ⚠️  Empty response - GPT-5 used all tokens for reasoning")
                print(f"    💡 Increasing max_completion_tokens to 16000 and retrying...")
                
                # Retry with more tokens
                if model.startswith('gpt-5'):
                    api_params["max_completion_tokens"] = 16000
                    response = client.chat.completions.create(**api_params)
                    result_text = response.choices[0].message.content
                    
                    if not result_text or len(result_text.strip()) == 0:
                        print(f"    ❌ Still empty after retry - skipping batch")
                        raise ValueError("Empty response even with 16000 tokens")
            
            result_text = result_text.strip()
            
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


def process_single_product(
    product: Dict,
    product_index: int,
    total_products: int,
    metafield_definitions: List[Dict],
    metafields_text: str,
    category_name: str,
    model: str
) -> Dict:
    """
    Process a single product with metafield filling (for parallel processing).
    
    Returns:
        Product with filled category_metafields
    """
    print(f"  [{product_index}/{total_products}] {product.get('title', 'N/A')[:60]}...")
    
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    product_info = extract_product_info(product)
    
    # Create prompt
    prompt = f"""You are filling Shopify category metafields for a product.

CATEGORY: {category_name}

METAFIELDS TO FILL:
{metafields_text}

PRODUCT:
{product_info}

INSTRUCTIONS:
1. READ THE ENTIRE DESCRIPTION CAREFULLY - Technical specs are often mentioned throughout
2. For list.single_line_text_field: SELECT from "Available values" provided above
3. Extract values from: Title, FULL Description (read all of it!), Variants, Tags
4. Look for technical specifications like:
   - Energy efficiency, HDR/SDR ratings (often in descriptions)
   - Screen size, resolution (often in variants or title)
   - Color, material (often in variants)
   - Audio technology, connectivity (in descriptions)
5. For fields with available values: ONLY use values from the list
6. IMPORTANT: Avoid selecting "Other" - try to find the closest specific match
7. Match variations to standard values (e.g., "Ultra HD" = "4K", "Stereo" might match a specific audio tech)
8. If truly cannot determine a value, use null (NOT "Other")
9. Only use "Other" if the product explicitly has a unique feature not in the list
10. Be thorough and read ALL product information before deciding

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
        # GPT-5 models have different API parameters than GPT-4
        api_params = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a product data expert. You analyze products and extract metafield values accurately. You always return valid JSON."
                },
                {"role": "user", "content": prompt}
            ]
        }
        
        # GPT-5 models use max_completion_tokens and don't support custom temperature
        if model.startswith('gpt-5'):
            # GPT-5 uses reasoning tokens, give plenty of room
            api_params["max_completion_tokens"] = 8000
        else:
            api_params["max_tokens"] = 1000
            api_params["temperature"] = 0.2
        
        response = client.chat.completions.create(**api_params)
        result_text = response.choices[0].message.content
        
        # Handle empty responses
        if not result_text or len(result_text.strip()) == 0:
            print(f"    ⚠️  Empty response - retrying with more tokens...")
            if model.startswith('gpt-5'):
                api_params["max_completion_tokens"] = 16000
                response = client.chat.completions.create(**api_params)
                result_text = response.choices[0].message.content
        
        if not result_text:
            raise ValueError("Empty response from API")
            
        result_text = result_text.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        product_copy = product.copy()
        product_copy["category_metafields"] = result.get("metafields", {})
        
        # Show filled count
        filled_count = sum(1 for v in result.get("metafields", {}).values() if v is not None)
        print(f"    ✅ Filled {filled_count}/{len(metafield_definitions)} metafields")
        
        return product_copy
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        product_copy = product.copy()
        product_copy["category_metafields"] = {}
        return product_copy


def fill_metafields_parallel(
    products: List[Dict],
    metafield_definitions: List[Dict],
    category_name: str,
    model: str = "gpt-5-nano",
    max_workers: int = 5
) -> List[Dict]:
    """
    Fill metafields for products using parallel workers (FAST!).
    
    Args:
        products: List of products to process
        metafield_definitions: List of metafield definitions from category
        category_name: Name of the Shopify category
        model: OpenAI model to use
        max_workers: Number of parallel workers (default: 5)
        
    Returns:
        List of products with filled metafields
    """
    print(f"\n🤖 Filling metafields for {len(products)} products using {model}...")
    print(f"⚡ Parallel mode with {max_workers} workers (FAST!)")
    print(f"📋 Category: {category_name}")
    print(f"🏷️  Metafields to fill: {len(metafield_definitions)}")
    
    # Prepare metafield definitions text (reuse for all workers)
    metafield_descriptions = []
    for mf in metafield_definitions:
        validations = ""
        if mf.get('validations'):
            val_list = [f"{v['name']}: {v['value']}" for v in mf['validations']]
            validations = f" (Validations: {', '.join(val_list)})"
        
        # Include available values
        values_info = ""
        if mf.get('values') and len(mf['values']) > 0:
            value_sample = mf['values'][:15]
            values_str = ', '.join(value_sample)
            if len(mf['values']) > 15:
                values_str += f" (and {len(mf['values'])-15} more)"
            values_info = f"\n  Available values: {values_str}"
        
        desc = mf.get('description', '')
        metafield_descriptions.append(
            f"- {mf['name']} (key: {mf['key']}, type: {mf['type']}){validations}\n"
            f"  Description: {desc if desc else 'No description'}{values_info}"
        )
    
    metafields_text = "\n".join(metafield_descriptions)
    
    # Process products in parallel
    start_time = time.time()
    results = [None] * len(products)  # Preserve order
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(
                process_single_product,
                product,
                i + 1,
                len(products),
                metafield_definitions,
                metafields_text,
                category_name,
                model
            ): i
            for i, product in enumerate(products)
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results[index] = result
                completed += 1
                
                if completed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    remaining = (len(products) - completed) / rate
                    print(f"\n  📊 Progress: {completed}/{len(products)} ({completed/len(products)*100:.1f}%) - ETA: {remaining:.0f}s")
            except Exception as e:
                print(f"    ❌ Worker error for product {index}: {e}")
                results[index] = products[index].copy()
                results[index]["category_metafields"] = {}
    
    elapsed = time.time() - start_time
    print(f"\n  ⚡ Completed in {elapsed:.1f}s ({len(products)/elapsed:.1f} products/sec)")
    
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
    
    # Prepare metafield definitions for prompt (with available values)
    metafield_descriptions = []
    for mf in metafield_definitions:
        validations = ""
        if mf.get('validations'):
            val_list = [f"{v['name']}: {v['value']}" for v in mf['validations']]
            validations = f" (Validations: {', '.join(val_list)})"
        
        # Include available values for list fields
        values_info = ""
        if mf.get('values') and len(mf['values']) > 0:
            value_sample = mf['values'][:15]
            values_str = ', '.join(value_sample)
            if len(mf['values']) > 15:
                values_str += f" (and {len(mf['values'])-15} more)"
            values_info = f"\n  Available values: {values_str}"
        
        desc = mf.get('description', '')
        metafield_descriptions.append(
            f"- {mf['name']} (key: {mf['key']}, type: {mf['type']}){validations}\n"
            f"  Description: {desc if desc else 'No description'}{values_info}"
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
1. READ THE ENTIRE DESCRIPTION CAREFULLY - Technical specs are often mentioned throughout
2. For list.single_line_text_field: SELECT from "Available values" provided above
3. Extract values from: Title, FULL Description (read all of it!), Variants, Tags
4. Look for technical specifications like:
   - Energy efficiency, HDR/SDR ratings (often in descriptions)
   - Screen size, resolution (often in variants or title)
   - Color, material (often in variants)
   - Audio technology, connectivity (in descriptions)
5. For fields with available values: ONLY use values from the list
6. IMPORTANT: Avoid selecting "Other" - try to find the closest specific match
7. Match variations to standard values (e.g., "Ultra HD" = "4K", "Stereo" might match a specific audio tech)
8. If truly cannot determine a value, use null (NOT "Other")
9. Only use "Other" if the product explicitly has a unique feature not in the list
10. Be thorough and read ALL product information before deciding

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
            # GPT-5 models have different API parameters than GPT-4
            api_params = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a product data expert. You analyze products and extract metafield values accurately. You always return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ]
            }
            
            # GPT-5 models use max_completion_tokens and don't support custom temperature
            if model.startswith('gpt-5'):
                # GPT-5 uses reasoning tokens + output tokens, so we need more
                api_params["max_completion_tokens"] = 4000
                # temperature=1 is default for GPT-5, don't set it
            else:
                api_params["max_tokens"] = 1000
                api_params["temperature"] = 0.2
            
            response = client.chat.completions.create(**api_params)
            
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
    parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model to use (default: gpt-4o-mini)')
    parser.add_argument('--mode', choices=['batch', 'single', 'parallel'], default='parallel', help='Processing mode (default: parallel)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for batch mode (default: 10)')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')
    parser.add_argument('--limit', type=int, help='Limit number of products to process (for testing, e.g., --limit 20)')
    
    args = parser.parse_args()
    
    # Validate OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(" Missing OPENAI_API_KEY in .env")
    
    # Load products
    print(f"Loading products from: {args.products}")
    products = load_json(args.products)
    
    # Limit products if specified (for testing)
    if args.limit and args.limit < len(products):
        print(f"  Loaded {len(products)} products, limiting to first {args.limit} for testing")
        products = products[:args.limit]
    else:
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
    if args.mode == 'parallel':
        results = fill_metafields_parallel(
            products=products,
            metafield_definitions=metafield_definitions,
            category_name=category_name,
            model=args.model,
            max_workers=args.workers
        )
    elif args.mode == 'single':
        results = fill_metafields_single(
            products=products,
            metafield_definitions=metafield_definitions,
            category_name=category_name,
            model=args.model
        )
    else:  # batch mode
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


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dynamic_llm_filler.py
- Uses LLM to fill meta field values based on dynamically discovered meta fields
- Works with meta fields discovered from product samples
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import requests

load_dotenv()

# LLM Configuration
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "3000"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))

# Shopify Configuration
SHOPIFY_STORE_DOMAIN: str = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_ADMIN_ACCESS_TOKEN: str = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
SHOPIFY_API_VERSION: str = os.getenv("SHOPIFY_API_VERSION", "2024-07").strip()


def validate_environment() -> None:
    """Validate required environment variables."""
    missing: List[str] = []
    
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not SHOPIFY_STORE_DOMAIN:
        missing.append("SHOPIFY_STORE_DOMAIN")
    if not SHOPIFY_ADMIN_ACCESS_TOKEN:
        missing.append("SHOPIFY_ADMIN_ACCESS_TOKEN")
    
    if missing:
        raise SystemExit(
            f"Missing required environment variables: {', '.join(missing)}.\n"
            "Set them in .env or your environment and try again."
        )


def graphql_endpoint() -> str:
    return f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"


def shopify_headers() -> Dict[str, str]:
    return {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def make_graphql_request(query: str, variables: Optional[Dict] = None) -> Dict:
    """Make a GraphQL request to Shopify API."""
    if variables is None:
        variables = {}
    
    response = requests.post(
        graphql_endpoint(),
        headers=shopify_headers(),
        json={"query": query, "variables": variables}
    )
    
    if response.status_code != 200:
        raise SystemExit(f"HTTP {response.status_code}: {response.text}")
    
    data = response.json()
    if "errors" in data:
        raise SystemExit(f"GraphQL errors: {data['errors']}")
    
    return data["data"]


def create_dynamic_meta_field_prompt(product_data: Dict, discovered_fields: Dict[str, Any]) -> str:
    """Create a prompt for extracting meta field values using discovered fields."""
    
    # Build field descriptions from discovered fields
    field_descriptions = []
    for field_key, field_def in discovered_fields.items():
        field_type = field_def.get('type', 'single_line_text_field')
        field_name = field_def.get('name', field_key)
        field_desc = field_def.get('description', '')
        example_values = field_def.get('example_values', [])
        
        field_info = f"- {field_key} ({field_name}): {field_desc}"
        if example_values:
            field_info += f" [Examples: {', '.join(map(str, example_values[:3]))}]"
        field_descriptions.append(field_info)
    
    prompt = f"""
You are an expert e-commerce data extraction specialist. Analyze the following product information and extract the relevant meta field values using the discovered field definitions.

PRODUCT INFORMATION:
Title: {product_data.get('title', 'N/A')}
Description: {product_data.get('descriptionHtml', 'N/A')}
Tags: {', '.join(product_data.get('tags', []))}
Product Type: {product_data.get('productType', 'N/A')}
Vendor: {product_data.get('vendor', 'N/A')}

EXTRACT THESE SPECIFIC META FIELDS:
{chr(10).join(field_descriptions)}

INSTRUCTIONS:
1. Extract ONLY the requested meta field values from the product information
2. For numeric values, provide only the number (no units)
3. For boolean values, use true/false
4. For text values, be concise and specific
5. If information is not available, use null
6. Follow the exact field keys as specified above
7. Return ONLY a JSON object with the field keys as specified

RESPONSE FORMAT (JSON only, no other text):
{{
    "field_key1": "extracted_value_or_null",
    "field_key2": "extracted_value_or_null",
    ...
}}

Focus on accuracy and completeness. If you cannot determine a value from the available information, use null.
"""
    return prompt.strip()


def call_openai(prompt: str) -> str:
    """Call OpenAI API."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )
    
    if response.status_code != 200:
        raise SystemExit(f"OpenAI API error {response.status_code}: {response.text}")
    
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def parse_llm_response(response: str) -> Dict[str, Any]:
    """Parse LLM response and extract JSON."""
    # Try to find JSON in the response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON found in LLM response: {response}")
    
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {e}")


def fill_product_meta_fields_dynamic(product: Dict, discovered_fields: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """Fill meta fields for a single product using discovered field definitions."""
    if verbose:
        print(f"  Analyzing: {product.get('title', 'Unknown')}")
    
    try:
        # Create prompt using discovered fields
        prompt = create_dynamic_meta_field_prompt(product, discovered_fields)
        
        # Call LLM
        response = call_openai(prompt)
        
        # Parse response
        extracted_fields = parse_llm_response(response)
        
        if verbose:
            print(f"    ✅ Extracted {len(extracted_fields)} meta field values")
            for key, value in extracted_fields.items():
                print(f"      {key}: {value}")
        
        return extracted_fields
        
    except Exception as e:
        if verbose:
            print(f"    ❌ Error: {e}")
        return {}


def update_product_meta_fields(product_id: str, meta_fields: Dict[str, Any], discovered_fields: Dict[str, Any]) -> bool:
    """Update meta field values for a product in Shopify using discovered field types."""
    if not meta_fields:
        return True
    
    mutation = """
    mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          id
          key
          value
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    # Prepare metafields for the mutation
    metafield_inputs = []
    for key, value in meta_fields.items():
        if value is None:
            continue
        
        # Get field type from discovered fields
        field_def = discovered_fields.get(key, {})
        field_type = field_def.get('type', 'single_line_text_field')
        
        # Convert Shopify type format
        if 'number_integer' in field_type:
            shopify_type = "number_integer"
        elif 'number_decimal' in field_type:
            shopify_type = "number_decimal"
        elif 'boolean' in field_type:
            shopify_type = "boolean"
        else:
            shopify_type = "single_line_text_field"
        
        metafield_input = {
            "ownerId": product_id,
            "namespace": "spec",
            "key": key,
            "value": str(value),
            "type": shopify_type
        }
        
        metafield_inputs.append(metafield_input)
    
    if not metafield_inputs:
        return True
    
    variables = {"metafields": metafield_inputs}
    
    try:
        result = make_graphql_request(mutation, variables)
        metafields_set = result["metafieldsSet"]
        
        if metafields_set["userErrors"]:
            print(f"    ⚠️  User errors: {metafields_set['userErrors']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"    ❌ Update error: {e}")
        return False


def process_products_with_dynamic_llm(products: List[Dict], discovered_fields: Dict[str, Any], 
                                    update_shopify: bool = False, verbose: bool = False) -> List[Dict]:
    """Process multiple products with LLM using discovered meta fields."""
    print(f"🤖 Processing {len(products)} products with dynamic LLM...")
    
    processed_products = []
    successful = 0
    failed = 0
    
    for i, product in enumerate(products, 1):
        if verbose:
            print(f"\n[{i}/{len(products)}] Processing product...")
        
        # Create copy of product
        processed_product = product.copy()
        
        # Fill meta fields with LLM using discovered fields
        extracted_fields = fill_product_meta_fields_dynamic(product, discovered_fields, verbose)
        
        if extracted_fields:
            # Add extracted fields to product data
            if "metafields" not in processed_product:
                processed_product["metafields"] = {}
            
            processed_product["metafields"].update(extracted_fields)
            
            # Update in Shopify if requested
            if update_shopify:
                if verbose:
                    print(f"    📤 Updating meta fields in Shopify...")
                
                success = update_product_meta_fields(product["id"], extracted_fields, discovered_fields)
                if success:
                    successful += 1
                    if verbose:
                        print(f"    ✅ Updated in Shopify")
                else:
                    failed += 1
                    if verbose:
                        print(f"    ❌ Failed to update in Shopify")
            else:
                successful += 1
        else:
            failed += 1
        
        processed_products.append(processed_product)
        
        # Rate limiting
        time.sleep(1)
    
    print(f"\n📊 Dynamic LLM Processing Summary:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📝 Total processed: {len(products)}")
    
    return processed_products


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dynamic LLM meta field filler using discovered field definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process products with discovered meta fields
  python dynamic_llm_filler.py --input-file data/products.json --discovered-fields discovery_results.json
  
  # Update meta fields in Shopify after LLM processing
  python dynamic_llm_filler.py --input-file data/products.json --discovered-fields discovery_results.json --update-shopify
  
  # Process with verbose output
  python dynamic_llm_filler.py --input-file data/products.json --discovered-fields discovery_results.json --verbose
        """
    )
    
    parser.add_argument('--input-file', required=True, help='JSON file containing products')
    parser.add_argument('--discovered-fields', required=True, help='JSON file containing discovered meta field definitions')
    parser.add_argument('--output-file', help='Output file for processed products')
    parser.add_argument('--update-shopify', action='store_true', help='Update meta fields in Shopify after LLM processing')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    validate_environment()
    
    # Load products
    input_path = Path(args.input_file)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"📥 Loaded {len(products)} products from {input_path}")
    
    # Load discovered fields
    fields_path = Path(args.discovered_fields)
    if not fields_path.exists():
        raise SystemExit(f"Discovered fields file not found: {fields_path}")
    
    with open(fields_path, 'r', encoding='utf-8') as f:
        discovery_data = json.load(f)
    
    discovered_fields = discovery_data.get('discovered_fields', {})
    print(f"📋 Loaded {len(discovered_fields)} discovered meta field definitions")
    
    # Process products with dynamic LLM
    processed_products = process_products_with_dynamic_llm(
        products,
        discovered_fields,
        update_shopify=args.update_shopify,
        verbose=args.verbose
    )
    
    # Save results
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.parent / f"{input_path.stem}_dynamic_llm_processed.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_products, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved processed products to {output_path}")


if __name__ == "__main__":
    main()

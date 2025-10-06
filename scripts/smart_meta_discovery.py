#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
smart_meta_discovery.py
- LLM-powered meta field discovery and creation system
- Analyzes product samples to create search-optimized meta fields
- Designed for Arabic product recommendation bot integration
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
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

# Import existing modules
sys.path.append(str(Path(__file__).parent))
from fetch_products import make_graphql_request, graphql_endpoint, shopify_headers
from create_meta_fields import make_graphql_request as create_make_graphql_request


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


def get_sample_products(products: List[Dict], sample_percentage: float = 0.1) -> List[Dict]:
    """Get a random sample of products for analysis."""
    if not products:
        return []
    
    sample_size = max(1, int(len(products) * sample_percentage))
    sample_size = min(sample_size, len(products))  # Don't exceed total products
    
    return random.sample(products, sample_size)


def create_meta_field_discovery_prompt(products: List[Dict], category: str) -> str:
    """Create prompt for LLM to discover optimal meta fields for a category."""
    
    # Build product samples text
    products_text = ""
    for i, product in enumerate(products, 1):
        products_text += f"""
Product {i}:
Title: {product.get('title', 'N/A')}
Description: {product.get('descriptionHtml', 'N/A')}
Tags: {', '.join(product.get('tags', []))}
Product Type: {product.get('productType', 'N/A')}
Vendor: {product.get('vendor', 'N/A')}
"""
    
    prompt = f"""
You are an expert e-commerce data analyst specializing in creating optimal meta fields for product recommendation systems.

TASK: Analyze these {category} products and design meta fields that will enable:
1. Smart filtering (size ranges, price brackets, specifications)
2. Easy searching (brands, features, materials)
3. Product comparison (technical specs, ratings, features)
4. Arabic recommendation bot integration (slot-filling for user preferences)

PRODUCT SAMPLES ({len(products)} products):
{products_text}

REQUIREMENTS:
1. Create meta fields that are FILTERABLE, SEARCHABLE, and COMPARABLE
2. Use naming convention optimized for Arabic bot integration
3. Include technical specs, physical attributes, and features
4. Consider user decision-making factors (price, size, brand, features)
5. Make fields useful for product recommendations and cross-selling

META FIELD CATEGORIES TO CONSIDER:
- Technical Specifications (power, capacity, speed, resolution, etc.)
- Physical Attributes (size, weight, material, color, etc.)
- Features (smart features, modes, connectivity, etc.)
- Brand/Vendor Info (warranty, origin, model year, etc.)
- User Preferences (use case, difficulty level, target audience, etc.)

NAMING CONVENTION (for Arabic bot compatibility):
- Use descriptive keys that work in both English and Arabic contexts
- Include measurement units in the key (e.g., "power_w", "size_inch", "capacity_l")
- Use boolean fields for features (e.g., "smart_feature", "warranty_available")
- Use lists for multiple values (e.g., "compatible_brands", "color_options")

OUTPUT FORMAT (JSON only):
{{
    "meta_fields": {{
        "field_key": {{
            "name": "Display Name",
            "type": "number_integer|number_decimal|single_line_text_field|boolean|list.single_line_text_field",
            "description": "Field description for bot understanding",
            "category": "technical|physical|feature|brand|preference",
            "searchable": true|false,
            "filterable": true|false,
            "comparable": true|false,
            "arabic_keywords": ["كلمة1", "كلمة2"],
            "example_values": ["example1", "example2"]
        }}
    }},
    "reasoning": "Brief explanation of why these meta fields were chosen for the recommendation system"
}}

Focus on creating fields that will help users make informed decisions and enable the bot to provide accurate recommendations.
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


def parse_meta_field_discovery(response: str) -> Dict[str, Any]:
    """Parse LLM response and extract meta field definitions."""
    import re
    
    # Try to find JSON in the response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON found in LLM response: {response}")
    
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {e}")


def convert_to_shopify_definition(field_key: str, field_def: Dict[str, Any]) -> Dict[str, Any]:
    """Convert discovered meta field to Shopify meta field definition."""
    
    # Map LLM types to Shopify types
    type_mapping = {
        "number_integer": "number_integer",
        "number_decimal": "number_decimal", 
        "single_line_text_field": "single_line_text_field",
        "boolean": "boolean",
        "list.single_line_text_field": "single_line_text_field"  # Shopify doesn't have native lists
    }
    
    shopify_type = type_mapping.get(field_def["type"], "single_line_text_field")
    
    return {
        "name": field_def["name"],
        "namespace": "spec",
        "key": field_key,
        "type": shopify_type,
        "ownerType": "PRODUCT",
        "access": {"storefront": "PUBLIC_READ"},
        "description": field_def.get("description", ""),
        "validations": []
    }


def create_meta_field_definition(definition: Dict[str, Any]) -> Dict[str, Any]:
    """Create a single meta field definition in Shopify."""
    mutation = """
    mutation MetafieldDefinitionCreate($definition: MetafieldDefinitionInput!) {
      metafieldDefinitionCreate(definition: $definition) {
        createdDefinition {
          id
          key
          access {
            storefront
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {"definition": definition}
    return make_graphql_request(mutation, variables)


def discover_and_create_meta_fields(products: List[Dict], category: str, 
                                  sample_percentage: float = 0.1, 
                                  create_definitions: bool = True,
                                  verbose: bool = False) -> Dict[str, Any]:
    """Discover and create meta fields for a product category."""
    
    print(f"🔍 Discovering meta fields for {category} category...")
    print(f"📊 Total products: {len(products)}")
    
    # Get sample products
    sample_products = get_sample_products(products, sample_percentage)
    print(f"🎯 Analyzing sample of {len(sample_products)} products ({sample_percentage*100:.1f}%)")
    
    if verbose:
        print("\n📋 Sample products:")
        for i, product in enumerate(sample_products, 1):
            print(f"  {i}. {product.get('title', 'Unknown')}")
    
    # Create discovery prompt
    prompt = create_meta_field_discovery_prompt(sample_products, category)
    
    # Call LLM for discovery
    print("🤖 Analyzing products with LLM...")
    try:
        response = call_openai(prompt)
        discovery_result = parse_meta_field_discovery(response)
        
        print(f"✅ LLM discovered {len(discovery_result['meta_fields'])} meta fields")
        if verbose:
            print(f"💭 Reasoning: {discovery_result.get('reasoning', 'N/A')}")
        
    except Exception as e:
        print(f"❌ LLM discovery failed: {e}")
        return {"error": str(e)}
    
    # Convert to Shopify definitions and create them
    created_fields = {}
    failed_fields = {}
    
    if create_definitions:
        print("\n🔧 Creating meta field definitions in Shopify...")
        
        for field_key, field_def in discovery_result["meta_fields"].items():
            try:
                # Convert to Shopify format
                shopify_def = convert_to_shopify_definition(field_key, field_def)
                
                if verbose:
                    print(f"  Creating {field_key} ({field_def['name']})...")
                
                # Create in Shopify
                result = create_meta_field_definition(shopify_def)
                created_def = result["metafieldDefinitionCreate"]
                
                if created_def["userErrors"]:
                    print(f"    ❌ Error: {created_def['userErrors']}")
                    failed_fields[field_key] = created_def["userErrors"]
                else:
                    created = created_def["createdDefinition"]
                    print(f"    ✅ Created: {created['key']} (ID: {created['id']})")
                    created_fields[field_key] = {
                        "shopify_id": created["id"],
                        "definition": shopify_def,
                        "discovery_info": field_def
                    }
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    ❌ Failed to create {field_key}: {e}")
                failed_fields[field_key] = str(e)
    
    # Return comprehensive results
    return {
        "category": category,
        "total_products": len(products),
        "sample_size": len(sample_products),
        "sample_percentage": sample_percentage,
        "discovered_fields": discovery_result["meta_fields"],
        "reasoning": discovery_result.get("reasoning", ""),
        "created_fields": created_fields,
        "failed_fields": failed_fields,
        "success_count": len(created_fields),
        "failure_count": len(failed_fields)
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart meta field discovery using LLM analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover meta fields for blenders from JSON file
  python smart_meta_discovery.py --input-file data/products_with_lang.json --category blender
  
  # Analyze with custom sample size
  python smart_meta_discovery.py --input-file data/products_with_lang.json --category blender --sample-percentage 0.15
  
  # Discovery only (don't create definitions)
  python smart_meta_discovery.py --input-file data/products_with_lang.json --category blender --discovery-only
  
  # Verbose output
  python smart_meta_discovery.py --input-file data/products_with_lang.json --category blender --verbose
        """
    )
    
    parser.add_argument('--input-file', required=True, help='JSON file containing products')
    parser.add_argument('--category', required=True, help='Product category (blender, hair_dryer, drill, etc.)')
    parser.add_argument('--sample-percentage', type=float, default=0.1, help='Percentage of products to sample (default: 0.1 = 10%)')
    parser.add_argument('--discovery-only', action='store_true', help='Only discover fields, do not create definitions')
    parser.add_argument('--output-file', help='Output file for discovery results')
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
    
    # Discover and create meta fields
    results = discover_and_create_meta_fields(
        products,
        args.category,
        sample_percentage=args.sample_percentage,
        create_definitions=not args.discovery_only,
        verbose=args.verbose
    )
    
    # Save results
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.parent / f"{args.category}_meta_discovery_results.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Discovery results saved to {output_path}")
    
    # Summary
    print(f"\n📊 Discovery Summary:")
    print(f"  - Category: {results['category']}")
    print(f"  - Products analyzed: {results['total_products']}")
    print(f"  - Sample size: {results['sample_size']} ({results['sample_percentage']*100:.1f}%)")
    print(f"  - Fields discovered: {len(results['discovered_fields'])}")
    if not args.discovery_only:
        print(f"  - Fields created: {results['success_count']}")
        print(f"  - Failed creations: {results['failure_count']}")
    
    if args.verbose and results.get('reasoning'):
        print(f"\n💭 LLM Reasoning:")
        print(f"  {results['reasoning']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Match Product Tag to Shopify Category
Uses LLM to intelligently match a product tag to the best Shopify product category.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
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


def load_taxonomy(taxonomy_file: str = "data/shopify_taxonomy_full.json") -> Dict:
    """Load Shopify taxonomy data."""
    taxonomy_path = Path(taxonomy_file)
    
    if not taxonomy_path.exists():
        raise FileNotFoundError(
            f"Taxonomy file not found: {taxonomy_file}\n"
            f"Please run: python scripts/fetch_shopify_taxonomy.py"
        )
    
    with open(taxonomy_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_sample_products(products_file: str) -> List[Dict]:
    """Load sample products from JSON file."""
    with open(products_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_relevant_categories(tag: str, sample_products: List[Dict], all_categories: List[Dict], max_categories: int = 100) -> List[Dict]:
    """
    Filter categories to most relevant ones based on tag and product keywords.
    
    Args:
        tag: The product tag
        sample_products: Sample products
        all_categories: All available categories
        max_categories: Maximum number of categories to return
        
    Returns:
        Filtered list of relevant categories
    """
    print(f"  Filtering {len(all_categories)} categories to find most relevant...")
    
    # Extract keywords from tag and products
    keywords = set()
    keywords.add(tag.lower().replace("-", " ").replace("_", " "))
    
    for product in sample_products[:10]:  # Sample first 10 products
        title = product.get('title', '').lower()
        product_type = product.get('productType', '').lower()
        keywords.add(title)
        keywords.add(product_type)
    
    # Score each category based on keyword matches
    scored_categories = []
    
    for category in all_categories:
        full_name = category.get('fullName', '').lower()
        name = category.get('name', '').lower()
        
        score = 0
        for keyword in keywords:
            if keyword and len(keyword) > 2:
                if keyword in full_name:
                    score += 3
                if keyword in name:
                    score += 5
        
        if score > 0:
            scored_categories.append((score, category))
    
    # Sort by score and take top N
    scored_categories.sort(reverse=True, key=lambda x: x[0])
    filtered = [cat for score, cat in scored_categories[:max_categories]]
    
    print(f"  Filtered to {len(filtered)} most relevant categories")
    
    return filtered if filtered else all_categories[:max_categories]


def match_tag_to_category(
    tag: str,
    sample_products: List[Dict],
    categories: List[Dict],
    model: str = "gpt-4o"
) -> Dict:
    """
    Use LLM to match a tag to the best Shopify category.
    
    Args:
        tag: The product tag (e.g., "water-pump", "tv")
        sample_products: Sample products with this tag
        categories: List of Shopify categories with metafields
        model: OpenAI model to use
        
    Returns:
        Dictionary with matched category and confidence
    """
    print(f"\n Matching tag '{tag}' to Shopify category using {model}...")
    
    # Filter to relevant categories first (reduce token count!)
    relevant_categories = filter_relevant_categories(tag, sample_products, categories, max_categories=50)
    
    # Prepare category list for LLM
    category_list = "\n".join([
        f"- {cat['fullName']} (ID: {cat['id']})"
        for cat in relevant_categories
    ])
    
    # Prepare sample product info
    product_samples = []
    for i, product in enumerate(sample_products[:5], 1):  # Take 5 samples
        product_samples.append(
            f"{i}. Title: {product.get('title', 'N/A')}\n"
            f"   Type: {product.get('productType', 'N/A')}\n"
            f"   Vendor: {product.get('vendor', 'N/A')}\n"
            f"   Tags: {', '.join(product.get('tags', []))}"
        )
    
    product_info = "\n\n".join(product_samples)
    
    # Create prompt
    prompt = f"""You are analyzing products to match them to Shopify's standard product taxonomy.

TAG: "{tag}"

SAMPLE PRODUCTS WITH THIS TAG:
{product_info}

AVAILABLE SHOPIFY CATEGORIES (choose ONE that best matches):
{category_list}

INSTRUCTIONS:
1. Analyze the sample products carefully
2. Identify the most specific Shopify category that matches these products
3. Choose the category that best represents what these products ARE (not just what they're used for)
4. Return ONLY valid JSON in this exact format:

{{
  "category_id": "gid://shopify/ProductTaxonomyNode/...",
  "category_full_name": "Full Category Name > Subcategory",
  "confidence": "high|medium|low",
  "reasoning": "Brief explanation of why this category fits"
}}

Return only the JSON, no other text."""
    
    # Call OpenAI API
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a product categorization expert. You always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        result = json.loads(result_text)
        
        print(f"  Matched to: {result['category_full_name']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Reasoning: {result['reasoning']}")
        
        return result
        
    except Exception as e:
        print(f"  Error matching category: {e}")
        raise


def normalize_category_id(category_id: str) -> str:
    """Normalize category ID to handle different GID formats."""
    # Extract the actual ID part (e.g., "el-17-4" from "gid://shopify/.../el-17-4")
    if "/" in category_id:
        return category_id.split("/")[-1]
    return category_id


def get_category_metafields(category_id: str, taxonomy_data: Dict) -> Optional[Dict]:
    """Get metafield definitions for a specific category."""
    normalized_id = normalize_category_id(category_id)
    
    # First try exact match with normalization
    for cat in taxonomy_data["categories_with_metafields"]:
        if normalize_category_id(cat["id"]) == normalized_id:
            return cat
    
    # If no exact match, search all categories to find this one
    target_category = None
    for cat in taxonomy_data["all_categories"]:
        if normalize_category_id(cat["id"]) == normalized_id:
            target_category = cat
            break
    
    if not target_category:
        return None
    
    # Category exists but has no metafields
    # Try to find a parent category with metafields by matching fullName prefix
    full_name = target_category.get("fullName", "")
    
    print(f"\n  Category '{full_name}' has no metafields")
    print(f"  Looking for parent category with metafields...")
    
    # Look for categories with similar names (parent categories)
    name_parts = full_name.split(" > ")
    
    # Try progressively shorter parent paths
    for i in range(len(name_parts) - 1, 0, -1):
        parent_path = " > ".join(name_parts[:i])
        
        for cat in taxonomy_data["categories_with_metafields"]:
            if cat["fullName"] == parent_path or cat["fullName"].startswith(parent_path):
                print(f"  Found parent category with metafields: {cat['fullName']}")
                return cat
    
    return None


def save_category_mapping(
    tag: str,
    match_result: Dict,
    category_data: Dict,
    output_dir: str
) -> None:
    """Save category mapping and metafield definitions for this tag."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    mapping = {
        "tag": tag,
        "category": {
            "id": match_result["category_id"],
            "name": category_data["name"],
            "fullName": category_data["fullName"],
            "confidence": match_result["confidence"],
            "reasoning": match_result["reasoning"]
        },
        "metafields": category_data["metafields"]
    }
    
    # Save tag-specific mapping (sanitize tag for filename)
    safe_tag = tag.replace(' ', '_').replace('/', '_')
    mapping_file = output_path / f"tag_{safe_tag}_category_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved category mapping: {mapping_file}")
    print(f"Found {len(category_data['metafields'])} metafields for this category")
    
    # Print metafields summary
    if category_data['metafields']:
        print("\n Available Metafields:")
        for mf in category_data['metafields']:
            print(f"  - {mf['name']} ({mf['key']}) - {mf['type']}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Match product tag to Shopify category using LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Match water-pump tag
  python scripts/match_tag_to_category.py --tag water-pump --products exports/tag_water-pump/products_tag_water-pump_with_lang.json
  
  # Match tv tag
  python scripts/match_tag_to_category.py --tag tv --products exports/tag_tv/products_tag_tv_with_lang.json
        """
    )
    
    parser.add_argument('--tag', required=True, help='Product tag to match')
    parser.add_argument('--products', required=True, help='Path to products JSON file')
    parser.add_argument('--taxonomy', default='data/shopify_taxonomy_full.json', help='Path to taxonomy file')
    parser.add_argument('--output-dir', help='Output directory (default: same as products file)')
    parser.add_argument('--model', default='gpt-4o', help='OpenAI model to use (default: gpt-4o)')
    
    args = parser.parse_args()
    
    # Load taxonomy
    print(" Loading Shopify taxonomy...")
    taxonomy_data = load_taxonomy(args.taxonomy)
    print(f" Loaded {len(taxonomy_data['categories_with_metafields'])} categories with metafields")
    
    # Load sample products
    print(f"\nLoading products from: {args.products}")
    products = load_sample_products(args.products)
    print(f"  Loaded {len(products)} products")
    
    # Match tag to category
    match_result = match_tag_to_category(
        tag=args.tag,
        sample_products=products,
        categories=taxonomy_data["categories_with_metafields"],
        model=args.model
    )
    # Get category metafields
    category_data = get_category_metafields(match_result["category_id"], taxonomy_data)
    if not category_data:
        raise SystemExit(f"Could not find category data for: {match_result['category_id']}")
    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        # Use same directory as products file
        output_dir = Path(args.products).parent
    # Save mapping
    save_category_mapping(args.tag, match_result, category_data, output_dir)
    print("\nCategory matching complete!")
    print(f"\nNext step: Use this mapping to fill metafields for all products with tag '{args.tag}'")


if __name__ == "__main__":
    main()


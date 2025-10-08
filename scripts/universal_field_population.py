#!/usr/bin/env python3
"""
Universal field population that works with ANY collection type.
"""

import json
import re
from pathlib import Path
from collections import Counter
import html


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

def detect_collection_type(products: list) -> str:
    """Detect collection type from product data using AI analysis."""
    if not products:
        return 'generic'
    
    # Use the same analysis logic as dynamic_product_analyzer
    from dynamic_product_analyzer import analyze_product_tags
    analysis = analyze_product_tags(products)
    return analysis.get('detected_category', 'generic')

def extract_universal_data(product: dict, meta_field_definitions: dict) -> dict:
    """Extract data for any field type dynamically."""
    title = product.get('title', '').lower()
    description_html = product.get('descriptionHtml', '')
    description = clean_html(description_html).lower()
    tags = [tag.lower() for tag in product.get('tags', [])]
    vendor = product.get('vendor', '').lower()
    
    extracted_data = {}
    
    # Extract each discovered field dynamically
    for field_key, field_def in meta_field_definitions.items():
        extracted_value = ""
        
        if field_key in ['brand_vendor', 'brand', 'brand_name']:
            # Extract from vendor, tags, or title
            if vendor:
                extracted_value = vendor
            else:
                # Look for brand names in tags or title
                for tag in tags:
                    if any(brand_word in tag for brand_word in ['brand', 'marka', 'علامة']):
                        extracted_value = tag
                        break
                if not extracted_value:
                    # Extract from title (first word or known brand patterns)
                    title_words = title.split()
                    if title_words and len(title_words[0]) > 2:
                        extracted_value = title_words[0]
        
        elif field_key == 'material':
            # Extract material from title, description, or tags
            material_keywords = ['steel', 'wood', 'plastic', 'metal', 'aluminum', 'glass', 'fiber', 'carbon', 'حديد', 'خشب', 'بلاستيك', 'معدن', 'ألمنيوم', 'زجاج']
            for keyword in material_keywords:
                if keyword in title or keyword in description or any(keyword in tag for tag in tags):
                    extracted_value = keyword
                    break
        
        elif field_key == 'product_type':
            # Extract product type from title with better logic
            title_lower = title.lower()
            
            # Check for specific product types in title
            if any(keyword in title_lower for keyword in ['رطب', 'wet', 'شوربة', 'soup', 'طرية', 'soft']):
                extracted_value = 'wet_food'
            elif any(keyword in title_lower for keyword in ['جاف', 'dry', 'كروكيت', 'croquettes', 'بسكويت', 'biscuit', 'طعام جاف']):
                extracted_value = 'dry_food'
            elif any(keyword in title_lower for keyword in ['مكافآت', 'treats', 'snack', 'وجبة خفيفة']):
                extracted_value = 'treats'
            elif any(keyword in title_lower for keyword in ['مكمل', 'supplement', 'فيتامين', 'vitamin']):
                extracted_value = 'supplements'
            else:
                # Fallback to first tag or title word
                if tags:
                    extracted_value = tags[0]
                else:
                    title_words = title.split()
                    if title_words:
                        extracted_value = title_words[0]
        
        elif field_key == 'age_target':
            # Extract age target from description or title
            age_keywords = ['kitten', 'adult', 'senior', 'puppy', 'هريرة', 'بالغ', 'مسن', 'جرو']
            for keyword in age_keywords:
                if keyword in title or keyword in description:
                    extracted_value = keyword
                    break
            # Also check for age ranges in description
            if not extracted_value:
                age_patterns = [r'(\d+)\+', r'(\d+)\s*months?', r'(\d+)\s*years?']
                for pattern in age_patterns:
                    match = re.search(pattern, description)
                    if match:
                        age_num = int(match.group(1))
                        if age_num <= 6:
                            extracted_value = 'kitten'
                        elif age_num <= 12:
                            extracted_value = 'adult'
                        else:
                            extracted_value = 'senior'
                        break
        
        elif field_key in ['weight', 'weight_range', 'package_size', 'size']:
            # Extract weight from title or description
            weight_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:g|kg|gram|كيلو|جرام)',
                r'(\d+(?:\.\d+)?)\s*(?:oz|ounce)',
                r'(\d+(?:\.\d+)?)\s*(?:lb|pound)',
                r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(?:g|kg|gram|كيلو|جرام)',  # For patterns like "12x40g"
                r'(\d+(?:\.\d+)?)\s*×\s*(\d+(?:\.\d+)?)\s*(?:g|kg|gram|كيلو|جرام)'   # For patterns like "12×40g"
            ]
            for pattern in weight_patterns:
                match = re.search(pattern, title + ' ' + description, re.IGNORECASE)
                if match:
                    if 'x' in pattern or '×' in pattern:
                        # Handle multi-pack patterns like "12x40g"
                        extracted_value = match.group(0)
                    else:
                        extracted_value = match.group(0)
                    break
        
        elif field_key == 'dietary_features':
            # Extract dietary features from description or title
            dietary_keywords = [
                'grain-free', 'gluten-free', 'organic', 'natural', 'premium',
                'high-protein', 'low-fat', 'digestive', 'sensitive',
                'خالي من الحبوب', 'عضوي', 'طبيعي', 'بروتين عالي', 'قليل الدهون'
            ]
            features = []
            for keyword in dietary_keywords:
                if keyword in title or keyword in description:
                    features.append(keyword)
            if features:
                extracted_value = ', '.join(features)
        
        elif field_key in ['features', 'key_features', 'dietary_features']:
            # Extract features from description or tags
            feature_keywords = [
                'waterproof', 'fireproof', 'durable', 'lightweight', 'heavy', 'portable',
                'grain-free', 'gluten-free', 'organic', 'natural', 'premium',
                'high-protein', 'low-fat', 'digestive', 'sensitive',
                'خالي من الحبوب', 'عضوي', 'طبيعي', 'بروتين عالي', 'قليل الدهون',
                'غني بالفيتامينات', 'متوازن', 'كامل', 'صحي'
            ]
            features = []
            for keyword in feature_keywords:
                if keyword in title or keyword in description or any(keyword in tag for tag in tags):
                    features.append(keyword)
            if features:
                extracted_value = ', '.join(features)
        
        elif field_key == 'origin_country':
            # Extract from description or tags
            country_keywords = ['china', 'germany', 'usa', 'japan', 'korea', 'taiwan']
            for keyword in country_keywords:
                if keyword in description or any(keyword in tag for tag in tags):
                    extracted_value = keyword
                    break
        
        elif field_key == 'price_range':
            # Extract from variant prices
            variants = product.get('variants', [])
            if variants:
                prices = [float(v.get('price', 0)) for v in variants if v.get('price')]
                if prices:
                    min_price = min(prices)
                    if min_price < 10:
                        extracted_value = "Under 10 JOD"
                    elif min_price < 50:
                        extracted_value = "10-50 JOD"
                    elif min_price < 100:
                        extracted_value = "50-100 JOD"
                    elif min_price < 200:
                        extracted_value = "100-200 JOD"
                    else:
                        extracted_value = "200+ JOD"
        
        # If no specific extraction logic found, try generic extraction
        if not extracted_value:
            # Try to extract from title or description based on field name
            if 'weight' in field_key.lower():
                # Look for any weight patterns
                weight_patterns = [r'(\d+(?:\.\d+)?)\s*(?:g|kg|gram|كيلو|جرام|oz|ounce|lb|pound)']
                for pattern in weight_patterns:
                    match = re.search(pattern, title + ' ' + description, re.IGNORECASE)
                    if match:
                        extracted_value = match.group(0)
                        break
            elif 'price' in field_key.lower():
                # Look for price patterns
                price_patterns = [r'(\d+(?:\.\d+)?)\s*(?:jd|jod|دينار|ريال)']
                for pattern in price_patterns:
                    match = re.search(pattern, title + ' ' + description, re.IGNORECASE)
                    if match:
                        extracted_value = match.group(0)
                        break
            elif 'feature' in field_key.lower() or 'benefit' in field_key.lower():
                # Look for feature keywords
                feature_keywords = ['غني', 'مفيد', 'صحي', 'طبيعي', 'عضوي', 'متوازن', 'كامل']
                for keyword in feature_keywords:
                    if keyword in title or keyword in description:
                        extracted_value = keyword
                        break
        
        # Store the extracted value
        extracted_data[field_key] = extracted_value
    
    return extracted_data

def populate_products_with_discovered_fields(products: list, meta_field_definitions: dict, field_categories: dict) -> dict:
    """
    Populate products with discovered meta field values.
    
    Args:
        products: List of products to populate
        meta_field_definitions: Discovered meta field definitions
        field_categories: Field categories and options
        
    Returns:
        Population statistics
    """
    print("Populating products with discovered field values...")
    
    stats = Counter()
    
    for product in products:
        # Ensure metafields dict exists
        if 'metafields' not in product:
            product['metafields'] = {}
        
        # Extract data for all discovered fields
        extracted_data = extract_universal_data(product, meta_field_definitions)
        
        # Store extracted values
        for field_key, value in extracted_data.items():
            product['metafields'][f"{field_key}_original"] = value
            stats[f"{field_key}_original"] += 1
    
    print(f"Populated {len(products)} products with field values")
    return dict(stats)

def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Universal Field Population')
    parser.add_argument('input_file', help='Input JSON file path')
    parser.add_argument('-o', '--output', help='Output JSON file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Load data
    with open(args.input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        products = data
    elif isinstance(data, dict) and 'products' in data:
        products = data['products']
    else:
        products = [data]
    
    # Get meta field definitions and categories
    meta_field_definitions = data.get('meta_field_definitions', {})
    field_categories = data.get('field_categories', {})
    
    if not meta_field_definitions:
        print("ERROR: No meta field definitions found in input file")
        return
    
    # Populate products
    stats = populate_products_with_discovered_fields(products, meta_field_definitions, field_categories)
    
    # Save results
    output_file = args.output or str(Path(args.input_file).parent / f"{Path(args.input_file).stem}_populated.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Results saved to: {output_file}")
    print(f"Population stats: {stats}")

if __name__ == "__main__":
    main()
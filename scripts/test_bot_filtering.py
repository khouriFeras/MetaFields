#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_bot_filtering.py
- Test script to demonstrate Arabic bot filtering with dog food meta fields
- Shows how the bot would filter products based on user queries
"""

import json
from pathlib import Path
from typing import List, Dict, Any


def load_products(file_path: str) -> List[Dict]:
    """Load cleaned product data."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_by_age_group(products: List[Dict], age_query: str) -> List[Dict]:
    """Filter products by age group."""
    age_mapping = {
        "جراء": ["جراء", "puppy", "puppies"],
        "كلاب بالغة": ["بالغة", "بالغ", "adult", "adults"],
        "كلاب صغيرة": ["صغيرة", "صغير", "small"],
        "كلاب كبيرة": ["كبيرة", "كبير", "large"]
    }
    
    results = []
    for product in products:
        if 'metafields' in product:
            age_group = product['metafields'].get('age_group', '')
            if age_group and age_group != 'None':
                age_group = age_group.lower()
                
                # Check if any of the query keywords match the age group
                for age_key, keywords in age_mapping.items():
                    if any(keyword in age_group for keyword in keywords):
                        if any(keyword in age_query.lower() for keyword in keywords):
                            results.append(product)
                            break
    
    return results


def filter_by_brand(products: List[Dict], brand_query: str) -> List[Dict]:
    """Filter products by brand."""
    results = []
    brand_query_lower = brand_query.lower()
    
    for product in products:
        if 'metafields' in product:
            brand_name = product['metafields'].get('brand_name', '')
            if brand_name and brand_name != 'None':
                brand_name = brand_name.lower()
                if brand_query_lower in brand_name or brand_name in brand_query_lower:
                    results.append(product)
    
    return results


def filter_by_weight(products: List[Dict], weight_query: str) -> List[Dict]:
    """Filter products by weight."""
    results = []
    
    # Extract weight from query
    import re
    weight_match = re.search(r'(\d+(?:\.\d+)?)', weight_query)
    if not weight_match:
        return results
    
    target_weight = float(weight_match.group(1))
    
    for product in products:
        if 'metafields' in product:
            weight = product['metafields'].get('weight_kg')
            if weight and abs(float(weight) - target_weight) <= 0.5:  # Allow 0.5kg tolerance
                results.append(product)
    
    return results


def filter_by_product_type(products: List[Dict], type_query: str) -> List[Dict]:
    """Filter products by type."""
    type_mapping = {
        "طعام جاف": ["جاف", "dry", "kibble"],
        "طعام رطب": ["رطب", "wet", "moist"],
        "مكافآت": ["مكافآت", "treats", "rewards"],
        "عظام": ["عظام", "bones"]
    }
    
    results = []
    type_query_lower = type_query.lower()
    
    for product in products:
        if 'metafields' in product:
            product_type = product['metafields'].get('product_type', '')
            if product_type and product_type != 'None':
                product_type = product_type.lower()
                
                for type_key, keywords in type_mapping.items():
                    if any(keyword in type_key.lower() for keyword in keywords):
                        if any(keyword in type_query_lower for keyword in keywords):
                            results.append(product)
                            break
    
    return results


def filter_by_size(products: List[Dict], size_query: str) -> List[Dict]:
    """Filter products by dog size."""
    size_mapping = {
        "صغيرة": ["صغيرة", "صغير", "small", "<10"],
        "متوسطة": ["متوسطة", "متوسط", "medium", "11-25"],
        "كبيرة": ["كبيرة", "كبير", "large", "26-44"],
        "عملاقة": ["عملاقة", "giant", "45+", ">45"]
    }
    
    results = []
    size_query_lower = size_query.lower()
    
    for product in products:
        if 'metafields' in product:
            target_weight = product['metafields'].get('target_weight_kg', '')
            if target_weight and target_weight != 'None':
                target_weight = target_weight.lower()
                
                for size_key, keywords in size_mapping.items():
                    if any(keyword in target_weight for keyword in keywords):
                        if any(keyword in size_query_lower for keyword in keywords):
                            results.append(product)
                            break
    
    return results


def search_products(products: List[Dict], query: str) -> List[Dict]:
    """Search products based on Arabic query."""
    query_lower = query.lower()
    results = []
    
    for product in products:
        if 'metafields' in product:
            metafields = product['metafields']
            
            # Search in all text fields
            searchable_fields = ['product_title', 'brand_name', 'product_type', 
                               'nutritional_benefits', 'ingredients', 'special_features']
            
            found = False
            for field in searchable_fields:
                value = metafields.get(field, '')
                if value and value != 'None' and query_lower in str(value).lower():
                    found = True
                    break
            
            if found:
                results.append(product)
    
    return results


def format_product_card(product: Dict) -> str:
    """Format product as a bot card."""
    metafields = product.get('metafields', {})
    
    title = metafields.get('product_title', product.get('title', 'Unknown'))
    brand = metafields.get('brand_name', 'Unknown')
    product_type = metafields.get('product_type', 'Unknown')
    weight = metafields.get('weight_kg', 'Unknown')
    age_group = metafields.get('age_group', 'Unknown')
    
    card = f"""
🏷️ **{title}**
🏢 الماركة: {brand}
📦 النوع: {product_type}
⚖️ الوزن: {weight} كجم
🐕 العمر: {age_group}
"""
    
    # Add special features if available
    special_features = metafields.get('special_features')
    if special_features and special_features != 'None':
        card += f"✨ الميزات: {special_features}\n"
    
    # Add nutritional benefits if available
    benefits = metafields.get('nutritional_benefits')
    if benefits and benefits != 'None':
        card += f"💪 الفوائد: {benefits}\n"
    
    return card


def test_bot_queries(products: List[Dict]) -> None:
    """Test various Arabic bot queries."""
    
    print("🤖 Arabic Dog Food Bot - Test Queries")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        "بدي طعام للجراء",
        "بدي رويال كانين", 
        "بدي كيس 12 كيلو",
        "بدي طعام جاف",
        "بدي للكلاب الصغيرة",
        "بدي طعام بالدجاج",
        "بدي مكافآت",
        "بدي طعام يدعم المناعة"
    ]
    
    for query in test_queries:
        print(f"\n🔍 المستخدم: {query}")
        print("-" * 40)
        
        # Apply different filters based on query
        results = products.copy()
        
        # Age group filter
        if any(word in query for word in ["جراء", "puppy"]):
            results = filter_by_age_group(results, query)
        elif any(word in query for word in ["صغيرة", "كبيرة", "متوسطة"]):
            results = filter_by_size(results, query)
        
        # Brand filter
        if "رويال" in query or "royal" in query.lower():
            results = filter_by_brand(results, query)
        
        # Weight filter
        if "كيلو" in query or "kg" in query.lower():
            results = filter_by_weight(results, query)
        
        # Type filter
        if any(word in query for word in ["جاف", "رطب", "مكافآت", "عظام"]):
            results = filter_by_product_type(results, query)
        
        # General search
        if len(results) == len(products):  # No specific filter applied
            results = search_products(results, query)
        
        # Limit to top 4 results
        results = results[:4]
        
        if results:
            print(f"✅ وجدت {len(results)} منتج:")
            for i, product in enumerate(results, 1):
                print(f"\n{i}. {format_product_card(product)}")
        else:
            print("❌ لم أجد منتجات تطابق طلبك")
        
        print("-" * 40)


def main():
    """Main function."""
    # Load cleaned data
    data_file = "exports/collection_أطعمة_ومكافآت_كلاب_smart_processed_dynamic_llm_processed_cleaned.json"
    
    if not Path(data_file).exists():
        print(f"❌ Data file not found: {data_file}")
        return
    
    products = load_products(data_file)
    print(f"📥 Loaded {len(products)} dog food products")
    
    # Test bot queries
    test_bot_queries(products)
    
    # Show statistics
    print(f"\n📊 Data Statistics:")
    print(f"  - Total products: {len(products)}")
    
    # Count by brand
    brands = {}
    for product in products:
        if 'metafields' in product:
            brand = product['metafields'].get('brand_name', 'Unknown')
            brands[brand] = brands.get(brand, 0) + 1
    
    print(f"  - Brands:")
    for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True):
        print(f"    * {brand}: {count} products")
    
    # Count by product type
    types = {}
    for product in products:
        if 'metafields' in product:
            product_type = product['metafields'].get('product_type', 'Unknown')
            types[product_type] = types.get(product_type, 0) + 1
    
    print(f"  - Product types:")
    for product_type, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
        print(f"    * {product_type}: {count} products")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic Product Analyzer
Analyzes product tags, vendors, and content to dynamically create appropriate meta fields.
"""

import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from collections import Counter, defaultdict
import random
import openai
from dotenv import load_dotenv
import html
import sys

# Load environment variables
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


def analyze_product_tags(products: List[Dict]) -> Dict[str, Any]:
    """
    Analyze product tags to determine product categories and characteristics.
    
    Args:
        products: List of products
        
    Returns:
        Analysis results including detected categories and tag patterns
    """
    print(" Analyzing product tags and characteristics...")
    
    all_tags = []
    all_vendors = []
    all_titles = []
    all_descriptions = []
    all_product_types = []
    
    for product in products:
        # Collect tags
        tags = product.get('tags', [])
        all_tags.extend(tags)
        
        # Collect vendors
        vendor = product.get('vendor', '')
        if vendor:
            all_vendors.append(vendor)
        
        # Collect titles
        title = product.get('title', '')
        if title:
            all_titles.append(title)
        
        # Collect descriptions
        description = product.get('descriptionHtml', '')
        if description:
            all_descriptions.append(description)
        
        # Collect product types
        product_type = product.get('productType', '')
        if product_type:
            all_product_types.append(product_type)
    
    # Analyze tag patterns
    tag_counter = Counter(all_tags)
    vendor_counter = Counter(all_vendors)
    product_type_counter = Counter(all_product_types)
    
    # Detect main product category from tags - UPDATED FOR YOUR WEBSITE
    category_keywords = {
        'home_kitchen': ['منزل', 'مطبخ', 'kitchen', 'home', 'cookware', 'tableware', 'utensils', 'أدوات مطبخ', 'أواني', 'طبخ', 'طهي', 'cooking'],
        'tools_equipment': ['عدد', 'ادوات', 'أدوات', 'tools', 'equipment', 'hardware', 'drill', 'hammer', 'saw', 'مفك', 'شاكوش', 'منشار', 'مثقاب'],
        'furniture_accessories': ['اكسسوارات', 'أثاث', 'furniture', 'accessories', 'decor', 'decoration', 'ديكور', 'مفروشات', 'كراسي', 'طاولات'],
        'sanitary_supplies': ['لوازم صحية', 'حمام', 'sanitary', 'bathroom', 'plumbing', 'sink', 'toilet', 'shower', 'صنبور', 'مرحاض', 'دش'],
        'lighting_electrical': ['انارة', 'إنارة', 'كهرباء', 'lighting', 'electrical', 'light', 'lamp', 'bulb', 'switch', 'مصباح', 'لمبة', 'مفتاح كهرباء'],
        'paint_coating': ['دهان', 'طلاء', 'paint', 'coating', 'primer', 'varnish', 'brush', 'roller', 'فرشاة', 'رول', 'بويا'],
        'garden': ['حديقة', 'garden', 'outdoor', 'plant', 'lawn', 'irrigation', 'hose', 'نباتات', 'ري', 'خرطوم', 'زراعة'],
        'automotive': ['سيارة', 'سيارات', 'car', 'auto', 'automotive', 'vehicle', 'tire', 'oil', 'battery', 'إطار', 'زيت', 'بطارية'],
        'safety_security': ['سلامة', 'امان', 'أمان', 'safety', 'security', 'lock', 'alarm', 'camera', 'قفل', 'إنذار', 'كاميرا', 'حماية'],
        'storage': ['تخزين', 'storage', 'organization', 'container', 'box', 'shelf', 'cabinet', 'صندوق', 'رف', 'خزانة', 'تنظيم'],
        'travel_camping': ['سفر', 'تخييم', 'travel', 'camping', 'outdoor', 'tent', 'backpack', 'خيمة', 'حقيبة ظهر', 'رحلات'],
        'smart_home': ['منزل ذكي', 'smart home', 'automation', 'smart', 'wifi', 'iot', 'connected', 'ذكي', 'أتمتة', 'متصل'],
        'pets': ['حيوانات', 'أليفة', 'حيوانات أليفة', 'pets', 'pet', 'dog', 'cat', 'كلب', 'قطة', 'حيوان', 'طعام حيوانات', 'مكافآت']
    }
    
    # Count category matches in tags
    category_scores = {}
    all_text = ' '.join(all_tags + all_titles + all_descriptions).lower()
    
    for category, keywords in category_keywords.items():
        score = sum(1 for keyword in keywords if keyword in all_text)
        category_scores[category] = score
    
    # Determine main category
    detected_category = max(category_scores.items(), key=lambda x: x[1])[0]
    if category_scores[detected_category] == 0:
        detected_category = 'general'
    
    return {
        'detected_category': detected_category,
        'category_scores': category_scores,
        'top_tags': dict(tag_counter.most_common(20)),
        'top_vendors': dict(vendor_counter.most_common(10)),
        'top_product_types': dict(product_type_counter.most_common(10)),
        'total_products': len(products),
        'unique_tags': len(set(all_tags)),
        'unique_vendors': len(set(all_vendors))
    }


def create_dynamic_meta_field_prompt(products: List[Dict], analysis: Dict[str, Any]) -> str:
    """
    Create a prompt for dynamic meta field discovery based on product analysis.
    
    Args:
        products: Sample products for analysis
        analysis: Product analysis results
        
    Returns:
        Prompt string for LLM
    """
    detected_category = analysis['detected_category']
    top_tags = analysis['top_tags']
    top_vendors = analysis['top_vendors']
    top_product_types = analysis['top_product_types']
    
    # Sample products for analysis
    sample_products = random.sample(products, min(10, len(products)))
    
    products_text = "\n\n".join([
        f"Product {i+1}:\n"
        f"Title: {p.get('title', 'N/A')}\n"
        f"Vendor: {p.get('vendor', 'N/A')}\n"
        f"Product Type: {p.get('productType', 'N/A')}\n"
        f"Price: {p.get('priceRange', 'N/A')}\n"
        f"Tags: {', '.join(p.get('tags', []))}\n"
        f"Body HTML/Description: {clean_html(p.get('descriptionHtml', ''))[:2000]}\n"
        f"Existing Meta Fields: {p.get('metafields', {})}"
        for i, p in enumerate(sample_products)
    ])
    
    prompt = f"""Analyze these {len(sample_products)} products and create a meta field system for filtering.

CATEGORY: {detected_category}
TOP BRANDS: {', '.join(list(top_vendors.keys())[:5])}
TOP TYPES: {', '.join(list(top_product_types.keys())[:5])}

PRODUCTS:
{products_text}

TASK: Create 5-7 meta fields customers can filter by. Read the Body HTML carefully.

CONTEXT-AWARE FIELD SELECTION:
- For FOOD products: brand, product_type, key_features, size_weight, target_audience, special_attributes
- For TOYS: brand, product_type, material, key_features, target_audience, special_attributes (NO weight!)
- For LITTER: brand, product_type, material, size_weight, key_features, special_attributes
- For ACCESSORIES: brand, product_type, material, size, color, special_attributes
- For ELECTRONICS: brand, product_type, power_rating, features, special_attributes

ADAPT FIELDS TO PRODUCT TYPE:
1. brand_vendor - Always include
2. product_type - Main category (4-8 types based on actual products)
3. Choose relevant fields from: material, size_weight, color, key_features, power_rating, etc.
4. target_audience - Age/use case if relevant
5. special_attributes - UNIQUE claims (Made in X, Certified, Awards, Vet Recommended)

For TOYS specifically:
- MUST include: material (fabric, plastic, sisal, wood, feather, etc.)
- SKIP: size_weight (not important for toys)
- Include: toy_type or product_type with specific toy categories
- Include: key_features (interactive, with catnip, durable, etc.)

CATEGORIES: Create 4-8 options per field based on ACTUAL product data.

OUTPUT (JSON only):
{{
    "meta_fields": {{
        "brand_vendor": {{
            "name": "Brand (الماركة)",
            "type": "single_line_text_field",
            "multi_select": false,
            "description": "Product brand",
            "category": "brand",
            "searchable": true,
            "filterable": true,
            "comparable": true,
            "arabic_keywords": ["ماركة"],
            "example_values": ["Brand1", "Brand2"]
        }}
    }},
    "field_categories": {{
        "brand_vendor": [
            {{"value": "brand1", "label": "Brand Name (الاسم)"}},
            {{"value": "brand2", "label": "Brand Name 2 (الاسم 2)"}}
        ]
    }},
    "reasoning": "Why these fields"
}}"""
    return prompt.strip()


def call_openai(prompt: str, max_tokens: int = 3000) -> str:
    """Call OpenAI API with optimized parameters."""
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert e-commerce analyst. Extract data accurately and concisely. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=max_tokens
        )
        result = response.choices[0].message.content
        print(f"LLM Response length: {len(result)} characters")
        return result
    except Exception as e:
        print(f" OpenAI API error: {e}")
        return "{}"


def parse_llm_response(response: str) -> Dict[str, Any]:
    """Parse LLM response and handle JSON extraction."""
    if not response or response.strip() == "{}":
        return {}
    
    try:
        # Clean response - remove markdown code blocks if present
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        # Try to fix incomplete JSON
        if not clean_response.endswith('}'):
            last_brace = clean_response.rfind('}')
            if last_brace > 0:
                clean_response = clean_response[:last_brace + 1]
        
        return json.loads(clean_response)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing LLM response: {e}")
        print(f"Response content: {response[:500]}...")
        return {}


def create_fallback_meta_fields(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create fallback meta fields based on analysis when LLM fails.
    
    Args:
        analysis: Product analysis results
        
    Returns:
        Fallback meta field definitions
    """
    print("Creating fallback meta fields based on analysis...")
    
    detected_category = analysis['detected_category']
    top_vendors = analysis['top_vendors']
    top_product_types = analysis['top_product_types']
    
    # Create basic meta fields based on detected category
    if detected_category == 'pets':
        return {
            "meta_fields": {
                "brand_name": {
                    "name": "Brand (الماركة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Product brand/manufacturer",
                    "category": "brand",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["ماركة", "علامة تجارية"],
                    "example_values": list(top_vendors.keys())[:5]
                },
                "product_type": {
                    "name": "Product Type (نوع المنتج)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Main product category",
                    "category": "technical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["نوع", "فئة"],
                    "example_values": list(top_product_types.keys())[:5]
                },
                "age_group": {
                    "name": "Age Group (الفئة العمرية)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Target age group",
                    "category": "preference",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["عمر", "فئة عمرية"],
                    "example_values": ["Puppy", "Adult", "Senior", "All Ages"]
                }
            },
            "field_categories": {
                "brand_name": [
                    {"value": "royal_canin", "label": "Royal Canin"},
                    {"value": "duvo", "label": "Duvo"},
                    {"value": "other", "label": "Other Brand"}
                ],
                "product_type": [
                    {"value": "dog_food", "label": "Dog Food"},
                    {"value": "dog_treats", "label": "Dog Treats"},
                    {"value": "cat_food", "label": "Cat Food"},
                    {"value": "other", "label": "Other"}
                ],
                "age_group": [
                    {"value": "puppy", "label": "Puppy (0-12 months)"},
                    {"value": "adult", "label": "Adult (1-7 years)"},
                    {"value": "senior", "label": "Senior (7+ years)"},
                    {"value": "all_ages", "label": "All Ages"}
                ]
            },
            "reasoning": "Fallback meta fields created based on detected pets category"
        }
    elif detected_category == 'lighting_electrical':
        return {
            "meta_fields": {
                "brand_name": {
                    "name": "Brand (الماركة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Product brand/manufacturer",
                    "category": "brand",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["ماركة", "علامة تجارية"],
                    "example_values": list(top_vendors.keys())[:5]
                },
                "product_type": {
                    "name": "Product Type (نوع المنتج)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Main product category",
                    "category": "technical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["نوع", "فئة"],
                    "example_values": list(top_product_types.keys())[:5]
                },
                "power_rating": {
                    "name": "Power Rating (قوة المحرك)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Motor power rating",
                    "category": "technical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["قوة", "طاقة"],
                    "example_values": ["Low", "Medium", "High", "Professional"]
                }
            },
            "field_categories": {
                "brand_name": [
                    {"value": "ninja", "label": "Ninja"},
                    {"value": "vitamix", "label": "Vitamix"},
                    {"value": "other", "label": "Other Brand"}
                ],
                "product_type": [
                    {"value": "blender", "label": "Blender"},
                    {"value": "mixer", "label": "Mixer"},
                    {"value": "juicer", "label": "Juicer"},
                    {"value": "other", "label": "Other"}
                ],
                "power_rating": [
                    {"value": "low", "label": "Low Power (<500W)"},
                    {"value": "medium", "label": "Medium Power (500-1000W)"},
                    {"value": "high", "label": "High Power (1000-1500W)"},
                    {"value": "professional", "label": "Professional (>1500W)"}
                ]
            },
            "reasoning": "Fallback meta fields created based on detected lighting/electrical category"
        }
    elif detected_category == 'tools_equipment':
        return {
            "meta_fields": {
                "brand_name": {
                    "name": "Brand (الماركة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Tool brand/manufacturer",
                    "category": "brand",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["ماركة", "علامة تجارية"],
                    "example_values": list(top_vendors.keys())[:5]
                },
                "tool_type": {
                    "name": "Tool Type (نوع الأداة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Type of tool or equipment",
                    "category": "technical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["نوع", "أداة"],
                    "example_values": ["Hand Tools", "Power Tools", "Measuring Tools", "Safety Equipment"]
                },
                "power_type": {
                    "name": "Power Type (نوع الطاقة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Power source type",
                    "category": "technical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["طاقة", "كهرباء"],
                    "example_values": ["Manual", "Electric", "Battery", "Pneumatic"]
                }
            },
            "field_categories": {
                "brand_name": [{"value": v, "label": v} for v in list(top_vendors.keys())[:5]] if top_vendors else [{"value": "other", "label": "Other Brand"}],
                "tool_type": [
                    {"value": "hand_tools", "label": "Hand Tools (أدوات يدوية)"},
                    {"value": "power_tools", "label": "Power Tools (أدوات كهربائية)"},
                    {"value": "measuring", "label": "Measuring Tools (أدوات قياس)"},
                    {"value": "other", "label": "Other (أخرى)"}
                ],
                "power_type": [
                    {"value": "manual", "label": "Manual (يدوي)"},
                    {"value": "electric", "label": "Electric (كهربائي)"},
                    {"value": "battery", "label": "Battery (بطارية)"},
                    {"value": "pneumatic", "label": "Pneumatic (هوائي)"}
                ]
            },
            "reasoning": "Fallback meta fields created based on detected tools/equipment category"
        }
    elif detected_category in ['home_kitchen', 'furniture_accessories', 'storage']:
        return {
            "meta_fields": {
                "brand_name": {
                    "name": "Brand (الماركة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Product brand",
                    "category": "brand",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["ماركة", "علامة تجارية"],
                    "example_values": list(top_vendors.keys())[:5]
                },
                "material": {
                    "name": "Material (المادة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Main material",
                    "category": "physical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["مادة", "خامة"],
                    "example_values": ["Plastic", "Wood", "Metal", "Glass", "Stainless Steel"]
                },
                "size_capacity": {
                    "name": "Size/Capacity (الحجم/السعة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Product size or capacity",
                    "category": "physical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["حجم", "سعة"],
                    "example_values": ["Small", "Medium", "Large", "Extra Large"]
                }
            },
            "field_categories": {
                "brand_name": [{"value": v, "label": v} for v in list(top_vendors.keys())[:5]] if top_vendors else [{"value": "other", "label": "Other"}],
                "material": [
                    {"value": "plastic", "label": "Plastic (بلاستيك)"},
                    {"value": "wood", "label": "Wood (خشب)"},
                    {"value": "metal", "label": "Metal (معدن)"},
                    {"value": "glass", "label": "Glass (زجاج)"},
                    {"value": "stainless_steel", "label": "Stainless Steel (ستانلس ستيل)"}
                ],
                "size_capacity": [
                    {"value": "small", "label": "Small (صغير)"},
                    {"value": "medium", "label": "Medium (متوسط)"},
                    {"value": "large", "label": "Large (كبير)"},
                    {"value": "xlarge", "label": "Extra Large (كبير جداً)"}
                ]
            },
            "reasoning": f"Fallback meta fields created based on detected {detected_category} category"
        }
    elif detected_category in ['sanitary_supplies', 'paint_coating', 'garden', 'automotive', 'safety_security', 'travel_camping', 'smart_home']:
        return {
            "meta_fields": {
                "brand_name": {
                    "name": "Brand (الماركة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Product brand",
                    "category": "brand",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["ماركة", "علامة تجارية"],
                    "example_values": list(top_vendors.keys())[:5]
                },
                "product_type": {
                    "name": "Product Type (نوع المنتج)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Main product category",
                    "category": "technical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["نوع", "فئة"],
                    "example_values": list(top_product_types.keys())[:5]
                },
                "features": {
                    "name": "Features (المميزات)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Key product features",
                    "category": "feature",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["مميزات", "خصائص"],
                    "example_values": ["Waterproof", "Durable", "Eco-Friendly", "High Quality"]
                }
            },
            "field_categories": {
                "brand_name": [{"value": v, "label": v} for v in list(top_vendors.keys())[:5]] if top_vendors else [{"value": "other", "label": "Other"}],
                "product_type": [{"value": v, "label": v} for v in list(top_product_types.keys())[:5]] if top_product_types else [{"value": "other", "label": "Other"}],
                "features": [
                    {"value": "waterproof", "label": "Waterproof (مقاوم للماء)"},
                    {"value": "durable", "label": "Durable (متين)"},
                    {"value": "eco_friendly", "label": "Eco-Friendly (صديق للبيئة)"},
                    {"value": "high_quality", "label": "High Quality (جودة عالية)"}
                ]
            },
            "reasoning": f"Fallback meta fields created based on detected {detected_category} category"
        }
    else:  # general
        return {
            "meta_fields": {
                "brand_name": {
                    "name": "Brand (الماركة)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Product brand/manufacturer",
                    "category": "brand",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["ماركة", "علامة تجارية"],
                    "example_values": list(top_vendors.keys())[:5]
                },
                "product_type": {
                    "name": "Product Type (نوع المنتج)",
                    "type": "single_line_text_field",
                    "multi_select": False,
                    "description": "Main product category",
                    "category": "technical",
                    "searchable": True,
                    "filterable": True,
                    "comparable": True,
                    "arabic_keywords": ["نوع", "فئة"],
                    "example_values": list(top_product_types.keys())[:5]
                }
            },
            "field_categories": {
                "brand_name": [
                    {"value": "brand1", "label": list(top_vendors.keys())[0] if top_vendors else "Brand 1"},
                    {"value": "other", "label": "Other Brand"}
                ],
                "product_type": [
                    {"value": "type1", "label": list(top_product_types.keys())[0] if top_product_types else "Type 1"},
                    {"value": "other", "label": "Other"}
                ]
            },
            "reasoning": "Fallback meta fields created based on general product analysis"
        }


def standardize_products_with_discovered_fields(products: List[Dict], meta_field_definitions: Dict[str, Any], 
                                              field_categories: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    Standardize products using discovered meta field definitions.
    
    Args:
        products: List of products to standardize
        meta_field_definitions: Discovered meta field definitions
        field_categories: Field categories and options
        
    Returns:
        Standardization statistics
    """
    print("Standardizing products with discovered meta fields...")
    
    stats = defaultdict(Counter)
    
    for product in products:
        metafields = product.get('metafields', {})
        
        # Process each discovered meta field
        for field_key, field_def in meta_field_definitions.items():
            if field_key not in field_categories:
                continue
                
            # Get original value (populated in previous step)
            original_value = metafields.get(f"{field_key}_original", '')
            
            # Dynamic standardization based on discovered categories
            standardized_value = standardize_any_field(original_value, field_categories[field_key], field_key)
            
            # Store both original and standardized
            metafields[f"{field_key}_original"] = original_value
            metafields[field_key] = standardized_value
            
            # Count statistics
            if isinstance(standardized_value, list):
                for item in standardized_value:
                    stats[field_key][item] += 1
            else:
                stats[field_key][standardized_value] += 1
    
    return {k: dict(v) for k, v in stats.items()}


def standardize_brand_name(brand: str, categories: List[Dict]) -> str:
    """Standardize brand name based on discovered categories."""
    if not brand or brand in ['null', 'None', '']:
        return "Unknown Brand"
    
    brand_clean = str(brand).strip().upper()
    
    # Check against discovered categories
    for category in categories:
        category_label = category['label'].upper()
        if category_label in brand_clean or brand_clean in category_label:
            return category['label']
    
    # If no match, return "Other Brand" if available
    for category in categories:
        if 'other' in category['value'].lower():
            return category['label']
    
    return brand_clean.title()


def standardize_product_type(product_type: str, categories: List[Dict]) -> str:
    """Standardize product type based on discovered categories."""
    if not product_type or product_type in ['null', 'None', '']:
        return "Not Specified"
    
    type_clean = str(product_type).strip().lower()
    
    # Check against discovered categories (truly dynamic)
    for category in categories:
        category_label = category['label'].lower()
        if category_label in type_clean or type_clean in category_label:
            return category['label']
    
    # If no match, return "Other" if available
    for category in categories:
        if 'other' in category['value'].lower():
            return category['label']
    
    return product_type.title()


def standardize_age_group(age_group: str, categories: List[Dict], product_description: str = "") -> str:
    """Standardize age group based on discovered categories."""
    if not age_group or age_group in ['null', 'None', '']:
        return "Not Specified"
    
    age_clean = str(age_group).strip().lower()
    
    # Check against discovered categories (truly dynamic)
    for category in categories:
        category_label = category['label'].lower()
        if any(keyword in age_clean for keyword in category_label.split()):
            return category['label']
    
    return age_group.title()


def standardize_power_rating(power: str, categories: List[Dict]) -> str:
    """Standardize power rating based on discovered categories."""
    if not power or power in ['null', 'None', '']:
        return "Not Specified"
    
    power_clean = str(power).strip().lower()
    
    # Check against discovered categories (truly dynamic)
    for category in categories:
        category_label = category['label'].lower()
        if any(keyword in power_clean for keyword in category_label.split()):
            return category['label']
    
    return power.title()


def populate_field_values_with_llm(products: List[Dict], meta_field_definitions: Dict[str, Any], field_categories: Dict[str, List[Dict]]) -> None:
    """Use LLM to populate field values from product data."""
    print("Using LLM to extract field values from product data...")
    
    # Process products in batches
    batch_size = 10
    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        
        # Create prompt for LLM to extract field values
        product_descriptions = []
        for j, product in enumerate(batch):
            title = product.get('title', '')
            description_html = product.get('descriptionHtml', '')
            description_clean = clean_html(description_html)[:1000]  # Clean and limit description
            tags = product.get('tags', [])
            vendor = product.get('vendor', '')
            
            product_descriptions.append(f"""
Product {j+1}:
Title: {title}
Vendor: {vendor}
Tags: {', '.join(tags)}
Description: {description_clean}
""")
        
        # Get field names and categories
        field_info = []
        for field_key, field_def in meta_field_definitions.items():
            categories = field_categories.get(field_key, [])
            category_options = [cat['value'] for cat in categories]
            field_info.append(f"- {field_key}: {field_def['name']} (Options: {', '.join(category_options[:5])})")
        
        prompt = f"""Extract field values from these products. Read Description carefully.

FIELDS TO EXTRACT:
{chr(10).join(field_info)}

PRODUCTS:
{chr(10).join(product_descriptions)}

EXTRACTION GUIDE:
• brand_vendor: Use Vendor field, or extract from title
• product_type: Main category from title/description, match to options
• size_weight: Find patterns: "1kg", "500g", "12x40g", "5 لتر", "100ml"
• target_audience: Age/type from description (Adult, Kitten, Senior, Persian, etc.)

• key_features: COMMON features for filtering (2-3 max)
  → Extract: High Protein, Grain-Free, Natural, Vitamin-Enriched, Digestive Support
  → Simple consistent values many products share

• special_attributes: UNIQUE claims for SEO/search (1 only if exists)
  → Extract: Made in Italy, Vet Recommended, Award Winner, USDA Certified, Eco-Friendly, Limited Edition
  → ONLY if genuinely unique, leave EMPTY if nothing special

RULES:
1. Read Description thoroughly
2. Match to provided options when possible
3. Be specific, not generic
4. Leave empty only if truly no data
5. Don't duplicate info between key_features and special_attributes

JSON OUTPUT:
{{
  "products": [
    {{"product_index": 0, "field_values": {{"brand_vendor": "value", "product_type": "value", "key_features": "value1, value2", "size_weight": "value", "target_audience": "value", "special_attributes": "value or empty"}}}},
    {{"product_index": 1, "field_values": {{"brand_vendor": "value", ...}}}}
  ]
}}"""
        
        # Call LLM
        response = call_openai(prompt)
        result = parse_llm_response(response)
        
        if result and 'products' in result:
            # Apply the extracted values
            for product_result in result['products']:
                product_index = product_result.get('product_index', 0)
                field_values = product_result.get('field_values', {})
                
                if 0 <= product_index < len(batch):
                    product = batch[product_index]
                    if 'metafields' not in product:
                        product['metafields'] = {}
                    
                    for field_key, value in field_values.items():
                        if field_key in meta_field_definitions:
                            product['metafields'][f"{field_key}_original"] = value
        
        print(f"  Processed batch {i//batch_size + 1}/{(len(products) + batch_size - 1)//batch_size}")

def populate_field_values(products: List[Dict], meta_field_definitions: Dict[str, Any]) -> None:
    """
    Populate field values from product data (title, description, tags, vendor).
    
    Args:
        products: List of products to populate
        meta_field_definitions: Discovered meta field definitions
    """
    for product in products:
        # Ensure metafields dict exists
        if 'metafields' not in product:
            product['metafields'] = {}
        
        metafields = product['metafields']
        title = product.get('title', '').lower()
        description_html = product.get('descriptionHtml', '')
        description = clean_html(description_html).lower()
        tags = [tag.lower() for tag in product.get('tags', [])]
        vendor = product.get('vendor', '').lower()
        
        # Populate each discovered field
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
                material_keywords = ['steel', 'wood', 'plastic', 'metal', 'aluminum', 'glass', 'fiber', 'carbon']
                for keyword in material_keywords:
                    if keyword in title or keyword in description or any(keyword in tag for tag in tags):
                        extracted_value = keyword
                        break
            
            elif field_key == 'product_type':
                # Extract product type from title with better logic
                title_lower = title.lower()
                
                # Check for specific product types in title
                if any(keyword in title_lower for keyword in ['رطب', 'wet', 'شوربة', 'soup', 'طرية', 'soft']):
                    extracted_value = 'wet_cat_food'
                elif any(keyword in title_lower for keyword in ['جاف', 'dry', 'كروكيت', 'croquettes', 'بسكويت', 'biscuit', 'طعام جاف']):
                    extracted_value = 'dry_cat_food'
                elif any(keyword in title_lower for keyword in ['مكافآت', 'treats', 'snack', 'وجبة خفيفة']):
                    extracted_value = 'cat_treats'
                elif any(keyword in title_lower for keyword in ['مكمل', 'supplement', 'فيتامين', 'vitamin']):
                    extracted_value = 'cat_supplements'
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
                    import re
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
            
            elif field_key == 'weight':
                # Extract weight from title or description
                import re
                weight_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:g|kg|gram|كيلو|جرام)',
                    r'(\d+(?:\.\d+)?)\s*(?:oz|ounce)',
                    r'(\d+(?:\.\d+)?)\s*(?:lb|pound)'
                ]
                for pattern in weight_patterns:
                    match = re.search(pattern, title + ' ' + description, re.IGNORECASE)
                    if match:
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
            
            elif field_key == 'features':
                # Extract features from description or tags
                feature_keywords = ['waterproof', 'fireproof', 'durable', 'lightweight', 'heavy', 'portable']
                features = []
                for keyword in feature_keywords:
                    if keyword in description or any(keyword in tag for tag in tags):
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
            
            # Store the extracted value
            metafields[f"{field_key}_original"] = extracted_value

def standardize_any_field(value: str, categories: List[Dict], field_key: str) -> str:
    """
    Universal field standardization that works for ANY field type.
    
    Args:
        value: Original field value
        categories: Discovered categories for this field
        field_key: The field key name
        
    Returns:
        Standardized value
    """
    if not value or value in ['null', 'None', '']:
        return "Not Specified"
    
    value_clean = str(value).strip().lower()
    # Special handling for weight ranges - ONLY for fields with "weight" in the name
    if 'weight' in field_key.lower() or field_key == 'size_weight' or field_key == 'package_size':
        return standardize_weight_range(value, categories)
    
    # For "size" alone (dimensions), do NOT categorize - return as-is
    # This is for dimensional measurements like "65x45cm", not weight
    
    # Special handling for price ranges
    if 'price' in field_key.lower():
        return standardize_price_range(value, categories)
    
    # Try to match against discovered categories
    for category in categories:
        category_label = category['label'].lower()
        category_value = category.get('value', '').lower()
        
        # Check if the value matches the category label or value
        if (category_label in value_clean or 
            value_clean in category_label or
            category_value in value_clean or
            value_clean in category_value):
            return category['label']
    
    # If no exact match, try partial matching
    for category in categories:
        category_label = category['label'].lower()
        category_value = category.get('value', '').lower()
        
        # Split category label into words and check if any word matches
        category_words = category_label.split()
        if any(word in value_clean for word in category_words if len(word) > 2):
            return category['label']
    
    # If still no match, return the original value (cleaned up)
    return value.title() if value else "Not Specified"

def standardize_weight_range(value: str, categories: List[Dict]) -> str:
    """Standardize weight values to weight range categories."""
    import re
    
    if not value or value in ['', 'null', 'None', 'Not Specified']:
        return "Not Specified"
    
    # Extract numeric value from weight string
    weight_match = re.search(r'(\d+(?:\.\d+)?)', value)
    if not weight_match:
        return "Not Specified"
    
    weight_num = float(weight_match.group(1))
    
    # Convert to grams if needed
    if 'kg' in value.lower() or 'كيلو' in value:
        weight_num = weight_num * 1000
    elif 'l' in value.lower() or 'liter' in value.lower() or 'لتر' in value.lower():
        # Convert liters to approximate kg for cat litter (1L ≈ 0.6kg average)
        weight_num = weight_num * 600  # 1 liter = ~600 grams for cat litter
    elif 'oz' in value.lower():
        weight_num = weight_num * 28.35  # Convert oz to grams
    elif 'lb' in value.lower() or 'pound' in value.lower():
        weight_num = weight_num * 453.592  # Convert lbs to grams
    
    # Categorize into ranges (comprehensive from grams to large kg)
    if weight_num < 100:
        return "Under 100g (أقل من 100 جرام)"
    elif weight_num < 500:
        return "100g-500g (100-500 جرام)"
    elif weight_num < 1000:
        return "500g-1kg (500 جرام - 1 كيلو)"
    elif weight_num < 2000:
        return "1kg-2kg (1-2 كيلو)"
    elif weight_num < 5000:
        return "2kg-5kg (2-5 كيلو)"
    elif weight_num < 10000:
        return "5kg-10kg (5-10 كيلو)"
    elif weight_num < 25000:
        return "10kg-25kg (10-25 كيلو)"
    elif weight_num < 50000:
        return "25kg-50kg (25-50 كيلو)"
    elif weight_num < 100000:
        return "50kg-100kg (50-100 كيلو)"
    else:
        return "100kg+ (100 كيلو فأكثر)"

def standardize_package_size(value: str, categories: List[Dict]) -> str:
    """Standardize weight values to package size categories (Small/Medium/Large)."""
    import re
    
    if not value or value in ['', 'null', 'None', 'Not Specified']:
        return "Not Specified"
    
    # Extract numeric value from weight string
    weight_match = re.search(r'(\d+(?:\.\d+)?)', value)
    if not weight_match:
        return "Not Specified"
    
    weight_num = float(weight_match.group(1))
    
    # Convert to grams if needed
    if 'kg' in value.lower() or 'كيلو' in value:
        weight_num = weight_num * 1000
    elif 'l' in value.lower() or 'liter' in value.lower() or 'لتر' in value.lower():
        # Convert liters to approximate kg for cat litter (1L ≈ 0.6kg average)
        weight_num = weight_num * 600  # 1 liter = ~600 grams for cat litter
    elif 'oz' in value.lower():
        weight_num = weight_num * 28.35  # Convert oz to grams
    elif 'lb' in value.lower() or 'pound' in value.lower():
        weight_num = weight_num * 453.592
    
    # Use the same categorization as standardize_weight_range
    if weight_num < 100:
        return "Under 100g (أقل من 100 جرام)"
    elif weight_num < 500:
        return "100g-500g (100-500 جرام)"
    elif weight_num < 1000:
        return "500g-1kg (500 جرام - 1 كيلو)"
    elif weight_num < 2000:
        return "1kg-2kg (1-2 كيلو)"
    elif weight_num < 5000:
        return "2kg-5kg (2-5 كيلو)"
    elif weight_num < 10000:
        return "5kg-10kg (5-10 كيلو)"
    elif weight_num < 25000:
        return "10kg-25kg (10-25 كيلو)"
    elif weight_num < 50000:
        return "25kg-50kg (25-50 كيلو)"
    elif weight_num < 100000:
        return "50kg-100kg (50-100 كيلو)"
    else:
        return "100kg+ (100 كيلو فأكثر)"

def create_categories_with_llm(field_categories: Dict[str, List[Dict]], meta_field_definitions: Dict[str, Any], sample_products: List[Dict]) -> Dict[str, List[Dict]]:
    """Use LLM to create categories for discovered fields."""
    print(" Using LLM to create categories for discovered fields...")
    
    # Find fields that don't have categories
    fields_needing_categories = []
    for field_key, field_def in meta_field_definitions.items():
        if field_key not in field_categories or not field_categories[field_key]:
            fields_needing_categories.append((field_key, field_def))
    
    if not fields_needing_categories:
        return field_categories
    
    # Create prompt for LLM to generate categories
    field_descriptions = []
    for field_key, field_def in fields_needing_categories:
        field_descriptions.append(f"- {field_key}: {field_def['name']} - {field_def.get('description', '')}")
    
    # Get sample values for each field
    sample_values = {}
    for field_key, _ in fields_needing_categories:
        values = []
        for product in sample_products[:10]:  # Sample first 10 products
            title = product.get('title', '')
            description = product.get('descriptionHtml', '')
            tags = product.get('tags', [])
            
            # Extract potential values based on field type
            if 'weight' in field_key.lower() or 'size' in field_key.lower():
                import re
                weight_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:g|kg|gram|كيلو|جرام|oz|ounce)', title + ' ' + description, re.IGNORECASE)
                values.extend(weight_matches)
            elif 'price' in field_key.lower():
                variants = product.get('variants', [])
                for variant in variants:
                    if variant.get('price'):
                        values.append(str(variant['price']))
            elif 'screen' in field_key.lower() or 'display' in field_key.lower():
                screen_matches = re.findall(r'(led|oled|qled|lcd|plasma|ips|va)', title + ' ' + description, re.IGNORECASE)
                values.extend(screen_matches)
            elif 'resolution' in field_key.lower():
                res_matches = re.findall(r'(\d+x\d+|\d+\s*k)', title + ' ' + description, re.IGNORECASE)
                values.extend(res_matches)
            else:
                # Generic extraction
                words = (title + ' ' + ' '.join(tags)).split()
                values.extend(words[:3])  # Take first 3 words
        
        sample_values[field_key] = list(set(values))[:10]  # Unique values, max 10
    
    prompt = f"""You are an expert e-commerce analyst. I need you to create categories for the following meta fields based on the sample values found in the products.

Fields that need categories:
{chr(10).join(field_descriptions)}

Sample values found for each field:
{chr(10).join([f"- {field_key}: {', '.join(values[:5])}" for field_key, values in sample_values.items()])}

For each field, create 3-8 categories that would be useful for customers to filter by. Categories should:
1. Cover the range of values found in the sample
2. Be practical for filtering (not too specific, not too broad)
3. Include both English and Arabic labels
4. Be mutually exclusive (no overlap)

Return your response as a JSON object with this exact structure:
{{
  "field_categories": {{
    "field_key": [
      {{"value": "category_value", "label": "Category Label (التسمية بالعربية)"}},
      {{"value": "category_value2", "label": "Category Label 2 (التسمية بالعربية)"}}
    ]
  }}
}}"""
    
    # Call LLM
    response = call_openai(prompt)
    result = parse_llm_response(response)
    
    if result and 'field_categories' in result:
        # Merge the new categories
        for field_key, categories in result['field_categories'].items():
            if field_key in meta_field_definitions:
                field_categories[field_key] = categories
                print(f"  Created {len(categories)} categories for {field_key}")
    
    return field_categories

def add_missing_categories(field_categories: Dict[str, List[Dict]], meta_field_definitions: Dict[str, Any], sample_products: List[Dict]) -> None:
    """Add missing categories for fields that don't have them."""
    for field_key, field_def in meta_field_definitions.items():
        if field_key not in field_categories or not field_categories[field_key]:
            # Create categories based on field type
            if 'weight' in field_key.lower() or 'size' in field_key.lower() or 'package' in field_key.lower():
                field_categories[field_key] = [
                    {"value": "small", "label": "Small (صغير)"},
                    {"value": "medium", "label": "Medium (متوسط)"},
                    {"value": "large", "label": "Large (كبير)"}
                ]
            elif 'price' in field_key.lower():
                field_categories[field_key] = [
                    {"value": "under_10", "label": "Under 10 JOD (أقل من 10 دينار)"},
                    {"value": "10_50", "label": "10-50 JOD (10-50 دينار)"},
                    {"value": "50_100", "label": "50-100 JOD (50-100 دينار)"},
                    {"value": "100_200", "label": "100-200 JOD (100-200 دينار)"},
                    {"value": "200_plus", "label": "200+ JOD (200+ دينار)"}
                ]
            elif 'age' in field_key.lower() or 'target' in field_key.lower():
                field_categories[field_key] = [
                    {"value": "kitten", "label": "Kitten (هريرة)"},
                    {"value": "adult", "label": "Adult (بالغ)"},
                    {"value": "senior", "label": "Senior (مسن)"}
                ]
            else:
                # Generic categories
                field_categories[field_key] = [
                    {"value": "option1", "label": "Option 1 (خيار 1)"},
                    {"value": "option2", "label": "Option 2 (خيار 2)"},
                    {"value": "option3", "label": "Option 3 (خيار 3)"}
                ]

def standardize_price_range(value: str, categories: List[Dict]) -> str:
    """Standardize price values to price range categories."""
    import re
    
    # Extract numeric value from price string
    price_match = re.search(r'(\d+(?:\.\d+)?)', value)
    if not price_match:
        return "Not Specified"
    
    price_num = float(price_match.group(1))
    
    # Map to categories
    for category in categories:
        category_value = category.get('value', '').lower()
        
        if 'under' in category_value and '10' in category_value and price_num < 10:
            return category['label']
        elif '10' in category_value and '50' in category_value and 10 <= price_num < 50:
            return category['label']
        elif '50' in category_value and '100' in category_value and 50 <= price_num < 100:
            return category['label']
        elif '100' in category_value and '200' in category_value and 100 <= price_num < 200:
            return category['label']
        elif '200' in category_value and '+' in category_value and price_num >= 200:
            return category['label']
    
    # Fallback logic if categories don't match
    if price_num < 10:
        return "Under 10 JOD"
    elif price_num < 50:
        return "10-50 JOD"
    elif price_num < 100:
        return "50-100 JOD"
    elif price_num < 200:
        return "100-200 JOD"
    else:
        return "200+ JOD"


def calculate_optimal_sample_size(total_products: int) -> float:
    """
    Calculate optimal sample percentage based on collection size.
    
    Small collections need higher sample rates for accuracy.
    
    Args:
        total_products: Total number of products
        
    Returns:
        Sample percentage (0.0 to 1.0)
    """
    if total_products < 30:
        return 1.0  # 100% - analyze all
    elif total_products < 50:
        return 0.8  # 80%
    elif total_products < 100:
        return 0.7  # 70%
    elif total_products < 200:
        return 0.6  # 60%
    else:
        return 0.5  # 50%


def run_dynamic_product_analysis(input_file: str, output_file: str = None, 
                                sample_percentage: float = None) -> str:
    """
    Run dynamic product analysis and meta field discovery.
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file
        sample_percentage: Percentage of products to use for analysis (None = auto-calculate)
        
    Returns:
        Path to output file
    """
    print("Starting Dynamic Product Analysis")
    
    # Load data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        products = data
    elif isinstance(data, dict) and 'products' in data:
        products = data['products']
    else:
        products = [data]
    
    print(f"Total products: {len(products)}")
    
    # Auto-calculate sample percentage if not provided
    if sample_percentage is None:
        sample_percentage = calculate_optimal_sample_size(len(products))
    
    print(f"Sample percentage: {sample_percentage*100}% ({int(len(products) * sample_percentage)} products)")
    
    # Step 1: Analyze product tags and characteristics
    analysis = analyze_product_tags(products)
    print(f"Detected category: {analysis['detected_category']}")
    print(f"Top tags: {list(analysis['top_tags'].keys())[:5]}")
    print(f"Top vendors: {list(analysis['top_vendors'].keys())[:3]}")
    
    # Step 2: Sample products for meta field discovery with better diversity
    sample_size = max(1, int(len(products) * sample_percentage))
    
    # Ensure sample includes diverse products by sampling from different parts of the list
    # and including products with different characteristics
    sample_products = []
    
    # Take products from beginning, middle, and end for diversity
    if len(products) >= 3:
        step = len(products) // 3
        sample_products.extend(products[::step][:sample_size//3])
        sample_products.extend(products[step::step][:sample_size//3])
        sample_products.extend(products[step*2::step][:sample_size//3])
    
    # Fill remaining with random samples
    remaining_needed = sample_size - len(sample_products)
    if remaining_needed > 0:
        remaining_products = [p for p in products if p not in sample_products]
        if remaining_products:
            sample_products.extend(random.sample(remaining_products, min(remaining_needed, len(remaining_products))))
    
    # Ensure we have the requested sample size
    if len(sample_products) < sample_size:
        additional_needed = sample_size - len(sample_products)
        additional_products = [p for p in products if p not in sample_products]
        if additional_products:
            sample_products.extend(random.sample(additional_products, min(additional_needed, len(additional_products))))
    
    print(f"Analyzing {len(sample_products)} sample products for meta field discovery...")
    
    # Step 3: Create dynamic meta field prompt
    meta_field_prompt = create_dynamic_meta_field_prompt(sample_products, analysis)
    meta_field_response = call_openai(meta_field_prompt)
    meta_field_result = parse_llm_response(meta_field_response)
    
    if not meta_field_result:
        print("  Using fallback meta field discovery...")
        meta_field_result = create_fallback_meta_fields(analysis)
    
    meta_field_definitions = meta_field_result.get('meta_fields', {})
    field_categories = meta_field_result.get('field_categories', {})
    
    # Use LLM to create categories for discovered fields
    field_categories = create_categories_with_llm(field_categories, meta_field_definitions, sample_products)
    
    print(f"Discovered {len(meta_field_definitions)} meta fields:")
    for field_key, field_def in meta_field_definitions.items():
        print(f"  {field_key}: {field_def['name']}")
    
    # Step 4: Use LLM to populate field values from product data
    print("Using LLM to populate field values from product data...")
    populate_field_values_with_llm(products, meta_field_definitions, field_categories)
    
    # Step 5: Standardize all products with discovered fields
    standardization_stats = standardize_products_with_discovered_fields(
        products, meta_field_definitions, field_categories
    )
    
    # Step 5: Create output
    if output_file is None:
        output_file = str(Path(input_file).parent / f"{Path(input_file).stem}_dynamic_analyzed.json")
    
    output_data = {
        "system_info": {
            "input_file": input_file,
            "total_products": len(products),
            "sample_size": len(sample_products),
            "detected_category": analysis['detected_category'],
            "analysis_method": "dynamic_tag_based"
        },
        "product_analysis": analysis,
        "meta_field_discovery": meta_field_result,
        "meta_field_definitions": meta_field_definitions,
        "standardization_stats": standardization_stats,
        "products": products
    }
    
    # Save output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nDynamic product analysis completed!")
    print(f"Output saved to: {output_file}")
    
    # Print final statistics
    for field_name, field_stats in standardization_stats.items():
        print(f"\nSTANDARDIZED {field_name.upper()}:")
        for value, count in sorted(field_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {count:3d}x: {value}")
    
    return output_file


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dynamic Product Analysis')
    parser.add_argument('input_file', help='Input JSON file path')
    parser.add_argument('-o', '--output', help='Output JSON file path')
    parser.add_argument('-s', '--sample', type=float, default=None, help='Sample percentage (0.1-1.0, default=auto based on collection size)')
    
    args = parser.parse_args()
    
    try:
        # Run dynamic analysis
        json_output = run_dynamic_product_analysis(args.input_file, args.output, args.sample)
        
        print(f"\n Success! File created: {json_output}")
            
    except Exception as e:
        print(f" Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

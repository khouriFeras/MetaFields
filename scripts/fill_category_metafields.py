#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fill Category Metafields for Products
- Uses LLM to extract values
- Formats values to match Shopify metafield definitions
- (Optional) Exports a Matrixify-ready CSV
"""
import json
import os
import sys
import re
import html
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from dotenv import load_dotenv
import importlib.util

# OpenAI client import compatible with new SDKs
try:
    from openai import OpenAI
    _OPENAI_CLIENT_CTOR = OpenAI
except Exception:
    import openai as openai_legacy  # fallback
    _OPENAI_CLIENT_CTOR = openai_legacy.OpenAI  # type: ignore

load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass


# --------------------------
# Utilities
# --------------------------
def clean_html(html_text: str) -> str:
    """
    Clean HTML while preserving structure and ALL text content.
    Preserves line breaks and list structures for better LLM understanding.
    """
    if not html_text:
        return ""
    
    # Preserve line breaks from <br>, <p>, <div>, <li> tags
    html_text = re.sub(r'<br\s*/?>', '\n', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'</p>', '\n', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'</div>', '\n', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'</li>', '\n', html_text, flags=re.IGNORECASE)
    html_text = re.sub(r'<li>', '• ', html_text, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags but preserve text
    clean_text = re.sub(r'<[^>]+>', ' ', html_text)
    
    # Decode HTML entities (like &amp; -> &, &nbsp; -> space)
    clean_text = html.unescape(clean_text)
    
    # Normalize whitespace but preserve line breaks
    lines = [line.strip() for line in clean_text.split('\n')]
    clean_text = '\n'.join(line for line in lines if line)
    
    return clean_text.strip()

def load_json(file_path: str) -> Any:
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(file_path: str, data: Any) -> None:
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def slugify_label(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r'[\s/]+', '-', s)
    s = s.replace('+', 'plus')
    s = re.sub(r'[^a-z0-9\-._]', '', s)
    s = re.sub(r'-{2,}', '-', s)
    return s

def is_list_type(t: str) -> bool:
    return t.startswith('list.')

def is_metaobject_ref(t: str) -> bool:
    return 'metaobject_reference' in t

def ensure_list(v: Any) -> List[str]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()]

def extract_namespace_and_key(mf: Dict) -> Tuple[str, str]:
    # >>> FIX: make namespace explicit (default to 'shopify' if omitted)
    ns = mf.get('namespace') or 'shopify'
    key = mf['key']
    return ns, key


# --------------------------
# Product text for LLM
# --------------------------
def extract_product_info(product: Dict) -> str:
    """
    Extract ALL product information including FULL HTML descriptions.
    Reads descriptionHtml and all language variants to capture complete information.
    """
    title = product.get('title', 'N/A')
    product_type = product.get('productType', 'N/A')
    vendor = product.get('vendor', 'N/A')
    tags = ', '.join(product.get('tags', []))
    
    # Collect ALL description HTML fields to capture complete information
    descriptions = []
    
    # Main description
    description_html = product.get('descriptionHtml', '')
    if description_html:
        desc_cleaned = clean_html(description_html)
        if desc_cleaned:
            descriptions.append(desc_cleaned)
    
    # Language-specific descriptions (might contain additional info)
    description_ar = product.get('descriptionHtml_ar', '')
    if description_ar and description_ar != description_html:
        desc_ar_cleaned = clean_html(description_ar)
        if desc_ar_cleaned and desc_ar_cleaned not in descriptions:
            descriptions.append(f"[Arabic]\n{desc_ar_cleaned}")
    
    description_en = product.get('descriptionHtml_en', '')
    if description_en and description_en != description_html:
        desc_en_cleaned = clean_html(description_en)
        if desc_en_cleaned and desc_en_cleaned not in descriptions:
            descriptions.append(f"[English]\n{desc_en_cleaned}")
    
    # Combine all descriptions
    full_description = '\n\n'.join(descriptions) if descriptions else 'No description available'

    variants_info = []
    variants_data = product.get('variants', [])
    
    # Handle GraphQL format (with edges/node) or direct list format
    if isinstance(variants_data, dict) and 'edges' in variants_data:
        # GraphQL format: variants.edges[].node
        variants_list = [edge.get('node', {}) for edge in variants_data.get('edges', [])]
    elif isinstance(variants_data, list):
        # Direct list format
        variants_list = variants_data
    else:
        variants_list = []
    
    for variant in variants_list:
        if isinstance(variant, dict):
            v_title = variant.get('title', 'Default')
            v_price = variant.get('price', 'N/A')
            options = variant.get('selectedOptions', variant.get('selected_options', []))
            options_str = ", ".join([f"{opt.get('name', '')}: {opt.get('value', '')}" for opt in options if isinstance(opt, dict)])
            if options_str:
                variants_info.append(f"{v_title} - {options_str} - {v_price}")
            else:
                variants_info.append(f"{v_title} - {v_price}")
    
    variants_text = "\n  ".join(variants_info) if variants_info else "No variants"

    price_info = product.get('priceRange', 'N/A')

    product_info = f"""
╔════════════════════════════════════════════════════════════════╗
║                    PRODUCT TITLE (READ CAREFULLY)              ║
╚════════════════════════════════════════════════════════════════╝
{title}

╔════════════════════════════════════════════════════════════════╗
║              PRODUCT DESCRIPTION (READ CAREFULLY)               ║
╚════════════════════════════════════════════════════════════════╝
{full_description}

╔════════════════════════════════════════════════════════════════╗
║                    ADDITIONAL PRODUCT INFO                     ║
╚════════════════════════════════════════════════════════════════╝
Product Type: {product_type}
Vendor: {vendor}
Price Range: {price_info}
Tags: {tags}

Variants:
  {variants_text}
"""
    return product_info.strip()


# --------------------------
# VALUE FORMATTER (the core fix)
# --------------------------
def map_value_to_handle(label: str, mf: Dict) -> Optional[str]:
    """
    For metaobject_reference fields, convert a human label (e.g., 'HDR10+') to a metaobject handle
    via mapping in metafield definition: mf['value_to_handle'].
    """
    if not label:
        return None
    mapping = (mf.get('value_to_handle') or {})
    # Try exact, case-insensitive
    for k, v in mapping.items():
        if k.strip().lower() == label.strip().lower():
            return v.strip()
    # No mapping → cannot safely guess handle
    return None

def normalize_text_value(label: str, mf: Dict) -> str:
    """For plain text types, keep label as-is (Matrixify expects plain values, not handles or prefixes)."""
    return label.strip()

def format_value_for_type(raw_value: Any, mf: Dict) -> Optional[str]:
    """
    Return a Matrixify-ready string for the metafield column, or None if not resolvable.
    Rules:
      - list types: JSON array format (Matrixify requirement)
      - single_line_text_field: plain text
    """
    import json
    mf_type = mf['type']
    labels = ensure_list(raw_value)
    if not labels:
        return None

    # For list types, Matrixify expects JSON array format
    if is_list_type(mf_type):
        # Filter out None/empty values and normalize
        values = [normalize_text_value(x, mf) for x in labels if x]
        if not values:
            return None
        # Return as JSON array string
        return json.dumps(values, ensure_ascii=False)
    else:
        # Single value field
        return normalize_text_value(labels[0], mf)


# --------------------------
# LLM wrappers (kept from your code, minor tweaks)
# --------------------------
def build_metafields_prompt_section(metafield_definitions: List[Dict]) -> str:
    blocks = []
    for mf in metafield_definitions:
        validations = ""
        if mf.get('validations'):
            val_list = [f"{v['name']}: {v['value']}" for v in mf['validations']]
            validations = f" (Validations: {', '.join(val_list)})"

        values_info = ""
        if mf.get('values'):
            sample = mf['values'][:15]
            values_str = ', '.join(sample)
            if len(mf['values']) > 15:
                values_str += f" (and {len(mf['values'])-15} more)"
            values_info = f"\n  Available values: {values_str}"

        desc = mf.get('description', '') or 'No description'
        ns, key = extract_namespace_and_key(mf)
        blocks.append(
            f"- {mf.get('name','(no name)')} (ns: {ns}, key: {key}, type: {mf['type']}){validations}\n"
            f"  Description: {desc}{values_info}"
        )
    return "\n".join(blocks)

def openai_client():
    return _OPENAI_CLIENT_CTOR(api_key=os.getenv("OPENAI_API_KEY"))

def call_llm(model: str, system: str, user: str, max_retries: int = 3) -> str:
    """Call LLM with retry logic for rate limits."""
    client = openai_client()
    params = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # Be compatible with both SDKs
    if model.startswith('gpt-5'):
        params["max_completion_tokens"] = 8000
    else:
        params["max_tokens"] = 1000
        params["temperature"] = 0.2

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(**params)
            txt = resp.choices[0].message.content or ""
            txt = txt.strip()
            if txt.startswith("```"):
                parts = txt.split("```")
                if len(parts) >= 2:
                    txt = parts[1]
                    if txt.startswith("json"):
                        txt = txt[4:]
                    txt = txt.strip()
            return txt
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str.lower():
                # Extract wait time from error message if available
                import re
                wait_match = re.search(r'Please try again in ([\d.]+)s', error_str)
                wait_time = float(wait_match.group(1)) if wait_match else (2 ** attempt) + 1
                wait_time = min(wait_time, 60)  # Cap at 60 seconds
                
                if attempt < max_retries - 1:
                    print(f"    ⏳ Rate limit hit, waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
            # If not rate limit or final attempt, raise
            raise


# --------------------------
# Extraction modes (kept, but use new formatter)
# --------------------------
def merge_llm_result_into_product(product: Dict, result_json: Dict, metafield_definitions: List[Dict]) -> Dict:
    raw = result_json.get("metafields", {}) if "metafields" in result_json else result_json.get("products", [{}])[0].get("metafields", {})
    mf_out: Dict[str, Any] = {}
    for mf in metafield_definitions:
        key = mf["key"]
        if key in raw:
            mf_out[key] = raw[key]
    product_copy = product.copy()
    product_copy["category_metafields"] = mf_out
    return product_copy

def fill_metafields_single(products: List[Dict], metafield_definitions: List[Dict], category_name: str, model: str = "gpt-4o-mini") -> List[Dict]:
    results = []
    section = build_metafields_prompt_section(metafield_definitions)
    for i, product in enumerate(products, 1):
        print(f"  [{i}/{len(products)}] {product.get('title','N/A')[:60]}...")
        product_info = extract_product_info(product)
        prompt = f"""You are filling Shopify category metafields for a product.

⚠️⚠️⚠️ CRITICAL: ABSOLUTELY NO UNIT CONVERSIONS ⚠️⚠️⚠️
- If product says "12 inches" → return "12" (NOT 30.48, NOT 30, NOT any conversion)
- If product says "30 cm" → return "30" (NOT 11.8, NOT 12, NOT any conversion)
- Extract ONLY the number as written - NEVER convert between units
- This is the MOST IMPORTANT rule - violating it will cause errors

CATEGORY: {category_name}

METAFIELDS TO FILL:
{section}

PRODUCT INFORMATION:
{product_info}

CRITICAL RULES - NO HALLUCINATION:

1. READ THE TITLE FIRST - The product title often contains the most important specifications:
   - Look for numbers (capacity, size, dimensions, power, etc.)
   - Look for brand names, model numbers, types
   - Look for key features mentioned in the title
   - Example: "كيزر كهرباء ايطالي 80 لتر نوع اريستون- ايكو" contains:
     * Capacity: 80 لتر (80 liters)
     * Type: اريستون (Ariston brand)
     * Power: كهرباء (electric)

2. READ THE DESCRIPTION CAREFULLY - The description contains detailed specifications:
   - Look in the "PRODUCT DESCRIPTION" section above
   - Read all paragraphs and bullet points
   - Check both Arabic and English descriptions if available
   - Extract all technical specifications mentioned

3. ONLY extract information that is EXPLICITLY stated in the product data:
   - Product TITLE (check this FIRST - it often has key specs)
   - Product DESCRIPTION (read carefully - contains detailed info)
   - Variants and their selected options (Color, Size, etc.)
   - Tags
   - Product type

4. DO NOT infer, guess, or assume ANY values based on:
   - Product category or type
   - Similar products
   - Common characteristics
   - Your knowledge of similar items

5. If information is NOT explicitly found in the product data:
   - Return null for that metafield
   - DO NOT make up values
   - DO NOT use common/default values
   - Empty/null is the CORRECT answer when information is missing

6. For list fields: return array ONLY when multiple values are explicitly stated.

7. For single values: return the exact value as stated, or null if not found.

8. CRITICAL - UNIT HANDLING - NO CONVERSIONS:
   - Extract the EXACT NUMBER as stated in the product (title, description, etc.)
   - DO NOT convert units (liters to gallons, kg to lbs, inches to cm, cm to inches, etc.)
   - DO NOT convert between measurement systems (imperial to metric or vice versa)
   - If product says "80 لتر" (80 liters) → extract "80" (the number, not converted)
   - If product says "50 gallons" → extract "50" (the number)
   - If product says "12 inches" → extract "12" (NOT converted to 30.48 cm)
   - If product says "30 cm" → extract "30" (NOT converted to 11.8 inches)
   - If metafield name says "blade-diameter-cm" but product says "12 inches" → extract "12" (NOT 30.48)
   - The metafield name may indicate the expected unit, but extract the literal number from the product
   - Only use the number that appears in the product data itself
   - NEVER perform unit conversions - use the exact number as written

EXAMPLES:
- Title: "كيزر كهرباء ايطالي 80 لتر نوع اريستون- ايكو"
  → Extract capacity: "80" (from "80 لتر" in title)
  → Extract power-source: ["AC-powered"] (from "كهرباء" = electric in title)
  → Extract brand/type: "اريستون" (Ariston mentioned in title)
  
- If description says "Color: Black" or variant has "Color: Black" → use "Black"
- If NO mention of color anywhere → use null (NOT a guessed color)
- If description says "140 watts" → extract "140" for power
- If product title says "80 لتر" (80 liters) and metafield is capacity-gallons → extract "80" (NOT converted to 21)
- If product says "50 kg" and metafield expects lbs → extract "50" (NOT converted to 110)
- If product says "12 inches" and metafield is blade-diameter-cm → extract "12" (NOT converted to 30.48)
- If product says "30 cm" and metafield expects inches → extract "30" (NOT converted to 11.8)
- If NO mention of capacity → use null (NOT a guessed value)

IMPORTANT: The TITLE is often the most reliable source for key specifications. Read it word by word, including Arabic text.

Return ONLY valid JSON (no comments allowed):
{{
  "metafields": {{
    "metafield_key1": "value1",
    "metafield_key2": ["value1","value2"],
    "metafield_key3": null
  }}
}}"""
        try:
            txt = call_llm(model, system="⚠️ CRITICAL: Extract EXACT numbers as written in product data. ABSOLUTELY NO UNIT CONVERSIONS. If product says '12 inches', return '12' NOT '30.48'. If product says '30 cm', return '30' NOT '11.8'. NEVER convert between units (inches/cm, liters/gallons, kg/lbs, etc.). Extract ONLY explicitly stated information. NEVER guess values. Read TITLE first - it contains key specs. Use null when information not found. Return valid JSON.", user=prompt)
            result = json.loads(txt)
            results.append(merge_llm_result_into_product(product, result, metafield_definitions))
        except Exception as e:
            print(f"    Error: {e}")
            p = product.copy()
            p["category_metafields"] = {}
            results.append(p)
    return results

def fill_metafields_parallel(products: List[Dict], metafield_definitions: List[Dict], category_name: str, model: str = "gpt-4o-mini", max_workers: int = 3) -> List[Dict]:
    # same logic as your parallel version but calling fill_metafields_single per item
    from concurrent.futures import ThreadPoolExecutor, as_completed
    section = build_metafields_prompt_section(metafield_definitions)
    def _one(p):
        product_info = extract_product_info(p)
        prompt = f"""You are filling Shopify category metafields for a product.

 CRITICAL: ABSOLUTELY NO UNIT CONVERSIONS 
- If product says "12 inches" → return "12" (NOT 30.48, NOT 30, NOT any conversion)
- If product says "30 cm" → return "30" (NOT 11.8, NOT 12, NOT any conversion)
- Extract ONLY the number as written - NEVER convert between units
- This is the MOST IMPORTANT rule - violating it will cause errors

CATEGORY: {category_name}

METAFIELDS TO FILL:
{section}

PRODUCT INFORMATION:
{product_info}

CRITICAL RULES - NO HALLUCINATION:

1. READ THE TITLE FIRST - The product title often contains the most important specifications:
   - Look for numbers (capacity, size, dimensions, power, etc.)
   - Look for brand names, model numbers, types
   - Look for key features mentioned in the title
   - Example: "كيزر كهرباء ايطالي 80 لتر نوع اريستون- ايكو" contains:
     * Capacity: 80 لتر (80 liters)
     * Type: اريستون (Ariston brand)
     * Power: كهرباء (electric)

2. READ THE DESCRIPTION CAREFULLY - The description contains detailed specifications:
   - Look in the "PRODUCT DESCRIPTION" section above
   - Read all paragraphs and bullet points
   - Check both Arabic and English descriptions if available
   - Extract all technical specifications mentioned

3. ONLY extract information that is EXPLICITLY stated in the product data:
   - Product TITLE (check this FIRST - it often has key specs)
   - Product DESCRIPTION (read carefully - contains detailed info)
   - Variants and their selected options (Color, Size, etc.)
   - Tags
   - Product type

4. DO NOT infer, guess, or assume ANY values based on:
   - Product category or type
   - Similar products
   - Common characteristics
   - Your knowledge of similar items

5. If information is NOT explicitly found in the product data:
   - Return null for that metafield
   - DO NOT make up values
   - DO NOT use common/default values
   - Empty/null is the CORRECT answer when information is missing

6. For list fields: return array ONLY when multiple values are explicitly stated.

7. For single values: return the exact value as stated, or null if not found.

8. CRITICAL - UNIT HANDLING - NO CONVERSIONS:
   - Extract the EXACT NUMBER as stated in the product (title, description, etc.)
   - DO NOT convert units (liters to gallons, kg to lbs, inches to cm, cm to inches, etc.)
   - DO NOT convert between measurement systems (imperial to metric or vice versa)
   - If product says "80 لتر" (80 liters) → extract "80" (the number, not converted)
   - If product says "50 gallons" → extract "50" (the number)
   - If product says "12 inches" → extract "12" (NOT converted to 30.48 cm)
   - If product says "30 cm" → extract "30" (NOT converted to 11.8 inches)
   - If metafield name says "blade-diameter-cm" but product says "12 inches" → extract "12" (NOT 30.48)
   - The metafield name may indicate the expected unit, but extract the literal number from the product
   - Only use the number that appears in the product data itself
   - NEVER perform unit conversions - use the exact number as written

EXAMPLES:
- Title: "كيزر كهرباء ايطالي 80 لتر نوع اريستون- ايكو"
  → Extract capacity: "80" (from "80 لتر" in title)
  → Extract power-source: ["AC-powered"] (from "كهرباء" = electric in title)
  → Extract brand/type: "اريستون" (Ariston mentioned in title)
  
- If description says "Color: Black" or variant has "Color: Black" → use "Black"
- If NO mention of color anywhere → use null (NOT a guessed color)
- If description says "140 watts" → extract "140" for power
- If product title says "80 لتر" (80 liters) and metafield is capacity-gallons → extract "80" (NOT converted to 21)
- If product says "50 kg" and metafield expects lbs → extract "50" (NOT converted to 110)
- If product says "12 inches" and metafield is blade-diameter-cm → extract "12" (NOT converted to 30.48)
- If product says "30 cm" and metafield expects inches → extract "30" (NOT converted to 11.8)
- If NO mention of capacity → use null (NOT a guessed value)

IMPORTANT: The TITLE is often the most reliable source for key specifications. Read it word by word, including Arabic text.

Return ONLY valid JSON (no comments allowed):
{{
  "metafields": {{
    "metafield_key1": "value1",
    "metafield_key2": ["value1","value2"],
    "metafield_key3": null
  }}
}}"""
        try:
            txt = call_llm(model, system="⚠️ CRITICAL: Extract EXACT numbers as written in product data. ABSOLUTELY NO UNIT CONVERSIONS. If product says '12 inches', return '12' NOT '30.48'. If product says '30 cm', return '30' NOT '11.8'. NEVER convert between units (inches/cm, liters/gallons, kg/lbs, etc.). Extract ONLY explicitly stated information. NEVER guess values. Read TITLE first - it contains key specs. Use null when information not found. Return valid JSON.", user=prompt)
            result = json.loads(txt)
            return merge_llm_result_into_product(p, result, metafield_definitions)
        except Exception as e:
            print(f"    Error: {e}")
            q = p.copy()
            q["category_metafields"] = {}
            return q

    results = [None]*len(products)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {ex.submit(_one, p): i for i,p in enumerate(products)}
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            results[idx] = fut.result()
    return results


# --------------------------
# MATRIXIFY CSV EXPORT (new)
# --------------------------
def matrixify_header(mf: Dict, check_products_for_handles: List[Dict] = None) -> str:
    """
    Generate Matrixify header for a metafield.
    If check_products_for_handles is provided, checks actual product values
    to determine if this should be metaobject_reference type.
    """
    ns, key = extract_namespace_and_key(mf)
    mf_type = mf.get('type', '')
    
    # Check if this should be metaobject_reference instead of single_line_text_field
    # Matrixify reports these fields as metaobject_reference when they contain handles
    if 'list.single_line_text_field' in mf_type:
        # Check if any actual product values look like handles (contain __)
        is_metaobject = False
        
        if check_products_for_handles:
            for product in check_products_for_handles:
                mf_values = product.get("category_metafields", {}).get(key)
                if mf_values:
                    values_list = mf_values if isinstance(mf_values, list) else [mf_values]
                    if any('__' in str(v) for v in values_list if v):
                        is_metaobject = True
                        break
        
        if not is_metaobject:
            values = mf.get('values', [])
            has_handles = any('__' in str(v) for v in values)
            has_handle_mapping = bool(mf.get('value_to_handle'))
            is_metaobject = has_handles or has_handle_mapping
        
        if is_metaobject:
            mf_type = mf_type.replace('single_line_text_field', 'metaobject_reference')
    
    return f"Metafield: {ns}.{key} [{mf_type}]"

def to_matrixify_row(product: Dict, metafield_definitions: List[Dict], handle_field: str = "handle", header_map: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Build a single Matrixify row:
    - Must include 'Handle' (or you can change to 'ID' if that's your workflow).
    - Include 'Title' column for product identification
    - One column per metafield: "Metafield: namespace.key [type]"
    - header_map: optional dict mapping metafield key to header name (if provided, use this instead of generating)
    """
    row: Dict[str, Any] = {}
    handle = product.get(handle_field) or product.get("handle") or product.get("Handle")
    if not handle:
        handle = product.get('onlineStoreUrl', '').rsplit('/', 1)[-1] if product.get('onlineStoreUrl') else None
    row["Handle"] = handle or ""
    
    row["Title"] = product.get("title", product.get("Title", ""))

    mf_values = product.get("category_metafields", {})
    for mf in metafield_definitions:
        if header_map and mf["key"] in header_map:
            col = header_map[mf["key"]]
        else:
            col = matrixify_header(mf)
        raw = mf_values.get(mf["key"])
        formatted = format_value_for_type(raw, mf) 
        row[col] = formatted if formatted is not None else ""
    return row

def write_matrixify_csv(products: List[Dict], metafield_definitions: List[Dict], csv_path: str, handle_field: str = "handle") -> None:
    import csv

    headers = []
    header_map = {}  
    for mf in metafield_definitions:
        header = matrixify_header(mf, check_products_for_handles=products)
        headers.append(header)
        header_map[mf["key"]] = header
    
    fieldnames = ["Handle", "Title"] + headers
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in products:
            w.writerow(to_matrixify_row(p, metafield_definitions, handle_field=handle_field, header_map=header_map))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fill category metafields and optionally export Matrixify CSV")
    parser.add_argument('--products', required=True, help='Path to products JSON file')
    parser.add_argument('--mapping', required=True, help='Path to category mapping JSON file')
    parser.add_argument('--output', required=True, help='Output JSON file for products with metafields')
    parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model (default: gpt-4o-mini)')
    parser.add_argument('--mode', choices=['single', 'parallel'], default='parallel', help='Processing mode')
    parser.add_argument('--workers', type=int, default=5, help='Parallel workers (default 5)')
    parser.add_argument('--limit', type=int, help='Limit number of products (testing)')
    parser.add_argument('--matrixify-csv', help='If set, write Matrixify-ready CSV to this path')
    parser.add_argument('--handle-field', default='handle', help='Field name in product JSON to use as Handle')
    parser.add_argument('--use-handles', action='store_true', default=True, help='Convert values to Shopify handles (default: True)')
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Missing OPENAI_API_KEY in .env")

    print(f"Loading products: {args.products}")
    products = load_json(args.products)
    if args.limit and args.limit < len(products):
        products = products[:args.limit]
        print(f"  Limited to {len(products)} products")
    else:
        print(f"  Loaded {len(products)} products")

    print(f"Loading mapping: {args.mapping}")
    mapping = load_json(args.mapping)
    category_name = mapping["category"]["fullName"]
    metafield_definitions = mapping["metafields"]
    print(f"  Category: {category_name}")
    print(f"  Metafields: {len(metafield_definitions)}")

    if args.mode == 'parallel':
        enriched = fill_metafields_parallel(products, metafield_definitions, category_name, model=args.model, max_workers=args.workers)
    else:
        enriched = fill_metafields_single(products, metafield_definitions, category_name, model=args.model)

    # Convert values to handles if requested
    if args.use_handles:
        print("Converting values to Shopify handles...")
        try:
            # Import handle mapping module
            handles_module_path = Path(__file__).parent / "load_shopify_handles.py"
            spec = importlib.util.spec_from_file_location("load_shopify_handles", handles_module_path)
            handles_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(handles_module)
            
            handle_map = handles_module.load_shopify_handles()
            # Create attribute key map: metafield key -> attribute handle
            attribute_key_map = {}
            for mf in metafield_definitions:
                key = mf.get("key", "")
                # Try to get handle from namespace.key format
                namespace = mf.get("namespace", "standard")
                attr_handle = mf.get("handle")
                if not attr_handle:
                    # Derive handle from key (replace underscore with dash)
                    attr_handle = key.replace("_", "-")
                attribute_key_map[key] = attr_handle
            
            converted_count = 0
            total_converted = 0
            for product in enriched:
                if "category_metafields" in product:
                    original = product["category_metafields"].copy()
                    product["category_metafields"] = handles_module.map_metafields_to_handles(
                        product["category_metafields"], 
                        handle_map, 
                        attribute_key_map
                    )
                    # Count how many values were converted
                    for key, new_val in product["category_metafields"].items():
                        old_val = original.get(key)
                        if new_val != old_val:
                            total_converted += 1
                    if product["category_metafields"] != original:
                        converted_count += 1
            print(f"  ✓ Converted {total_converted} values to handles for {converted_count} products")
        except Exception as e:
            print(f"  ⚠ Warning: Could not convert to handles: {e}")
            import traceback
            traceback.print_exc()
            print("  Continuing with plain text values...")

    print(f"Saving JSON: {args.output}")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    save_json(args.output, enriched)

    if args.matrixify_csv:
        print(f"Writing Matrixify CSV: {args.matrixify_csv}")
        write_matrixify_csv(enriched, metafield_definitions, args.matrixify_csv, handle_field=args.handle_field)

    # Stats
    total = len(enriched)
    with_mf = sum(1 for p in enriched if p.get("category_metafields"))
    filled = 0
    for p in enriched:
        filled += sum(1 for v in (p.get("category_metafields") or {}).values() if v not in (None, "", []))
    print("\n==== SUMMARY ====")
    print(f"Products processed: {total}")
    print(f"Products with any metafields: {with_mf}")
    print(f"Total metafield entries (pre-format): {filled}")
    print("=================")


if __name__ == "__main__":
    main()

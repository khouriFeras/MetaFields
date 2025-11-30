#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Key Metafields for a Collection using OpenAI

Given a Shopify COLLECTION (e.g. "Water Heaters", "TVs", "Pumps"),
return the MOST IMPORTANT metafields that will give the best customer experience:
- great filters
- clear product cards
- easy comparison between products
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

COLLECTION_SYSTEM_PROMPT = """
You are an expert Shopify metafield strategist specializing in e-commerce product data.

Your task:
Given a PRODUCT COLLECTION name, design the MOST IMPORTANT and USEFUL metafields that will
create an exceptional shopping experience for customers browsing that collection.

"Exceptional shopping experience" means:
1. FILTERING: Customers can easily filter products by the most important attributes
2. COMPARISON: Customers can compare products side-by-side on key decision factors
3. DISCOVERY: Customers can quickly identify products that match their specific needs
4. TRUST: Customers can see technical specifications that build confidence

STRATEGIC APPROACH:
- Think like a customer: What questions do they ask when shopping for this product type?
- Think like a merchant: What attributes differentiate products and drive sales?
- Think like a search engine: What filters would help customers find exactly what they need?

STRICT RULES:
- Output 4 to 8 metafields maximum (prioritize quality over quantity).
- Focus on the 20% of specs that matter for 80% of buying decisions.
- Use clean namespace "shopify".
- Key must be kebab-case (example: water-heater-type, room-size-m2, max-temperature-c).
- Use ONLY these metafield types:
    - single_line_text_field (for free text)
    - number_integer (for whole numbers: count, quantity, etc.)
    - number_decimal (for measurements: capacity, dimensions, weight, etc.)
    - list.single_line_text_field (for predefined options: types, categories, features)
- For list types: Include 3-15 allowed values that cover the most common options.
- Keep names short, clear, and customer-friendly for filters (e.g., "Capacity (L)", "Power (W)", "Installation Type").
- Include units in the name when relevant (e.g., "Capacity (L)", "Power (W)", "Room Size (m²)").
- Do NOT include advanced technical fields that only experts care about.

METAFIELD SELECTION STRATEGY:
- INCLUDE standard Shopify taxonomy metafields when they are:
  * Highly relevant to the collection (e.g., orientation for water heaters/TVs, power-source for appliances)
  * Important for filtering and comparison (e.g., energy-efficiency-class for energy-consuming products)
  * Collection-specific attributes (e.g., capacity, dimensions, weight when they matter for this product type)
  
- EXCLUDE generic metafields that don't add value:
  * color, pattern, material, size (unless collection-specific like "TV screen size")
  * brand, model, sku, barcode (these are product identifiers, not filters)
  * warranty, price, rating (these are not product attributes)
  
- PRIORITIZE metafields that are:
  * Essential for product selection (e.g., orientation for water heaters - Vertical/Horizontal)
  * Key differentiators within the collection
  * Frequently used in customer searches and filters
  
  Good examples (INCLUDE these when relevant):
    - For water heaters: 
      * orientation (Vertical/Horizontal) - CRITICAL for installation
      * water-heater-type (Tank/Tankless/Heat Pump)
      * capacity-liters
      * installation-type (Indoor/Outdoor)
      * max-temperature-c
      * fuel-type (Electric/Gas/Solar)
      * power-source (if relevant - AC-powered/Gasoline/Electricity)
      * energy-efficiency-class (if relevant for energy-consuming products)
    
    - For TVs:
      * screen-size-inches
      * display-resolution (4K/8K/1080p)
      * display-technology (LED/OLED/QLED)
      * smart-platform (Android TV/Roku/Tizen)
      * refresh-rate-hz
      * orientation (if wall-mounting is important)
    
    - For heaters:
      * heater-type (Radiator/Ceramic/Fan)
      * power-watts
      * room-size-m2
      * safety-features (Tip-over protection/Thermostat)
      * orientation (if relevant)
      * power-source (if relevant)
    
    - For pumps:
      * pump-type (Submersible/Surface)
      * flow-rate-lpm
      * max-head-meters
      * power-source (Electric/Gas/Solar)
      * orientation (if relevant)
  
  Bad examples (EXCLUDE these):
    - color, brand, warranty, price (too generic)
    - Fields that apply to all products equally
    - Fields that are too technical and not useful for filtering
    - Duplicate fields (don't create both "power-source" and "fuel-type" if they mean the same thing)

METAFIELD NAMING GUIDELINES:
- Use clear, descriptive names that customers understand
- Include units when applicable: "Capacity (L)", "Power (W)", "Weight (kg)"
- For list types, use names that work well in dropdown filters
- Avoid abbreviations unless universally understood

VALUE QUALITY:
- Each metafield should be genuinely useful for filtering or comparison
- If a metafield won't help customers make decisions, don't include it
- Prioritize metafields that differentiate products within the collection
- Include standard taxonomy metafields (orientation, power-source, energy-efficiency-class, etc.) when they are highly relevant to the collection
- Don't exclude important metafields just because they exist in Shopify taxonomy - include them if they're essential for this product type

Return JSON ONLY in this exact structure:

{
  "collection": "...",
  "metafields": [
    {
      "namespace": "shopify",
      "key": "example-key",
      "name": "Readable Name",
      "type": "single_line_text_field",
      "allowed_values": ["a", "b", "c"] or null
    }
  ]
}
"""


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in .env")
    return OpenAI(api_key=api_key)


ARABIC_TRANSLATION_SYSTEM_PROMPT = """
You are a professional Arabic translator specializing in e-commerce and product specifications.

Your task is to translate Shopify metafield names and their allowed values to Arabic.

CRITICAL RULES:
1. Translate metafield names to clear, professional Arabic that customers will understand
2. Translate allowed_values arrays to Arabic, maintaining technical accuracy
3. Keep technical terms consistent (e.g., "4K", "OLED", "LED" may stay as-is if commonly used in Arabic markets)
4. Preserve units and numbers (e.g., "Capacity (L)" -> "السعة (لتر)", "Power (W)" -> "القدرة (واط)")
5. Use proper Arabic terminology for e-commerce and product specifications
6. Maintain the same structure and format as the input

Return JSON ONLY in this exact structure:
{
  "metafields": [
    {
      "name": "Arabic translated name",
      "allowed_values": ["Arabic value 1", "Arabic value 2"] or null
    }
  ]
}
"""


def translate_metafields_to_arabic(
    metafields: List[Dict[str, Any]],
    model: str = "gpt-4o-mini"
) -> List[Dict[str, Any]]:
    """
    Translate metafield names and allowed_values to Arabic using LLM.
    
    Args:
        metafields: List of metafield dictionaries with English names
        model: OpenAI model (default: "gpt-4o-mini")
    
    Returns:
        List of metafield dictionaries with Arabic names and allowed_values
    """
    if not metafields:
        return metafields
    
    client = get_client()
    
    # Prepare input for translation
    translation_input = {
        "metafields": [
            {
                "name": mf.get("name", ""),
                "allowed_values": mf.get("allowed_values") or mf.get("values")
            }
            for mf in metafields
        ]
    }
    
    prompt = f"""Translate the following metafield names and allowed values to Arabic:

{json.dumps(translation_input, ensure_ascii=False, indent=2)}

Return the translations in the same JSON structure with Arabic names and values."""
    
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": ARABIC_TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Strip markdown fences if present
        if "```json" in raw_output:
            raw_output = raw_output.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_output:
            raw_output = raw_output.split("```")[1].split("```")[0].strip()
        
        translation_result = json.loads(raw_output)
        
        if "metafields" not in translation_result:
            raise ValueError("Missing 'metafields' key in translation response")
        
        # Merge translations back into original metafields
        translated_metafields = []
        for i, mf in enumerate(metafields):
            translated_mf = mf.copy()
            if i < len(translation_result["metafields"]):
                translated_data = translation_result["metafields"][i]
                translated_mf["name"] = translated_data.get("name", mf.get("name", ""))
                # Update allowed_values if present in translation
                if "allowed_values" in translated_data and translated_data["allowed_values"] is not None:
                    translated_mf["allowed_values"] = translated_data["allowed_values"]
                    # Also update "values" key
                    translated_mf["values"] = translated_data["allowed_values"]
                elif "allowed_values" in translated_data and translated_data["allowed_values"] is None:
                    # Explicitly set to None if translation says None
                    translated_mf["allowed_values"] = None
                    if "values" not in translated_mf:
                        translated_mf["values"] = []
                # Preserve existing values if translation doesn't provide new ones
                if "allowed_values" not in translated_data:
                    # Translation didn't provide allowed_values, keep original
                    if "allowed_values" not in translated_mf:
                        translated_mf["allowed_values"] = mf.get("allowed_values")
                    if "values" not in translated_mf:
                        translated_mf["values"] = mf.get("values", [])
            else:
                # Translation result doesn't have this metafield - keep original
                pass
            
            # Ensure all required fields are preserved
            if "key" not in translated_mf:
                translated_mf["key"] = mf.get("key", "")
            if "namespace" not in translated_mf:
                translated_mf["namespace"] = mf.get("namespace", "shopify")
            if "type" not in translated_mf:
                translated_mf["type"] = mf.get("type", "single_line_text_field")
            
            translated_metafields.append(translated_mf)
        
        # Verify we didn't lose any metafields
        if len(translated_metafields) != len(metafields):
            print(f"⚠️ WARNING: Translation lost {len(metafields) - len(translated_metafields)} metafields!")
            # Add back any missing metafields
            original_keys = {mf.get("key") for mf in metafields}
            translated_keys = {mf.get("key") for mf in translated_metafields}
            missing_keys = original_keys - translated_keys
            for mf in metafields:
                if mf.get("key") in missing_keys:
                    translated_metafields.append(mf)
                    print(f"  Restored: {mf.get('name', 'Unknown')} ({mf.get('key', 'unknown')})")
        
        return translated_metafields
        
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON for translation:\n{raw_output}\n\nError: {e}")
    except Exception as e:
        raise ValueError(f"Error translating to Arabic: {e}")


def generate_collection_metafields(
    collection_name: str,
    existing_metafields: Optional[List[Dict[str, Any]]] = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Generate the most important metafields for a Shopify collection.

    Args:
        collection_name: Collection title or handle (e.g., "Heaters", "Water Heaters", "TVs")
        existing_metafields: Optional list of existing taxonomy metafields to avoid duplicates
        model: OpenAI model (default: "gpt-4o-mini")

    Returns:
        Dict with "collection" and "metafields" keys
    """
    client = get_client()

    # Build list of existing metafield keys/names to avoid
    existing_keys: set[str] = set()
    existing_names: set[str] = set()

    if existing_metafields:
        for mf in existing_metafields:
            namespace = mf.get("namespace", "standard")
            key = mf.get("key", "")
            name = mf.get("name", "").lower()
            if key:
                existing_keys.add(f"{namespace}.{key}")
                existing_keys.add(key)
            if name:
                existing_names.add(name)

    # Tell the model what to avoid, if we know existing metafields
    existing_info = ""
    if existing_keys:
        existing_info = "\n\nEXISTING METAFIELDS TO AVOID (already in taxonomy):\n"
        preview = ", ".join(sorted(existing_keys)[:20])
        existing_info += preview
        if len(existing_keys) > 20:
            existing_info += f" (and {len(existing_keys) - 20} more)"
        existing_info += "\nDO NOT create metafields with these keys or similar names."

    prompt = f"Design the most important metafields for this Shopify collection: {collection_name}{existing_info}"

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": COLLECTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        raw_output = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if "```json" in raw_output:
            raw_output = raw_output.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_output:
            raw_output = raw_output.split("```")[1].split("```")[0].strip()

        result = json.loads(raw_output)

        if "metafields" not in result:
            raise ValueError("Missing 'metafields' key in LLM response")

        filtered: List[Dict[str, Any]] = []
        for mf in result.get("metafields", []):
            # Basic validation
            if "namespace" not in mf:
                mf["namespace"] = "shopify"
            if "key" not in mf:
                raise ValueError("Metafield missing 'key' field")
            if "name" not in mf:
                raise ValueError("Metafield missing 'name' field")
            if "type" not in mf:
                raise ValueError("Metafield missing 'type' field")

            namespace = mf.get("namespace", "shopify")
            key = mf["key"]
            name_lower = mf["name"].lower()

            # Skip duplicates vs existing taxonomy
            is_duplicate = False
            if existing_metafields:
                for ex in existing_metafields:
                    ex_ns = ex.get("namespace", "standard")
                    ex_key = ex.get("key", "")
                    ex_name = ex.get("name", "").lower()

                    if (namespace == ex_ns and key == ex_key) or key == ex_key:
                        is_duplicate = True
                        break

                    # Simple semantic duplicate check for energy/efficiency-like fields
                    if name_lower and ex_name:
                        if name_lower in ex_name or ex_name in name_lower:
                            energy_words = ["energy", "efficiency", "rating", "class"]
                            if any(w in name_lower for w in energy_words) and any(
                                w in ex_name for w in energy_words
                            ):
                                is_duplicate = True
                                break

            if not is_duplicate:
                filtered.append(mf)

        result["metafields"] = filtered
        result["collection"] = collection_name
        
        # Translate metafields to Arabic
        print("Translating metafields to Arabic...")
        try:
            translated_metafields = translate_metafields_to_arabic(filtered, model)
            result["metafields"] = translated_metafields
            print(f"✓ Translated {len(translated_metafields)} metafields to Arabic")
        except Exception as e:
            print(f"⚠ Warning: Failed to translate to Arabic: {e}")
            print("  Continuing with English names...")
            # Continue with English names if translation fails
        
        return result

    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON:\n{raw_output}\n\nError: {e}")
    except Exception as e:
        raise ValueError(f"Error calling OpenAI API: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_collection_metafields.py <collection name>")
        sys.exit(1)

    # Support multi-word collection names
    collection_name = " ".join(sys.argv[1:])
    print(f"Generating key metafields for collection: {collection_name}")
    try:
        result = generate_collection_metafields(collection_name)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

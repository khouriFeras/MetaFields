#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Basic Metafields using OpenAI
Creates 3-6 basic metafields for a given product category.
"""
import json
import os
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv

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

BASIC_SYSTEM_PROMPT = """
You are a Shopify metafield designer.

Your task:

Given a product CATEGORY, output ONLY the *basic metafields* needed to describe this category.

STRICT RULES:

- Output 3 to 6 metafields maximum.

- Keep them generic and basic.

- Use clean namespace "shopify".

- Key must be kebab-case (example: water-heater-type).

- Use ONLY these metafield types:

    - single_line_text_field

    - number_integer

    - number_decimal

    - list.single_line_text_field

- If allowed values make sense, include them. Otherwise return null.

- Do NOT include advanced or unnecessary fields.

- Keep everything short and simple.

CRITICAL - AVOID DUPLICATES:
- DO NOT create metafields that already exist in Shopify taxonomy (standard namespace)
- Common taxonomy metafields to AVOID:
  * color, pattern, material, size, brand, model
  * energy-efficiency-class, power-source, orientation
  * capacity, dimensions, weight (these may exist)
  * warranty, price, rating
- Focus on category-SPECIFIC fields that are NOT in standard taxonomy
- Examples of GOOD basic metafields: water-heater-type, installation-type, fuel-type
- Examples of BAD basic metafields: color, energy-efficiency-class, power-source

Return JSON ONLY in this exact structure:

{
  "category": "...",
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


def display_metafields(metafields: List[Dict], title: str = "Metafields") -> None:
    """Display metafields in a readable format."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    if not metafields:
        print("  (No metafields)")
        return
    
    for i, mf in enumerate(metafields, 1):
        namespace = mf.get("namespace", "shopify")
        key = mf.get("key", "unknown")
        name = mf.get("name", "Unknown")
        mf_type = mf.get("type", "unknown")
        allowed_values = mf.get("allowed_values") or mf.get("values")
        
        print(f"\n{i}. {name}")
        print(f"   Key: {namespace}.{key}")
        print(f"   Type: {mf_type}")
        if allowed_values:
            values_str = ", ".join(str(v) for v in allowed_values[:5])
            if len(allowed_values) > 5:
                values_str += f" (and {len(allowed_values) - 5} more)"
            print(f"   Allowed Values: {values_str}")
    print(f"\n{'='*60}")


def add_single_metafield(description: str, category: str, existing_metafields: List[Dict] = None, model: str = "gpt-4o-mini") -> Dict:
    """
    Add a single metafield based on user description.
    
    Args:
        description: User's description of the metafield they want (e.g., "warranty period")
        category: Category name
        existing_metafields: List of existing metafields to avoid duplicates
        model: OpenAI model to use
    
    Returns:
        Single metafield dictionary
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in .env")
    
    client = _OPENAI_CLIENT_CTOR(api_key=api_key)
    
    # Build list of existing keys
    existing_keys = set()
    if existing_metafields:
        for mf in existing_metafields:
            key = mf.get("key", "")
            if key:
                existing_keys.add(key)
    
    existing_info = ""
    if existing_keys:
        existing_info = f"\n\nEXISTING METAFIELD KEYS TO AVOID: {', '.join(sorted(existing_keys)[:15])}"
    
    prompt = f"""Create a SINGLE metafield for category "{category}" based on this description: "{description}"

REQUIREMENTS:
- Create exactly ONE metafield
- Use namespace "shopify"
- Key must be kebab-case (e.g., warranty-period-years)
- Use appropriate type: single_line_text_field, number_integer, number_decimal, or list.single_line_text_field
- Include allowed_values if it makes sense (e.g., for list types or limited options)
- DO NOT duplicate existing metafields{existing_info}

Return JSON ONLY in this exact structure:
{{
  "namespace": "shopify",
  "key": "example-key",
  "name": "Readable Name",
  "type": "single_line_text_field",
  "allowed_values": ["a", "b", "c"] or null
}}"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": "You create Shopify metafield definitions. Return ONLY valid JSON, no comments."},
                {"role": "user", "content": prompt}
            ]
        )
        
        output = response.choices[0].message.content.strip()
        
        # Extract JSON
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
        
        result = json.loads(output)
        
        # Ensure namespace
        if "namespace" not in result:
            result["namespace"] = "shopify"
        
        # Check for duplicates
        if existing_metafields:
            key = result.get("key", "")
            for existing_mf in existing_metafields:
                if existing_mf.get("key") == key:
                    raise ValueError(f"Metafield with key '{key}' already exists!")
        
        return result
        
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON:\n{output}\n\nError: {e}")
    except Exception as e:
        raise ValueError(f"Error creating metafield: {e}")


def generate_basic_metafields(category: str, existing_metafields: List[Dict] = None, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Generate basic metafields for a category using OpenAI.
    
    Args:
        category: Category name (e.g., "Televisions", "Water Pumps")
        existing_metafields: List of existing metafields from taxonomy to avoid duplicates
        model: OpenAI model to use (default: "gpt-4o-mini")
    
    Returns:
        Dictionary with "category" and "metafields" keys (duplicates filtered out)
        
    Raises:
        ValueError: If LLM doesn't return valid JSON
        SystemExit: If OPENAI_API_KEY is missing
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY in .env")
    
    client = _OPENAI_CLIENT_CTOR(api_key=api_key)
    
    # Build list of existing metafield keys to avoid
    existing_keys = set()
    existing_names = set()
    if existing_metafields:
        for mf in existing_metafields:
            namespace = mf.get("namespace", "standard")
            key = mf.get("key", "")
            name = mf.get("name", "").lower()
            if key:
                existing_keys.add(f"{namespace}.{key}")
                existing_keys.add(key)  # Also check without namespace
            if name:
                existing_names.add(name)
    
    # Build prompt with existing metafields info
    existing_info = ""
    if existing_keys:
        existing_info = f"\n\nEXISTING METAFIELDS TO AVOID (already in taxonomy):\n"
        existing_info += ", ".join(sorted(existing_keys)[:20])  # Show first 20
        if len(existing_keys) > 20:
            existing_info += f" (and {len(existing_keys) - 20} more)"
        existing_info += "\nDO NOT create metafields with these keys or similar names."
    
    prompt = f"Generate basic metafields for category: {category}{existing_info}"
    
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": BASIC_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse JSON returned by the LLM
        output = response.choices[0].message.content.strip()
        
        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(output)
            
            # Validate structure
            if "metafields" not in result:
                raise ValueError("Missing 'metafields' key in LLM response")
            
            # Ensure all metafields have required fields and filter duplicates
            filtered_metafields = []
            for mf in result.get("metafields", []):
                if "namespace" not in mf:
                    mf["namespace"] = "shopify"
                if "key" not in mf:
                    raise ValueError("Metafield missing 'key' field")
                if "name" not in mf:
                    raise ValueError("Metafield missing 'name' field")
                if "type" not in mf:
                    raise ValueError("Metafield missing 'type' field")
                
                # Check for duplicates with existing metafields
                namespace = mf.get("namespace", "shopify")
                key = mf.get("key", "")
                name_lower = mf.get("name", "").lower()
                
                is_duplicate = False
                if existing_metafields:
                    for existing_mf in existing_metafields:
                        existing_ns = existing_mf.get("namespace", "standard")
                        existing_key = existing_mf.get("key", "")
                        existing_name = existing_mf.get("name", "").lower()
                        
                        # Check by key (namespace.key or just key)
                        if (namespace == existing_ns and key == existing_key) or key == existing_key:
                            is_duplicate = True
                            break
                        # Check by similar name (fuzzy match)
                        if name_lower and existing_name:
                            # Check if names are very similar (e.g., "energy efficiency rating" vs "energy efficiency class")
                            if name_lower in existing_name or existing_name in name_lower:
                                # Check if they're semantically the same
                                if any(word in name_lower for word in ["energy", "efficiency", "rating", "class"]) and \
                                   any(word in existing_name for word in ["energy", "efficiency", "rating", "class"]):
                                    is_duplicate = True
                                    break
                
                if not is_duplicate:
                    filtered_metafields.append(mf)
            
            result["metafields"] = filtered_metafields
            return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM did not return valid JSON:\n{output}\n\nError: {e}")
            
    except Exception as e:
        raise ValueError(f"Error calling OpenAI API: {e}")


if __name__ == "__main__":
    """Example usage"""
    if len(sys.argv) < 2:
        print("Usage: python generate_basic_metafields.py <category_name>")
        sys.exit(1)
    
    category = sys.argv[1]
    print(f"Generating basic metafields for category: {category}")
    
    try:
        result = generate_basic_metafields(category)
        print("\nGenerated metafields:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


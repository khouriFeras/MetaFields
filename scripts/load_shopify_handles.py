#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load Shopify handles from YAML files for metafield value mapping.
Maps human-readable values to Shopify handle format.
"""
import yaml
from pathlib import Path
from typing import Dict, Optional, List
import re


def normalize_value(value: str) -> str:
    """Normalize value name for matching (lowercase, remove special chars)."""
    if not value:
        return ""
    # Convert to lowercase
    normalized = value.lower().strip()
    # Remove common prefixes/suffixes
    normalized = re.sub(r'^(the|a|an)\s+', '', normalized)
    # Replace common variations
    normalized = normalized.replace("'", "")
    normalized = normalized.replace('"', '')
    return normalized


def load_shopify_handles(attributes_file: str = "data/shopify_attributes.yml",
                        values_file: str = "data/shopify_values.yml") -> Dict[str, Dict[str, str]]:
    """
    Load Shopify handles mapping.
    Returns: {attribute_handle: {value_name: handle}}
    Example: {"audio-technology": {"dolby atmos": "audio-technology__dolby-atmos"}}
    """
    attributes_path = Path(attributes_file)
    values_path = Path(values_file)
    
    if not attributes_path.exists() or not values_path.exists():
        raise FileNotFoundError(
            f"YAML files not found. Expected:\n"
            f"  - {attributes_file}\n"
            f"  - {values_file}"
        )
    
    # Load values first to build a lookup
    print(f"  Loading values from {values_file}...")
    with open(values_path, 'r', encoding='utf-8') as f:
        values_data = yaml.safe_load(f)
    
    # Build value lookup: {friendly_id: {handle, name}}
    value_lookup = {}
    if values_data:
        for value_item in values_data:
            handle = value_item.get('handle', '')
            name = value_item.get('name', '')
            friendly_id = value_item.get('friendly_id', '')
            if handle and friendly_id:
                value_lookup[friendly_id] = {
                    'handle': handle,
                    'name': name
                }
    
    print(f"  Loaded {len(value_lookup)} values")
    
    # Load attributes to get attribute handles and their values
    print(f"  Loading attributes from {attributes_file}...")
    with open(attributes_path, 'r', encoding='utf-8') as f:
        attributes_data = yaml.safe_load(f)
    
    # Build final mapping: {attribute_handle: {value_name: handle}}
    result = {}
    
    if attributes_data and 'base_attributes' in attributes_data:
        for attr in attributes_data['base_attributes']:
            attr_handle = attr.get('handle', '').replace('_', '-')
            friendly_id = attr.get('friendly_id', '')
            
            if not attr_handle:
                continue
            
            result[attr_handle] = {}
            
            # For each value friendly_id listed in attribute
            for value_friendly_id in attr.get('values', []):
                if value_friendly_id in value_lookup:
                    value_info = value_lookup[value_friendly_id]
                    value_handle = value_info['handle']
                    value_name = value_info['name']
                    
                    # Map by normalized name, original name (lowercase), and friendly_id
                    normalized = normalize_value(value_name)
                    result[attr_handle][normalized] = value_handle
                    result[attr_handle][value_name.lower()] = value_handle
                    result[attr_handle][value_friendly_id] = value_handle
                    # Also map by exact handle if it starts with attribute
                    if value_handle.startswith(attr_handle.replace('-', '__')):
                        result[attr_handle][value_handle] = value_handle
    
    print(f"  Loaded {len(result)} attributes with handle mappings")
    return result


def map_value_to_handle(attribute_handle: str, value: str, handle_map: Dict[str, Dict[str, str]]) -> Optional[str]:
    """
    Map a human-readable value to its Shopify handle.
    
    Args:
        attribute_handle: Attribute handle (e.g., "audio-technology")
        value: Human-readable value (e.g., "Dolby atmos", "Dolby Atmos")
        handle_map: Handle mapping from load_shopify_handles()
    
    Returns:
        Shopify handle (e.g., "audio-technology__dolby-atmos") or None if not found
    """
    if not value or not attribute_handle:
        return None
    
    # If value is already a handle (contains "__"), return as-is
    if "__" in str(value) and value.startswith(f"{attribute_handle.replace('-', '__')}__"):
        return str(value)
    
    attr_mapping = handle_map.get(attribute_handle, {})
    if not attr_mapping:
        # Try alternative attribute handle formats
        alt_handles = [
            attribute_handle.replace('-', '_'),
            attribute_handle.replace('_', '-'),
        ]
        for alt in alt_handles:
            if alt in handle_map:
                attr_mapping = handle_map[alt]
                break
    
    if not attr_mapping:
        return None
    
    # Try multiple matching strategies
    normalized = normalize_value(value)
    
    # 1. Exact normalized match
    if normalized in attr_mapping:
        return attr_mapping[normalized]
    
    # 2. Case-insensitive match
    for key, handle in attr_mapping.items():
        if normalize_value(key) == normalized:
            return handle
    
    # 3. Try with common variations (before partial match)
    variations = [
        value.lower(),
        value.lower().replace('-', ' '),
        value.lower().replace('_', ' '),
        value.lower().replace('+', ' plus'),
        value.lower().replace('/', ' '),
        value.lower().replace(':', ''),
        normalized,
    ]
    for variant in variations:
        normalized_variant = normalize_value(variant)
        if normalized_variant in attr_mapping:
            return attr_mapping[normalized_variant]
        # Also try case-insensitive match for variant
        for key, handle in attr_mapping.items():
            if normalize_value(key) == normalized_variant:
                return handle
    
    # 4. Partial match (contains) - more aggressive
    for key, handle in attr_mapping.items():
        key_normalized = normalize_value(key)
        # Check if one contains the other
        if normalized in key_normalized or key_normalized in normalized:
            # Only return if it's a reasonable match (not too short)
            if len(normalized) >= 3 or len(key_normalized) >= 3:
                return handle
    
    return None


def map_metafields_to_handles(metafields: Dict, handle_map: Dict[str, Dict[str, str]], 
                              attribute_key_map: Dict[str, str]) -> Dict:
    """
    Convert metafield values to Shopify handles.
    
    Args:
        metafields: {key: value} where key is like "audio-technology", value is string or list
        handle_map: Handle mapping from load_shopify_handles()
        attribute_key_map: Maps metafield keys to attribute handles (e.g., {"audio-technology": "audio-technology"})
    
    Returns:
        {key: handle_value} where values are converted to handles
    """
    result = {}
    
    for key, value in metafields.items():
        if value is None:
            result[key] = None
            continue
        
        # Get attribute handle (may need to map from key)
        attr_handle = attribute_key_map.get(key, key)
        
        # Handle list values
        if isinstance(value, list):
            mapped_list = []
            for item in value:
                handle = map_value_to_handle(attr_handle, str(item), handle_map)
                if handle:
                    mapped_list.append(handle)
                else:
                    # If not found, keep original (or could skip)
                    mapped_list.append(str(item))
            result[key] = mapped_list if mapped_list else None
        else:
            # Single value
            handle = map_value_to_handle(attr_handle, str(value), handle_map)
            result[key] = handle if handle else value
    
    return result


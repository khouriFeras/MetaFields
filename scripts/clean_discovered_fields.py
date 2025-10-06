#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
clean_discovered_fields.py
- Cleans up discovered meta fields by removing unnecessary fields
- Removes price (already in variants), ratings, and user_preferences (always NULL)
"""

import json
from pathlib import Path


def clean_discovered_fields(input_file: str, output_file: str = None) -> None:
    """Clean discovered meta fields by removing unnecessary fields."""
    
    # Load discovery results
    with open(input_file, 'r', encoding='utf-8') as f:
        discovery_data = json.load(f)
    
    # Fields to remove
    fields_to_remove = ['price', 'ratings', 'user_preferences']
    
    # Clean discovered fields
    cleaned_fields = {}
    for field_key, field_def in discovery_data['discovered_fields'].items():
        if field_key not in fields_to_remove:
            cleaned_fields[field_key] = field_def
    
    # Update discovery data
    discovery_data['discovered_fields'] = cleaned_fields
    
    # Update counts
    discovery_data['original_field_count'] = len(discovery_data['discovered_fields']) + len(fields_to_remove)
    discovery_data['cleaned_field_count'] = len(cleaned_fields)
    discovery_data['removed_fields'] = fields_to_remove
    
    # Save cleaned results
    if output_file is None:
        output_file = input_file.replace('.json', '_cleaned.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(discovery_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Cleaned meta fields:")
    print(f"  - Original fields: {discovery_data['original_field_count']}")
    print(f"  - Removed fields: {fields_to_remove}")
    print(f"  - Cleaned fields: {discovery_data['cleaned_field_count']}")
    print(f"  - Saved to: {output_file}")
    
    return output_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean discovered meta fields")
    parser.add_argument('--input-file', required=True, help='Discovery results JSON file')
    parser.add_argument('--output-file', help='Output file for cleaned results')
    
    args = parser.parse_args()
    
    clean_discovered_fields(args.input_file, args.output_file)

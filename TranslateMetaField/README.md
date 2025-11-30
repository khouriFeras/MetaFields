# Translate MetaFields from Arabic to English

This directory contains a script to translate Shopify metafield definitions from Arabic to English, preserving both languages in a bilingual JSON dictionary.

## Overview

The translation script:
- Fetches metafield definitions from Shopify using GraphQL API
- Can work with all metafields or focus on metafields used by products in a specific collection
- Extracts metafield names, descriptions, and allowed values (options)
- Translates Arabic text to English using OpenAI
- Generates safe machine names (slugs) for each allowed value
- Preserves both Arabic and English versions in the output

### Collection Mode

When using `--collection`, the script:
1. Fetches all products from the specified collection
2. Extracts unique metafield namespace.key pairs from those products
3. Fetches only the metafield definitions for those keys
4. Translates only those metafields

This is useful when you want to translate metafields for a specific product category or collection, rather than all metafields in your store.

## Usage

### Basic Usage

Translate metafields in the "custom" namespace (default):

```bash
python TranslateMetaField/translate_metafields.py
```

### Options

- `--namespace NAMESPACE` - Filter by namespace (default: `custom`)
- `--collection IDENTIFIER` - Translate metafields used by products in a specific collection (by handle, title, or ID)
- `--all` - Fetch metafields from all namespaces (overrides `--namespace`)
- `--output PATH` - Output JSON file path (default: `TranslateMetaField/metafields_translations.json`)
- `--model MODEL` - OpenAI model to use (default: `gpt-4o-mini`)
- `--dry-run` - Preview translations without saving (processes first 5 metafields)

### Examples

```bash
# Translate metafields in "custom" namespace
python TranslateMetaField/translate_metafields.py

# Translate metafields used by products in a collection
python TranslateMetaField/translate_metafields.py --collection "مراوح"

# Translate metafields from collection, filtered by namespace
python TranslateMetaField/translate_metafields.py --collection "مراوح" --namespace custom

# Translate metafields in a specific namespace
python TranslateMetaField/translate_metafields.py --namespace shopify

# Fetch all namespaces
python TranslateMetaField/translate_metafields.py --all

# Dry run (preview first 5)
python TranslateMetaField/translate_metafields.py --dry-run

# Custom output file
python TranslateMetaField/translate_metafields.py --output custom_translations.json

# Use a different OpenAI model
python TranslateMetaField/translate_metafields.py --model gpt-4
```

## Output Structure

The script generates a JSON file with the following structure:

```json
{
  "locale_source": "ar",
  "locale_target": "en",
  "namespace_filter": "custom",
  "collection": "مراوح",
  "total_metafields": 10,
  "metafields": [
    {
      "id": "gid://shopify/MetafieldDefinition/123",
      "namespace": "custom",
      "key": "power-source",
      "type": "list.single_line_text_field",
      "locale_source": "ar",
      "locale_target": "en",
      "name_ar": "مصدر الطاقة",
      "name_en": "Power source",
      "description_ar": "وصف بالعربي",
      "description_en": "Description in English",
      "allowed_values_ar": ["كهرباء", "غاز"],
      "allowed_values_en": [
        {
          "value_ar": "كهرباء",
          "value_en": "Electric",
          "slug": "electric"
        },
        {
          "value_ar": "غاز",
          "value_en": "Gas",
          "slug": "gas"
        }
      ]
    }
  ]
}
```

## Requirements

- Python 3.7+
- Required packages (install via `pip install -r requirements.txt`):
  - `requests`
  - `openai`
  - `python-dotenv`

## Environment Variables

Make sure your `.env` file contains:

```env
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_your_access_token_here
SHOPIFY_API_VERSION=2024-07
OPENAI_API_KEY=your_openai_api_key_here
```

## Error Handling

The script:
- Skips failed translations and continues with others
- Logs warnings for failed items
- Preserves original Arabic text when translation fails
- Processes metafields in batches to avoid token limits

## Use Cases

The generated bilingual JSON can be used for:

1. **Validation** - Validate metafield values against allowed options
2. **Matrixify Templates** - Generate import templates with both languages
3. **LLM Prompts** - Drive AI prompts with structured metafield data
4. **Reference Dictionary** - Maintain a single source of truth for Arabic/English metafields

## Phase 2: Upload Translations to Shopify

The `upload_translations.py` script reads the translation JSON and registers English translations in Shopify using the `translationsRegister` mutation. This keeps Arabic as the default language and enables English translations to appear when customers view the store in English.

### Usage

```bash
# Register translations (definitions and product values)
python TranslateMetaField/upload_translations.py

# Dry run (preview without making changes)
python TranslateMetaField/upload_translations.py --dry-run

# Only register definition translations (skip product values)
python TranslateMetaField/upload_translations.py --skip-values

# Only register product value translations (skip definitions)
python TranslateMetaField/upload_translations.py --skip-definitions

# Limit to specific collection
python TranslateMetaField/upload_translations.py --collection "مراوح"
```

### What It Does

1. **Metafield Definition Translations**: Registers English translations for metafield definition names and descriptions using `translationsRegister`. Arabic remains the default.

2. **Product Metafield Value Translations**: Registers English translations for product metafield values. Arabic values stay on products; English translations are registered so they appear when the store language is English.

### Important Notes

- **Arabic values are preserved**: The script does NOT replace Arabic values. It only registers translations.
- **Translation keys**: Uses `"name"`, `"description"`, and `"value"` as translation keys (may need adjustment based on Shopify's schema).
- **Rate limiting**: Includes small delays between requests to respect Shopify's rate limits.
- **Error handling**: Continues processing even if some translations fail, with detailed error reporting.

### Options

- `--input PATH` - Path to translation JSON file (default: `TranslateMetaField/metafields_translations.json`)
- `--dry-run` - Preview actions without making changes
- `--skip-definitions` - Skip registering definition translations
- `--skip-values` - Skip registering product value translations
- `--locale LOCALE` - Target locale (default: `en`)
- `--collection IDENTIFIER` - Limit product updates to a specific collection


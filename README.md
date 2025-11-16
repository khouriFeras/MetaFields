# 🚀 Shopify Metafields Management System

**AI-Powered metafield filling and management using Shopify's standard product taxonomy**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Workflow](#workflow)
- [Scripts Reference](#scripts-reference)
- [Data Formats](#data-formats)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## ✨ Overview

This system automatically fills **Shopify's standard category metafields** for your products using AI. It:

1. ✅ Matches products to **Shopify's official categories** (21,000+ available)
2. ✅ Gets **standard metafields** for each category (proper types included)
3. ✅ **AI fills metafields** by analyzing product data (title, description, etc.)
4. ✅ Exports to **Excel for review** and manual editing
5. ✅ **Converts between Excel and JSON** formats
6. ✅ **Adds new metafields** without affecting existing ones
7. ✅ **Uploads metafields to Shopify** with proper key mapping
8. ✅ **Verifies uploads** and manages metafield definitions

**⚠️ Important:** This system is for **ANALYSIS ONLY** by default. It will NOT upload data to Shopify unless you explicitly request it.

---

## 🔑 Key Features

- **21,396 Shopify categories** - Complete product taxonomy
- **8,486 categories with metafields** - Standard field definitions
- **Proper types** - `list.single_line_text_field` vs `single_line_text_field`
- **Predefined values** - Dropdown options for list fields
- **Smart matching** - AI-powered category selection
- **100% coverage** - Analyzes all products
- **Excel reports** - Easy review before upload
- **Bilingual support** - Arabic and English metafields
- **GitHub-based** - No API version issues

---

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages

- `requests` - HTTP requests to Shopify API
- `python-dotenv` - Environment variable management
- `openpyxl` - Excel file handling
- `openai` - AI-powered metafield filling
- `pandas` - Data manipulation
- `pyyaml` - YAML file parsing

---

## ⚙️ Configuration

### 1. Create `.env` File

Create a `.env` file in the project root:

```env
# Shopify Configuration
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_your_token_here
SHOPIFY_API_VERSION=2024-07

# OpenAI Configuration (for AI metafield filling)
OPENAI_API_KEY=sk-your_openai_key_here

# Optional: Language Settings
TARGET_LANGUAGE=en
ORIGINAL_LANGUAGE=ar

# Optional: Output Directory
OUTPUT_DIR=exports
```

### 2. One-Time Setup: Fetch Shopify Taxonomy

Download Shopify's product taxonomy (only needs to be done once):

```bash
python scripts/fetch_shopify_taxonomy.py
```

This creates:
- `data/shopify_taxonomy_full.json` - Complete taxonomy (21K+ categories)
- `data/shopify_attributes.yml` - Metafield definitions
- `data/shopify_values.yml` - Predefined values for list fields

---

## 🔄 Workflow

### Complete Workflow Overview

```
1. Fetch Products from Shopify
   ↓
2. Match Products to Shopify Categories (AI-powered)
   ↓
3. Get Category Metafields
   ↓
4. AI Fills Metafield Values
   ↓
5. Export to Excel for Review
   ↓
6. Edit Excel File (Optional)
   ↓
7. Convert Excel Back to JSON
   ↓
8. Upload to Shopify (When Ready)
```

### Step-by-Step Guide

#### Step 1: Fetch Products

Fetch products by tag, collection, or all products:

```bash
# Fetch products by tag
python scripts/fetch_products.py --tag "Water Heaters" --output exports/water_heaters.json

# Fetch products by collection
python scripts/fetch_products.py --collection "كيزر" --output exports/geyser.json

# Fetch all products
python scripts/fetch_products.py --all --output exports/all_products.json
```

#### Step 2: Fill Metafields

Use AI to fill metafields based on product data:

```bash
python scripts/fill_category_metafields.py \
  --products exports/water_heaters.json \
  --category "Home & Garden > Household Appliances > Water Heaters" \
  --output exports/water_heaters_filled.json
```

#### Step 3: Create Excel Report

Generate Excel file for review:

```bash
python scripts/create_metafields_excel.py \
  --products exports/water_heaters_filled.json \
  --output exports/water_heaters_metafields.xlsx
```

#### Step 4: Review and Edit Excel

Open the Excel file (`exports/water_heaters_metafields.xlsx`) and review/edit:
- **Summary sheet** - Statistics and category information
- **Products sheet** - All products with metafields (editable)
- **Metafield Definitions sheet** - Field specifications

#### Step 5: Convert Excel Back to JSON

After editing, convert back to JSON:

```bash
python scripts/excel_to_json.py exports/water_heaters_metafields.xlsx
```

This creates `exports/water_heaters_metafields.json` with all your changes.

#### Step 6: Upload to Shopify (Optional)

**⚠️ Only when you're ready to upload:**

```bash
python scripts/upload_metafields.py \
  --products exports/water_heaters_metafields.json \
  --limit 10  # Test with 10 products first
```

---

## 📚 Scripts Reference

### Core Scripts

#### `fetch_products.py`
Fetches products from Shopify.

**Usage:**
```bash
python scripts/fetch_products.py --tag TAG_NAME --output OUTPUT_FILE.json
python scripts/fetch_products.py --collection COLLECTION_NAME --output OUTPUT_FILE.json
python scripts/fetch_products.py --all --output OUTPUT_FILE.json
```

**Options:**
- `--tag` - Fetch products by tag
- `--collection` - Fetch products by collection (handle, ID, or title)
- `--all` - Fetch all products
- `--output` - Output JSON file path
- `--format` - Output format: json, csv, or xlsx

#### `fetch_shopify_taxonomy.py`
Downloads Shopify's product taxonomy (one-time setup).

**Usage:**
```bash
python scripts/fetch_shopify_taxonomy.py
```

#### `fill_category_metafields.py`
Fills metafields using AI based on product data.

**Usage:**
```bash
python scripts/fill_category_metafields.py \
  --products PRODUCTS_FILE.json \
  --category "Category Path" \
  --output OUTPUT_FILE.json
```

**Options:**
- `--products` - Input products JSON file
- `--category` - Shopify category path (e.g., "Home & Garden > Household Appliances > Water Heaters")
- `--output` - Output JSON file path
- `--batch-size` - Number of products to process per batch (default: 10)

#### `create_metafields_excel.py`
Creates Excel report with products and metafields.

**Usage:**
```bash
python scripts/create_metafields_excel.py \
  --products PRODUCTS_FILE.json \
  --output OUTPUT_FILE.xlsx
```

**Options:**
- `--products` - Input products JSON file
- `--output` - Output Excel file path

#### `excel_to_json.py`
Converts Excel file to JSON format.

**Usage:**
```bash
python scripts/excel_to_json.py EXCEL_FILE.xlsx [OUTPUT_FILE.json]
```

**Options:**
- First argument: Excel file path
- Second argument (optional): Output JSON file path (default: same name as Excel file)

#### `json_to_excel.py`
Converts JSON file to Excel format.

**Usage:**
```bash
python scripts/json_to_excel.py JSON_FILE.json [OUTPUT_FILE.xlsx]
```

**Options:**
- First argument: JSON file path
- Second argument (optional): Output Excel file path (default: same name as JSON file)

#### `add_metafield_to_json.py`
Adds a new metafield column to all products in JSON file.

**Usage:**
```bash
python scripts/add_metafield_to_json.py JSON_FILE.json NAMESPACE KEY TYPE [DEFAULT_VALUE]
```

**Example:**
```bash
python scripts/add_metafield_to_json.py \
  exports/products.json \
  shopify \
  geyser_type \
  list.single_line_text_field \
  ""
```

**Common Metafield Types:**
- `single_line_text_field` - Text
- `number_integer` - Whole numbers
- `number_decimal` - Decimal numbers
- `list.single_line_text_field` - List/dropdown
- `boolean` - True/False

#### `upload_metafields.py`
Uploads metafields to Shopify products.

**Usage:**
```bash
python scripts/upload_metafields.py \
  --products PRODUCTS_FILE.json \
  --limit LIMIT
```

**Options:**
- `--products` - Products JSON file with metafields
- `--limit` - Number of products to upload (use small number for testing)

**⚠️ Warning:** This will upload data to Shopify. Test with `--limit 10` first!

#### `verify_metafields.py`
Verifies metafields on a Shopify product.

**Usage:**
```bash
python scripts/verify_metafields.py --product-id PRODUCT_ID
```

#### `delete_metafields.py`
Deletes metafields from Shopify products.

**Usage:**
```bash
python scripts/delete_metafields.py \
  --products PRODUCTS_FILE.json \
  --namespace NAMESPACE \
  --key KEY
```

### Utility Scripts

#### `load_shopify_handles.py`
Loads and processes Shopify product handles.

#### `generate_basic_metafields.py`
Generates basic metafield structures.

#### `fill_geyser_type.py`
Example script for filling a specific metafield based on product titles.

---

## 📊 Data Formats

### JSON Structure

Products JSON file structure:

```json
[
  {
    "id": "gid://shopify/Product/123456",
    "title": "Product Title",
    "handle": "product-handle",
    "vendor": "Vendor Name",
    "status": "ACTIVE",
    "category_metafields": {
      "power-source": "AC-powered",
      "capacity": "80",
      "geyser_type": "storage"
    }
  }
]
```

### Excel Structure

Excel files contain three sheets:

1. **Summary** - Category information and statistics
2. **Products** - Product data with metafield columns
3. **Metafield Definitions** - Field specifications

Metafield columns in Products sheet follow format:
```
Metafield: {namespace}.{key} [{type}]
```

Example:
```
Metafield: shopify.geyser_type [list.single_line_text_field]
```

---

## 💡 Examples

### Example 1: Water Heaters (كيزر)

```bash
# 1. Fetch products
python scripts/fetch_products.py --collection "كيزر" --output exports/geyser.json

# 2. Fill metafields
python scripts/fill_category_metafields.py \
  --products exports/geyser.json \
  --category "Home & Garden > Household Appliances > Water Heaters" \
  --output exports/geyser_filled.json

# 3. Create Excel report
python scripts/create_metafields_excel.py \
  --products exports/geyser_filled.json \
  --output exports/geyser_metafields.xlsx

# 4. After editing Excel, convert back to JSON
python scripts/excel_to_json.py exports/geyser_metafields.xlsx

# 5. Add custom metafield
python scripts/add_metafield_to_json.py \
  exports/geyser_metafields.json \
  shopify geyser_type list.single_line_text_field ""

# 6. Fill the new metafield (example)
python scripts/fill_geyser_type.py exports/geyser_metafields.json

# 7. Convert back to Excel
python scripts/json_to_excel.py exports/geyser_metafields.json
```

### Example 2: Adding a New Metafield

```bash
# Add warranty period metafield
python scripts/add_metafield_to_json.py \
  exports/products.json \
  shopify \
  warranty-period \
  single_line_text_field \
  ""

# Add weight metafield (number)
python scripts/add_metafield_to_json.py \
  exports/products.json \
  shopify \
  weight \
  number_decimal \
  "0"
```

---

## 🛠️ Project Structure

```
metaFields/
├── scripts/
│   ├── fetch_products.py              # Fetch products from Shopify
│   ├── fetch_shopify_taxonomy.py     # Download taxonomy (one-time)
│   ├── fill_category_metafields.py   # AI metafield filling
│   ├── create_metafields_excel.py    # Excel report generator
│   ├── excel_to_json.py              # Excel → JSON converter
│   ├── json_to_excel.py              # JSON → Excel converter
│   ├── add_metafield_to_json.py      # Add new metafields
│   ├── upload_metafields.py          # Upload to Shopify
│   ├── verify_metafields.py          # Verify uploads
│   ├── delete_metafields.py          # Delete metafields
│   ├── load_shopify_handles.py       # Handle utilities
│   ├── generate_basic_metafields.py   # Generate metafield structures
│   └── fill_geyser_type.py            # Example: Fill specific metafield
│
├── data/
│   ├── shopify_taxonomy_full.json    # Complete taxonomy (21K+ categories)
│   ├── shopify_attributes.yml        # Metafield definitions
│   └── shopify_values.yml            # Predefined values
│
├── exports/
│   └── [your export files here]
│
├── .env                               # Environment variables (create this)
├── requirements.txt                   # Python dependencies
└── README.md                          # This file
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. "Missing required environment variables"
**Solution:** Create `.env` file with required variables (see Configuration section).

#### 2. "File not found" errors with Arabic filenames
**Solution:** Use full paths or ensure proper encoding in terminal.

#### 3. Excel file has "Unnamed" columns
**Solution:** This is normal for report-style Excel files. The data is still correct.

#### 4. Metafield upload fails
**Solution:**
- Check API token permissions
- Verify metafield namespace and key format
- Test with `--limit 1` first
- Check Shopify API version compatibility

#### 5. AI filling returns incorrect values
**Solution:**
- Review product descriptions (more detail = better results)
- Manually edit in Excel after AI filling
- Adjust batch size if needed

### Getting Help

1. Check script help: `python scripts/SCRIPT_NAME.py --help`
2. Verify `.env` configuration
3. Check Shopify API status
4. Review error messages for specific issues

---

## 📝 Notes

- **Analysis Mode:** By default, scripts are in analysis mode and won't upload to Shopify
- **Excel Editing:** Always review Excel files before uploading
- **Backup:** Keep backups of JSON files before uploading
- **Testing:** Always test with `--limit 10` before full uploads
- **API Limits:** Shopify has rate limits; scripts include delays

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- Shopify Product Taxonomy: [GitHub Repository](https://github.com/Shopify/product-taxonomy)
- Uses OpenAI GPT models for AI-powered metafield filling

---

**Last Updated:** 2025


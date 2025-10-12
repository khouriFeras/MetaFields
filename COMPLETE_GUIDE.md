# 🚀 Complete Guide: Shopify Category Metafields System

## 📋 Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Installation & Setup](#installation--setup)
4. [Step-by-Step Usage](#step-by-step-usage)
5. [Understanding the Output](#understanding-the-output)
6. [Technical Details](#technical-details)
7. [Troubleshooting](#troubleshooting)
8. [Examples](#examples)

---

## Overview

### What This System Does

This system automatically fills **Shopify's standard category metafields** for your products using AI. Instead of manually creating custom metafields, it:

1. ✅ Uses **Shopify's official product taxonomy** (21,000+ categories)
2. ✅ Matches your products to the **correct Shopify category**
3. ✅ Gets **standard metafields** for that category
4. ✅ **Fills metafields automatically** using GPT-4o
5. ✅ Exports to **Excel for review** before uploading

### Why Use This System?

✅ **Shopify Standard** - Uses official taxonomy and metafields  
✅ **AI-Powered** - Intelligent category matching and data extraction  
✅ **100% Coverage** - Analyzes all products, not samples  
✅ **Proper Types** - Correct metafield types (list, text, etc.)  
✅ **Predefined Values** - Includes value lists for list fields  
✅ **Excel Reports** - Review before uploading to Shopify  

---

## How It Works

### The Complete Process

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: One-Time Setup                                      │
│ ↓ Fetch Shopify's Product Taxonomy from GitHub             │
│ ↓ Downloads 21,000+ categories with metafield definitions  │
│ ↓ Saves to: data/shopify_taxonomy_full.json                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Fetch Products                                      │
│ ↓ Gets products from Shopify by tag                        │
│ ↓ Example: tag "Televisions" → 201 TV products             │
│ ↓ Saves to: exports/tag_Televisions/products_*.json        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Match Tag to Shopify Category                       │
│ ↓ AI analyzes sample products                              │
│ ↓ Filters 8,486 categories to top 50 relevant ones         │
│ ↓ GPT-4o selects best match with confidence                │
│ ↓ Example: "Televisions" → "Electronics > Video > TVs"     │
│ ↓ Gets 14 metafields for this category                     │
│ ↓ Saves to: tag_Televisions_category_mapping.json          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Fill Metafields for ALL Products                    │
│ ↓ GPT-4o analyzes each product                             │
│ ↓ Extracts metafield values from title/description/variants│
│ ↓ Processes in batches of 10 (configurable)                │
│ ↓ Uses correct types (list vs text)                        │
│ ↓ Example: 201 TVs → 1,192 metafields filled               │
│ ↓ Saves to: products_with_metafields.json                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Create Excel Report                                 │
│ ↓ 3-sheet Excel file for review                            │
│ ↓ Sheet 1: Summary (statistics, coverage)                  │
│ ↓ Sheet 2: Products (all products with metafields)         │
│ ↓ Sheet 3: Metafield Definitions (field specs)             │
│ ↓ Saves to: Televisions_metafields_final.xlsx              │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    ✅ Review & Upload
```

### Data Sources

**Shopify's Open Source Taxonomy:**
- Source: [github.com/Shopify/product-taxonomy](https://github.com/Shopify/product-taxonomy)
- 21,396 total categories
- 8,486 categories with metafields
- 2,023 attributes with types and values
- Always up-to-date

**No API Required:**
- Downloads directly from GitHub
- No authentication needed
- No API version issues
- Fast and reliable

---

## Installation & Setup

### Prerequisites

- Python 3.8+
- Shopify store with Admin API access
- OpenAI API key (for GPT-4o)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `requests` - HTTP requests
- `openai` - OpenAI API
- `python-dotenv` - Environment variables
- `openpyxl` - Excel file creation

### Step 2: Configure Environment

Create `.env` file in project root:

```env
# Shopify Credentials
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_your_access_token

# OpenAI API
OPENAI_API_KEY=sk-your_openai_api_key

# Optional Settings
SHOPIFY_API_VERSION=2024-10
OUTPUT_DIR=exports
```

**Getting Your Credentials:**

1. **Shopify Admin Access Token:**
   - Go to: Shopify Admin → Settings → Apps and sales channels
   - Create a custom app with Admin API access
   - Permissions needed: `read_products`, `read_product_listings`

2. **OpenAI API Key:**
   - Go to: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Create new secret key
   - Ensure you have GPT-4o access

### Step 3: Fetch Shopify Taxonomy (One Time Only)

```bash
python scripts/fetch_shopify_taxonomy.py
```

**What this does:**
- Downloads Shopify's product taxonomy from GitHub
- Processes 21,396 categories
- Maps 2,023 attributes with proper types
- Saves to `data/shopify_taxonomy_full.json` (reusable!)

**Output:**
```
✅ Processed 21,396 total categories
✅ Found 19,296 leaf categories
✅ 8,486 categories have metafields
```

**This only needs to run ONCE!** The taxonomy file is reused for all future analyses.

---

## Step-by-Step Usage

### Quick Start (One Command)

```bash
python scripts/category_metafields_workflow.py --tag YOUR_TAG
```

This runs all 5 steps automatically!

### Example: Analyze Televisions

```bash
# Complete workflow
python scripts/category_metafields_workflow.py --tag Televisions
```

**What happens:**
1. Fetches products with tag "Televisions"
2. Matches to category "Electronics > Video > Televisions"
3. Gets 14 metafields for this category
4. Fills metafields for all 201 products
5. Creates Excel report

**Output location:**
```
exports/tag_Televisions/
├── products_tag_Televisions_with_lang.json
├── tag_Televisions_category_mapping.json
├── products_with_metafields.json
└── Televisions_metafields_final.xlsx ⭐
```

### Manual Steps (Advanced Control)

If you prefer to run each step individually:

#### Step 1: Fetch Products

```bash
python scripts/fetch_products.py tag --name Televisions
```

**Output:** `exports/tag_Televisions/products_tag_Televisions_with_lang.json`

#### Step 2: Match Category

```bash
python scripts/match_tag_to_category.py \
  --tag Televisions \
  --products exports/tag_Televisions/products_tag_Televisions_with_lang.json
```

**Output:** `exports/tag_Televisions/tag_Televisions_category_mapping.json`

**Shows:**
- Matched category: "Electronics > Video > Televisions"
- Confidence: High
- Reasoning: Why this category was chosen
- 14 metafields available

#### Step 3: Fill Metafields

```bash
python scripts/fill_category_metafields.py \
  --products exports/tag_Televisions/products_tag_Televisions_with_lang.json \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json \
  --output exports/tag_Televisions/products_with_metafields.json \
  --mode batch \
  --batch-size 10
```

**Options:**
- `--mode batch` - Process multiple products at once (faster)
- `--mode single` - Process one at a time (more accurate)
- `--batch-size 10` - Products per batch (default: 10)

**Output:** `exports/tag_Televisions/products_with_metafields.json`

#### Step 4: Create Excel

```bash
python scripts/create_metafields_excel.py \
  --products exports/tag_Televisions/products_with_metafields.json \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json \
  --output exports/tag_Televisions/Televisions_metafields_final.xlsx
```

**Output:** `exports/tag_Televisions/Televisions_metafields_final.xlsx`

---

## Understanding the Output

### Excel Report Structure

#### Sheet 1: Summary

**Category Information:**
- Tag analyzed
- Shopify category matched
- Confidence level (High/Medium/Low)
- AI reasoning for category choice

**Statistics:**
- Total products
- Products with metafields
- Coverage percentage
- Top vendors

**Metafield Coverage:**
- Each metafield's fill rate
- How many products have each field
- Coverage percentages

#### Sheet 2: Products

**Columns:**
- Product Title
- Product Type
- Vendor
- Price Range
- Status
- **All Metafield Values** (one column per metafield)

**Highlighting:**
- 🟡 Yellow cells = Empty metafields (AI couldn't extract value)
- ⚪ White cells = Filled metafields

#### Sheet 3: Metafield Definitions

**Information for Each Metafield:**
- Name (e.g., "Display Resolution")
- Key (e.g., "display-resolution")
- Namespace (always "standard" for Shopify fields)
- Type (e.g., "list.single_line_text_field")
- Description (what the field is for)

**Use this sheet when creating metafields in Shopify!**

### Metafield Types Explained

#### `single_line_text_field`
- Free text input
- No predefined values
- Example: "Television shape" - users can enter any shape

#### `list.single_line_text_field`
- Dropdown/select field
- Predefined values available
- Example: "Display resolution" - 4K, 8K, Full HD, etc.

**The system automatically determines the correct type!**

### Category Mapping File

Location: `exports/tag_XXX/tag_XXX_category_mapping.json`

**Contains:**
```json
{
  "tag": "Televisions",
  "category": {
    "id": "gid://shopify/TaxonomyCategory/el-17-4",
    "name": "Televisions",
    "fullName": "Electronics > Video > Televisions",
    "confidence": "high",
    "reasoning": "All products are televisions..."
  },
  "metafields": [
    {
      "name": "Display resolution",
      "key": "display-resolution",
      "type": "list.single_line_text_field",
      "values": ["4K", "8K", "Full HD", "HD", ...],
      "description": "Specifies the resolution..."
    },
    ...
  ]
}
```

---

## Technical Details

### Metafield Type Detection

The system infers metafield types from Shopify's attributes:

**Has Predefined Values?**
- YES → `list.single_line_text_field`
- NO → `single_line_text_field`

**Example:**

```json
// Display Resolution - HAS predefined values
{
  "type": "list.single_line_text_field",
  "values": ["4K", "8K", "Full HD", "HD", "720p", ...]
}

// Television Shape - NO predefined values
{
  "type": "single_line_text_field",
  "values": []
}
```

### Smart Category Filtering

To avoid OpenAI token limits, the system:

1. **Extracts keywords** from tag and product titles
2. **Scores categories** based on keyword matches
3. **Filters to top 50** most relevant categories
4. **Sends only relevant** categories to GPT-4o

**Example for "water-pump":**
- All categories: 8,486
- Filtered to: 36 relevant categories
- Matched to: "Centrifugal Pumps"

### Batch Processing

**Batch Mode** (default):
- Processes 10 products at once
- Faster for large collections
- Slightly lower accuracy
- Cost-effective

**Single Mode** (optional):
- Processes 1 product at a time
- Slower but more accurate
- Higher API costs
- Better for small collections

### Cost Estimation

**Per 100 Products:**
- Taxonomy fetch: ~$0.10 (one time only)
- Category match: ~$0.02
- Metafield filling (batch): ~$0.30
- **Total: ~$0.40-0.50** for first analysis
- **Then: ~$0.30** per additional tag (taxonomy reused)

**Cost Optimization:**
- Use batch mode (10 products/batch)
- Taxonomy only fetched once
- Reusable for unlimited tags

---

## Troubleshooting

### "Taxonomy file not found"

**Problem:** Haven't fetched Shopify taxonomy yet

**Solution:**
```bash
python scripts/fetch_shopify_taxonomy.py
```

### "Category confidence: LOW"

**Problem:** AI not confident about category match

**Check:**
1. Look at "Reasoning" in Excel Summary sheet
2. Products may be too diverse
3. Consider splitting into multiple tags

**Solution:**
- Ensure products with same tag are similar
- Check if product descriptions are detailed enough

### "Many empty metafields (yellow cells)"

**Problem:** AI can't extract values from product data

**Reasons:**
1. Product descriptions lack details
2. Information not in title/description/variants
3. Metafield doesn't apply to some products

**Solution:**
1. Add more details to product descriptions
2. Include specs in product titles
3. Some empty fields are normal (not all products have all features)

### "OpenAI API error: 429 (Rate Limit)"

**Problem:** Too many requests to OpenAI

**Solution:**
1. Wait a few minutes
2. Use `--batch-size 5` (smaller batches)
3. Use `--mode single` (slower but more reliable)

### "Token limit exceeded"

**Problem:** Too much data in one request

**Solution:**
- System automatically filters categories
- If still occurring, reduce batch size:
  ```bash
  --batch-size 5
  ```

---

## Examples

### Example 1: Electronics (Televisions)

```bash
python scripts/category_metafields_workflow.py --tag Televisions
```

**Results:**
- **Category:** Electronics > Video > Televisions
- **Products:** 201 TVs analyzed
- **Metafields:** 14 fields
  - Audio technology (list)
  - Display resolution (list)
  - Display technology (list)
  - Smart TV platform (list)
  - Connection type (list)
  - HDR format (list)
  - Color (list)
  - etc.
- **Filled:** 1,192 metafields (5.9 avg/product)

### Example 2: Hardware (Water Pumps)

```bash
python scripts/category_metafields_workflow.py --tag water-pump
```

**Results:**
- **Category:** Hardware > Hardware Pumps > Centrifugal Pumps
- **Products:** 182 pumps analyzed
- **Metafields:** 5 fields
  - Color (list)
  - Hardware material (list)
  - Power source (list)
  - Pattern (list)
  - Suitable for water feature type (list)
- **Filled:** ~900 metafields

### Example 3: Pet Products (Cat Food)

```bash
# Fetch products
python scripts/fetch_products.py tag --name cat-food

# Run workflow
python scripts/category_metafields_workflow.py --tag cat-food --skip-fetch
```

**Expected Category:** "Pet Supplies > Cat Supplies > Cat Food"

**Expected Metafields:**
- Life stage (kitten, adult, senior)
- Flavor
- Special diet (grain-free, hypoallergenic, etc.)
- Size/Weight
- etc.

---

## Quick Reference

### Commands Cheat Sheet

```bash
# One-time setup
python scripts/fetch_shopify_taxonomy.py

# Complete workflow (recommended)
python scripts/category_metafields_workflow.py --tag YOUR_TAG

# Skip fetching (use existing products)
python scripts/category_metafields_workflow.py --tag YOUR_TAG --skip-fetch

# Single product mode (more accurate)
python scripts/category_metafields_workflow.py --tag YOUR_TAG --mode single

# Custom batch size
python scripts/category_metafields_workflow.py --tag YOUR_TAG --batch-size 5
```

### File Locations

```
data/
└── shopify_taxonomy_full.json          # Taxonomy (reusable)

exports/
└── tag_YOUR_TAG/
    ├── products_tag_YOUR_TAG_with_lang.json
    ├── tag_YOUR_TAG_category_mapping.json
    ├── products_with_metafields.json
    └── YOUR_TAG_metafields_final.xlsx  # ⭐ REVIEW THIS
```

### Key Features

✅ **21,396 Shopify categories** available  
✅ **8,486 categories with metafields**  
✅ **2,023 attributes** with proper types  
✅ **Automatic type detection** (list vs text)  
✅ **Predefined value lists** included  
✅ **Smart category filtering** (avoids token limits)  
✅ **Batch processing** (configurable)  
✅ **Excel reports** (3 sheets)  
✅ **100% product coverage**  

---

## Success Checklist

Before considering the analysis complete, verify:

- [ ] Taxonomy fetched successfully (`data/shopify_taxonomy_full.json` exists)
- [ ] Products fetched from Shopify
- [ ] Category matched with "high" or "medium" confidence
- [ ] Metafield coverage > 70% (check Summary sheet)
- [ ] Excel file opens correctly
- [ ] Metafield values look accurate
- [ ] Empty fields make sense (product doesn't have that feature)
- [ ] Ready to create metafields in Shopify

---

## Next Steps After Analysis

1. **Review Excel File**
   - Check Summary sheet statistics
   - Verify metafield values in Products sheet
   - Note metafield definitions from sheet 3

2. **Create Metafields in Shopify**
   - Go to: Shopify Admin → Settings → Custom Data → Products
   - Create new metafield for each one
   - Use definitions from Excel sheet 3
   - Set namespace to "custom" (Shopify standard)

3. **Upload Data**
   - Export products with metafields from Excel
   - Use Shopify CSV import or API
   - Or manually add to products

4. **Verify**
   - Check products in Shopify admin
   - Ensure metafields display correctly
   - Test on storefront if using theme

---

## Support & Resources

**Documentation:**
- This file (COMPLETE_GUIDE.md)
- Shopify Taxonomy: [github.com/Shopify/product-taxonomy](https://github.com/Shopify/product-taxonomy)

**Common Issues:**
- See [Troubleshooting](#troubleshooting) section above

**System Status:**
- ✅ Fully operational
- ✅ Production-ready
- ✅ GitHub-based (no API issues)
- ✅ Proper types implemented

---

## Summary

This system provides **end-to-end automation** for filling Shopify category metafields:

1. **One command** runs complete workflow
2. **AI-powered** category matching and data extraction
3. **Proper types** (list vs text) automatically detected
4. **Excel reports** for easy review
5. **100% coverage** - all products analyzed

**Ready to use!** 🚀

Start with:
```bash
python scripts/fetch_shopify_taxonomy.py
python scripts/category_metafields_workflow.py --tag YOUR_TAG
```

Then review: `exports/tag_YOUR_TAG/YOUR_TAG_metafields_final.xlsx`


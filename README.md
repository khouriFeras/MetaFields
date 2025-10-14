# 🚀 Shopify Category Metafields System

**AI-Powered metafield filling using Shopify's standard product taxonomy**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## ✨ What This Does

Automatically fills **Shopify's standard category metafields** for your products using AI:

1. ✅ Matches products to **Shopify's official categories** (21,000+ available)
2. ✅ Gets **standard metafields** for each category (proper types included)
3. ✅ **AI fills metafields** by analyzing product data
4. ✅ Exports to **Excel for review** and manual editing
5. ✅ **Syncs Excel changes back to JSON**
6. ✅ **Uploads metafields to Shopify** with proper key mapping
7. ✅ **Creates metafield definitions** for storefront visibility and filters

---

## 🎯 Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

Create `.env` file:

```env
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_your_token
OPENAI_API_KEY=sk-your_openai_key
```

### 3. One-Time Setup

```bash
# Fetch Shopify's taxonomy (only once!)
python scripts/fetch_shopify_taxonomy.py
```

### 4. Analyze Products

```bash
# Complete workflow - one command!
python scripts/category_metafields_workflow.py --tag YOUR_TAG

# Example:
python scripts/category_metafields_workflow.py --tag Televisions
```

### 5. Review & Edit Results

Open: `exports/tag_YOUR_TAG/YOUR_TAG_metafields_final.xlsx`

**3 sheets:**

1. Summary - Statistics and category match
2. Products - All products with filled metafields (editable)
3. Metafield Definitions - Field specifications

**💡 Edit the Excel file to:**
- Remove unwanted metafields
- Fix incorrect values
- Add missing values

### 6. Sync Changes & Upload to Shopify

```bash
# Sync Excel changes back to JSON
python scripts/sync_excel_to_json.py \
  --excel exports/tag_YOUR_TAG/YOUR_TAG_metafields_final.xlsx \
  --json exports/tag_YOUR_TAG/products_with_metafields.json \
  --output exports/tag_YOUR_TAG/products_synced.json

# Upload metafields to Shopify (test with 10 products first)
python scripts/upload_metafields.py \
  --products exports/tag_YOUR_TAG/products_synced.json \
  --mapping exports/tag_YOUR_TAG/tag_YOUR_TAG_category_mapping.json \
  --limit 10

# Create metafield definitions (enables filters)
python scripts/create_metafield_definitions.py \
  --mapping exports/tag_YOUR_TAG/tag_YOUR_TAG_category_mapping.json

# Verify upload (check a product)
python scripts/verify_metafields.py --product-id PRODUCT_ID
```



---

github link of shopify texo
[Shopify/storefront-api-learning-kit](https://github.com/Shopify/storefront-api-learning-kit)

📊 Example Results

### Televisions (201 products)

**Category Matched:** `Electronics > Video > Televisions`
**Confidence:** High
**Metafields:** 14 fields with proper types
**Results:** 1,192 metafields filled (5.9 avg/product)

**Metafields:**

- Display resolution (list) - 26 options
- Display technology (list) - 31 options
- Smart TV platform (list) - 9 options
- Audio technology (list) - 15 options
- HDR format (list) - 7 options
- Connection type (list) - 39 options
- Color (list) - 19 options
- +7 more fields

### Water Pumps (182 products)

**Category Matched:** `Hardware > Hardware Pumps > Centrifugal Pumps`
**Confidence:** High
**Metafields:** 5 fields
**Results:** 900+ metafields filled

---

## 🔑 Key Features

✅ **21,396 Shopify categories** - Complete product taxonomy
✅ **8,486 categories with metafields** - Standard field definitions
✅ **Proper types** - `list.single_line_text_field` vs `single_line_text_field`
✅ **Predefined values** - Dropdown options for list fields
✅ **Smart matching** - AI-powered category selection
✅ **100% coverage** - Analyzes all products
✅ **Excel reports** - Easy review before upload
✅ **GitHub-based** - No API version issues

---

## 📖 Documentation

**👉 [READ THE COMPLETE GUIDE](COMPLETE_GUIDE.md)** 👈

The complete guide includes:

- Detailed step-by-step instructions
- How the system works
- Technical details
- Troubleshooting
- Examples for different product types

---

## 🛠️ System Architecture

```
GitHub Taxonomy
  ↓
Fetch & Process (one time)
  ↓
Match Products → Shopify Category
  ↓
Get Category Metafields
  ↓
AI Fills Values (GPT-4o-mini)
  ↓
Excel Report → Manual Review/Edit
  ↓
Sync Excel → JSON (key mapping)
  ↓
Upload to Shopify → Create Definitions → Enable Filters
```

**Data Source:** [Shopify&#39;s Product Taxonomy](https://github.com/Shopify/product-taxonomy) (Open Source)

---

## 📁 Project Structure

```
scripts/
├── category_metafields_workflow.py    # Complete workflow ⭐
├── fetch_category_products.py         # Gets products from Shopify
├── match_tag_to_category.py           # AI category matching
├── fill_category_metafields.py        # AI metafield filling (with key extraction fixes)
├── create_excel_from_json.py          # Excel report generator
├── sync_excel_to_json.py              # Sync Excel edits back to JSON
├── upload_metafields.py               # Upload to Shopify (with key mapping)
├── create_metafield_definitions.py    # Create definitions for filters
├── verify_metafields.py               # Verify uploads
└── remove_metafields.py               # Remove specific metafields

data/
└── shopify_taxonomy_full.json         # Cached taxonomy (21K+ categories)

exports/
└── tag_YOUR_TAG/
    ├── products_*.json
    ├── tag_*_category_mapping.json
    ├── products_with_metafields.json
    ├── products_synced.json           # After Excel sync
    └── *_metafields_final.xlsx        # Edit this! ⭐
```

---

## 💡 Use Cases

### Electronics

- TVs, Monitors, Cameras, Phones
- Standard tech specs extracted

### Hardware & Tools

- Pumps, Drills, Saws, Equipment
- Technical specifications filled

### Pet Products

- Food, Toys, Accessories
- Life stage, flavor, size extracted

### Fashion & Apparel

- Clothing, Shoes, Accessories
- Size, color, material filled

### Home & Garden

- Furniture, Decor, Appliances
- Dimensions, material, features

**Works for any product category in Shopify's taxonomy!**

---

## 🎯 Workflow Commands

```bash
# Complete workflow (recommended)
python scripts/category_metafields_workflow.py --tag YOUR_TAG

# Skip fetching (use existing products)
python scripts/category_metafields_workflow.py --tag YOUR_TAG --skip-fetch

# Single product mode (more accurate)
python scripts/category_metafields_workflow.py --tag YOUR_TAG --mode single

# Custom batch size
python scripts/category_metafields_workflow.py --tag YOUR_TAG --batch-size 5
```

---

## 📊 Statistics

- **Categories:** 21,396 total
- **Leaf categories:** 19,296 (most specific)
- **Categories with metafields:** 8,486
- **Attributes:** 2,023 with proper types
- **Success rate:** 100% (all products processed)
- **Average coverage:** 70-90% metafields filled

---

## 💰 Cost Estimate (Optimized)

**Per 200 Products (Using gpt-4o-mini - Default):**

- Taxonomy fetch: $0 (downloads from GitHub)
- Category match: $0.003
- Metafield filling: $0.08
- **Total: ~$0.08** per tag

**Per 200 Products (Using gpt-5-nano - Recommended for max savings):**

- Taxonomy fetch: $0 (downloads from GitHub)
- Category match: $0.001
- Metafield filling: $0.03
- **Total: ~$0.03** per tag 🔥

**Cost Optimizations Applied:**

- ✅ Default model: gpt-4o-mini (85% cheaper than gpt-4o)
- ✅ Batch size: 20 (50% fewer API calls)
- ✅ Description length: 300 chars (token optimization)
- ✅ Variants: 2 per product (token optimization)

**Use gpt-5-nano for maximum savings: `--model gpt-5-nano`**

---

## ⚠️ Important Notes

- **Review Required** - Always check and edit Excel before uploading to Shopify
- **OpenAI API** - Uses GPT-4o-mini by default (cost-effective)
- **GitHub-Based** - No Shopify API version dependencies
- **Storefront Filters** - Metafield definitions enable collection page filters
- **Key Mapping** - Automatically handles Excel format to Shopify format conversion
- **Custom Metafields** - Supports adding custom metafields (e.g., Screen size for TVs)

---

## 🔧 Requirements

**Python Packages:**

```
requests>=2.32.0
openai>=1.0.0
python-dotenv>=1.0.0
openpyxl>=3.1.0
pandas>=2.0.0
```

**APIs:**

- Shopify Admin API (read products)
- OpenAI API (GPT-4o)

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file

---

## 🙏 Credits

- **Shopify Product Taxonomy:** [github.com/Shopify/product-taxonomy](https://github.com/Shopify/product-taxonomy)
- **OpenAI GPT-4o:** Category matching and data extraction

---

## 🚀 Get Started

1. **Read:** [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)
2. **Setup:** Install dependencies and configure `.env`
3. **Fetch taxonomy:** `python scripts/fetch_shopify_taxonomy.py`
4. **Analyze:** `python scripts/category_metafields_workflow.py --tag YOUR_TAG`
5. **Review & Edit:** Open and edit Excel file in `exports/tag_YOUR_TAG/`
6. **Sync:** `python scripts/sync_excel_to_json.py ...`
7. **Upload:** `python scripts/upload_metafields.py ...` (test with `--limit 10` first)
8. **Enable filters:** `python scripts/create_metafield_definitions.py ...`
9. **Verify:** `python scripts/verify_metafields.py --product-id ID`

---

**Questions?** Check the [Complete Guide](COMPLETE_GUIDE.md) for detailed documentation!

**Ready to fill your metafields!** 🎉

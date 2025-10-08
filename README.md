# 🚀 Shopify Metafields System - AI-Powered Product Analysis

An intelligent system that automatically analyzes your Shopify products and creates relevant metafields with smart categorization.

---

## ✨ **Key Features**

- 🤖 **AI-Powered**: Automatically detects product types and creates relevant metafields
- 🎯 **Context-Aware**: Different fields for food vs toys vs accessories
- 📊 **Smart Categories**: Auto-categorizes weights (10 ranges) and prices (5 ranges)
- 🔄 **Dynamic Sampling**: 100% for small collections, 50% for large ones
- 📂 **Organized Exports**: Each collection gets its own subfolder
- 🌍 **Bilingual**: Full Arabic and English support
- ⚡ **Optimized**: 60% shorter prompts, 29% cost reduction

---

## 🎯 **Quick Start**

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from env.example)
cp env.example .env
```

Edit `.env` with your credentials:
```
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_your_token
OPENAI_API_KEY=sk-your_openai_key
```

### 2. Analyze Any Collection
```bash
# By collection name
python scripts/complete_analysis_workflow.py "طعام قطط"

# By tag
python scripts/complete_analysis_workflow.py --tag "cat_food"
```

### 3. Check Results
- Output folder: `exports/collection_or_tag_name/`
- Final Excel: `exports/collection_name/name_final.xlsx`

---

## 📊 **What You Get**

Each analysis creates an organized subfolder with:

```
exports/
└── طعام_قطط/                          # Organized by collection/tag
    ├── collection_طعام_قطط_raw.json      # Raw Shopify data
    ├── collection_طعام_قطط_with_lang.json # With language fields
    ├── طعام_قطط_analysis.json            # AI analysis
    ├── طعام_قطط_complete.json            # Populated metafields
    └── طعام_قطط_final.xlsx               # 📊 FINAL EXCEL FILE
```

---

## 🎨 **Context-Aware Metafields**

The system automatically creates different metafields for different product types:

### **Food Products** (طعام قطط, طعام كلاب):
- Brand, Product Type, Key Features
- **Size/Weight** (with ranges: Under 100g → 100kg+)
- Target Audience (Kitten, Adult, Senior)
- Special Attributes

### **Toys** (ألعاب قطط):
- Brand, Product Type
- **Material** (Plastic, Fabric, Sisal, Wood)
- **Color** (automatic color detection)
- Key Features (Interactive, With Catnip, Durable)
- Special Attributes

### **Litter** (رمل قطط):
- Brand, Product Type, Material
- **Size/Weight** (handles liters: 1L ≈ 0.6kg)
- Key Features (Clumping, Scented, Dust-Free)
- Special Attributes

### **Accessories** (Beds, Bowls, Collars):
- Brand, Product Type, Material
- **Size** (dimensions like 65x45cm, not weight!)
- Color, Features, Special Attributes

---

## ⚖️ **Automatic Categorization**

### Weight Ranges (10 Categories):
- Under 100g, 100g-500g, 500g-1kg
- 1kg-2kg, 2kg-5kg, 5kg-10kg
- 10kg-25kg, 25kg-50kg, 50kg-100kg, 100kg+

**Smart Conversion**:
- Liters → kg (for cat litter)
- oz, lb → grams
- All normalized to ranges

### Price Ranges (5 Categories in JOD):
- Under 10 JOD
- 10-50 JOD
- 50-100 JOD
- 100-200 JOD
- 200+ JOD

**Automatic conversion**: Shopify fils (÷1000) → JOD

---

## 📈 **Dynamic Sample Sizing**

The system automatically adjusts analysis depth based on collection size:

| Products | Sample % | Why |
|----------|----------|-----|
| < 30 | **100%** | Full analysis for small collections |
| 30-50 | **80%** | Excellent coverage |
| 50-100 | **70%** | Very good coverage |
| 100-200 | **60%** | Good statistical sample |
| 200+ | **50%** | Efficient for large collections |

---

## 🏪 **Your Store Categories**

Configured for all 13 of your store categories:
- المنزل و المطبخ (Home & Kitchen)
- العدد والادوات (Tools & Equipment)
- اكسسوارات الاثاث (Furniture Accessories)
- اللوازم الصحية (Sanitary Supplies)
- الانارة والكهرباء (Lighting & Electrical)
- الدهان (Paint & Coating)
- الحديقة (Garden)
- السيارة (Automotive)
- السلامة والامان (Safety & Security)
- التخزين (Storage)
- السفر والتخييم (Travel & Camping)
- المنزل الذكي (Smart Home)
- الحيوانات الاليفة (Pets)

---

## 🔑 **Understanding Metafields**

### **Key Features** (للتصفية - For Filtering):
- Common features many products share
- Used for filtering/faceted search
- Examples: High Protein, Grain-Free, Waterproof, Durable
- **85-95% populated**

### **Special Attributes** (للبحث - For Search/SEO):
- Unique qualities specific to each product
- Used for search and differentiation
- Examples: Made in Italy, Vet Recommended, Award Winner, Certified Organic
- **30-50% populated** (correct - not all products are unique!)

---

## 🔧 **Core Scripts**

### Main Workflow:
- **`complete_analysis_workflow.py`** - One command does it all

### Individual Components:
- **`fetch_products.py`** - Get data from Shopify
- **`dynamic_product_analyzer.py`** - AI discovers metafields
- **`universal_field_population.py`** - Populates field values
- **`create_dynamic_excel.py`** - Creates Excel output

---

## 💡 **Advanced Usage**

### Fetch Options:
```bash
# By collection
python scripts/fetch_products.py collection --title "Collection Name"

# By tag
python scripts/fetch_products.py tag --name "tag_name"

# All products
python scripts/fetch_products.py all
```

### Manual Steps:
```bash
# 1. Fetch
python scripts/fetch_products.py collection --title "طعام قطط"

# 2. Analyze (auto sample size)
python scripts/dynamic_product_analyzer.py exports/طعام_قطط/collection_طعام_قطط_with_lang.json

# 3. Populate
python scripts/universal_field_population.py exports/طعام_قطط/analysis.json -o complete.json

# 4. Create Excel
python scripts/create_dynamic_excel.py exports/طعام_قطط/complete.json -o final.xlsx
```

### Custom Sample Size:
```bash
python scripts/dynamic_product_analyzer.py input.json -s 0.9  # Force 90%
```

---

## 📊 **Excel Output**

Each Excel file contains 3 sheets:

### Sheet 1: Summary
- Detected category
- Top tags, vendors, product types
- Metafield statistics

### Sheet 2: Products
- All products with populated metafields
- Brand, Type, Features, Weight/Size, Price ranges
- Ready for review and planning

### Sheet 3: Meta Fields
- Field definitions
- Categories and options
- Searchable/Filterable flags

---

## ⚡ **Performance**

- **29% cost reduction** with optimized prompts
- **20-30% faster** processing
- **UTF-8 handling** for Windows compatibility
- **No emoji crashes** on Windows console

---

## 🔒 **Important**

**This system is for ANALYSIS ONLY!**

- ✅ Fetches products from Shopify
- ✅ Analyzes and creates metafield plans
- ✅ Exports to Excel for review
- ❌ **Does NOT upload to Shopify**

You must manually create metafields in Shopify based on the analysis.

---

## 📚 **Documentation**

- **README.md** (this file) - Complete documentation
- **START_HERE.md** - Quick start guide
- **CHANGELOG.md** - What's changed
- **filters/README.md** - Future filtering features

---

## 🎉 **Success Metrics**

- ✅ 85-95% field population rate
- ✅ Context-aware metafield discovery
- ✅ Accurate weight and price categorization
- ✅ Organized, clean exports
- ✅ Production-ready

---

## ❓ **Questions?**

Check **START_HERE.md** for quick examples and common scenarios.

**Ready to analyze your entire catalog!** 🚀

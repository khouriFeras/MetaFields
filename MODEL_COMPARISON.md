# 🤖 Model Comparison & Selection Guide

## Available Models (October 2025)

### GPT-5 Models (Latest)

| Model | Input Cost | Output Cost | Best For |
|-------|-----------|-------------|----------|
| **gpt-5-mini** | TBD | TBD | Standard tasks, low cost |
| **gpt-5-nano** | $0.05/1M | $0.40/1M | Maximum cost savings |
| **gpt-5** | TBD | TBD | Complex reasoning |

### GPT-4o Models (Proven)

| Model | Input Cost | Output Cost | Best For |
|-------|-----------|-------------|----------|
| **gpt-4o-mini** | $0.15/1M | $0.60/1M | Good balance |
| **gpt-4o** | $2.50/1M | $10/1M | Maximum accuracy |

---

## 💰 Cost Estimates (200 Products)

| Model | Category Match | Metafield Fill | Total Cost |
|-------|----------------|----------------|------------|
| **gpt-5-nano** | $0.001 | ~$0.03 | **$0.03** ⭐ |
| **gpt-5-mini** | TBD | TBD | **TBD** |
| **gpt-4o-mini** | $0.003 | ~$0.08 | **$0.08** |
| **gpt-4o** | $0.05 | ~$0.50 | **$0.52** |

**Savings: gpt-5-nano is 17x cheaper than gpt-4o!**

---

## 📊 Model Selection Guide

### For This Metafield System:

#### ✅ **Recommended: gpt-5-nano** or **gpt-5-mini**
- **Why:** Structured extraction task
- **Tasks:** Category matching, metafield extraction
- **Input:** Product titles, descriptions, specs
- **Output:** Simple JSON with field values
- **Complexity:** Low-Medium (perfect for nano/mini)

#### ⚠️ **Only Use gpt-4o if:**
- Very complex products (custom/handmade)
- Unusual categories
- Need maximum accuracy
- Cost is not a concern

---

## 🚀 How to Use Each Model

### GPT-5 Nano (Recommended)

```bash
python scripts/category_metafields_workflow.py \
  --tag YOUR_TAG \
  --model gpt-5-nano \
  --batch-size 25

# Cost: ~$0.03 per 200 products
# Speed: Ultra-fast
# Quality: Excellent for structured tasks
```

### GPT-5 Mini (If Available)

```bash
python scripts/category_metafields_workflow.py \
  --tag YOUR_TAG \
  --model gpt-5-mini

# Check OpenAI pricing page for exact costs
```

### GPT-4o-mini (Fallback)

```bash
python scripts/category_metafields_workflow.py \
  --tag YOUR_TAG \
  --model gpt-4o-mini \
  --batch-size 20

# Cost: ~$0.04 per 200 products
# Proven to work well
```

### GPT-4o (Maximum Accuracy)

```bash
python scripts/category_metafields_workflow.py \
  --tag YOUR_TAG \
  --model gpt-4o \
  --batch-size 10

# Cost: ~$0.52 per 200 products
# Use for complex products only
```

---

## 💡 Best Practices

### Start with Cheapest Model

1. **Test with gpt-5-nano** first
2. **Check quality** in Excel output
3. **If good** → use for all tags
4. **If not** → try gpt-5-mini or gpt-4o-mini

### Optimize Batch Size

| Model | Recommended Batch Size | Why |
|-------|----------------------|-----|
| gpt-5-nano | 25-30 | Can handle more |
| gpt-5-mini | 20-25 | Good balance |
| gpt-4o-mini | 15-20 | Safe size |
| gpt-4o | 10 | Conservative |

### When to Upgrade Models

**Use gpt-5-nano/mini for:**
- ✅ Electronics (TVs, phones, cameras)
- ✅ Hardware (pumps, tools, equipment)
- ✅ Pet products (food, toys, accessories)
- ✅ Fashion (clothing, shoes, accessories)
- ✅ Home & Garden (furniture, appliances)

**Upgrade to gpt-4o if:**
- ❌ Low accuracy (<70% fields filled)
- ❌ Many incorrect values
- ❌ Complex/unusual products
- ❌ Custom/handmade items

---

## 🧪 Testing Protocol

### Step 1: Test with Small Sample

```bash
# Test with 20 products first
python scripts/fetch_products.py --output-dir exports tag --name YOUR_TAG
# Manually limit to 20 in JSON file

python scripts/category_metafields_workflow.py \
  --tag YOUR_TAG \
  --model gpt-5-nano \
  --skip-fetch
```

### Step 2: Review Quality

- Open Excel file
- Check filled metafields percentage
- Verify value accuracy
- Look at empty fields (yellow)

### Step 3: Choose Model

- **>80% accuracy** → Use gpt-5-nano for all
- **70-80% accuracy** → Try gpt-5-mini
- **<70% accuracy** → Use gpt-4o-mini or gpt-4o

---

## 📈 Cost Projections

### Your Store (Example Calculations)

**Assume:**
- 50 tags to process
- Average 150 products per tag
- 7,500 total products

| Model | Cost per Tag | Total (50 tags) | Savings |
|-------|-------------|-----------------|---------|
| gpt-4o | $0.40 | $20 | Baseline |
| gpt-4o-mini | $0.06 | $3 | 85% |
| **gpt-5-nano** | **$0.02** | **$1** | **95%** 🔥 |

**Savings: $19 with gpt-5-nano!**

---

## 🎯 My Recommendation

### **Use gpt-5-nano (or gpt-5-mini if it exists):**

**Pros:**
- ✅ 95% cost reduction
- ✅ Same API (easy switch)
- ✅ Fast responses
- ✅ Good for structured extraction

**Implementation:**

```bash
# Default command (I'll make this the default)
python scripts/category_metafields_workflow.py --tag YOUR_TAG

# Will use gpt-5-nano automatically
# Can override with --model gpt-4o if needed
```

---

## 🔧 System Update

Want me to:

1. ✅ Set **gpt-5-nano as default** (or gpt-5-mini if you confirm it exists)
2. ✅ Add **--model** flag for easy switching
3. ✅ Add **cost estimation** before running
4. ✅ Update **batch size to 25** (optimal for nano)
5. ✅ Add this **MODEL_COMPARISON.md** guide

**This will give you 95% cost savings immediately!**

---

**Can you confirm which GPT-5 models you see on OpenAI's pricing page?**
- gpt-5-mini?
- gpt-5-nano?
- gpt-5?

Then I'll update the system to use the best one! 🚀



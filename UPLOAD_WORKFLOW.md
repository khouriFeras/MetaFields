# 📤 Complete Upload Workflow

**Step-by-step guide for uploading metafields to Shopify**

---

## ✅ Prerequisites

1. Virtual environment activated: `venv\Scripts\activate`
2. `.env` file configured with API credentials
3. Completed analysis phase (Excel file generated)

---

## 🔄 Workflow Steps

### **Step 1: Review & Edit Excel File**

Open the Excel file:
```
exports/tag_YOUR_TAG/YOUR_TAG_metafields_final.xlsx
```

**Edit as needed:**
- ✏️ Fix incorrect values
- 🗑️ Delete unwanted metafields (delete columns)
- ✅ Verify all values are correct

**💡 Tip:** The AI may occasionally extract incorrect values. Always review!

---

### **Step 2: Sync Excel Changes to JSON**

```bash
python scripts/sync_excel_to_json.py \
  --excel exports/tag_Televisions/Televisions_metafields_final.xlsx \
  --json exports/tag_Televisions/products_with_metafields.json \
  --output exports/tag_Televisions/products_synced.json
```

**What this does:**
- Reads your edited Excel file
- Matches products by Title
- Updates the JSON file with your changes
- Outputs: `products_synced.json`

---

### **Step 3: Test Upload (10 Products)**

```bash
python scripts/upload_metafields.py \
  --products exports/tag_Televisions/products_synced.json \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json \
  --limit 10
```

**What this does:**
- Uploads metafields for first 10 products
- Converts Excel keys (e.g., "Audio technology") to Shopify keys (e.g., "audio-technology")
- Creates metafield definitions automatically if they don't exist

**✅ Success indicators:**
- `✅ Successfully uploaded X metafields`
- No errors in output

---

### **Step 4: Verify Upload**

```bash
python scripts/verify_metafields.py --product-id 8545469759700
```

**Check in Shopify Admin:**
1. Go to **Products** → Find the product
2. Scroll to **Metafields** section
3. Verify values are correct and not empty

---

### **Step 5: Upload All Products**

Once verified, upload all products:

```bash
python scripts/upload_metafields.py \
  --products exports/tag_Televisions/products_synced.json \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json
```

**⏱️ This may take a while for many products (rate limiting)**

---

### **Step 6: Create Metafield Definitions**

Enable storefront visibility for filters:

```bash
python scripts/create_metafield_definitions.py \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json
```

**What this does:**
- Creates metafield definitions with `visibleToStorefrontApi: true`
- Enables metafields to be used as collection filters
- Skips definitions that already exist

---

### **Step 7: Enable Filters in Theme (Manual)**

**⚠️ This step must be done manually in Shopify Admin:**

1. Go to **Online Store** → **Themes**
2. Click **Customize** on your active theme
3. Navigate to **Collection pages**
4. Look for **Product filters** or **Filtering** section
5. **Enable** the metafield filters you want to show:
   - Audio technology
   - Display resolution
   - Screen size
   - HDR format
   - etc.
6. **Save** theme changes

---

## 🎯 Real Example: Televisions

```bash
# Step 2: Sync Excel to JSON
python scripts/sync_excel_to_json.py \
  --excel exports/tag_Televisions/Televisions_metafields_final_201_products.xlsx \
  --json exports/tag_Televisions/products_with_metafields.json \
  --output exports/tag_Televisions/products_synced.json

# Step 3: Test with 10 products
python scripts/upload_metafields.py \
  --products exports/tag_Televisions/products_synced.json \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json \
  --limit 10

# Step 4: Verify one product
python scripts/verify_metafields.py --product-id 8545469759700

# Step 5: Upload all 201 products
python scripts/upload_metafields.py \
  --products exports/tag_Televisions/products_synced.json \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json

# Step 6: Create definitions
python scripts/create_metafield_definitions.py \
  --mapping exports/tag_Televisions/tag_Televisions_category_mapping.json

# Step 7: Enable filters in theme (manual step)
```

---

## 🔧 Troubleshooting

### **Problem: Metafields are empty in Shopify Admin**

**Cause:** Metafield definitions don't exist yet

**Solution:**
```bash
python scripts/create_metafield_definitions.py \
  --mapping exports/tag_YOUR_TAG/tag_YOUR_TAG_category_mapping.json
```

### **Problem: Keys are incorrect (spaces instead of hyphens)**

**Cause:** Using old JSON file without key mapping

**Solution:** The upload script now automatically handles key mapping. Make sure you're using the latest `upload_metafields.py` (has `key_mapping` logic).

### **Problem: Filters don't appear on collection page**

**Cause:** Filters not enabled in theme

**Solution:** Follow Step 7 (manual theme customization)

---

## 📋 Utility Scripts

### **Remove Specific Metafields**

```bash
python scripts/remove_metafields.py \
  --json products_with_metafields.json \
  --output products_cleaned.json \
  --keys "Color" "Energy efficiency" "Contrast ratio"
```

### **Verify Product Metafields**

```bash
python scripts/verify_metafields.py --product-id 8545469759700
```

---

## ✅ Final Checklist

- [ ] Excel file reviewed and edited
- [ ] Synced Excel to JSON
- [ ] Tested with 10 products
- [ ] Verified upload in Shopify Admin
- [ ] Uploaded all products
- [ ] Created metafield definitions
- [ ] Enabled filters in theme
- [ ] Tested filters on collection page

---

## 💡 Pro Tips

1. **Always test with 10 products first** (`--limit 10`)
2. **Verify in Shopify Admin** before uploading all products
3. **Edit Excel file** to remove unwanted metafields before upload
4. **Use verify_metafields.py** to check individual products
5. **Custom metafields** (like Screen size) need to be added to category mapping first

---

**🎉 You're done! Your metafields are now live and filterable on Shopify!**


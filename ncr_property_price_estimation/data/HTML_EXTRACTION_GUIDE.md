# How to Get HTML for Selector Optimization

## 📋 **Step-by-Step Guide**

### **Method 1: Full Page HTML (Recommended)**

1. **Open 99acres in Chrome**
   - Go to: https://www.99acres.com/property-in-gurgaon-ffid?page=1
   - Let the page fully load (wait for all listings to appear)

2. **Open Developer Tools**
   - Press `F12` OR
   - Right-click anywhere → "Inspect"

3. **Get Full HTML**
   - In DevTools, click the "Elements" tab
   - Find the `<html>` tag at the very top
   - Right-click on `<html>` → **Copy** → **Copy outerHTML**

4. **Save to File**
   - Create a new file: `gurgaon_page1.html`
   - Paste the copied HTML
   - Save in project root

5. **Share with me**
   - You can either:
     - Paste the HTML here (if not too large)
     - Save to file and I'll read it
     - Share first 500 lines if it's huge

---

### **Method 2: Single Property Card HTML (Faster)**

If the full page is too large, just get one property card:

1. **Open 99acres page**
   - https://www.99acres.com/property-in-gurgaon-ffid?page=1

2. **Inspect a Property Card**
   - Right-click on any property listing
   - Click "Inspect"
   - DevTools will highlight the card's HTML

3. **Find the Card Container**
   - Look for a `<div>` with class containing "tuple" or "card"
   - It should contain: title, price, location, etc.

4. **Copy Card HTML**
   - Right-click on that `<div>` → **Copy** → **Copy outerHTML**

5. **Save to File**
   - Create: `single_property_card.html`
   - Paste and save

---

### **Method 3: Screenshot + Network Tab (Alternative)**

If HTML is too messy:

1. **Take Screenshot**
   - Open 99acres page
   - Take screenshot of a property listing
   - Show me what data you want extracted

2. **Check Network Tab**
   - Open DevTools → "Network" tab
   - Reload page
   - Look for API calls (XHR/Fetch)
   - If 99acres loads data via API, we can use that instead!

---

## 🎯 **What I'll Do With the HTML**

Once you provide the HTML, I will:

1. ✅ **Identify correct CSS selectors** for:
   - Property title
   - Price
   - Location/Society name
   - Area (sq ft)
   - Bedrooms, bathrooms
   - Amenities
   - All other fields

2. ✅ **Update extraction logic** in `ingestion.py`

3. ✅ **Test selectors** to ensure 100% data capture

4. ✅ **Optimize performance** (faster extraction)

---

## 📝 **Quick Test**

To verify you got the right HTML:

1. Open the saved HTML file in a text editor
2. Search for a property title you see on the page
3. If found → ✅ You got the right HTML!
4. If not found → ❌ Try again, might be incomplete

---

## 🚀 **What to Do Now**

**Option A: Get Full Page HTML**
```
1. Open: https://www.99acres.com/property-in-gurgaon-ffid?page=1
2. F12 → Elements tab
3. Right-click <html> → Copy outerHTML
4. Save to: gurgaon_page1.html
5. Share with me
```

**Option B: Get Single Card HTML**
```
1. Open same page
2. Right-click on a property listing → Inspect
3. Find the card's <div> container
4. Right-click → Copy outerHTML
5. Paste here or save to file
```

**Option C: Just Describe What You See**
```
Tell me:
- What fields are visible for each property?
- What's missing in current extraction?
- Any specific data you want captured?
```

---

## 💡 **Pro Tip**

If you're comfortable with browser DevTools, you can also:

1. Open Console tab (F12 → Console)
2. Run this to get all property cards:
   ```javascript
   document.querySelectorAll('div[class*="tuple"]').length
   ```
3. This tells us how many cards are on the page
4. Then we can test selectors live!

---

**Ready when you are!** Just paste the HTML or let me know which method you prefer. 🎯

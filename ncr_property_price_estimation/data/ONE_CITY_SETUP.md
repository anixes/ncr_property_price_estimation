# One-City-at-a-Time Setup - Complete! ✅

## 🎯 **What's Been Configured**

### **1. Config Updated for Single-City Scraping**

**Location:** `ncr_property_price_estimation/data/config.yaml`

**Changes:**
```yaml
cities:
  # ✅ COMPLETED: Noida (686 listings)
  # - name: "Noida"  ← Commented out
  
  # 🔄 CURRENTLY ACTIVE:
  - name: "Gurgaon"  ← Only this one active
  
  # All others commented out:
  # - Greater Noida
  # - Ghaziabad
  # - Faridabad
  # - New Delhi
  # - Bhiwadi
```

**More Conservative Delays:**
```yaml
scraper:
  coffee_break_interval: 10   # Break every 10 pages (was 20)
  coffee_break_duration: 120  # 2-minute breaks (was 60 seconds)
```

---

## 📋 **How to Use**

### **To Scrape Gurgaon (Current):**

```bash
cd ncr_property_price_estimation/data
python ingestion.py
```

**What will happen:**
1. Loads checkpoint (skips Noida - already done)
2. Scrapes ONLY Gurgaon
3. Takes 2-minute break every 10 pages
4. Pauses if CAPTCHA appears
5. Saves to same CSV file
6. Stops when Gurgaon is complete

---

### **To Scrape Next City:**

1. **Open `config.yaml`**

2. **Comment out current city:**
   ```yaml
   # - name: "Gurgaon"  ← Add # to comment
   #   url: "..."
   #   target_count: 8000
   ```

3. **Uncomment next city:**
   ```yaml
   - name: "Greater Noida"  ← Remove # to activate
     url: "https://www.99acres.com/property-in-greater-noida-ffid?page={}"
     target_count: 8000
   ```

4. **Run scraper:**
   ```bash
   python ingestion.py
   ```

---

## 📊 **Scraping Schedule (Recommended)**

To minimize CAPTCHA, scrape **one city per day**:

| Day | City          | Expected Listings | Status |
|-----|---------------|-------------------|--------|
| ✅ 1 | Noida         | 686               | Done   |
| 🔄 2 | Gurgaon       | ~8,000            | Ready  |
| 3   | Greater Noida | ~8,000            | Pending|
| 4   | Ghaziabad     | ~8,000            | Pending|
| 5   | Faridabad     | ~8,000            | Pending|
| 6   | New Delhi     | ~8,000            | Pending|
| 7   | Bhiwadi       | ~8,000            | Pending|

**Total:** ~56,000 listings in 7 days

---

## ⏰ **Best Time to Run**

**Recommended:** 2 AM - 6 AM IST (off-peak hours)

**Why:**
- Less traffic on 99acres
- Less strict bot detection
- Fewer CAPTCHAs

**How to schedule (Windows):**
```powershell
# Create a scheduled task to run at 2 AM
$action = New-ScheduledTaskAction -Execute "python" -Argument "ingestion.py" -WorkingDirectory "d:\DATA SCIENCE\ncr_property_price_estimation\ncr_property_price_estimation\data"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "99acres_Scraper" -Description "Scrape one city per night"
```

---

## 🎯 **Expected Performance**

### Per City (with new settings):

- **Pages to scrape:** ~300 pages (for 8,000 listings)
- **Time per page:** ~10-15 seconds (with delays)
- **Break every 10 pages:** 2 minutes
- **Total breaks:** ~30 breaks × 2 min = 60 minutes
- **Scraping time:** 300 pages × 12 sec = 60 minutes
- **CAPTCHA interventions:** 2-3 times (manual solving)

**Total time per city:** ~2-3 hours

---

## 🛡️ **CAPTCHA Handling**

When CAPTCHA appears:

```
======================================================================
CAPTCHA DETECTED - Manual Intervention Required
======================================================================
99acres has detected suspicious activity.

ACTION REQUIRED:
1. Go to the Chrome window that's open
2. Solve the CAPTCHA manually
3. Wait for the page to load normally
4. Come back here and press Enter to continue

OR press 'q' + Enter to quit and resume later
======================================================================
```

**What to do:**
1. Switch to Chrome window
2. Solve CAPTCHA
3. Return to terminal
4. Press **Enter**
5. Scraper continues automatically

---

## 📁 **Data Accumulation**

All cities save to the **same CSV file:**
```
data/raw/99acres_NCR_ML_Final.csv
```

**Current:**
- Noida: 686 listings

**After Gurgaon:**
- Noida: 686 listings
- Gurgaon: ~8,000 listings
- **Total:** ~8,686 listings

**After all cities:**
- **Total:** ~56,000 listings

---

## ✅ **Checklist for Each City**

Before starting each city:

- [ ] Update `config.yaml` (comment/uncomment cities)
- [ ] Check cookies are fresh (re-export if needed)
- [ ] Clear old checkpoint if starting fresh city
- [ ] Run during off-peak hours (2-6 AM)
- [ ] Monitor first 10 pages for issues
- [ ] Be ready to solve CAPTCHA manually

---

## 🚀 **Ready to Start Gurgaon!**

**Current config is set for Gurgaon.** Just run:

```bash
cd ncr_property_price_estimation/data
python ingestion.py
```

**The scraper will:**
- ✅ Skip Noida (already done)
- ✅ Start Gurgaon from page 1
- ✅ Take 2-minute breaks every 10 pages
- ✅ Pause for CAPTCHA (you solve manually)
- ✅ Save all data to `data/raw/99acres_NCR_ML_Final.csv`
- ✅ Create checkpoint for resume capability

---

## 📝 **Next: HTML Optimization**

Once you provide the HTML (see `HTML_EXTRACTION_GUIDE.md`), I will:
1. Optimize all CSS selectors
2. Ensure 100% data capture
3. Improve extraction speed
4. Add any missing fields

**For now, the scraper is ready to run with current selectors!** 🎯

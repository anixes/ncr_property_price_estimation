# Making the Scraper More CAPTCHA-Proof

## ❌ **Bad News: BeautifulSoup Alone Won't Work**

99acres uses **JavaScript rendering** - the property listings are loaded dynamically after page load. A simple HTTP request returns only ~12KB of HTML (mostly empty shell), not the full listings.

**Proof:**
- Direct HTTP request: 12,579 bytes
- Browser-rendered page: Much larger with all listings

**Conclusion:** You MUST use a browser (Selenium/Playwright) to render JavaScript.

---

## ✅ **Better Strategies to Avoid CAPTCHA**

### **Option 1: Residential Proxy Rotation** ⭐ BEST for Large Scale

**How it works:**
- Use rotating residential proxies (real home IPs)
- Each request appears from different location
- 99acres can't ban you (looks like different users)

**Implementation:**
```python
# Using a proxy service like BrightData, Oxylabs, or Smartproxy
proxies = {
    'http': 'http://username:password@proxy.provider.com:port',
    'https': 'http://username:password@proxy.provider.com:port'
}

chrome_options.add_argument(f'--proxy-server={proxy}')
```

**Pros:**
- ✅ Can scrape 24/7 without CAPTCHA
- ✅ Looks like real users from different locations
- ✅ Professional solution

**Cons:**
- 💰 Costs money ($50-200/month for good service)
- ⚠️ Requires setup

**Recommended Services:**
- BrightData (formerly Luminati) - Premium
- Smartproxy - Mid-range
- Oxylabs - Enterprise

---

### **Option 2: Slower Scraping + Longer Breaks** ⭐ FREE & SIMPLE

**Current settings:**
```yaml
coffee_break_interval: 20  # Break every 20 pages
coffee_break_duration: 60  # 60 second breaks
```

**More conservative:**
```yaml
coffee_break_interval: 10  # Break every 10 pages
coffee_break_duration: 180  # 3 minute breaks
```

**Add random long pauses:**
```python
# Every 50 pages, take a 10-minute break
if page_count % 50 == 0:
    logging.info("Taking extended break (10 minutes)...")
    time.sleep(600)
```

**Pros:**
- ✅ Free
- ✅ Simple to implement
- ✅ Reduces CAPTCHA triggers

**Cons:**
- ⏱️ Much slower (7 cities = 2-3 days instead of hours)
- ⚠️ Still might trigger CAPTCHA eventually

---

### **Option 3: Scrape During Off-Peak Hours** ⭐ EASY WIN

**Best times:**
- 2 AM - 6 AM IST (least traffic)
- Weekends (less monitoring)

**Why it works:**
- Less server load = less strict detection
- Fewer real users = your activity less suspicious

**Implementation:**
```python
import datetime

# Only run during off-peak hours
current_hour = datetime.datetime.now().hour
if not (2 <= current_hour <= 6):
    print("Waiting for off-peak hours (2 AM - 6 AM)...")
    # Calculate wait time and sleep
```

---

### **Option 4: Multiple Accounts + Cookie Rotation**

**How it works:**
1. Create 3-5 different 99acres accounts
2. Browse manually with each account
3. Export cookies for each
4. Rotate cookies every 100 pages

**Implementation:**
```python
cookie_files = ['cookies1.json', 'cookies2.json', 'cookies3.json']
current_cookie_index = 0

# Every 100 pages
if page_count % 100 == 0:
    current_cookie_index = (current_cookie_index + 1) % len(cookie_files)
    load_cookies(cookie_files[current_cookie_index])
    driver.refresh()
```

**Pros:**
- ✅ Spreads activity across multiple accounts
- ✅ Harder to detect as bot

**Cons:**
- ⚠️ Need multiple accounts
- ⚠️ Manual cookie management

---

### **Option 5: Playwright with Stealth Plugin** ⭐ BETTER than Selenium

**Why Playwright:**
- More modern than Selenium
- Better anti-detection
- Built-in stealth mode

**Installation:**
```bash
pip install playwright playwright-stealth
playwright install chromium
```

**Implementation:**
```python
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    stealth_sync(page)  # Apply stealth patches
    page.goto('https://www.99acres.com/...')
```

**Pros:**
- ✅ Better than undetected-chromedriver
- ✅ More features
- ✅ Actively maintained

**Cons:**
- ⚠️ Need to rewrite scraper
- ⚠️ Learning curve

---

### **Option 6: Manual CAPTCHA Solving Service** 💰

**How it works:**
- Script detects CAPTCHA
- Sends CAPTCHA image to solving service (2Captcha, Anti-Captcha)
- Service solves it (humans or AI)
- Script continues

**Cost:** ~$1-3 per 1000 CAPTCHAs

**Implementation:**
```python
from twocaptcha import TwoCaptcha

solver = TwoCaptcha('YOUR_API_KEY')
result = solver.recaptcha(sitekey='...', url='...')
# Inject solution and continue
```

**Pros:**
- ✅ Fully automated
- ✅ No manual intervention

**Cons:**
- 💰 Costs money
- ⏱️ Slower (30-60 seconds per CAPTCHA)

---

## 🎯 **RECOMMENDED APPROACH for You**

Based on your needs (free, simple, effective):

### **Hybrid Strategy:**

1. **Keep current Selenium setup** (it's working!)

2. **Make it more conservative:**
   ```yaml
   coffee_break_interval: 10  # Every 10 pages
   coffee_break_duration: 120  # 2 minutes
   ```

3. **Add random delays:**
   ```python
   # After every page
   time.sleep(random.uniform(8, 15))  # Instead of 3-7
   ```

4. **Scrape during off-peak hours:**
   - Run between 2 AM - 6 AM IST
   - Set up as scheduled task

5. **Manual CAPTCHA solving:**
   - Keep current implementation (pause and wait for you)
   - You solve it manually when it appears
   - Much cheaper than paid services

6. **One city per day:**
   - Don't scrape all 7 cities in one session
   - Do Gurgaon today, Greater Noida tomorrow, etc.
   - Spreads activity over time

---

## 📊 **Expected Results**

### Current Approach (with improvements):
- **Speed:** 1 city per day
- **CAPTCHA frequency:** Every 50-100 pages
- **Manual intervention:** 2-3 times per city
- **Total time:** 7 days for all cities
- **Cost:** FREE

### With Proxies (if you invest):
- **Speed:** All cities in 1 day
- **CAPTCHA frequency:** Rare/never
- **Manual intervention:** None
- **Total time:** 6-8 hours
- **Cost:** $50-100/month

---

## 🚀 **Quick Wins You Can Implement Now**

1. **Update config.yaml:**
   ```yaml
   scraper:
     coffee_break_interval: 10
     coffee_break_duration: 120
   ```

2. **Scrape one city at a time:**
   Comment out other cities in config, run separately

3. **Run at night:**
   Start scraper at 2 AM

4. **Accept manual CAPTCHA solving:**
   It's free and works!

---

## ❓ **Can You Provide HTML?**

Yes! If you can provide me with:
1. Full HTML of a property listing page (from browser DevTools)
2. I can optimize the selectors
3. But we still need Selenium for JavaScript rendering

**To get HTML:**
1. Open 99acres in Chrome
2. Right-click → Inspect
3. Right-click on `<html>` tag → Copy → Copy OuterHTML
4. Paste into a file and share

This will help me improve the extraction logic, but won't eliminate need for browser.

---

**Bottom line:** Stick with Selenium + manual CAPTCHA solving + slower scraping. It's free and effective! 🎯

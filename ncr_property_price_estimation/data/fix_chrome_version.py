"""
ChromeDriver Version Fix Utility
=================================

This script helps resolve Chrome/ChromeDriver version mismatches.
"""

import subprocess
import sys
from pathlib import Path

def get_chrome_version():
    """Try to detect installed Chrome version."""
    try:
        # Windows Chrome location
        chrome_path = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        if not chrome_path.exists():
            chrome_path = Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")
        
        if chrome_path.exists():
            result = subprocess.run(
                [str(chrome_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip().split()[-1]
            return version
    except Exception as e:
        print(f"Could not detect Chrome version: {e}")
    
    return None

def main():
    print("=" * 70)
    print("Chrome/ChromeDriver Version Fix Utility")
    print("=" * 70)
    
    # Detect Chrome version
    chrome_version = get_chrome_version()
    if chrome_version:
        print(f"\n✓ Detected Chrome version: {chrome_version}")
    else:
        print("\n⚠ Could not auto-detect Chrome version")
    
    print("\n" + "=" * 70)
    print("SOLUTION OPTIONS:")
    print("=" * 70)
    
    print("\n📌 OPTION 1: Update Chrome Browser (RECOMMENDED)")
    print("-" * 70)
    print("1. Open Chrome browser")
    print("2. Go to: chrome://settings/help")
    print("3. Chrome will auto-update to the latest version")
    print("4. Restart Chrome")
    print("5. Run the scraper again")
    
    print("\n📌 OPTION 2: Force ChromeDriver Download")
    print("-" * 70)
    print("Run this command to force download the correct ChromeDriver:")
    print("\n  pip uninstall undetected-chromedriver -y")
    print("  pip install undetected-chromedriver --force-reinstall")
    
    print("\n📌 OPTION 3: Use Specific ChromeDriver Version")
    print("-" * 70)
    print("If you want to match your current Chrome (144):")
    print("\n  pip install undetected-chromedriver==3.5.4")
    
    print("\n📌 OPTION 4: Let It Auto-Download (May Work)")
    print("-" * 70)
    print("Sometimes undetected-chromedriver auto-downloads the correct version.")
    print("Just run the scraper again - it might work!")
    
    print("\n" + "=" * 70)
    print("QUICK FIX (Try this first):")
    print("=" * 70)
    print("\n1. Update Chrome: chrome://settings/help")
    print("2. Restart Chrome")
    print("3. Run: python ingestion.py")
    
    print("\n" + "=" * 70)
    
    # Offer to try reinstall
    print("\n")
    choice = input("Do you want to try reinstalling undetected-chromedriver now? (y/n): ").lower()
    
    if choice == 'y':
        print("\nReinstalling undetected-chromedriver...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "uninstall", "undetected-chromedriver", "-y"], check=True)
            subprocess.run([sys.executable, "-m", "pip", "install", "undetected-chromedriver", "--force-reinstall"], check=True)
            print("\n✓ Reinstall complete! Try running the scraper again.")
        except Exception as e:
            print(f"\n✗ Reinstall failed: {e}")
            print("Please try manual installation.")
    else:
        print("\nNo problem! Follow the options above manually.")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

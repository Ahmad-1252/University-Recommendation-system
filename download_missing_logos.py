import os
import time
import requests
from pymongo import MongoClient
import undetected_chromedriver as uc
from urllib.parse import urlparse

# Connect to MongoDB
MONGO_URI = "mongodb://localhost:27017/smart-university-finder"
client = MongoClient(MONGO_URI)
db = client.get_database()
University = db.universities

def download_missing_logos():
    # Find all universities with an http logoUrl (meaning it failed previously)
    failed_docs = list(University.find({"logoUrl": {"$regex": "^http"}}))
    print(f"Found {len(failed_docs)} universities missing local logos.")
    
    if not failed_docs:
        print("No missing logos to download.")
        return

    output_dir = os.path.abspath(os.path.join("..", "uniscout", "frontend", "public", "logos"))
    os.makedirs(output_dir, exist_ok=True)

    print("Starting undetected-chromedriver...")
    options = uc.ChromeOptions()
    options.headless = True
    # In headless, CF sometimes still blocks. Let's try headless False if it fails, but headless True usually works with UC.
    driver = uc.Chrome(options=options)
    
    # Pre-warm the browser with topuniversities
    driver.get("https://www.topuniversities.com")
    time.sleep(3)
    
    # Get cookies
    selenium_cookies = driver.get_cookies()
    session = requests.Session()
    session.headers.update({
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://www.topuniversities.com/"
    })
    for cookie in selenium_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    success_count = 0
    fail_count = 0

    for i, doc in enumerate(failed_docs):
        url = doc.get("logoUrl")
        slug = doc.get("slug")
        name = doc.get("name")
        
        if not url or not slug:
            continue
            
        print(f"[{i+1}/{len(failed_docs)}] Downloading {name}...")
        
        try:
            # Let's try to fetch with the requests session having CF cookies
            res = session.get(url, timeout=10)
            if res.status_code == 200 and 'image' in res.headers.get('Content-Type', ''):
                filepath = os.path.join(output_dir, f"{slug}.jpg")
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                
                # Update DB
                local_url = f"/logos/{slug}.jpg"
                University.update_one({"_id": doc["_id"]}, {"$set": {"logoUrl": local_url}})
                success_count += 1
                print(f"  ✓ Saved to {local_url}")
                time.sleep(0.5)
            else:
                # If forbidden, maybe we need to navigate directly with the browser
                if res.status_code == 403:
                    driver.get(url)
                    time.sleep(1.5)
                    # Get updated cookies
                    for c in driver.get_cookies():
                        session.cookies.set(c['name'], c['value'], domain=c['domain'])
                    
                    res2 = session.get(url, timeout=10)
                    if res2.status_code == 200 and 'image' in res2.headers.get('Content-Type', ''):
                        filepath = os.path.join(output_dir, f"{slug}.jpg")
                        with open(filepath, 'wb') as f:
                            f.write(res2.content)
                        local_url = f"/logos/{slug}.jpg"
                        University.update_one({"_id": doc["_id"]}, {"$set": {"logoUrl": local_url}})
                        success_count += 1
                        print(f"  ✓ Saved (after browser nav) to {local_url}")
                    else:
                        print(f"  ✗ Failed after browser nav: {res2.status_code} {res2.headers.get('Content-Type')}")
                        fail_count += 1
                else:
                    print(f"  ✗ Failed: {res.status_code}")
                    fail_count += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            fail_count += 1
            
    print(f"\nDone! Successfully downloaded {success_count} logos. Failed: {fail_count}")
    driver.quit()

if __name__ == "__main__":
    download_missing_logos()

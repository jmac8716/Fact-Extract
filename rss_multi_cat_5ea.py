import json, urllib.request, trafilatura, datetime, os, feedparser, re, subprocess
from trafilatura.feeds import find_feed_urls
from playwright.sync_api import sync_playwright

SEEN_URLS_FILE = r"C:\Users\jmac8\OneDrive\Documents\GitHub\Fact Extract\seen_urls.txt"
if not os.path.exists(SEEN_URLS_FILE):
    with open(SEEN_URLS_FILE, 'w') as f: f.write("")

# --- 1. DEFINE YOUR FEEDS & CATEGORIES ---
NEWS_SOURCES = {
    "Headlines": [
        "https://feeds.npr.org/1003/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "http://www.politico.com/rss/politicopicks.xml",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.cbsnews.com/latest/rss/main"
    ],
    "Tech": [
        "https://www.wired.com/feed/rss",
        "https://techcrunch.com/feed/",
        "http://www.theverge.com/rss/full.xml",
        "http://www.engadget.com/rss-full.xml",
        "https://feeds.arstechnica.com/arstechnica/technology-lab"
    ],
    "Business and Finance": [
        "https://feeds.marketwatch.com/marketwatch/topstories",
        "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=yhoo,goog&region=US&lang=en-US",
        "https://investing.com/rss/news.rss",
        "https://cnbc.com/id/10000115/device/rss/rss.html"
    ],
    "Sports": [
        "https://www.espn.com/espn/rss/news",
        "http://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.cbssports.com/rss/headlines/",
        "https://sports.yahoo.com/general/news/rss/",
        "https://feeds.feedburner.com/sportzwire/IlZkQmMNRf7"
    ],
    "Entertainment": [
        "https://variety.com/feed",
        "https://www.tmz.com/rss.xml",
        "https://deadline.com/feed",
        "https://www.buzzfeed.com/tvandmovies.xml",
    ],
    "Gaming": [
        "https://www.gamespot.com/feeds/mashup",
        "https://feeds.ign.com/ign/news",
        "https://www.pcgamer.com/rss/"
    ]
}
ARCHIVE_FOLDER = r"C:\Users\jmac8\OneDrive\Documents\GitHub\Fact Extract\NewsArchive"
if not os.path.exists(ARCHIVE_FOLDER): os.makedirs(ARCHIVE_FOLDER)

# --- 2. AI & BROWSER FUNCTIONS (Same as before) ---
def extract_pro_intel(article_text, category):
    url = "http://127.0.0.1:11434/api/generate"
    # We tell the AI what category it's looking at to improve context
    prompt = f"Category: {category}. Analyze this news and provide a 4-sentence summary and 4 key facts:\n\n{article_text[:3000]}"
    payload = {"model": "llama3.1:70b-instruct-q8_0", "prompt": prompt, "stream": False}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as res:
            return json.loads(res.read().decode('utf-8'))['response']
    except: return "Analysis Error"

def get_content_with_browser(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            text = trafilatura.extract(page.content())
            browser.close()
            return text
    except: return None

def get_safe_title(metadata, url):
    # 1. Try the metadata title first
    title = getattr(metadata, 'title', None)

    # 2. SANITY CHECK: If title is empty, too short, or looks like gibberish (IDs)
    # This regex looks for long strings of random letters/numbers often found in IDs
    is_gibberish = title and (re.search(r'[A-Za-z0-9]{10,}', title) and " " not in title)
    
    if not title or len(title) < 10 or is_gibberish:
        # Fallback: Extract from the URL but skip the "ID" part
        # We split the URL and take the part that looks like words
        parts = url.split('/')
        # Look for the segment with the most dashes (usually the headline)
        slug = max(parts, key=lambda x: x.count('-'))
        
        # Clean the slug: remove numbers at the end (like 4637480)
        clean_slug = re.sub(r'\d{5,}', '', slug) # Removes 5+ digit numbers
        title = clean_slug.replace(".html", "").replace("-", " ").strip().title()

    # 3. Final Polish: Remove common junk
    title = re.sub(r'\s+', ' ', title) # Fix double spaces
    return title.strip()

# --- 3. THE MULTI-LOOP ---
all_results = []
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
cutoff_date = datetime.datetime.now() - datetime.timedelta(hours=48) # Only last 48h

# Load seen URLs into memory for speed
with open(SEEN_URLS_FILE, 'r') as f:
    seen_urls = set(f.read().splitlines())

for category, rss_list in NEWS_SOURCES.items():
    print(f"📡 Processing Category: {category}")
    
    for rss_url in rss_list:
        print(f"   📥 Opening Feed: {rss_url}")
        links = find_feed_urls(rss_url)
        
        if "npr.org" in rss_url:
        # Use feedparser for NPR feeds - it understands their XML better
            feed = feedparser.parse(rss_url)
            links = [entry.link for entry in feed.entries]
        else:
            # Keep trafilatura for other standard feeds
            links = find_feed_urls(rss_url)

        if links:
            for link in links[:1]:
                # EDIT A: SKIP IF ALREADY SEEN
                if link in seen_urls:
                    continue 
            # 2. DEFINE A DEFAULT TITLE IMMEDIATELY
            # This prevents the NameError if the metadata check fails later
                article_title = link.split('/')[-1].split('?')[0].replace(".html", "").replace("-", " ").title()
                
                print(f"      🕵️ Analyzing: {link[:60]}...")
                
                # Fetch content
                content_raw = get_content_with_browser(link)
                
                if content_raw:
                    # EDIT B: DATE FILTERING (Only newest)
                    # We use trafilatura to check the metadata date
                    metadata = trafilatura.extract_metadata(content_raw)

                    # 2. PLACE THE SMART CLEANER HERE
                    # This uses the function we just built to fix those gibberish IDs
                    article_title = get_safe_title(metadata, link)
                    
                    # --- ADD THIS GUARD ---
                    # If trafilatura returned less than 200 characters, it probably failed
                    if len(content_raw.strip()) < 100:
                        print(f"   ❌ Skipping: No readable content found for {article_title}")
                        continue

                    if metadata and metadata.date:
                        try:
                            # 1. Parse the date string from the website
                            # Trafilatura usually provides YYYY-MM-DD HH:MM:SS or just YYYY-MM-DD
                            article_date = datetime.datetime.fromisoformat(metadata.date.replace('Z', '+00:00'))
                            # 2. Add timezone awareness if missing (to prevent 'offset-naive' errors)
                            if article_date.tzinfo is None:
                                article_date = article_date.replace(tzinfo=datetime.timezone.utc)
                                
                            cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=48)
                            
                            # 3. THE ACTUAL FILTER
                            if article_date < cutoff_time:
                                print(f"   ⏳ Skipping: Article is older than 48 hours ({metadata.date})")
                                continue

                        except:
                            print(f"   ⚠️ Date parse failed for {link}, proceeding anyway.")
                            
                    # 5. NOW 'article_title' IS GUARANTEED TO EXIST
                    report = extract_pro_intel(content_raw, category)

                    # --- ADD THIS GUARD ---
                    # Skip if the AI failed or returned an empty response
                    if not report or "Analysis Error" in report or len(report.strip()) < 50:
                        print(f"   ❌ Skipping: AI failed to generate a report for {article_title}")
                        continue

                    all_results.append({
                        "title": article_title,
                        "category": category,
                        "url": link,
                        "report": report,
                        "time": timestamp
                    })
                    
                    # Mark as seen so we never scrape it again
                    with open(SEEN_URLS_FILE, 'a') as f:
                        f.write(link + '\n')
                    seen_urls.add(link)

# Save to unique file
save_path = os.path.join(ARCHIVE_FOLDER, f"{timestamp}.json")
with open(save_path, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=4, ensure_ascii=False)
print(f"✨ Multi-Category Report Archived: {save_path}")

# THE UPDATED SYNC FUNCTION

def push_to_github():
        print("🚀 Syncing new intelligence to GitHub...")
        try:
            # IMPORTANT: Change this path to exactly where your GitHub repo folder is
            os.chdir(r"C:\Users\jmac8\OneDrive\Documents\GitHub\Fact Extract\NewsArchive") 
            
            # These commands talk to GitHub Desktop's engine
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Auto-update News Archive"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("✅ Cloud Update Complete!")
        except Exception as e:
            print(f"⚠️ GitHub sync failed: {e}")
            print("Make sure GitHub Desktop is installed and the path is correct.")

    # RUN THE SYNC
push_to_github()
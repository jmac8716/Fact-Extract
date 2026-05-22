import json, urllib.request, trafilatura, datetime, time, os, feedparser, re, subprocess
from trafilatura.feeds import find_feed_urls
from playwright.sync_api import sync_playwright
from gtts import gTTS
from docx import Document

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
       "https://techcrunch.com/feed/",
        "http://www.engadget.com/rss-full.xml",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://feeds.feedburner.com/thenextweb",
        "https://rss.slashdot.org/Slashdot/slashdotMain"
    ],
    "Business and Finance": [
        "https://feeds.marketwatch.com/marketwatch/topstories",
        "https://www.investing.com/rss/121899.rss",
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
        "https://screenrant.com/feed",
        "https://deadline.com/feed",
        "https://www.buzzfeed.com/tvandmovies.xml",
        "https://hollywoodreporter.com/feed"
    ],
    "Gaming": [
        "https://www.gamespot.com/feeds/mashup",
        "https://feeds.ign.com/ign/news",
        "https://www.pcgamer.com/rss/",
        "https://www.polygon.com/rss/index.xml",
        "https://www.gameinformer.com/news.xml"
    ]
}

ARCHIVE_FOLDER = r"C:\Users\jmac8\OneDrive\Documents\GitHub\Fact Extract\NewsArchive"
if not os.path.exists(ARCHIVE_FOLDER): os.makedirs(ARCHIVE_FOLDER)

SOURCE_DOCS_FOLDER = r"C:\Users\jmac8\OneDrive\Documents\GitHub\Fact Extract\SourceDocs"
if not os.path.exists(SOURCE_DOCS_FOLDER): os.makedirs(SOURCE_DOCS_FOLDER)


# --- 2. AI, BROWSER, & WORD FUNCTIONS ---
def extract_pro_intel(article_text, category):
    url = "http://127.0.0.1:11434/api/generate"
    prompt = f"Category: {category}. Analyze this news and provide a 4-sentence summary and 5 key facts:\n\n{article_text[:3000]}"
    payload = {"model": "llama3.1:70b-instruct-q8_0", "prompt": prompt, "stream": False}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=900) as res:
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
    title = getattr(metadata, 'title', None)
    is_gibberish = title and (re.search(r'[A-Za-z0-9]{10,}', title) and " " not in title)
    
    if not title or len(title) < 10 or is_gibberish:
        parts = url.split('/')
        slug = max(parts, key=lambda x: x.count('-'))
        clean_slug = re.sub(r'\d{5,}', '', slug)
        title = clean_slug.replace(".html", "").replace("-", " ").strip().title()

    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def extract_metadata_and_body_from_docx(file_path):
    """Extracts text from Word file, parsing out an optional URL (Line 1) and optional Category (Line 2)."""
    try:
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        if not paragraphs:
            return None, None, None
            
        source_url = None
        category = None
        start_index = 0
        
        # 1. Look for a URL on Line 1
        if paragraphs[start_index].startswith(("http://", "https://")):
            source_url = paragraphs[start_index]
            start_index += 1
            
            # 2. Check if Line 2 contains a short string (likely a category)
            if start_index < len(paragraphs) and len(paragraphs[start_index]) < 40 and not paragraphs[start_index].startswith(("http://", "https://")):
                category = paragraphs[start_index]
                start_index += 1
        
        # 3. Compile the remaining paragraphs as the body text for the AI
        body_text = "\n".join(paragraphs[start_index:])
        return body_text, source_url, category
    except Exception as e:
        print(f"   ❌ Error reading document file layout: {e}")
        return None, None, None


# --- 3. THE MULTI-LOOP ---
all_results = []
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")

# Load seen URLs into memory
with open(SEEN_URLS_FILE, 'r') as f:
    seen_urls = set(f.read().splitlines())

# --- PART A: PROCESS LIVE RSS FEEDS ---
for category, rss_list in NEWS_SOURCES.items():
    print(f"📡 Processing Category: {category}")
    articles_found_for_this_category = 0
    
    for rss_url in rss_list:
        print(f"   📥 Opening Feed: {rss_url}")
        
        if "npr.org" in rss_url:
            feed = feedparser.parse(rss_url)
            links = [entry.link for entry in feed.entries]
        else:
            links = find_feed_urls(rss_url)

        if links:
            for link in links[:1]:
                if link in seen_urls:
                    continue 
                
                article_title = link.split('/')[-1].split('?')[0].replace(".html", "").replace("-", " ").title()
                print(f"      🕵️ Analyzing: {link[:60]}...")
                
                content_raw = get_content_with_browser(link)
                
                if content_raw:
                    metadata = trafilatura.extract_metadata(content_raw)
                    article_title = get_safe_title(metadata, link)
                    
                    if len(content_raw.strip()) < 100:
                        print(f"   ❌ Skipping: No readable content found for {article_title}")
                        continue

                    if metadata and metadata.date:
                        try:
                            article_date = datetime.datetime.fromisoformat(metadata.date.replace('Z', '+00:00'))
                            if article_date.tzinfo is None:
                                article_date = article_date.replace(tzinfo=datetime.timezone.utc)
                                
                            cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=48)
                            
                            if article_date < cutoff_time and articles_found_for_this_category > 0:
                                print(f"   ⏳ Skipping: Article is older than 48 hours ({metadata.date})")
                                continue
                            elif article_date < cutoff_time:
                                print(f"   ⚠️ Taking older article to ensure {category} isn't empty.")
                        except:
                            print(f"   ⚠️ Date parse failed for {link}, proceeding anyway.")
                            
                    report = extract_pro_intel(content_raw, category)
                    print(f" wait 5 sec")
                    time.sleep(5)
                    
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
                    
                    with open(SEEN_URLS_FILE, 'a') as f:
                        f.write(link + '\n')
                    seen_urls.add(link)

                    articles_found_for_this_category += 1
                    print(f"   ... Saved to {category} (Total for this category: {articles_found_for_this_category})")

                    if articles_found_for_this_category >= 2:
                        print(f"   🏁 Reached max articles for {category}. Moving to next category.")
                        break


# --- PART B: PROCESS LOCAL WORD DOCUMENTS ---
print("📄 Sweeping SourceDocs folder for Word Assets...")
if os.path.exists(SOURCE_DOCS_FOLDER):
    docx_files = [f for f in os.listdir(SOURCE_DOCS_FOLDER) if f.endswith('.docx')]
    
    for file_name in docx_files:
        doc_path = os.path.join(SOURCE_DOCS_FOLDER, file_name)
        print(f"   🕵️ Reading Asset Document: {file_name}")
        
        doc_text, embedded_url, custom_category = extract_metadata_and_body_from_docx(doc_path)
        
        # Fallback default assignments (Now defaulting to HEADLINES)
        tracking_key = embedded_url if embedded_url else f"local-file://{file_name}"
        display_category = custom_category if custom_category else "HEADLINES"
        
        if tracking_key in seen_urls:
            print(f"   ⏭️ Skipping {file_name}: Source URL or filename already processed.")
            continue

        if doc_text and len(doc_text.strip()) > 50:
            cleaned_title = file_name.replace(".docx", "").replace("-", " ").replace("_", " ").strip().title()
            
            report = extract_pro_intel(doc_text, display_category)
            
            if report and "Analysis Error" not in report:
                all_results.append({
                    "title": cleaned_title,
                    "category": display_category,
                    "url": tracking_key,
                    "report": report,
                    "time": timestamp
                })
                
                with open(SEEN_URLS_FILE, 'a') as f:
                    f.write(tracking_key + '\n')
                seen_urls.add(tracking_key)
                print(f"   ✅ Processed document [{display_category}]: {cleaned_title}")
            else:
                print(f"   ❌ AI extraction failed for document content inside {file_name}")
else:
    print("   ⚠️ SourceDocs directory path not accessible.")


# --- PART C: SAVE AND SYNC HUB ---
def push_to_github():
    print("🚀 Syncing new intelligence to GitHub...")
    try:
        os.chdir(r"C:\Users\jmac8\OneDrive\Documents\GitHub\Fact Extract") 
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update News Archive with Audio Broadcast"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Cloud Update Complete!")
    except Exception as e:
        print(f"⚠️ GitHub sync failed: {e}")

if len(all_results) > 0:
    save_path = os.path.join(ARCHIVE_FOLDER, f"{timestamp}.json")
    
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    print(f"✅ Successfully saved {len(all_results)} total combined reports to {save_path}")

    # ========================================================
    # 🎙️ NEURAL AUDIO GENERATION ENGINE (UPGRADED)
    # ========================================================
    print("🔊 Generating NEURAL audio broadcast from scraped intel...")
    
    # 1. Compile the news text into a single spoken script
    audio_script = "Here are your updates on current events from Fact Extract. "
    for entry in all_results:
        category = entry.get('category', 'General').upper()
        title = entry.get('title', 'Untitled Report')
        facts = entry.get('report', entry.get('facts', 'No content summary available.'))
        
        audio_script += f" New Update in Category: {category}. Headline: {title}. Details: {facts}. "
    
    try:
        import asyncio
        import edge_tts
        
        # 2. Define filenames and paths
        audio_filename = f"{timestamp}.mp3"
        audio_filepath = os.path.join(ARCHIVE_FOLDER, audio_filename)
        
        # 3. Compile the script using Emma's neural voice
        async def voice_compile():
            communicate = edge_tts.Communicate(audio_script, "en-US-EmmaNeural")
            await communicate.save(audio_filepath)
            
        asyncio.run(voice_compile())
        print(f"🔊 Neural audio file successfully compiled: {audio_filepath}")
        
    except Exception as e:
        print(f"⚠️ Neural audio generation failed: {e}")
    # ========================================================

    # 🔥 NEW BUFFER: Give OneDrive 5 seconds to scan the heavy mp3 file and let go of its lock
    print("⏳ Waiting 5 seconds for system file locks to clear...")
    time.sleep(5)

    # Fire the GitHub routine to push BOTH files smoothly
    push_to_github()
else:
    print("⚠️ No new updates found or compiled from any source arrays. Sync skipped.")
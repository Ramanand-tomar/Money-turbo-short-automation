import json
from loguru import logger
from app.services import db

DEFAULT_TRENDS = {
    "all": [
        {"topic": "AI Automation Tools", "suggested_hook": "AI is changing the game, and these 3 tools are leading the charge.", "score": 90},
        {"topic": "Remote Work Life Hacks", "suggested_hook": "If you work from home, this simple routine will double your output.", "score": 85},
        {"topic": "Morning Routine Ideas", "suggested_hook": "How successful people structure their first 60 minutes.", "score": 80},
        {"topic": "Travel Hacks 2026", "suggested_hook": "These travel secrets will save you thousands on your next flight.", "score": 75},
        {"topic": "Healthy Meal Prep", "suggested_hook": "Eat healthy all week with this 20-minute Sunday routine.", "score": 70}
    ],
    "motivation": [
        {"topic": "Consistency Mindset Hacks", "suggested_hook": "Consistency isn't about motivation; it is about this one simple rule.", "score": 95},
        {"topic": "Overcoming Procrastination", "suggested_hook": "The 5-second rule that stops procrastination instantly.", "score": 90},
        {"topic": "Building Good Habits", "suggested_hook": "Atomic habits start with this daily 2-minute decision.", "score": 88},
        {"topic": "Discipline vs Motivation", "suggested_hook": "Why relying on motivation is the biggest reason you fail.", "score": 85},
        {"topic": "Mental Resilience Practices", "suggested_hook": "How to train your mind to handle stress without breaking.", "score": 80}
    ],
    "finance": [
        {"topic": "Side Hustle Ideas", "suggested_hook": "These 3 side hustles can make you $500 a week from your couch.", "score": 92},
        {"topic": "Passive Income Guide", "suggested_hook": "Stop trading time for money: here are 3 real passive income streams.", "score": 89},
        {"topic": "Smart Investing Strategies", "suggested_hook": "Where to invest your first $1,000 for long-term growth.", "score": 87},
        {"topic": "Crypto Trends Analysis", "suggested_hook": "If you hold cryptocurrency, you need to watch this critical level.", "score": 85},
        {"topic": "Budgeting Tips for Beginners", "suggested_hook": "The 50/30/20 rule that will save your bank account this month.", "score": 80}
    ],
    "health": [
        {"topic": "Home Workout Routines", "suggested_hook": "No gym? No problem. Get fit with this 15-minute bodyweight routine.", "score": 91},
        {"topic": "Intermittent Fasting Guide", "suggested_hook": "What actually happens to your body when you fast for 16 hours.", "score": 88},
        {"topic": "Mental Health Routine", "suggested_hook": "Do these 3 things daily to completely reset your nervous system.", "score": 85},
        {"topic": "Sleep Optimization Tips", "suggested_hook": "The exact routine that will give you the best sleep of your life.", "score": 82},
        {"topic": "Superfoods for Energy", "suggested_hook": "Swap your morning coffee for this one natural energy booster.", "score": 78}
    ],
    "tech": [
        {"topic": "AI Video Generation Tools", "suggested_hook": "These brand new AI video tools are scarily realistic.", "score": 94},
        {"topic": "New Gadget Launches", "suggested_hook": "Is this new smartphone actually worth the massive price tag?", "score": 89},
        {"topic": "Coding with AI Assistants", "suggested_hook": "How junior devs are coding like seniors using AI prompts.", "score": 86},
        {"topic": "Future of Smart Devices", "suggested_hook": "The smart home tech you didn't know you needed in 2026.", "score": 83},
        {"topic": "Cybersecurity Tips 2026", "suggested_hook": "Check this setting on your phone right now to stop hackers.", "score": 80}
    ],
    "entertainment": [
        {"topic": "New Movie Releases", "suggested_hook": "The shocking ending of this new movie has everyone talking.", "score": 93},
        {"topic": "Viral TikTok Audio Trends", "suggested_hook": "Why this 10-second sound is taking over everyone's FYP.", "score": 88},
        {"topic": "Binge-Worthy Show Reviews", "suggested_hook": "This is the best series on Netflix right now, hands down.", "score": 85},
        {"topic": "Behind the Scenes Stories", "suggested_hook": "The crazy reason this famous scene was almost cut from the movie.", "score": 82},
        {"topic": "Viral Meme Analysis", "suggested_hook": "The origin story of the internet's biggest meme of the week.", "score": 79}
    ]
}

def fetch_youtube_trending(category: str = "all", region: str = "US", user_id: str = "global") -> list:
    try:
        from youtube_uploader import get_authenticated_service
        youtube = get_authenticated_service(user_id=user_id)
        
        cat_id = None
        if category == "tech":
            cat_id = "28"
        elif category == "entertainment":
            cat_id = "24"
        elif category in ["education", "motivation", "finance"]:
            cat_id = "27"
        elif category == "health":
            cat_id = "22"
            
        request = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=region,
            videoCategoryId=cat_id,
            maxResults=10
        )
        response = request.execute()
        trends = []
        items = response.get("items", [])
        for idx, item in enumerate(items):
            snippet = item.get("snippet", {})
            title = snippet.get("title", "")
            suggested_hook = f"Here is the truth about: '{title}' that you need to hear."
            trends.append({
                "topic": title[:100],
                "platform": "youtube",
                "score": 100 - idx * 5,
                "category": category,
                "suggested_hook": suggested_hook
            })
        return trends
    except Exception as e:
        logger.warning(f"Failed to fetch YouTube trending via OAuth API: {e}")
        return []

def fetch_google_trends(category: str = "all") -> list:
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360)
        
        if category == "all":
            df = pytrends.trending_searches(pn='united_states')
            topics = df[0].head(10).tolist()
        else:
            keywords_map = {
                "motivation": ["discipline", "mindset", "success", "motivational quotes"],
                "finance": ["bitcoin", "stocks", "investing", "crypto", "side hustle"],
                "health": ["workout", "fitness", "healthy diet", "mental health"],
                "tech": ["ChatGPT", "AI tools", "tech news", "smartphones"],
                "entertainment": ["trending movies", "netflix series", "viral videos"]
            }
            kws = keywords_map.get(category, ["trending"])
            pytrends.build_payload(kw_list=[kws[0]], timeframe='now 1-d')
            rq = pytrends.related_queries()
            if kws[0] in rq and rq[kws[0]] and 'top' in rq[kws[0]] and rq[kws[0]]['top'] is not None:
                top_queries = rq[kws[0]]['top']
                topics = top_queries['query'].head(10).tolist()
            else:
                topics = [f"{kw} tips" for kw in kws]
                
        trends = []
        for idx, topic in enumerate(topics):
            topic = str(topic).title()
            suggested_hook = f"Most people get '{topic}' wrong. Here is the actual secret."
            trends.append({
                "topic": topic,
                "platform": "google",
                "score": 100 - idx * 5,
                "category": category,
                "suggested_hook": suggested_hook
            })
        return trends
    except Exception as e:
        logger.warning(f"Failed to fetch Google Trends via pytrends: {e}")
        return []

def generate_trends_via_llm(platform: str, category: str, user_id: str) -> list:
    try:
        from app.services import llm
        prompt = f"""
        # Role: Video Script Topic & Hook Generator
        ## Objective:
        Generate a list of 10 hot, engaging, and highly clickable trending topics for the platform '{platform}' in the category '{category}'.
        
        ## Requirements:
        1. Each topic should be a high-conversion video subject or search phrase (1-5 words).
        2. For each topic, write a dynamic and highly engaging suggested_hook (1 sentence) designed to hook viewers in the first 2 seconds.
        3. The response must be a valid JSON array of objects, each containing exactly two keys: "topic" and "suggested_hook".
        4. Return ONLY the raw JSON block without markdown formatting wrapper like ```json or similar.
        
        ## Examples:
        [
          {{"topic": "Consistent Morning Routines", "suggested_hook": "How successful leaders build consistency in their first 60 minutes."}},
          {{"topic": "Bitcoin Price Signals", "suggested_hook": "If you hold Bitcoin, this one indicator shows where the price goes next."}}
        ]
        """
        response = llm._generate_response(prompt, user_id=user_id)
        if "Error: " in response:
            raise ValueError(response)
            
        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_response = "\n".join(lines).strip()
            
        data = json.loads(clean_response)
        trends = []
        for idx, item in enumerate(data):
            topic = item.get("topic", "").strip()
            hook = item.get("suggested_hook", "").strip()
            if topic:
                trends.append({
                    "topic": topic,
                    "platform": platform,
                    "score": 100 - idx * 5,
                    "category": category,
                    "suggested_hook": hook or f"Here is what you need to know about {topic}."
                })
        return trends
    except Exception as e:
        logger.error(f"Failed to generate trends via LLM: {e}")
        return []

def get_trends(platform: str = "google", category: str = "all", user_id: str = "global") -> list:
    cached = db.get_cached_trends(platform=platform, category=category, max_age_minutes=60)
    if cached:
        logger.info(f"Loaded cached trends for {platform}/{category}")
        return cached
        
    trends = []
    if platform == "youtube":
        trends = fetch_youtube_trending(category=category, user_id=user_id)
    else:
        trends = fetch_google_trends(category=category)
        
    if not trends:
        logger.info(f"APIs failed. Falling back to LLM trending generator for {platform}/{category}")
        trends = generate_trends_via_llm(platform=platform, category=category, user_id=user_id)
        
    if not trends:
        logger.warning(f"LLM fallback failed. Falling back to static defaults for {platform}/{category}")
        defaults = DEFAULT_TRENDS.get(category, DEFAULT_TRENDS["all"])
        trends = []
        for idx, item in enumerate(defaults):
            trends.append({
                "topic": item["topic"],
                "platform": platform,
                "score": item.get("score", 100 - idx * 5),
                "category": category,
                "suggested_hook": item["suggested_hook"]
            })
            
    if trends:
        db.save_trends(trends)
        
    return trends

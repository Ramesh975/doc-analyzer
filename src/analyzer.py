import os, json, re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_KEYS = [k for k in [
    os.getenv('GROQ_API_KEY'),
    os.getenv('GROQ_API_KEY_2'),
    os.getenv('GROQ_API_KEY_3'),
] if k]

MODELS = [
    'llama-3.1-8b-instant',
    'llama-3.3-70b-versatile',
    'gemma2-9b-it'
]

SYSTEM_PROMPT = '''You are a strict data extraction AI. You must return pure JSON.

{
  "summary": "2-3 sentences describing the core subject of the document.",
  "entities": {
    "names": ["Array of SPECIFIC INDIVIDUAL HUMAN NAMES ONLY"],
    "dates": ["Array of specific dates, years, and relative time periods"],
    "organizations": ["Array of companies, universities, banks, and agencies"],
    "amounts": ["Array of monetary values, statistics, and percentages"],
    "locations": ["Array of cities, countries, and specific addresses"]
  },
  "sentiment": "Positive"
}

CRITICAL RULES:
1. names: ONLY specific individual people (e.g. "Nina Lane"). NEVER include companies (e.g. "Google"). NEVER include plural job titles or groups (e.g. "researchers", "experts", "analysts").
2. organizations: Companies, banks, government agencies, universities, tech firms.
3. locations: Cities, countries, addresses, regions.
4. sentiment: Exactly "Positive", "Negative", or "Neutral".
5. If a category has no matches, return an empty array [].'''


def _verify_and_dedup(raw_list: list, text_lower: str) -> list:
    """Removes duplicates and ensures the entity actually exists in the text."""
    seen = set()
    clean_list = []
    
    for item in raw_list:
        item_str = str(item).strip()
        if len(item_str) < 2: continue
        item_lower = item_str.lower()
        
        if item_lower in seen: continue
        
        if item_lower in text_lower:
            seen.add(item_lower)
            clean_list.append(item_str)
            
    return clean_list[:10]

def _aggressive_name_cleaner(names: list, orgs: list) -> list:
    """The Sledgehammer: Mathematically deletes non-human names."""
    orgs_lower = {o.lower() for o in orgs}
    
    # Words that prove this is NOT a specific person
    forbidden_words = {
        'researchers', 'experts', 'analysts', 'professionals', 'team', 
        'doctors', 'engineers', 'scientists', 'users', 'customers',
        'agencies', 'authorities', 'providers', 'institutions'
    }
    
    forbidden_companies = {
        'google', 'microsoft', 'nvidia', 'apple', 'amazon', 'meta', 'openai'
    }
    
    clean_names = []
    for name in names:
        name_lower = name.lower()
        
        # 1. If it's already in the organizations list, delete it
        if name_lower in orgs_lower:
            continue
            
        # 2. If it is a known tech company, delete it
        if name_lower in forbidden_companies:
            continue
            
        # 3. If it contains plural job titles/groups, delete it
        has_forbidden_word = any(word in name_lower for word in forbidden_words)
        if has_forbidden_word:
            continue
            
        clean_names.append(name)
        
    return clean_names


def _regex_extract(text: str) -> dict:
    dates, organizations, amounts, locations = [], [], [], []

    for y in re.findall(r'\b(19|20)\d{2}\b', text): dates.append(y)
    months = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    for m in re.findall(rf'{months}\s+\d{{4}}', text): dates.append(m)
    for q in re.findall(r'Q[1-4]\s*\d{4}', text): dates.append(q)
    for rt in re.findall(r'(?:past|last|next|coming)\s+(?:few\s+)?(?:years?|months?|decades?|weeks?)', text, re.IGNORECASE): dates.append(rt.strip())

    for c in re.findall(r'[\$₹€£¥]\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion|thousand|crore|lakh))?', text): amounts.append(c.strip())
    for p in re.findall(r'\b\d+\.?\d*\s*%', text): amounts.append(p.strip())
    for n in re.findall(r'\d+\s*(?:million|billion|trillion|thousand)\s*(?:users|records|customers|people|dollars)?', text, re.IGNORECASE): amounts.append(n.strip())

    org_patterns = [
        r'financial institutions?', r'regional banks?', r'government agenc(?:y|ies)',
        r'regulatory authorit(?:y|ies)', r'payment service providers?', r'tech(?:nology)? companies',
        r'private companies', r'universities', r'central banks?'
    ]
    for pattern in org_patterns:
        for m in re.findall(pattern, text, re.IGNORECASE):
            organizations.append(m.strip().title())

    # Basic location regex (Countries/Cities usually capitalized)
    loc_patterns = [r'\b(?:USA|UK|India|China|Japan|Germany|France|London|New York|Delhi|Mumbai|Tokyo|Paris|Berlin)\b']
    for pattern in loc_patterns:
        for m in re.findall(pattern, text):
            locations.append(m.strip())

    text_lower = text.lower()
    return {
        "names": [], 
        "dates": _verify_and_dedup(dates, text_lower),
        "organizations": _verify_and_dedup(organizations, text_lower),
        "amounts": _verify_and_dedup(amounts, text_lower),
        "locations": _verify_and_dedup(locations, text_lower)
    }

def _merge(ai: dict, regex: dict) -> dict:
    ents = ai.get('entities', {})
    for key in ['names', 'dates', 'organizations', 'amounts', 'locations']:
        ai_list = ents.get(key, [])
        rx_list = regex.get(key, [])
        if not ai_list:
            ents[key] = rx_list
        else:
            merged = list(ai_list)
            seen = {str(item).lower() for item in merged}
            for item in rx_list:
                if str(item).lower() not in seen:
                    merged.append(item)
                    seen.add(str(item).lower())
            ents[key] = merged[:10]
    ai['entities'] = ents
    return ai

def _try_groq(text: str, model: str, api_key: str):
    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': f'Analyze:\n\n{text[:6000]}'}
            ],
            temperature=0.0, 
            max_tokens=1000,
            response_format={"type": "json_object"} 
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        if '429' in str(e) or 'rate' in str(e).lower(): return 'RATE_LIMIT'
        return None

def analyze_text(text: str) -> dict:
    text_lower = text.lower()
    regex_result = _regex_extract(text)

    for model in MODELS:
        for api_key in GROQ_KEYS:
            result = _try_groq(text, model, api_key)

            if result == 'RATE_LIMIT': continue 

            if result is not None:
                ents = result.setdefault('entities', {})
                for k in ['names', 'dates', 'organizations', 'amounts', 'locations']:
                    ents.setdefault(k, [])
                
                ents['names'] = _verify_and_dedup(ents['names'], text_lower)
                ents['dates'] = _verify_and_dedup(ents['dates'], text_lower)
                ents['organizations'] = _verify_and_dedup(ents['organizations'], text_lower)
                ents['amounts'] = _verify_and_dedup(ents['amounts'], text_lower)
                ents['locations'] = _verify_and_dedup(ents['locations'], text_lower)
                
                # Apply the sledgehammer to clean up names
                ents['names'] = _aggressive_name_cleaner(ents['names'], ents['organizations'])

                result.setdefault('summary', 'Summary extracted successfully.')
                sent = result.get('sentiment', 'Neutral').capitalize()
                if sent not in ["Positive", "Negative", "Neutral"]: sent = "Neutral"
                result['sentiment'] = sent

                return _merge(result, regex_result)

    return {
        'summary': _summary_fallback(text),
        'entities': regex_result,
        'sentiment': _sentiment_fallback(text)
    }

def _summary_fallback(text: str) -> str:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 40]
    return '. '.join(sentences[:3]) + '.' if sentences else 'Document processed.'

def _sentiment_fallback(text: str) -> str:
    t = text.lower()
    pos = sum(1 for w in ['growth','success','improve','benefit','positive','increase','opportunity'] if w in t)
    neg = sum(1 for w in ['breach','attack','fail','loss','risk','threat','incident','vulnerability','crisis','concern'] if w in t)
    if neg > pos: return 'Negative'
    if pos > neg: return 'Positive'
    return 'Neutral'
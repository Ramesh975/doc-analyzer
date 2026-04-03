import os, json, re
import spacy
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Multiple Groq clients with different API keys for rotation
GROQ_KEYS = [
    os.getenv('GROQ_API_KEY'),
    os.getenv('GROQ_API_KEY_2'),
    os.getenv('GROQ_API_KEY_3'),
]
GROQ_KEYS = [k for k in GROQ_KEYS if k]  # remove None values

# Models to try in order (Fastest -> Most Accurate -> Fallback)
MODELS = [
    'llama-3.1-8b-instant',   # Very fast, extremely high limits
    'llama-3.3-70b-versatile',# Best quality, lower limits
    'gemma2-9b-it',           # Fast, good fallback
    'mixtral-8x7b-32768',     # Heavy fallback
]

# Load spaCy safely
try:
    nlp = spacy.load("en_core_web_sm")
    print("spaCy loaded successfully")
except Exception as e:
    print(f"spaCy not available (will use regex fallbacks): {e}")
    nlp = None

SYSTEM_PROMPT = '''You are a document analysis expert. You must respond in JSON format.
Extract the key information into this exact JSON schema:

{
  "summary": "2-3 sentences describing what this document is about.",
  "entities": {
    "names": ["John Smith", "Nina Lane"],
    "dates": ["2024", "March 2026", "Q3 2023", "next decade"],
    "organizations": ["Google", "regional banks", "government agencies"],
    "amounts": ["$10,000", "35%", "3 million users"]
  },
  "sentiment": "Positive"
}

RULES:
- names: Real people only (no job titles).
- sentiment: Must be exactly "Positive", "Negative", or "Neutral".
- If a category has no matches, return an empty array [].
- Return ONLY valid JSON.'''

def _spacy_extract(text: str) -> dict:
    """Fast local NLP extraction — no API needed"""
    names, dates, organizations, amounts = [], [], [], []

    if nlp:
        doc = nlp(text[:10000])
        for ent in doc.ents:
            val = ent.text.strip()
            if not val or len(val) < 2: continue
            
            if ent.label_ == "PERSON" and val not in names:
                names.append(val)
            elif ent.label_ in ("DATE", "TIME") and val not in dates:
                dates.append(val)
            elif ent.label_ == "ORG" and val not in organizations:
                organizations.append(val)
            elif ent.label_ in ("MONEY", "PERCENT", "QUANTITY") and val not in amounts:
                amounts.append(val)

    # Regex patterns — always run to catch what spaCy misses
    for y in re.findall(r'\b(19|20)\d{2}\b', text):
        if y not in dates: dates.append(y)

    for p in re.findall(r'\b\d+\.?\d*\s*%', text):
        ps = p.strip()
        if ps not in amounts: amounts.append(ps)

    for c in re.findall(r'[\$₹€£¥]\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion|thousand|crore|lakh))?', text):
        cs = c.strip()
        if cs not in amounts: amounts.append(cs)

    org_patterns = [
        r'financial institutions?', r'regional banks?',
        r'government agenc(?:y|ies)', r'regulatory authorit(?:y|ies)',
        r'tech(?:nology)? companies', r'universities'
    ]
    for pattern in org_patterns:
        for m in re.findall(pattern, text, re.IGNORECASE):
            ms = m.strip().title()
            if ms not in organizations: organizations.append(ms)

    return {
        "names": list(dict.fromkeys(names))[:10],
        "dates": list(dict.fromkeys(dates))[:10],
        "organizations": list(dict.fromkeys(organizations))[:10],
        "amounts": list(dict.fromkeys(amounts))[:10]
    }

def _merge(ai: dict, sp: dict) -> dict:
    """AI takes priority, spaCy fills empty fields"""
    ents = ai.get('entities', {})
    for key in ['names', 'dates', 'organizations', 'amounts']:
        ai_list = ents.get(key, [])
        sp_list = sp.get(key, [])
        if not ai_list:
            ents[key] = sp_list
        else:
            merged = list(ai_list)
            for item in sp_list:
                if item not in merged:
                    merged.append(item)
            ents[key] = merged[:10]
    ai['entities'] = ents
    return ai

def _try_groq(text: str, model: str, api_key: str) -> dict | None:
    """Try one Groq model with Native JSON Mode"""
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
            timeout=15,
            response_format={"type": "json_object"} # FORCES LLM TO RETURN PARSEABLE JSON
        )
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return None
    except Exception as e:
        if '429' in str(e) or 'rate' in str(e).lower():
            return 'RATE_LIMIT'
        return None

def analyze_text(text: str) -> dict:
    # 1. Instant local extraction
    spacy_result = _spacy_extract(text)

    # 2. Try each model + key combination
    for model in MODELS:
        for api_key in GROQ_KEYS:
            print(f'Attempting extraction with {model}...')
            result = _try_groq(text, model, api_key)

            if result == 'RATE_LIMIT':
                continue # Immediately jump to the next API key/model

            if result is not None:
                # Ensure all keys exist to prevent ValidationErrors in FastAPI
                ents = result.setdefault('entities', {})
                for k in ['names', 'dates', 'organizations', 'amounts']:
                    ents.setdefault(k, [])
                
                result.setdefault('summary', 'Summary extracted successfully.')
                
                # Force correct sentiment casing
                sent = result.get('sentiment', 'Neutral').capitalize()
                if sent not in ["Positive", "Negative", "Neutral"]: sent = "Neutral"
                result['sentiment'] = sent

                return _merge(result, spacy_result)

    # 3. Ultimate Fallback: All AI failed, return local processing only
    print('All APIs failed. Falling back to local NLP heuristics.')
    return {
        'summary': _generate_summary(text),
        'entities': spacy_result,
        'sentiment': _detect_sentiment(text)
    }

def _generate_summary(text: str) -> str:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 30]
    if len(sentences) >= 3: return '. '.join(sentences[:3]) + '.'
    elif sentences: return '. '.join(sentences) + '.'
    return 'Document processed successfully.'

def _detect_sentiment(text: str) -> str:
    text_lower = text.lower()
    positive = ['growth', 'success', 'improve', 'benefit', 'increase', 'opportunity', 'innovation', 'advance']
    negative = ['breach', 'attack', 'fail', 'loss', 'risk', 'threat', 'concern', 'damage', 'vulnerable', 'decline']

    pos = sum(1 for w in positive if w in text_lower)
    neg = sum(1 for w in negative if w in text_lower)

    if pos > neg: return 'Positive'
    elif neg > pos: return 'Negative'
    return 'Neutral'
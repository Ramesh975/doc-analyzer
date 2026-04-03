import os, json, re, time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_KEYS = [k for k in [
    os.getenv('GROQ_API_KEY'),
    os.getenv('GROQ_API_KEY_2'),
    os.getenv('GROQ_API_KEY_3'),
] if k]

MODELS = [
    'gemma2-9b-it',
    'llama-3.1-8b-instant',
    'llama-3.3-70b-versatile',
]

SYSTEM_PROMPT = '''You are a document analysis expert. Return ONLY valid JSON.

{
  "summary": "2-3 sentences describing what this document is about",
  "entities": {
    "names": ["full person names found"],
    "dates": ["all dates, years, months, time periods"],
    "organizations": ["all companies, institutions, agencies"],
    "amounts": ["all money, percentages, statistics"]
  },
  "sentiment": "Positive"
}

RULES:
names: Real people only. "John Smith", "Nina Lane"
dates: "2024", "March 2026", "next decade", "past few years"
organizations: "Google", "regional banks", "government agencies"
amounts: "$10,000", "35%", "thousands of records"
sentiment: Exactly Positive OR Negative OR Neutral
Return [] only if absolutely nothing of that type exists.
No markdown. Pure JSON only.'''


def _regex_extract(text: str) -> dict:
    """Pure regex extraction — no external libraries needed"""
    names, dates, organizations, amounts = [], [], [], []

    # Years
    for y in re.findall(r'\b(19|20)\d{2}\b', text):
        if y not in dates:
            dates.append(y)

    # Month + Year patterns
    months = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    for m in re.findall(rf'{months}\s+\d{{4}}', text):
        if m not in dates:
            dates.append(m)

    # Quarter patterns
    for q in re.findall(r'Q[1-4]\s*\d{4}', text):
        if q not in dates:
            dates.append(q)

    # Relative time
    for rt in re.findall(r'(?:past|last|next|coming)\s+(?:few\s+)?(?:years?|months?|decades?|weeks?)', text, re.IGNORECASE):
        rt = rt.strip()
        if rt not in dates:
            dates.append(rt)

    # Currency amounts
    for c in re.findall(r'[\$₹€£¥]\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion|thousand|crore|lakh))?', text):
        c = c.strip()
        if c not in amounts:
            amounts.append(c)

    # Percentages
    for p in re.findall(r'\b\d+\.?\d*\s*%', text):
        p = p.strip()
        if p not in amounts:
            amounts.append(p)

    # Large number phrases
    for n in re.findall(r'\d+\s*(?:million|billion|trillion|thousand)\s*(?:users|records|customers|people|dollars)?', text, re.IGNORECASE):
        n = n.strip()
        if n not in amounts:
            amounts.append(n)

    # Common org patterns
    org_patterns = [
        r'financial institutions?',
        r'regional banks?',
        r'government agenc(?:y|ies)',
        r'regulatory authorit(?:y|ies)',
        r'payment service providers?',
        r'tech(?:nology)? companies',
        r'private companies',
        r'universities',
        r'central banks?',
    ]
    for pattern in org_patterns:
        for m in re.findall(pattern, text, re.IGNORECASE):
            ms = m.strip().title()
            if ms not in organizations:
                organizations.append(ms)

    return {
        "names": names[:8],
        "dates": list(dict.fromkeys(dates))[:8],
        "organizations": list(dict.fromkeys(organizations))[:8],
        "amounts": list(dict.fromkeys(amounts))[:8]
    }


def _merge(ai: dict, regex: dict) -> dict:
    """AI takes priority, regex fills empty fields"""
    ents = ai.get('entities', {})
    for key in ['names', 'dates', 'organizations', 'amounts']:
        ai_list = ents.get(key, [])
        rx_list = regex.get(key, [])
        if not ai_list:
            ents[key] = rx_list
        else:
            merged = list(ai_list)
            for item in rx_list:
                if item not in merged:
                    merged.append(item)
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
            max_tokens=1000
        )
        raw = resp.choices[0].message.content
        clean = re.sub(r'```json|```', '', raw).strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        return None
    except Exception as e:
        if '429' in str(e) or 'rate' in str(e).lower():
            return 'RATE_LIMIT'
        return None


def analyze_text(text: str) -> dict:
    # Always run regex first — instant, no API needed
    regex_result = _regex_extract(text)
    print(f'Regex: dates={regex_result["dates"]} amounts={regex_result["amounts"]}')

    # Try each model + key combination
    for model in MODELS:
        for api_key in GROQ_KEYS:
            print(f'Trying {model}...')
            result = _try_groq(text, model, api_key)

            if result == 'RATE_LIMIT':
                print(f'Rate limit on {model} — next model')
                break  # try next model immediately

            if result is not None:
                if 'entities' not in result:
                    result['entities'] = {}
                result['entities'].setdefault('names', [])
                result['entities'].setdefault('dates', [])
                result['entities'].setdefault('organizations', [])
                result['entities'].setdefault('amounts', [])
                result.setdefault('summary', '')
                result.setdefault('sentiment', 'Neutral')

                # Merge regex to fill gaps AI missed
                final = _merge(result, regex_result)
                print(f'Done: {model}')
                return final

    # All AI failed — use regex + keyword fallback
    print('All AI failed - using regex only')
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


def _fallback():
    return {
        'summary': 'Unable to generate summary.',
        'entities': {'names': [], 'dates': [], 'organizations': [], 'amounts': []},
        'sentiment': 'Neutral'
    }
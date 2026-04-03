import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv('GROQ_API_KEY'))
SYSTEM_PROMPT = '''You are an expert document analysis assistant.
Analyze the provided text and respond ONLY with a valid JSON object.
No markdown fences, no preamble, no explanation — pure JSON only.

Required JSON schema:
{
  "summary": "2-3 sentence concise summary of the document content.",
  "entities": [
    {"text": "entity name", "type": "PERSON|ORG|DATE|MONEY|LOCATION|OTHER"}
  ],
  "sentiment": {
    "label": "positive|negative|neutral",
    "score": 0.95
  }
}

ENTITY EXTRACTION RULES — follow every rule strictly:

PERSON: ONLY real named individuals with actual names (e.g. "John Smith", "Nina Lane")
         NEVER use job titles like "analysts", "experts", "researchers" as PERSON
         Job titles without names = OTHER type

ORG: Every company, bank, agency, university, government body, institution
     Examples: "Google", "World Bank", "Harvard University", "FBI"

DATE: Every specific or relative time reference found in text
      Examples: "2024", "Q3 2023", "last year", "next decade",
                "March 2017", "five years ago", "by 2030"
      IMPORTANT: Search entire text for ANY year numbers like 2020, 2023, 2024

MONEY: Every financial figure, percentage, statistic, or numeric measure
       Examples: "$4.5 trillion", "35% growth", "200 million users",
                 "increased by 40%", "€50M funding"
       IMPORTANT: Percentages and statistics ARE money/numeric entities

LOCATION: Every country, city, region, address
          Examples: "United States", "New York", "Southeast Asia"

OTHER: Technologies, products, methodologies, events, technical terms
       Job titles without names go here

CRITICAL RULES:
1. NEVER tag generic job titles as PERSON — only real named people
2. ALWAYS extract year numbers as DATE entities
3. ALWAYS extract percentages and statistics as MONEY entities
4. Extract minimum 10 entities — search thoroughly
5. Never return empty entities list'''

def analyze_text(text: str) -> dict:
    truncated = text[:8000]
    try:
        print('Sending to Groq...')
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': f'Analyze this document:\n\n{truncated}'}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        raw = response.choices[0].message.content
        print(f'Raw response: {raw[:300]}')
        clean = re.sub(r'```json|```', '', raw).strip()
        result = json.loads(clean)
        print('SUCCESS')
        return result

    except json.JSONDecodeError as e:
        print(f'JSON parse error: {e}')
        return _fallback_response()
    except Exception as e:
        print(f'Groq error: {e}')
        raise RuntimeError(f'Groq API error: {e}')

def _fallback_response() -> dict:
    return {
        'summary': 'Unable to generate summary.',
        'entities': [],
        'sentiment': {'label': 'neutral', 'score': 0.5}
    }
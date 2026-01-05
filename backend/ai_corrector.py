"""
AI Corrector - Uses Amazon Bedrock to correct spelling, grammar, and factual accuracy.
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class AICorrector:
    """AI-powered text correction using Amazon Bedrock."""
    
    def __init__(self):
        self.provider = None
        self.bearer_token = os.getenv('AWS_BEARER_TOKEN_BEDROCK')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        
        if self.bearer_token:
            self.api_endpoint = f"https://bedrock-runtime.{self.region}.amazonaws.com"
            self.provider = 'bedrock'
            print(f"AI corrections enabled (region: {self.region})")
        else:
            print("AI not configured - set AWS_BEARER_TOKEN_BEDROCK")
    
    def is_available(self) -> bool:
        return self.provider is not None
    
    def get_provider(self) -> str:
        return self.provider or 'none'
    
    async def correct_text(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Correct text using AI for spelling, grammar, and factual accuracy."""
        text = extracted_data.get('text', '')
        
        if not text.strip():
            return {**extracted_data, 'text': '', 'changes': [], 'summary': 'No text to correct'}
        
        if self.provider == 'bedrock':
            return await self._bedrock_correct(text, extracted_data)
        
        return self._fallback_correct(text, extracted_data)
    
    def _get_prompt(self, text: str) -> str:
        return f"""You are an expert editor and fact-checker. Correct the following document for:

1. Spelling errors - fix all typos and misspellings
2. Grammar errors - fix grammar, punctuation, and sentence structure  
3. Factual errors - correct any incorrect facts, statistics, dates, or claims

Return the COMPLETE corrected text. Do not shorten or truncate.

Respond with JSON only:
{{
    "corrected_text": "complete corrected text here",
    "changes": [
        {{"type": "spelling|grammar|factual", "original": "...", "corrected": "...", "explanation": "..."}}
    ],
    "summary": "brief summary of corrections"
}}

Document:
---
{text}
---"""

    async def _bedrock_correct(self, text: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use Amazon Bedrock API for corrections."""
        prompt = self._get_prompt(text)
        
        models = [
            "amazon.nova-pro-v1:0",
            "amazon.nova-lite-v1:0",
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
        ]
        
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        for model_id in models:
            try:
                if model_id.startswith("amazon.nova"):
                    request_body = {
                        "messages": [{"role": "user", "content": [{"text": prompt}]}],
                        "inferenceConfig": {"maxTokens": 8000, "temperature": 0.2}
                    }
                else:
                    request_body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 8000,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2
                    }
                
                url = f"{self.api_endpoint}/model/{model_id}/invoke"
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        headers=headers,
                        json=request_body,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            
                            if model_id.startswith("amazon.nova"):
                                output = response_data.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
                            else:
                                output = response_data.get('content', [{}])[0].get('text', '')
                            
                            result = self._parse_json(output)
                            
                            return {
                                **extracted_data,
                                'text': result.get('corrected_text', text),
                                'changes': result.get('changes', []),
                                'summary': result.get('summary', 'Corrections applied'),
                                'original_structure': extracted_data,
                                'original_text': text
                            }
                        else:
                            error = await response.text()
                            print(f"{model_id}: {response.status} - {error[:100]}")
                            
            except Exception as e:
                print(f"{model_id} error: {e}")
                continue
        
        return self._fallback_correct(text, extracted_data)
    
    def _parse_json(self, text: str) -> dict:
        """Parse JSON from response."""
        import re
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return {}
    
    def _fallback_correct(self, text: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic spelling corrections when AI unavailable."""
        import re
        
        corrected = text
        changes = []
        
        corrections = {
            'teh': 'the', 'recieve': 'receive', 'seperate': 'separate',
            'occured': 'occurred', 'definately': 'definitely',
            'neccessary': 'necessary', 'goverment': 'government',
            'enviroment': 'environment', 'recomend': 'recommend',
            'untill': 'until', 'wich': 'which', 'becuase': 'because',
            'thier': 'their', 'patiant': 'patient', 'symtom': 'symptom',
            'treatement': 'treatment', 'desease': 'disease',
        }
        
        for wrong, right in corrections.items():
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
            for match in pattern.findall(corrected):
                replacement = right.capitalize() if match[0].isupper() else right
                corrected = pattern.sub(replacement, corrected, count=1)
                changes.append({
                    'type': 'spelling',
                    'original': match,
                    'corrected': replacement,
                    'explanation': 'Spelling correction'
                })
        
        return {
            **extracted_data,
            'text': corrected,
            'changes': changes,
            'summary': f'{len(changes)} basic corrections. Set AWS_BEARER_TOKEN_BEDROCK for full AI.',
            'original_structure': extracted_data,
            'original_text': text
        }

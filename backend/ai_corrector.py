"""
AI Corrector - Uses Amazon Nova (Bedrock) with Bearer Token authentication.
"""

import os
import json
import asyncio
import aiohttp
import base64
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class AICorrector:
    """AI-powered text correction using Amazon Nova via Bedrock API."""
    
    def __init__(self):
        self.provider = None
        self.bearer_token = None
        self.api_endpoint = None
        
        # Get the Bedrock bearer token
        bearer_token = os.getenv('AWS_BEARER_TOKEN_BEDROCK')
        region = os.getenv('AWS_REGION', 'us-east-1')
        
        if bearer_token:
            self.bearer_token = bearer_token
            self.api_endpoint = f"https://bedrock-runtime.{region}.amazonaws.com"
            self.provider = 'nova'
            print(f"✅ Using Amazon Nova with Bearer Token (region: {region})")
        else:
            print("⚠️ AWS_BEARER_TOKEN_BEDROCK not set. AI corrections unavailable.")
    
    def is_available(self) -> bool:
        return self.provider is not None
    
    def get_provider(self) -> str:
        return self.provider or 'none'
    
    async def correct_text(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        text = extracted_data.get('text', '')
        
        if not text.strip():
            return {**extracted_data, 'text': '', 'changes': [], 'summary': 'No text to correct'}
        
        if self.provider == 'nova':
            return await self._nova_correct(text, extracted_data)
        else:
            return self._fallback_correct(text, extracted_data)
    
    def _get_prompt(self, text: str) -> str:
        return f"""You are an expert medical editor, scientific fact-checker, and professional copy editor. 

Thoroughly correct the following document for:
1. ALL spelling errors and typos
2. ALL grammar issues (subject-verb agreement, tense, punctuation, sentence structure)
3. ALL medically/scientifically incorrect claims - fix wrong statistics, dates, names, drug info, anatomical errors
4. Make the text professional and publication-ready

IMPORTANT: Return the COMPLETE corrected text. Do not truncate.

Respond ONLY with valid JSON:
{{
    "corrected_text": "The COMPLETE corrected text with ALL paragraphs",
    "changes": [
        {{"type": "spelling|grammar|factual", "original": "...", "corrected": "...", "explanation": "..."}}
    ],
    "summary": "Brief summary of corrections"
}}

DOCUMENT TO CORRECT:
---
{text}
---

Return ONLY valid JSON, no markdown."""

    async def _nova_correct(self, text: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use Amazon Nova via Bedrock API with bearer token."""
        
        prompt = self._get_prompt(text)
        
        # Models to try
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
                # Construct request based on model type
                if model_id.startswith("amazon.nova"):
                    request_body = {
                        "messages": [
                            {"role": "user", "content": [{"text": prompt}]}
                        ],
                        "inferenceConfig": {
                            "maxTokens": 8000,  # Nova max is 10240
                            "temperature": 0.2
                        }
                    }
                else:
                    # Anthropic Claude format
                    request_body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 16000,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
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
                            
                            # Extract text based on model type
                            if model_id.startswith("amazon.nova"):
                                output_text = response_data.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
                            else:
                                output_text = response_data.get('content', [{}])[0].get('text', '')
                            
                            result = self._parse_json_response(output_text)
                            
                            print(f"✅ Successfully used {model_id}")
                            
                            return {
                                **extracted_data,
                                'text': result.get('corrected_text', text),
                                'changes': result.get('changes', []),
                                'summary': result.get('summary', 'Corrections applied via Amazon Nova'),
                                'original_structure': extracted_data,
                                'original_text': text
                            }
                        else:
                            error_text = await response.text()
                            print(f"Model {model_id} returned {response.status}: {error_text[:200]}")
                            
            except Exception as e:
                print(f"Model {model_id} failed: {e}")
                continue
        
        # All models failed, try fallback
        print("All Bedrock models failed, using fallback")
        return self._fallback_correct(text, extracted_data)
    
    def _parse_json_response(self, output_text: str) -> dict:
        """Parse JSON from AI response."""
        import re
        
        # Try direct parse
        try:
            return json.loads(output_text)
        except:
            pass
        
        # Try extracting from code blocks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output_text)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # Try finding JSON object
        match = re.search(r'\{[\s\S]*\}', output_text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        raise ValueError("Could not parse JSON")
    
    def _fallback_correct(self, text: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic fallback when AI unavailable."""
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
            'summary': f'Applied {len(changes)} basic corrections. ⚠️ Set AWS_BEARER_TOKEN_BEDROCK for full AI corrections.',
            'original_structure': extracted_data,
            'original_text': text
        }

"""User-configured OpenAI-compatible SSE transport."""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request


class APIError(RuntimeError):
    def __init__(self, message, retryable=True):
        super().__init__(message)
        self.retryable = retryable


def consume_sse(lines) -> dict:
    chunks, usage, model, finish = [], {}, None, None
    done = False
    for raw in lines:
        line = raw.decode('utf-8').strip() if isinstance(raw, bytes) else raw.strip()
        if not line.startswith('data:'): continue
        data = line[5:].strip()
        if data == '[DONE]':
            done = True
            break
        event = json.loads(data)
        if event.get('error') or (event.get('code') not in (None, 0) and 'choices' not in event):
            raise APIError('Upstream streaming error (response body withheld)')
        model = event.get('model') or model
        usage = event.get('usage') or usage
        choices = event.get('choices') or []
        if choices:
            choice = choices[0]
            delta = choice.get('delta') or {}
            content = delta.get('content')
            if isinstance(content, str): chunks.append(content)
            if choice.get('finish_reason'): finish = choice['finish_reason']
    if not done and finish is None:
        raise APIError('Incomplete SSE stream')
    return {'text': ''.join(chunks), 'usage': usage, 'response_model': model, 'finish_reason': finish}


def chat(messages: list, config: dict, max_tokens: int) -> dict:
    key = os.environ.get('API_KEY')
    if not key: raise APIError('Set API_KEY', retryable=False)
    extra = config['extra']
    reserved = {'model', 'messages', 'stream', 'max_tokens', 'temperature'}
    if reserved & extra.keys(): raise ValueError('API extra JSON cannot override transport/judging fields')
    payload = {**extra, 'model': config['model'], 'messages': messages, 'stream': True,
               'max_tokens': max_tokens, 'temperature': config['temperature']}
    req = urllib.request.Request(config['base_url'].rstrip('/') + '/chat/completions',
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}',
                 'Accept': 'text/event-stream', 'User-Agent': 'OmniVBench-RFIR/1'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=config['timeout']) as resp:
            return consume_sse(resp)
    except urllib.error.HTTPError as exc:
        # Never persist server bodies: proxies sometimes echo headers or submitted payloads.
        raise APIError(f'HTTP {exc.code}', retryable=exc.code in (408, 429, 500, 502, 503, 504)) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise APIError(f'Transport {type(exc).__name__}') from None

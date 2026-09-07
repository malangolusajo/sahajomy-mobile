"""Read-only verification of public/legal references. Never sends credentials or mutations."""
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Sahajomy-Mobile-App/Sahajomy-Mobile-App/mobile-redesign'
BASE = 'https://sahajomy.co.tz'


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=25) as response:
            return response.status, response.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode('utf-8', errors='replace')
    except (OSError, TimeoutError) as error:
        return None, str(error)


checks = []
for path in ['/', '/privacy', '/terms', '/api/v1/public/containers', '/api/v1/public/agizisha/agents', '/api/v1/public/agizisha/products', '/api/v1/public/platform-stats', '/api/v1/auth/me']:
    status, content = get(path)
    try:
        data = json.loads(content)
        shape = list(data.keys()) if isinstance(data, dict) else f'list[{len(data)}]' if isinstance(data, list) else type(data).__name__
    except ValueError:
        shape = 'HTML / non-JSON'
    checks.append({'method': 'GET', 'url': BASE + path, 'status': status, 'shape': shape, 'authentication': 'none'})
    print(path, status, shape, flush=True)
    if path == '/':
        scripts = re.findall(r'src="(/static/js/[^\"]+)"', content)
        for script in scripts:
            _, bundle = get(script)
            snippets = []
            for match in re.finditer(r'Privacy Policy|Terms of Service|Terms and Conditions|Terms & Conditions|By creating an account|By continuing|I agree', bundle):
                snippets.append(bundle[max(0, match.start()-150):match.end()+350])
            (OUT / 'legal-source-excerpts.txt').write_text('\n\n'.join(snippets), encoding='utf-8')
            print('Legal source excerpts:', len(snippets), flush=True)
(OUT / 'public-api-verification.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')

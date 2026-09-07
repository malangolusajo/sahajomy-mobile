"""Produce reproducible source inventories without importing or running the backend."""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'Sahajomy-Mobile-App/Sahajomy-Mobile-App'
BACKEND = PACK / 'backend-app-folder/app'
OUT = PACK / 'mobile-redesign'


def expression(node):
    return ast.unparse(node) if node else ''


def main():
    OUT.mkdir(exist_ok=True)
    endpoints = []
    models = []
    router_prefixes = {}
    router_edges = {}
    module_trees = {}
    for path in sorted(BACKEND.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        module = 'app.' + '.'.join(path.relative_to(BACKEND).with_suffix('').parts)
        module_trees[module] = tree
        prefixes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if expression(node.value.func).endswith('APIRouter'):
                    prefix = next((k.value.value for k in node.value.keywords
                                   if k.arg == 'prefix' and isinstance(k.value, ast.Constant)), '')
                    for target in node.targets:
                        prefixes[expression(target)] = prefix
                        router_prefixes[(module, expression(target))] = prefix
            if isinstance(node, ast.ClassDef):
                models.append({'name': node.name, 'source': str(path.relative_to(ROOT)),
                               'fields': [expression(n) for n in node.body if isinstance(n, ast.AnnAssign)]})
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                    continue
                method = dec.func.attr.upper()
                if method not in {'GET', 'POST', 'PATCH', 'PUT', 'DELETE'} or not dec.args:
                    continue
                if not isinstance(dec.args[0], ast.Constant):
                    continue
                router = expression(dec.func.value)
                route = prefixes.get(router, '') + dec.args[0].value
                endpoints.append({'method': method, 'path': '/api/v1' + route,
                                  'module': module, 'local_path': dec.args[0].value,
                                  'router': router, 'function': node.name,
                                  'signature': expression(node.args),
                                  'response_model': next((expression(k.value) for k in dec.keywords if k.arg == 'response_model'), 'Inline response; inspect handler'),
                                  'source': str(path.relative_to(ROOT)), 'line': node.lineno})
    # Resolve include_router recursively from the actual FastAPI application.
    for module, tree in module_trees.items():
        symbols = {}
        constants = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for name in node.names:
                    symbols[name.asname or name.name] = (node.module, name.name)
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for target in node.targets:
                    constants[expression(target)] = node.value.value
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != 'include_router' or not node.args:
                continue
            parent = (module, expression(node.func.value))
            child_name = expression(node.args[0])
            child = symbols.get(child_name, (module, child_name))
            prefix_node = next((k.value for k in node.keywords if k.arg == 'prefix'), None)
            prefix = prefix_node.value if isinstance(prefix_node, ast.Constant) else constants.get(expression(prefix_node), '')
            router_edges.setdefault(parent, []).append((child, prefix))
    registered = []
    def visit(router, prefix='', seen=frozenset()):
        if router in seen:
            return
        prefix += router_prefixes.get(router, '')
        for endpoint in endpoints:
            if (endpoint['module'], endpoint['router']) == router:
                registered.append({**endpoint, 'path': prefix + endpoint['local_path']})
        for child, extra in router_edges.get(router, []):
            visit(child, prefix + extra, seen | {router})
    visit(('app.main', 'app'))
    if registered:
        endpoints = registered
    dart = {p: p.read_text(encoding='utf-8-sig') for p in (ROOT / 'lib').rglob('*.dart')}
    calls = []
    for path, content in dart.items():
        for match in re.finditer(r"(?:client|_client|apiClient|_api|api)\.(getList|getObject|get|postForm|post|put|patch|delete)(?:<[^;\n]*?>)?\(\s*'([^']+)'", content):
            method = {'getList': 'GET', 'getObject': 'GET', 'postForm': 'POST'}.get(match[1], match[1].upper())
            route = re.sub(r'\$\{[^}]+\}|\$\w+', '{id}', match[2])
            normalized = re.sub(r'\{[^}]+\}', '{}', '/api/v1/' + route)
            matches = [e for e in endpoints if e['method'] == method and re.sub(r'\{[^}]+\}', '{}', e['path']) == normalized]
            calls.append({'method': method, 'path': match[2], 'source': str(path.relative_to(ROOT)),
                          'line': content[:match.start()].count('\n') + 1,
                          'status': 'SOURCE MATCH (not live verified)' if matches else 'REQUIRES REVIEW (router composition or stale route)',
                          'backend': matches})
        for match in re.finditer(r"endpoint: '([^']+)'", content):
            calls.append({'method': 'GET/POST (widget dependent)', 'path': match[1],
                          'source': str(path.relative_to(ROOT)), 'line': content[:match.start()].count('\n') + 1,
                          'status': 'REQUIRES WIDGET/SCHEMA REVIEW', 'backend': []})
    specs_text = (ROOT / 'lib/features/reference/presentation/native_screen_specs.dart').read_text(encoding='utf-8-sig')
    wrappers = (ROOT / 'lib/features/reference/presentation/dedicated_preview_pages.dart').read_text(encoding='utf-8-sig')
    aliases = (ROOT / 'lib/app/app_route_aliases.dart').read_text(encoding='utf-8-sig')
    screens = []
    for match in re.finditer(r"fileName: '([^']+)',\s*role: '([^']+)',\s*title: '([^']+)'", specs_text):
        filename, role, title = match.groups()
        mapped = re.search(re.escape("'" + filename + "'") + r'\s*=>\s*const (\w+)\(', wrappers)
        name = mapped[1] if mapped else ''
        cls = re.search(r'class ' + name + r' extends.*?(?=\nclass |\Z)', wrappers, re.S) if name else None
        body = cls[0] if cls else ''
        routes = re.findall(r"'([^']+)': '" + re.escape(filename) + "'", aliases)
        presentational = filename.startswith('public-') and any(k in filename for k in ['about', 'faq', 'privacy', 'terms', 'how-it', 'africa', 'pricing', 'contact'])
        category = 'C — PRESENTATIONAL' if presentational else ('D — PLACEHOLDER / FUTURE' if 'PreviewPageLayout' in body else 'B — PARTIALLY FUNCTIONAL / verification pending')
        screens.append({'screen': title, 'preview': filename, 'role': role,
                        'routes': routes, 'implementation': name, 'category': category,
                        'endpoint': re.findall(r"endpoint: '([^']+)'", body),
                        'source': 'lib/features/reference/presentation/dedicated_preview_pages.dart'})
    for path, content in dart.items():
        if '/presentation/' not in path.as_posix() or 'reference/presentation' in path.as_posix():
            continue
        for name in re.findall(r'class (\w+(?:Page|Shell)) extends', content):
            screens.append({'screen': name, 'source': str(path.relative_to(ROOT)),
                            'category': 'C — LOCKED' if name in {'SplashPage', 'OnboardingPage'} else 'B — PARTIALLY FUNCTIONAL / verification pending'})
    (OUT / 'api-inventory.json').write_text(json.dumps({'backend_routes': endpoints, 'models': models, 'flutter_calls': calls}, indent=2), encoding='utf-8')
    (OUT / 'screen-inventory.json').write_text(json.dumps(screens, indent=2), encoding='utf-8')
    lines = ['# Mobile screen inventory', '', 'Source-based inventory. Source matching is not live API verification. No screen is classified fully functional before request, response, state and permission checks.', '', '| Screen | Role | Classification | Routes / source |', '|---|---|---|---|']
    lines += [f"| {s['screen']} | {s.get('role', 'Native')} | {s['category']} | {', '.join(s.get('routes', [])) or s['source']} |" for s in screens]
    (OUT / 'SCREEN_INVENTORY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    lines = ['# Mobile API inventory', '', 'Full request signatures, declared response models, source lines and model fields are in `api-inventory.json`. Dependency expressions identify authentication/role guards; inline responses require handler inspection. Router composition must be reviewed when a source match is absent.', '', '| Method | Route | Flutter source | Verification |', '|---|---|---|---|']
    lines += [f"| {c['method']} | {c['path']} | {c['source']}:{c['line']} | {c['status']} |" for c in calls]
    (OUT / 'API_INVENTORY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    lock_path = OUT / 'locked-visual-baseline.json'
    if not lock_path.exists():
        locked = [ROOT / 'lib/features/onboarding/presentation/splash_page.dart', ROOT / 'lib/features/onboarding/presentation/onboarding_page.dart', *sorted((ROOT / 'assets/branding').glob('*'))]
        lock_path.write_text(json.dumps({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in locked if p.is_file()}, indent=2), encoding='utf-8')
    print(f'Inventoried {len(screens)} screen entries, {len(endpoints)} backend operations, {len(calls)} Flutter calls, {len(models)} model/schema classes.')
    if '--routes' in sys.argv:
        pattern = sys.argv[sys.argv.index('--routes') + 1]
        for endpoint in endpoints:
            if re.search(pattern, endpoint['path']):
                print(endpoint['method'], endpoint['path'], endpoint['signature'][:1000])


if __name__ == '__main__':
    main()

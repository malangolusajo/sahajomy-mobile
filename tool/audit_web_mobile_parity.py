"""Build a reproducible React -> FastAPI -> Flutter functionality matrix."""
from __future__ import annotations

import ast
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = Path(r"D:/Projects/sahajomy-platform/frontend/src")
BACKEND = ROOT / "Sahajomy-Mobile-App/Sahajomy-Mobile-App/backend-app-folder/app"
OUT = ROOT / "docs/parity"

METHODS = {"get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH", "delete": "DELETE"}


def clean_route(value: str) -> str:
    value = value.split("?", 1)[0]
    value = re.sub(r"\$\{[^}]+\}|:[A-Za-z][\w]*|\{[^}]+\}", "{id}", value)
    value = re.sub(r"/+", "/", value)
    return "/" + value.strip("/")


def route_key(value: str) -> str:
    normalized = clean_route(value)
    if normalized == "/api/v1":
        normalized = "/"
    elif normalized.startswith("/api/v1/"):
        normalized = normalized[len("/api/v1"):]
    return re.sub(r"\{[^}]+\}", "{}", normalized)


def route_matches(left: str, right: str) -> bool:
    a, b = route_key(left).strip("/").split("/"), route_key(right).strip("/").split("/")
    return len(a) == len(b) and all(x == y or x == "{}" or y == "{}" for x, y in zip(a, b))


def source_role(path: Path) -> str:
    parts = set(path.parts)
    if "sourcing_agent" in parts:
        return "Sourcing Agent"
    if "cargo_admin" in parts:
        return "Cargo Company"
    if "super_admin" in parts:
        return "Super Admin"
    if "customer" in parts:
        return "Customer"
    if "shared" in parts:
        return "Shared authenticated"
    return "Public / shared"


def string_expr(node: ast.AST | None, constants: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id, "")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return string_expr(node.left, constants) + string_expr(node.right, constants)
    return ""


def backend_inventory() -> list[dict]:
    trees: dict[str, ast.Module] = {}
    routers: dict[tuple[str, str], str] = {}
    aliases: dict[tuple[str, str], tuple[str, str]] = {}
    edges: dict[tuple[str, str], list[tuple[tuple[str, str], str]]] = defaultdict(list)
    declared: list[dict] = []
    for path in sorted(BACKEND.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = "app." + ".".join(path.relative_to(BACKEND).with_suffix("").parts)
        trees[module] = tree
        constants: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_module = node.module if node.module.startswith("app") else f"app.{node.module}"
                for item in node.names:
                    aliases[(module, item.asname or item.name)] = (imported_module, item.name)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            constants[target.id] = node.value.value
                        elif isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "APIRouter":
                            prefix = next((string_expr(k.value, constants) for k in node.value.keywords if k.arg == "prefix"), "")
                            routers[(module, target.id)] = prefix
                        elif isinstance(node.value, ast.Name):
                            aliases[(module, target.id)] = (module, node.value.id)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute) or not dec.args:
                    continue
                method = dec.func.attr.lower()
                local = string_expr(dec.args[0], constants)
                if method not in METHODS or not isinstance(dec.args[0], (ast.Constant, ast.Name, ast.BinOp)):
                    continue
                router_name = ast.unparse(dec.func.value)
                permissions = sorted(set(re.findall(r'require_permission\(["\']([^"\']+)', ast.unparse(node))))
                response = next((ast.unparse(k.value) for k in dec.keywords if k.arg == "response_model"), "inline")
                declared.append({
                    "method": METHODS[method], "local_path": local, "module": module,
                    "router": router_name, "handler": node.name,
                    "request": ast.unparse(node.args)[:800], "response": response,
                    "permissions": permissions,
                    "backend_source": str(path), "backend_line": node.lineno,
                })
    for module, tree in trees.items():
        imports: dict[str, tuple[str, str]] = {}
        constants: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_module = node.module if node.module.startswith("app") else f"app.{node.module}"
                for item in node.names:
                    imports[item.asname or item.name] = (imported_module, item.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        constants[target.id] = node.value.value
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "include_router" or not node.args:
                continue
            parent = (module, ast.unparse(node.func.value))
            child_expr = ast.unparse(node.args[0])
            if isinstance(node.args[0], ast.Attribute) and isinstance(node.args[0].value, ast.Name):
                base = imports.get(node.args[0].value.id)
                child = (base[0], node.args[0].attr) if base else (module, child_expr)
            else:
                child = imports.get(child_expr, (module, child_expr))
            extra = next((string_expr(k.value, constants) for k in node.keywords if k.arg == "prefix"), "")
            edges[parent].append((child, extra))

    def resolve(router: tuple[str, str]) -> tuple[str, str]:
        seen = set()
        while router in aliases and router not in seen:
            seen.add(router)
            router = aliases[router]
        return router

    registered: list[dict] = []
    def visit(router: tuple[str, str], inherited: str = "", seen=frozenset()):
        router = resolve(router)
        if router in seen:
            return
        prefix = inherited + routers.get(router, "")
        for endpoint in declared:
            if resolve((endpoint["module"], endpoint["router"])) == router:
                registered.append({**endpoint, "path": clean_route(prefix + endpoint["local_path"])})
        for child, extra in edges.get(router, []):
            visit(child, prefix + extra, seen | {router})

    visit(("app.main", "app"))
    return registered or [{**e, "path": clean_route(routers.get((e["module"], e["router"]), "") + e["local_path"])} for e in declared]


def react_routes() -> tuple[dict[str, dict], dict[str, list[str]]]:
    source = (WEB / "routes/AppRoutes.jsx").read_text(encoding="utf-8-sig")
    imports = {m[1]: m[2] for m in re.finditer(r"const\s+(\w+)\s*=\s*lazy\([\s\S]*?import\([\"'](\.\./pages/[^\"']+)[\"']\)[\s\S]*?\);", source)}
    imports.update({m[1]: m[2] for m in re.finditer(r"const\s+(\w+)\s*=\s*lazy\(\(\)\s*=>\s*import\([\"'](\.\./pages/[^\"']+)[\"']\)\);", source)})
    routes = {}
    by_file: dict[str, list[str]] = defaultdict(list)
    for match in re.finditer(r'<Route\s+path="([^"]+)"\s+element=\{<(\w+)', source):
        route, component = match.groups()
        imported = imports.get(component)
        if not imported:
            continue
        relative = imported.replace("../pages/", "pages/") + ".jsx"
        routes[route] = {"component": component, "frontend_file": relative}
        by_file[relative].append(route)
    return routes, by_file


def flutter_calls() -> tuple[list[dict], set[str]]:
    calls = []
    routes = set()
    for path in sorted((ROOT / "lib").rglob("*.dart")):
        source = path.read_text(encoding="utf-8-sig")
        for match in re.finditer(r"(?:client|_client|apiClient|_api|api)\.(getList|getObject|downloadBytes|downloadPublicBytes|get|postForm|post|put|patch|delete)(?:<[^\n;]*?>)?\(\s*['\"]([^'\"]+)", source):
            method = {
                "getList": "GET", "getObject": "GET", "downloadBytes": "GET",
                "downloadPublicBytes": "GET", "postForm": "POST",
            }.get(match[1], match[1].upper())
            calls.append({"method": method, "path": clean_route(match[2]), "source": str(path.relative_to(ROOT)), "line": source[:match.start()].count("\n") + 1})
        # Shared native workflow widgets receive their route as a constructor
        # value, so the repository call itself is intentionally dynamic.
        for widget, method in (("LiveWorkflowPage", "GET"), ("ApiFormPage", "POST")):
            pattern = rf"{widget}\([\s\S]*?endpoint:\s*['\"]([^'\"]+)['\"]"
            for match in re.finditer(pattern, source):
                calls.append({"method": method, "path": clean_route(match[1]), "source": str(path.relative_to(ROOT)), "line": source[:match.start()].count("\n") + 1})
        routes.update(re.findall(r"GoRoute\(\s*path:\s*['\"]([^'\"]+)", source))
    return calls, routes


def web_calls(by_file: dict[str, list[str]], backend: list[dict], mobile_calls: list[dict], mobile_routes: set[str]) -> list[dict]:
    rows = []
    call_pattern = re.compile(r"api\.(get|post|put|patch|delete)\(\s*([`\"'])(.+?)\2", re.S)
    for path in sorted(WEB.rglob("*.jsx")):
        relative = str(path.relative_to(WEB)).replace("\\", "/")
        source = path.read_text(encoding="utf-8-sig")
        routes = by_file.get(relative, [])
        actions = sorted(set(re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<button\b[^>]*>([\s\S]*?)</button>", source) if "{" not in x and re.sub(r"<[^>]+>", "", x).strip()))
        matches = list(call_pattern.finditer(source))
        if not matches and routes:
            rows.append({
                "web_page_component": path.stem, "role": source_role(path), "function": "Present page content / navigation",
                "web_route": " | ".join(routes), "frontend_file": relative, "api_service_used": "none",
                "backend_endpoint": "none", "http_method": "none", "request": "none", "response": "none",
                "permissions": "public or route guard", "current_mobile_equivalent": "route" if any(clean_route(r) in mobile_routes for r in routes) else "none",
                "mobile_status": "partially implemented" if any(clean_route(r) in mobile_routes for r in routes) else "missing",
                "required_mobile_screen_action": "Mobile page and all navigation actions",
                "web_actions": " | ".join(actions), "api_ui_mismatch": "",
            })
        for match in matches:
            method = METHODS[match[1]]
            raw = match[3].replace("${encodeURIComponent(normalizedTracking)}", "{id}")
            endpoint_path = clean_route(raw)
            handlers = [item for item in backend if item["method"] == method and route_matches(item["path"], endpoint_path)]
            handler = handlers[0] if handlers else None
            exact_mobile = any(item["method"] == method and route_matches(item["path"], endpoint_path) for item in mobile_calls)
            page_route = any(clean_route(route) in mobile_routes for route in routes)
            if exact_mobile and page_route:
                status = "partially implemented"
                equivalent = "API call and route exist; interaction/state parity requires verification"
            elif exact_mobile:
                status = "partially implemented"
                equivalent = "API call exists without verified page/action parity"
            else:
                status = "missing"
                equivalent = "none found"
            preceding = source[max(0, match.start() - 500):match.start()]
            fn = re.findall(r"(?:const\s+([\w]+)\s*=|function\s+([\w]+))", preceding)
            function_name = next((part for pair in fn[-1:] for part in pair if part), "")
            rows.append({
                "web_page_component": path.stem, "role": source_role(path),
                "function": function_name or f"{method} {endpoint_path}",
                "web_route": " | ".join(routes) or "component/subflow",
                "frontend_file": relative, "api_service_used": "services/api.js",
                "backend_endpoint": endpoint_path, "http_method": method,
                "request": handler["request"] if handler else source[match.start():match.end() + 220].replace("\n", " ")[:500],
                "response": handler["response"] if handler else "No registered backend handler matched",
                "permissions": ", ".join(handler["permissions"]) if handler and handler["permissions"] else ("FastAPI authenticated/role dependency; inspect handler" if handler else "unmatched"),
                "current_mobile_equivalent": equivalent, "mobile_status": status,
                "required_mobile_screen_action": f"Expose {function_name or method.lower()} in the mobile {path.stem} flow",
                "web_actions": " | ".join(actions),
                "api_ui_mismatch": "" if handler else "Web call did not match a registered FastAPI operation; review stale path/router composition",
                "backend_source": f'{handler["backend_source"]}:{handler["backend_line"]}' if handler else "",
            })
    return rows


def main():
    if not WEB.exists() or not BACKEND.exists():
        raise SystemExit("Expected React and FastAPI projects under D:/Projects/sahajomy-platform")
    OUT.mkdir(parents=True, exist_ok=True)
    backend = backend_inventory()
    routes, by_file = react_routes()
    mobile_calls, mobile_routes = flutter_calls()
    rows = web_calls(by_file, backend, mobile_calls, mobile_routes)
    fields = [
        "web_page_component", "role", "function", "web_route", "frontend_file", "api_service_used",
        "backend_endpoint", "http_method", "request", "response", "permissions", "current_mobile_equivalent",
        "mobile_status", "required_mobile_screen_action", "web_actions", "api_ui_mismatch", "backend_source",
    ]
    with (OUT / "web-mobile-functionality-matrix.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    (OUT / "web-mobile-functionality-matrix.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    counts = defaultdict(lambda: defaultdict(int))
    for row in rows:
        counts[row["role"]][row["mobile_status"]] += 1
    lines = [
        "# Web → mobile functionality matrix", "",
        "Generated by `tool/audit_web_mobile_parity.py`. Each row is a source-level React page/API action matched to the registered FastAPI graph and Flutter literals. A route or API literal is not proof of complete UX, so unverified matches remain partially implemented.", "",
        f"- React routes inventoried: {len(routes)}", f"- Web page/API rows: {len(rows)}",
        f"- Registered FastAPI operations resolved: {len(backend)}", f"- Flutter API call sites: {len(mobile_calls)}", "",
        "| Role | Already implemented | Partially implemented | Missing |", "|---|---:|---:|---:|",
    ]
    for role in sorted(counts):
        lines.append(f'| {role} | {counts[role]["already implemented"]} | {counts[role]["partially implemented"]} | {counts[role]["missing"]} |')
    lines += ["", "The CSV/JSON are the authoritative row-level inventory, including frontend file, web route, action, API, method, backend signature/response, permissions, current mobile equivalent, status, required action, mismatch, and backend source.", ""]
    (OUT / "FUNCTIONAL_PARITY_MATRIX.md").write_text("\n".join(lines), encoding="utf-8")
    unmatched = [r for r in rows if r["api_ui_mismatch"]]
    (OUT / "web-api-mismatches.json").write_text(json.dumps(unmatched, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows from {len(routes)} React routes; {len(backend)} registered backend operations; {len(unmatched)} unmatched web calls.")


if __name__ == "__main__":
    main()

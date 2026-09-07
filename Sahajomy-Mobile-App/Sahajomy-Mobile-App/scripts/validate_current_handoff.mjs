import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const mobileRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(mobileRoot, "..");
const routeSource = readFileSync(
  resolve(repositoryRoot, "frontend/src/routes/AppRoutes.jsx"),
  "utf8"
);
const inventoryPath = resolve(mobileRoot, "GENERATED_SCREEN_INVENTORY.md");
const inventory = readFileSync(inventoryPath, "utf8");
const previewRoot = resolve(mobileRoot, "html-previews");
const errors = [];

const routePattern = /<Route\s+path="([^"]+)"/g;
const currentRoutes = [];
for (const match of routeSource.matchAll(routePattern)) {
  const route = match[1];
  if (route === "*") continue;
  const nearby = routeSource.slice(match.index, match.index + 360);
  if (nearby.includes("<Navigate ")) continue;
  currentRoutes.push(route);
}

for (const route of currentRoutes) {
  if (!inventory.includes(`\`${route}\``)) {
    errors.push(`Current non-redirect route is missing from inventory: ${route}`);
  }
}

const previewLinks = [
  ...inventory.matchAll(/\]\(html-previews\/([^\)]+\.html)\)/g),
].map((match) => match[1]);
for (const preview of previewLinks) {
  if (!existsSync(resolve(previewRoot, preview))) {
    errors.push(`Inventory preview does not exist: ${preview}`);
  }
}

const previews = readdirSync(previewRoot).filter((name) => name.endsWith(".html"));
if (previews.length !== 120) {
  errors.push(`Expected 120 HTML previews, found ${previews.length}`);
}

const openapi = JSON.parse(
  readFileSync(resolve(repositoryRoot, "docs/flutter-handoff/openapi.json"), "utf8")
);
const operations = Object.values(openapi.paths || {}).reduce(
  (count, path) =>
    count +
    Object.keys(path).filter((method) =>
      ["get", "post", "put", "patch", "delete"].includes(method.toLowerCase())
    ).length,
  0
);
const schemas = Object.keys(openapi.components?.schemas || {}).length;
if (Object.keys(openapi.paths || {}).length !== 342 || operations !== 389 || schemas !== 163) {
  errors.push(
    `OpenAPI snapshot mismatch: ${Object.keys(openapi.paths || {}).length} paths, ${operations} operations, ${schemas} schemas`
  );
}

JSON.parse(
  readFileSync(resolve(repositoryRoot, "docs/flutter-handoff/design_tokens.json"), "utf8")
);

if (errors.length) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(
    `Handoff valid: ${new Set(currentRoutes).size} current routes, ${previews.length} previews, ${operations} API operations.`
  );
}

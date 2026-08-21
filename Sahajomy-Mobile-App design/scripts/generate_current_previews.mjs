import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "html-previews");
mkdirSync(output, { recursive: true });

const screens = [];
const add = (file, route, role, title, summary, primary, items) => screens.push({ file, route, role, title, summary, primary, items });

add("public-landing", "/", "Public", "Source, ship, and track", "One place for sourcing, sea cargo, air cargo, and shipment visibility.", "Explore Sahajomy", ["Agizisha marketplace", "Container shipping", "Express Air Cargo"]);
add("public-agizisha-catalogue", "/agizisha", "Public", "Agizisha marketplace", "Browse live products from verified sourcing agents.", "Search products", ["Featured products", "Verified agent storefronts", "Filter by category"]);
add("public-agizisha-product-detail", "/agizisha/product/:id", "Public", "Product details", "Review photos, options, MOQ, agent details, and order terms.", "Request this product", ["Product gallery and options", "Pricing and minimum order", "Verified sourcing agent"]);
add("public-agizisha-agent-storefront", "/agizisha/agents/:handle", "Public", "Agent storefront", "Browse a verified sourcing agent's public profile and live products.", "View available products", ["Verified profile", "Sourcing specialties", "Published products"]);
add("public-shared-batch", "/shared/:token", "Public", "Shared sourcing batch", "Open a secure shared batch and review products currently accepting orders.", "View batch products", ["Batch deadline", "Available products", "Order status guidance"]);
add("public-receipt-verification", "/verify-receipt", "Public", "Verify a receipt", "Check whether a Sahajomy receipt is genuine using its secure reference.", "Verify receipt", ["Enter verification reference", "Issuer and customer summary", "Verified or invalid result"]);

const staticPages = [
  ["public-privacy", "/privacy", "Privacy policy", "How Sahajomy collects, protects, and uses account and shipment data."],
  ["public-terms", "/terms", "Terms of service", "The current terms governing Sahajomy accounts and logistics services."],
  ["public-contact", "/contact", "Contact Sahajomy", "Reach support for account, sourcing, booking, or shipment questions."],
  ["public-about", "/about", "About Sahajomy", "Learn how Sahajomy connects customers, agents, and cargo operators."],
  ["public-how-it-works", "/how-it-works", "How it works", "Follow the journey from product sourcing or booking to delivery."],
  ["public-pricing", "/pricing", "Pricing", "Understand service pricing and when final operator rates apply."],
  ["public-faq", "/faq", "Frequently asked questions", "Answers about accounts, bookings, payment, tracking, and collection."],
  ["public-warehouses", "/warehouses", "Warehouses", "Explore available forwarding and cargo warehouse locations."],
  ["public-warehouse-detail", "/warehouses/:warehouseSlug", "Warehouse details", "Review location, supported cargo modes, and contact information."],
  ["public-support", "/support", "Support centre", "Find help articles and the right path for a service issue."],
  ["public-support-tickets", "/support/tickets", "Support tickets", "Review or start a support request for an unresolved issue."],
  ["public-feedback", "/feedback", "Share feedback", "Tell Sahajomy what worked and what needs improvement."],
  ["public-cookies", "/cookies", "Cookie information", "Review how browser storage supports secure web sessions."],
  ["public-accessibility", "/accessibility", "Accessibility", "Read Sahajomy's accessible-product commitments and support options."],
  ["public-legal", "/legal", "Legal information", "Find the current legal notices and service policies."],
  ["public-sitemap", "/sitemap", "Sitemap", "Browse public Sahajomy destinations by service."],
  ["public-air-cargo", "/air-cargo", "Express Air Cargo", "Learn about air cargo routes, service expectations, and booking."],
];
for (const [file, route, title, summary] of staticPages) add(file, route, "Public", title, summary, "Continue", ["Current information", "Related service guidance", "Contact and support"]);

add("public-containers", "/public/containers", "Public", "Available containers", "Browse open container capacity before signing in to reserve.", "Browse routes", ["Origin and destination", "Available CBM", "Departure schedule"]);
add("public-fcl-quote-request", "/fcl-quote-request", "Public", "Request an FCL quote", "Send full-container requirements to a Cargo Admin for review.", "Submit quote request", ["Route and container size", "Cargo description", "Contact details and consent"]);
add("public-sourcing-agent-registration", "/sourcing-agent/register", "Public", "Become a sourcing agent", "Apply to join Sahajomy as a sourcing operator.", "Start application", ["Identity and contact", "Sourcing experience", "Approval and verification"]);
add("shared-air-shipping-label", "/label/air/:bookingId", "Shared", "Air shipping label", "Display the authoritative Express Air Cargo label for this booking.", "Share or download label", ["Tracking and airway bill", "Warehouse and recipient", "Booking reference"]);
add("shared-sea-shipping-label", "/label/sea/:reservationId", "Shared", "Sea shipping label", "Display the authoritative container-reservation shipping label.", "Share or download label", ["Shipping mark", "Container route", "Customer destination"]);
add("shared-product-detail", "/product/:productId", "Shared", "Sourcing product", "Open a role-safe product detail from a batch or notification.", "Open product action", ["Product media", "Options and order terms", "Batch and agent context"]);

add("customer-reservations", "/customer/reservations", "Customer", "My reservations", "Review active and historical container-space reservations.", "Find container space", ["Pending reservation", "Confirmed and paid", "Arrival and collection state"]);
add("customer-reservation-detail", "/customer/reservations/:reservationId", "Customer", "Reservation details", "Review route, CBM, payment, goods state, documents, and tracking.", "Open shipping label", ["Reservation summary", "Payment and collection", "Packing list and documents"]);
add("customer-shipment-order-detail", "/customer/shipment-orders/:shipmentOrderId", "Customer", "Shipment order", "Follow operational stages and references for this shipment order.", "Track shipment", ["Current operational stage", "Carrier and tracking", "Timeline and remarks"]);
add("customer-agizisha", "/customer/agizisha", "Customer", "Agizisha", "Browse the public catalogue inside the authenticated customer shell.", "Browse products", ["Recommended products", "Verified agents", "My sourcing requests"]);
add("customer-express-air-cargo", "/customer/express-air-cargo", "Customer", "Express Air Cargo", "Book air cargo, upload cargo photos, and review existing bookings.", "Book air cargo", ["Service and warehouse", "Weight and goods type", "Bookings and labels"]);
add("customer-china-addresses", "/customer/china-addresses", "Customer", "My China addresses", "Save reusable forwarding addresses for sea and air bookings.", "Add China address", ["Default forwarding address", "Shipping and billing use", "Edit or deactivate"]);

add("agent-pending-approval", "/agent/pending-approval", "Sourcing Agent", "Approval pending", "Track verification before accessing approved agent operations.", "Refresh approval", ["Application received", "Verification in progress", "Support contact"]);
add("agent-agizisha-orders", "/agent/agizisha-orders", "Sourcing Agent", "Agizisha orders", "Review public product requests and move each customer enquiry forward.", "Open newest request", ["New product request", "Customer contact", "Request status"]);
add("agent-storefront", "/agent/agizisha-storefront", "Sourcing Agent", "Public storefront", "Manage the verified profile customers see in Agizisha.", "Save storefront", ["Public introduction", "Specialties and contact", "Published product preview"]);
add("agent-batches", "/agent/batches", "Sourcing Agent", "Sourcing batches", "Manage open and closed customer sourcing batches.", "Create batch", ["Open batch", "Order count and deadline", "Closed batch history"]);
add("agent-batch-financials", "/agent/batches/:batchId/financials", "Sourcing Agent", "Batch financials", "Review customer totals, payment states, fees, and documents for one batch.", "Open documents", ["Revenue summary", "Customer payment status", "Invoices and receipts"]);
add("agent-order-detail", "/agent/orders/:orderId", "Sourcing Agent", "Order details", "Review product selections, customer details, payment, and fulfilment state.", "Update order", ["Customer and product", "Quantity and options", "Payment and documents"]);
add("agent-create-packing-list", "/agent/batches/:batchId/packing-lists/new", "Sourcing Agent", "Create packing list", "Build a packing list from confirmed batch orders.", "Generate packing list", ["Select orders", "Cartons and weights", "Review before generation"]);
add("agent-packing-lists", "/agent/packing-lists", "Sourcing Agent", "Packing lists", "Review generated sourcing documents and export status.", "Open latest list", ["Draft documents", "Finalized lists", "PDF and Excel exports"]);
add("agent-packing-list-detail", "/agent/packing-lists/:packingListId", "Sourcing Agent", "Packing list details", "Review items, totals, customer references, and available exports.", "Download PDF", ["Document summary", "Item rows", "Totals and exports"]);
add("agent-express-air-cargo", "/agent/express-air-cargo", "Sourcing Agent", "Express Air Cargo", "Book air cargo for sourced goods and manage labels.", "Create air booking", ["Warehouse address", "Cargo and customer", "Booking status and label"]);
add("agent-financials", "/agent/financials", "Sourcing Agent", "Financials", "Review receipts, invoices, open documents, and payment status.", "Open documents", ["Revenue and payment", "Receipts", "Invoices"]);
add("agent-containers", "/agent/containers", "Sourcing Agent", "Book container space", "Browse available routes and reserve CBM for agent cargo.", "Find container", ["Available routes", "Capacity and price", "Reserve for batch or direct cargo"]);
add("agent-container-detail", "/agent/containers/:containerId", "Sourcing Agent", "Container details", "Review route, capacity, schedule, and reservation action.", "Reserve CBM", ["Route and schedule", "Available capacity", "Price and currency"]);
add("agent-reservations", "/agent/reservations", "Sourcing Agent", "My reservations", "Track container reservations, payment, documents, and goods state.", "Open reservation", ["Pending payment", "Confirmed reservation", "Arrival and collection"]);
add("agent-track-shipment", "/agent/track-shipments", "Sourcing Agent", "Track shipments", "Search sourcing, sea, and air references in one operational view.", "Track reference", ["Enter tracking number", "Current stage", "Movement timeline"]);

add("cargo-admin-warehouses", "/cargo/warehouses", "Cargo Admin", "Manage warehouses", "Create and maintain forwarding warehouses and supported cargo modes.", "Create warehouse", ["Warehouse address", "Sea, air, or both", "Contact and coordinates"]);
add("cargo-admin-reservations", "/cargo/reservations", "Cargo Admin", "Reservations", "Manage payment, holds, release, documents, and collection.", "Open next action", ["Pending reservations", "Payment confirmation", "Hold, release, and collect"]);
add("cargo-admin-receipts", "/cargo/receipts", "Cargo Admin", "Receipts and invoices", "Search financial documents and download authoritative PDFs.", "Search documents", ["Recent receipts", "Invoices by reservation", "Void and share controls"]);
add("cargo-admin-documentation-workspace", "/cargo/documentationworkspace", "Cargo Admin", "Cargo documentation", "One workspace for packing lists, manual intake, and customer records.", "Open packing lists", ["Customs packing lists", "Manual cargo intake", "Cargo customers"]);
add("cargo-admin-manual-intake", "/cargo/documentationworkspace/manual-cargo-intake", "Cargo Admin", "Manual cargo intake", "Register warehouse goods without a prior booking. This remains available in every automation mode.", "New cargo intake", ["Customer and warehouse", "Goods, cartons, dimensions", "Rates, receipt, and packing list"]);
add("cargo-admin-express-air-cargo", "/cargo/express-air-cargo", "Cargo Admin", "Express Air Cargo", "Manage schedules, assigned bookings, labels, and operational status.", "Publish departure", ["Departure schedules", "Customer bookings", "Labels and status"]);

add("super-admin-sourcing-agents", "/admin/sourcing-agents", "Super Admin", "Sourcing agents", "Review agent profiles, approvals, status, and storefront readiness.", "Review agents", ["Pending verification", "Approved agents", "Suspended or incomplete"]);
add("super-admin-operators", "/admin/operators", "Super Admin", "Operators", "Review Cargo Admin and operational account access.", "Open operator", ["Cargo Admin accounts", "Verification and status", "Role and access controls"]);
add("super-admin-goods-classification", "/admin/goods", "Super Admin", "Goods classification", "Manage categories, goods types, and dynamic attribute templates.", "Add goods type", ["Categories", "Goods types", "Attribute templates"]);
add("super-admin-reservations", "/admin/reservations", "Super Admin", "Platform reservations", "Audit reservations across operators without bypassing operational ownership.", "Search reservations", ["Customer and operator", "Payment state", "Goods and collection state"]);
add("super-admin-commission", "/admin/commission", "Super Admin", "Commission settings", "Review current commission configuration and immutable history.", "Update commission", ["Current rate", "Effective configuration", "Change history"]);
add("super-admin-track-shipment", "/admin/track-shipments", "Super Admin", "Track shipments", "Search platform shipment references for support and governance.", "Track reference", ["Search all modes", "Current status", "Operator and timeline"]);

const navByRole = {
  Public: ["Home", "Services", "Agizisha", "Sign in"],
  Shared: ["Back", "Details", "Share", "More"],
  Customer: ["Home", "Shipments", "Agizisha", "More"],
  "Cargo Admin": ["Home", "Operations", "Documents", "More"],
  "Sourcing Agent": ["Home", "Batches", "Orders", "More"],
  "Super Admin": ["Home", "Users", "Activity", "More"],
};

const existingRouteMappings = [
  ["Public", "/login", "customer-login.html", "Registration and OTP states are also previewed by customer-register.html and customer-otp.html."],
  ["Customer", "/customer/dashboard", "customer-dashboard.html", ""],
  ["Customer", "/customer/containers", "customer-search-container.html", "Container detail, reservation, and confirmation have supplementary previews."],
  ["Customer", "/customer/orders", "customer-orders.html", ""],
  ["Customer", "/customer/orders/:orderId", "customer-order-details.html", ""],
  ["Customer", "/customer/track-shipments", "customer-shipment-tracking.html", ""],
  ["Customer", "/customer/warehouse-access/:token", "customer-warehouse-parcels.html", "Collection-code state is previewed separately."],
  ["Sourcing Agent", "/agent/dashboard", "agent-dashboard.html", ""],
  ["Sourcing Agent", "/agent/batches/new", "agent-create-batch.html", ""],
  ["Sourcing Agent", "/agent/batches/:batchId", "agent-batch-details.html", "Product and order-generation actions have supplementary previews."],
  ["Cargo Admin", "/cargo/dashboard", "cargo-admin-dashboard.html", ""],
  ["Cargo Admin", "/cargo/containers", "cargo-admin-container-management.html", ""],
  ["Cargo Admin", "/cargo/containers/new", "cargo-admin-container-management.html", "This route opens the create state of the same container-management screen."],
  ["Cargo Admin", "/cargo/documentationworkspace/packing-lists", "cargo-admin-packing-lists.html", "Legacy packing-list URLs redirect here."],
  ["Cargo Admin", "/cargo/documentationworkspace/customers", "cargo-admin-customer-management.html", "The legacy customer URL redirects here."],
  ["Cargo Admin", "/cargo/shipment-orders", "cargo-admin-shipment-orders.html", ""],
  ["Cargo Admin", "/cargo/fcl-requests", "cargo-admin-fcl-requests.html", ""],
  ["Cargo Admin", "/cargo/track-shipments", "cargo-admin-track-shipment.html", ""],
  ["Cargo Admin", "/cargo/warehouse-automation", "cargo-admin-warehouse-automation.html", ""],
  ["Super Admin", "/admin/dashboard", "super-admin-dashboard.html", ""],
  ["Super Admin", "/admin/users", "super-admin-user-management.html", ""],
  ["Super Admin", "/admin/users/:userId", "super-admin-user-details.html", ""],
  ["Super Admin", "/admin/pending-approvals", "super-admin-approvals.html", ""],
  ["Super Admin", "/admin/audit-logs", "super-admin-platform-activity.html", ""],
  ["Super Admin", "/admin/warehouse-automation", "super-admin-warehouse-automation.html", ""],
];

const esc = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const render = (screen) => {
  const nav = navByRole[screen.role] || navByRole.Public;
  const rows = screen.items.map((item, index) => `<button class="row" onclick="toast('${esc(item)}')"><span class="rowIcon">${index + 1}</span><span><b>${esc(item)}</b><small>Open the current ${esc(screen.title.toLowerCase())} flow.</small></span><i>›</i></button>`).join("");
  return `<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sahajomy · ${esc(screen.role)} · ${esc(screen.title)}</title><style>
*{box-sizing:border-box}body{margin:0;background:#e2e8f0;color:#0f172a;font-family:Inter,ui-sans-serif,system-ui,sans-serif}.phone{position:relative;width:min(100%,393px);height:min(100dvh,852px);overflow:hidden;background:#f7f8fa}.top{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 20px;border-bottom:1px solid #e2e8f0;background:#fff}.back,.bell{border:0;background:none;color:#0f3d5e;font-size:22px}.context{text-align:center}.context small{display:block;color:#ff6b4a;font-size:10px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.context b{font-size:14px;color:#0f3d5e}.content{height:calc(100% - 136px);overflow:auto;padding:22px 20px 32px}.route{font:11px ui-monospace,monospace;color:#64748b;overflow-wrap:anywhere}.content h1{margin:8px 0 4px;color:#0f3d5e;font-size:26px;line-height:1.15}.summary{margin:0 0 22px;color:#64748b;font-size:14px;line-height:1.5}.list{border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;background:#fff}.row{width:100%;min-height:72px;display:flex;align-items:center;gap:12px;border:0;border-bottom:1px solid #e2e8f0;background:#fff;padding:12px;text-align:left;color:#0f172a}.row:last-child{border-bottom:0}.rowIcon{width:30px;height:30px;display:grid;place-items:center;flex:none;background:#fff2ee;color:#e85a3a;font-size:12px;font-weight:800}.row span:nth-child(2){flex:1}.row b{display:block;font-size:14px}.row small{display:block;margin-top:4px;color:#64748b;line-height:1.35}.row i{color:#94a3b8;font-size:20px}.primary{width:100%;min-height:52px;margin-top:18px;border:0;border-radius:12px;background:#ff6b4a;color:#fff;font-weight:800}.states{margin-top:18px;border:1px dashed #cbd5e1;background:#fff;padding:12px}.states b{display:block;color:#94a3b8;font-size:10px;letter-spacing:.12em;text-transform:uppercase}.states button{margin:8px 4px 0 0;border:0;background:#f1f5f9;padding:7px 9px;font-size:11px;font-weight:700}.nav{position:absolute;inset:auto 0 0;height:72px;display:flex;justify-content:space-around;border-top:1px solid #e2e8f0;background:#fff;padding:9px 8px 16px}.nav button{min-width:62px;border:0;background:none;color:#94a3b8;font-size:10px}.nav button:first-child{color:#ff6b4a;font-weight:800}.nav span{display:block;font-size:17px}.overlay{position:fixed;inset:0;display:none;place-items:center;background:#0f172a66;padding:20px}.overlay.open{display:grid}.dialog{width:min(100%,320px);background:#fff;padding:24px;text-align:center}.dialog h2{margin:0;color:#0f3d5e}.dialog p{color:#64748b;font-size:14px;line-height:1.5}.dialog button{width:100%;border:0;background:#0f3d5e;color:#fff;padding:12px;font-weight:800}.toast{position:fixed;left:50%;bottom:18px;display:none;transform:translateX(-50%);border-radius:99px;background:#0f172a;color:#fff;padding:9px 14px;font-size:12px;white-space:nowrap}@media(min-width:500px){.phone{height:852px;margin:24px auto;border:10px solid #0f172a;border-radius:38px;box-shadow:0 25px 70px #0f172a55}}
</style></head><body><main class="phone"><header class="top"><button class="back" onclick="toast('Back navigation preview')">‹</button><div class="context"><small>${esc(screen.role)}</small><b>${esc(screen.title)}</b></div><button class="bell" onclick="toast('Notifications preview')">♧</button></header><section class="content"><div class="route">${esc(screen.route)}</div><h1>${esc(screen.title)}</h1><p class="summary">${esc(screen.summary)}</p><div class="list">${rows}</div><button class="primary" onclick="toast('${esc(screen.primary)}')">${esc(screen.primary)}</button><div class="states"><b>Prototype states</b><button onclick="showState('loading')">Loading</button><button onclick="showState('empty')">Empty</button><button onclick="showState('error')">Error</button></div></section><nav class="nav">${nav.map((item, index) => `<button><span>${["⌂", "▦", "≡", "•••"][index]}</span>${esc(item)}</button>`).join("")}</nav></main><div id="overlay" class="overlay"><div class="dialog"><h2 id="stateTitle"></h2><p id="stateText"></p><button onclick="closeState()">Return to screen</button></div></div><div id="toast" class="toast"></div><script>function toast(message){const node=document.getElementById('toast');node.textContent=message;node.style.display='block';setTimeout(()=>node.style.display='none',1600)}function showState(kind){const states={loading:['Loading','Fetching the latest authoritative Sahajomy information.'],empty:['Nothing here yet','This screen has no current records.'],error:['Something went wrong','Check the connection and retry without duplicating the action.']};document.getElementById('stateTitle').textContent=states[kind][0];document.getElementById('stateText').textContent=states[kind][1];document.getElementById('overlay').classList.add('open')}function closeState(){document.getElementById('overlay').classList.remove('open')}</script></body></html>`;
};

for (const screen of screens) writeFileSync(resolve(output, `${screen.file}.html`), render(screen));

const lines = [
  "# Current-Platform Route Preview Matrix",
  "",
  "Generated from `scripts/generate_current_previews.mjs`. Every non-redirect route declared in `frontend/src/routes/AppRoutes.jsx` maps to a standalone HTML preview below.",
  "",
  "## Newly generated route previews",
  "",
  "| Role | Web route | HTML preview |",
  "|---|---|---|",
  ...screens.map((screen) => `| ${screen.role} | \`${screen.route}\` | [${screen.file}.html](html-previews/${screen.file}.html) |`),
  "",
  "## Routes covered by the original or hand-authored preview set",
  "",
  "| Role | Web route | HTML preview | Notes |",
  "|---|---|---|---|",
  ...existingRouteMappings.map(([role, route, file, notes]) => `| ${role} | \`${route}\` | [${file}](html-previews/${file}) | ${notes} |`),
  "",
  "Redirect-only routes reuse their destination preview: `/customer/batches*` → `/agizisha`; `/cargo/packing-lists` and `/cargo/customs-packing-lists` → the documentation packing-list view; `/cargo/customers` → the documentation customer view. The wildcard route returns to `/`.",
  "",
];
writeFileSync(resolve(root, "GENERATED_SCREEN_INVENTORY.md"), lines.join("\n"));
console.log(`Generated ${screens.length} current-platform previews.`);

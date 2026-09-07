import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "html-previews");
mkdirSync(output, { recursive: true });

const previews = [
  { file: "customer-search-container", role: "Customer", mode: "sea", initialStep: 1 },
  { file: "customer-book-cbm", role: "Customer", mode: "sea", initialStep: 2 },
  { file: "customer-booking-confirmation", role: "Customer", mode: "sea", initialStep: 3 },
  { file: "customer-express-air-cargo", role: "Customer", mode: "air", initialStep: 1 },
  { file: "agent-containers", role: "Sourcing Agent", mode: "sea", initialStep: 1 },
  { file: "agent-express-air-cargo", role: "Sourcing Agent", mode: "air", initialStep: 1 },
];

const seaServices = [
  { badge: "Best match", name: "Bahari Cargo", route: "Guangzhou → Dar es Salaam", meta: "18.40 CBM available", rate: "TZS 485,000 / CBM", time: "Departs 28 Aug" },
  { badge: "Lowest price", name: "Umoja Freight", route: "Shanghai → Dar es Salaam", meta: "9.80 CBM available", rate: "TZS 460,000 / CBM", time: "Departs 02 Sep" },
  { badge: "Soonest", name: "EastBridge Cargo", route: "Ningbo → Zanzibar", meta: "6.25 CBM available", rate: "TZS 510,000 / CBM", time: "Departs 26 Aug" },
];

const airServices = [
  { badge: "Best match", name: "Sahajomy Air", route: "Guangzhou air warehouse", meta: "5–7 day transit", rate: "USD 8.20 / KG", time: "Daily intake" },
  { badge: "Lowest price", name: "Umoja Express", route: "Yiwu air warehouse", meta: "7–10 day transit", rate: "USD 7.60 / KG", time: "Mon / Thu" },
  { badge: "Fastest", name: "EastBridge Air", route: "Shenzhen air warehouse", meta: "3–5 day transit", rate: "USD 9.40 / KG", time: "Next flight 27 Aug" },
];

const esc = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

const serviceRows = (mode) => (mode === "sea" ? seaServices : airServices)
  .map((service, index) => `
    <article class="service ${index === 0 ? "recommended" : ""}">
      <div class="serviceTop">
        <span class="badge">${esc(service.badge)}</span>
        <span class="verified">✓ Verified</span>
      </div>
      <div class="serviceBody">
        <span class="avatar">${esc(service.name.slice(0, 1))}</span>
        <div class="serviceName"><b>${esc(service.name)}</b><small>${esc(service.route)}</small></div>
      </div>
      <div class="facts"><span><small>${mode === "sea" ? "Capacity" : "Transit"}</small><b>${esc(service.meta)}</b></span><span><small>Rate</small><b>${esc(service.rate)}</b></span></div>
      <div class="serviceAction"><span>${esc(service.time)}</span><button onclick="chooseService('${esc(service.name)}')">Choose</button></div>
    </article>`)
  .join("");

const seaFields = (role) => `
  <div class="fieldGrid">
${role === "Sourcing Agent" ? `    <label class="field full"><span>Closed batch <i>Optional</i></span><select><option>No batch — direct booking</option><option>August electronics batch</option></select></label>\n` : ""}    <label class="field"><span>CBM to book</span><input type="number" inputmode="decimal" value="1.25" /></label>
    <label class="field"><span>Cartons</span><input type="number" value="4" /></label>
    <label class="field full"><span>Goods type</span><select><option>Electronics and accessories</option><option>Clothing and textiles</option><option>Household items</option></select></label>
  </div>
  <button class="optional" onclick="toggleOptional(this)"><span>＋</span> Add supplier order details <small>Optional</small></button>`;

const airFields = () => `
  <div class="fieldGrid">
    <label class="field full"><span>Cargo type</span><select><option>Normal goods</option><option>Electronics</option><option>Textiles</option></select></label>
    <label class="field"><span>Weight (KG)</span><input type="number" inputmode="decimal" value="12.5" /></label>
    <label class="field"><span>Cartons</span><input type="number" value="2" /></label>
    <label class="field"><span>Shipment date</span><input type="date" value="2026-08-28" /></label>
    <label class="field"><span>Shipment time</span><input type="time" value="10:30" /></label>
    <label class="field full"><span>Cargo description</span><textarea>12 cartons of packaged phone accessories</textarea></label>
    <label class="upload full"><input type="file" accept="image/*" multiple /><span>＋</span><b>Add cargo photos</b><small>JPG or PNG · multiple allowed</small></label>
  </div>`;

const reviewDetails = (mode, role) => mode === "sea" ? `
  <dl class="reviewGrid">
    <div><dt>Booking reference</dt><dd>SEA-240826-018</dd></div><div><dt>Status</dt><dd class="successText">Awaiting confirmation</dd></div>
    <div><dt>Operator</dt><dd>Bahari Cargo</dd></div><div><dt>Space booked</dt><dd>1.25 m³</dd></div>
    <div><dt>Route</dt><dd>Guangzhou → Dar es Salaam</dd></div><div><dt>Cartons</dt><dd>4</dd></div>
    ${role === "Sourcing Agent" ? `<div><dt>Linked batch</dt><dd>Direct booking</dd></div>` : ""}<div><dt>Estimated charge</dt><dd>TZS 606,250</dd></div>
  </dl>` : `
  <dl class="reviewGrid">
    <div><dt>Booking reference</dt><dd>AIR-240826-032</dd></div><div><dt>Status</dt><dd class="successText">Pending review</dd></div>
    <div><dt>Service</dt><dd>Sahajomy Air</dd></div><div><dt>Weight</dt><dd>12.50 KG</dd></div>
    <div><dt>Cargo type</dt><dd>Normal goods</dd></div><div><dt>Cartons</dt><dd>2</dd></div>
    <div><dt>Route</dt><dd>Guangzhou → Tanzania</dd></div><div><dt>Shipping quote</dt><dd>USD 102.50</dd></div>
  </dl>`;

const reviewAddress = (mode, role) => {
  if (mode === "sea" && role === "Customer") {
    return `<section class="address"><div class="addressTitle"><b>Supplier shipping mark</b><span>Saved</span></div><code>SJ-A09-SEA</code><p>The full warehouse address is already available under My China Addresses.</p><div class="copyRow"><button onclick="toast('Shipping mark copied')">Copy shipping mark</button><button onclick="toast('Opening My China Addresses')">My China Addresses</button></div></section>`;
  }
  const label = mode === "sea" ? "Supplier shipping mark" : "Your China delivery address";
  return `<section class="address"><div class="addressTitle"><b>${label}</b><span>Prepared</span></div><code>SJ-A09-${mode === "sea" ? "SEA" : "AIR"}</code><p>Room 08, Building 3, Baiyun Logistics Park<br>Guangzhou, Guangdong, China · +86 138 0000 6688</p><div class="copyRow"><button onclick="toast('Address copied')">Copy address</button><button onclick="toast('Shipping mark copied')">Copy shipping mark</button></div></section>`;
};

const render = ({ role, mode, initialStep }) => {
  const modeLabel = mode === "sea" ? "Sea cargo" : "Air cargo";
  const selectedName = mode === "sea" ? "Bahari Cargo" : "Sahajomy Air";
  const selectedMeta = mode === "sea" ? "Guangzhou → Dar es Salaam · TZS 485,000 / CBM" : "Guangzhou air warehouse · USD 8.20 / KG";
  const serviceNoun = mode === "sea" ? "a container service" : "an air service";
  const detailsTitle = mode === "sea" ? "Cargo space details" : "Air cargo details";
  const nav = role === "Customer" ? ["Home", "Shipments", "Agizisha", "More"] : ["Home", "Batches", "Orders", "More"];
  return `<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sahajomy · ${esc(role)} · ${modeLabel} booking</title><style>
*{box-sizing:border-box}body{margin:0;background:#e2e8f0;color:#0f172a;font-family:Inter,ui-sans-serif,system-ui,sans-serif}.phone{position:relative;width:min(100%,393px);height:min(100dvh,852px);overflow:hidden;background:#f7f8fa}.top{height:60px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;border-bottom:1px solid #e2e8f0;background:#fff}.iconBtn{width:44px;height:44px;border:0;background:none;color:#0f3d5e;font-size:22px}.context{text-align:center}.context small{display:block;color:#ff6b4a;font-size:9px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.context b{font-size:14px;color:#0f3d5e}.scroll{height:calc(100% - 128px);overflow:auto;padding:14px 16px 28px}.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-bottom:16px}.step{position:relative;border:0;background:none;padding:0;text-align:left}.step:before{content:"";position:absolute;left:12px;right:-7px;top:12px;height:2px;background:#e2e8f0}.step:last-child:before{display:none}.step i{position:relative;z-index:1;display:grid;width:25px;height:25px;place-items:center;border:2px solid #cbd5e1;border-radius:50%;background:#f7f8fa;color:#64748b;font-size:10px;font-style:normal;font-weight:800}.step span{display:block;margin-top:5px;color:#64748b;font-size:9px;font-weight:700}.step.active i{border-color:#ff6b4a;background:#ff6b4a;color:#fff}.step.active span{color:#e85a3a}.step.done i{border-color:#0f3d5e;background:#0f3d5e;color:#fff}.panel{display:none}.panel.active{display:block}.eyebrow{margin:0;color:#ff6b4a;font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}h1{margin:5px 0 4px;color:#0f3d5e;font-size:23px;line-height:1.15}p.lead{margin:0 0 14px;color:#64748b;font-size:13px;line-height:1.45}.service{margin-bottom:9px;overflow:hidden;border:1px solid #e2e8f0;border-radius:14px;background:#fff}.service.recommended{border-color:#ffb29f;box-shadow:0 0 0 2px #fff2ee}.serviceTop,.serviceAction,.serviceBody,.facts{display:flex;align-items:center}.serviceTop{justify-content:space-between;padding:9px 11px 0}.badge{border-radius:99px;background:#fff2ee;padding:4px 7px;color:#e85a3a;font-size:9px;font-weight:800}.verified{color:#059669;font-size:9px;font-weight:700}.serviceBody{gap:9px;padding:9px 11px}.avatar{display:grid;width:34px;height:34px;flex:none;place-items:center;border-radius:50%;background:#0f3d5e;color:#fff;font-size:12px;font-weight:800}.serviceName{min-width:0}.serviceName b,.serviceName small{display:block}.serviceName b{font-size:13px}.serviceName small{margin-top:2px;overflow:hidden;color:#64748b;font-size:10px;text-overflow:ellipsis;white-space:nowrap}.facts{border-top:1px solid #eef2f7;border-bottom:1px solid #eef2f7}.facts span{width:50%;padding:8px 11px}.facts span+span{border-left:1px solid #eef2f7}.facts small,.facts b{display:block}.facts small{color:#94a3b8;font-size:9px}.facts b{margin-top:2px;font-size:10px}.serviceAction{justify-content:space-between;padding:8px 9px 8px 11px;color:#64748b;font-size:10px}.serviceAction button,.primary,.secondary{min-height:44px;border:0;border-radius:10px;font-weight:800}.serviceAction button{min-height:36px;background:#ff6b4a;padding:0 15px;color:#fff;font-size:11px}.browse{width:100%;min-height:44px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#0f3d5e;font-size:11px;font-weight:800}.selected{display:flex;align-items:center;gap:9px;margin-bottom:14px;padding:10px;border:1px solid #e2e8f0;border-radius:12px;background:#fff}.selected>div{min-width:0;flex:1}.selected b,.selected small{display:block}.selected b{font-size:12px}.selected small{margin-top:2px;overflow:hidden;color:#64748b;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.selected button{border:0;background:none;color:#e85a3a;font-size:10px;font-weight:800}.fieldGrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.full{grid-column:1/-1}.field span{display:block;margin-bottom:5px;color:#475569;font-size:10px;font-weight:800}.field i{color:#94a3b8;font-style:normal;font-weight:600}.field input,.field select,.field textarea{width:100%;min-height:46px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;padding:10px;color:#0f172a;font:12px inherit;outline:none}.field textarea{height:66px;resize:none}.field input:focus,.field select:focus,.field textarea:focus{border-color:#ff6b4a;box-shadow:0 0 0 2px #fff2ee}.upload{display:flex;min-height:66px;align-items:center;justify-content:center;gap:7px;border:1px dashed #94a3b8;border-radius:10px;background:#fff;color:#0f3d5e;text-align:center}.upload input{display:none}.upload span{font-size:18px}.upload b{font-size:11px}.upload small{color:#64748b;font-size:9px}.optional{display:flex;width:100%;min-height:44px;align-items:center;gap:7px;margin-top:10px;border:1px solid #e2e8f0;border-radius:10px;background:#fff;padding:0 11px;color:#0f3d5e;font-size:11px;font-weight:800}.optional small{margin-left:auto;color:#94a3b8}.actionRow{display:flex;gap:9px;margin-top:14px;padding-top:12px;border-top:1px solid #e2e8f0}.primary,.secondary{flex:1;padding:0 12px;font-size:11px}.primary{background:#ff6b4a;color:#fff}.secondary{border:1px solid #cbd5e1;background:#fff;color:#0f3d5e}.successHead{display:flex;gap:10px;margin-bottom:14px;padding:13px;border:1px solid #bfdbfe;border-radius:14px;background:#eff6ff}.successIcon{display:grid;width:34px;height:34px;flex:none;place-items:center;border-radius:50%;background:#0f3d5e;color:#fff;font-weight:900}.successHead b,.successHead small{display:block}.successHead b{color:#0f3d5e;font-size:14px}.successHead small{margin-top:3px;color:#475569;font-size:10px}.reviewGrid{display:grid;grid-template-columns:1fr 1fr;margin:0;border:1px solid #e2e8f0;border-radius:12px;background:#fff;overflow:hidden}.reviewGrid div{min-width:0;padding:9px 10px;border-bottom:1px solid #eef2f7}.reviewGrid div:nth-child(odd){border-right:1px solid #eef2f7}.reviewGrid dt{color:#94a3b8;font-size:9px}.reviewGrid dd{margin:3px 0 0;overflow-wrap:anywhere;font-size:10px;font-weight:800}.successText{color:#059669!important}.address{margin-top:12px;border:1px solid #e2e8f0;border-radius:12px;background:#fff;padding:12px}.addressTitle{display:flex;align-items:center;justify-content:space-between}.addressTitle b{color:#0f3d5e;font-size:12px}.addressTitle span{border-radius:99px;background:#ecfdf5;padding:4px 7px;color:#047857;font-size:8px;font-weight:800}.address p{margin:8px 0 0;color:#64748b;font-size:10px;line-height:1.45}.address code{display:block;margin-top:8px;color:#e85a3a;font-size:11px;font-weight:800}.copyRow{display:flex;gap:7px;margin-top:10px}.copyRow button{min-height:36px;flex:1;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:#0f3d5e;font-size:9px;font-weight:800}.nav{position:absolute;inset:auto 0 0;height:68px;display:flex;justify-content:space-around;border-top:1px solid #e2e8f0;background:#fff;padding:7px 6px 13px}.nav button{min-width:62px;border:0;background:none;color:#94a3b8;font-size:9px}.nav button:first-child{color:#ff6b4a;font-weight:800}.nav span{display:block;font-size:16px}.toast{position:fixed;left:50%;bottom:18px;z-index:10;display:none;max-width:90%;transform:translateX(-50%);border-radius:99px;background:#0f172a;color:#fff;padding:9px 13px;font-size:10px;white-space:nowrap}@media(min-width:500px){.phone{height:852px;margin:24px auto;border:10px solid #0f172a;border-radius:38px;box-shadow:0 25px 70px #0f172a55}}
</style></head><body><main class="phone"><header class="top"><button class="iconBtn" onclick="toast('Back navigation preview')">‹</button><div class="context"><small>${esc(role)}</small><b>${modeLabel} booking</b></div><button class="iconBtn" onclick="toast('Notifications preview')">♧</button></header><section class="scroll"><div class="steps"><button class="step" data-step="1" onclick="showStep(1)"><i>1</i><span>Choose service</span></button><button class="step" data-step="2" onclick="showStep(2)"><i>2</i><span>Cargo details</span></button><button class="step" data-step="3" onclick="showStep(3)"><i>3</i><span>Review</span></button></div>
<section class="panel" data-panel="1"><p class="eyebrow">Step 1 · Choose service</p><h1>Choose ${serviceNoun}</h1><p class="lead">Start with three useful options. Browse more operators only when needed.</p>${serviceRows(mode)}<button class="browse" onclick="toast('All operators open in a searchable compact list')">Browse all services</button></section>
<section class="panel" data-panel="2"><p class="eyebrow">Step 2 · Cargo details</p><h1>${detailsTitle}</h1><p class="lead">Only the fields needed for this ${modeLabel.toLowerCase()} booking are shown.</p><div class="selected"><span class="avatar">${selectedName.slice(0, 1)}</span><div><b>${selectedName}</b><small>${selectedMeta}</small></div><button onclick="showStep(1)">Change</button></div>${mode === "sea" ? seaFields(role) : airFields()}<div class="actionRow"><button class="secondary" onclick="showStep(1)">Cancel</button><button class="primary" onclick="openReview()">Continue to review</button></div></section>
<section class="panel" data-panel="3"><p class="eyebrow" id="reviewEyebrow">Step 3 · Review</p><h1 id="reviewTitle">Review and confirm</h1><p class="lead" id="reviewLead">Check the booking summary before the final submission.</p><div class="successHead"><span class="successIcon" id="reviewIcon">✓</span><div><b id="reviewNotice">Ready for confirmation</b><small id="reviewNoticeText">Nothing is submitted until you confirm below.</small></div></div>${reviewDetails(mode, role)}${reviewAddress(mode, role)}<div class="actionRow"><button class="secondary" id="reviewBack" onclick="showStep(2)">Back to details</button><button class="primary" id="reviewConfirm" onclick="confirmBooking()">Confirm booking</button></div></section></section><nav class="nav">${nav.map((item, index) => `<button><span>${["⌂", "▦", "≡", "•••"][index]}</span>${item}</button>`).join("")}</nav></main><div id="toast" class="toast"></div><script>
let currentStep=${initialStep};function showStep(step){currentStep=step;document.querySelectorAll('.panel').forEach(node=>node.classList.toggle('active',Number(node.dataset.panel)===step));document.querySelectorAll('.step').forEach(node=>{const value=Number(node.dataset.step);node.classList.toggle('active',value===step);node.classList.toggle('done',value<step)});document.querySelector('.scroll').scrollTop=0}function toast(message){const node=document.getElementById('toast');node.textContent=message;node.style.display='block';clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>node.style.display='none',1600)}function chooseService(name){toast('Preparing '+name+' address before booking…');setTimeout(()=>showStep(2),500)}function openReview(){toast('Cargo details ready for review');setTimeout(()=>showStep(3),250)}function confirmBooking(){document.querySelector('[data-step="3"]').classList.remove('active');document.querySelector('[data-step="3"]').classList.add('done');document.getElementById('reviewEyebrow').textContent='Booking confirmed';document.getElementById('reviewTitle').textContent='Booking submitted';document.getElementById('reviewLead').textContent='Your booking was received. Keep the China address for your supplier.';document.getElementById('reviewNotice').textContent='${modeLabel} booking received';document.getElementById('reviewNoticeText').textContent='The cargo team will update the booking status.';document.getElementById('reviewBack').textContent='Book another';document.getElementById('reviewBack').onclick=()=>showStep(1);document.getElementById('reviewConfirm').textContent='View booking';document.getElementById('reviewConfirm').onclick=()=>toast('Opening booking details');toast('Booking confirmed and submitted')}function toggleOptional(button){button.innerHTML='<span>✓</span> Supplier details section added <small>Ready</small>';toast('Optional supplier fields added')}showStep(currentStep);
</script></body></html>`;
};

for (const preview of previews) {
  writeFileSync(resolve(output, `${preview.file}.html`), render(preview));
}

console.log(`Generated ${previews.length} booking previews.`);

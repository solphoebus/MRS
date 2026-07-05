const el = (id) => document.getElementById(id);

const STORAGE_KEY = "medisense-pixel-savings";
const METER_CAP = 500;

const DEMO_TEXT = "Tab Aceclo Plus 10'S\nParacetamol 500mg Tablet\nBrufen 400mg Tablet";

function loadSavings() {
  const raw = Number(localStorage.getItem(STORAGE_KEY));
  return Number.isFinite(raw) && raw >= 0 ? raw : 0;
}

function saveSavings(total) {
  localStorage.setItem(STORAGE_KEY, String(total));
}

let totalSaved = loadSavings();

function renderSavings() {
  el("savingsAmount").textContent = `Rs ${totalSaved.toFixed(0)}`;
  const pct = Math.max(0, Math.min(100, (totalSaved / METER_CAP) * 100));
  el("meterFill").style.width = `${pct}%`;

  const mouth = document.getElementById("mascotMouth");
  if (totalSaved <= 0) {
    mouth.setAttribute("y", "9");
    mouth.setAttribute("height", "1");
    el("savingsCaption").textContent = "Scan a prescription to start saving!";
  } else if (totalSaved < 100) {
    mouth.setAttribute("y", "9");
    mouth.setAttribute("height", "2");
    el("savingsCaption").textContent = "Nice! Keep scanning to save more.";
  } else if (totalSaved < 300) {
    mouth.setAttribute("y", "9");
    mouth.setAttribute("height", "3");
    el("savingsCaption").textContent = "Great savings streak going!";
  } else {
    mouth.setAttribute("y", "8");
    mouth.setAttribute("height", "3");
    el("savingsCaption").textContent = "Legendary saver! Keep it up!";
  }
}

function setScanState(message, kind = "") {
  const node = el("scanState");
  node.textContent = message;
  node.className = `scan-state ${kind === "ok" ? "is-ok" : kind === "error" ? "is-error" : ""}`;
}

async function scanPrescription(text) {
  const response = await fetch("/scan-prescription", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prescription_text: text }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  return `Rs ${Number(value).toFixed(0)}`;
}

function renderLoot(data) {
  const items = data.items || [];
  if (!items.length) {
    el("lootList").innerHTML = '<p class="empty-note">No items detected. Try clearer prescription text.</p>';
    return;
  }

  el("lootList").innerHTML = items
    .map((item) => {
      const found = Boolean(item.matched_generic_name);
      const statusClass = found ? "loot-status-found" : "loot-status-miss";
      const statusText = found ? "MATCHED" : "NO MATCH";
      const savingsLine = item.estimated_savings
        ? `<p class="loot-line loot-save">+ Rs ${Number(item.estimated_savings).toFixed(0)} possible savings</p>`
        : "";
      return `
        <div class="loot-item">
          <div class="loot-item-head">
            <span class="loot-name">${item.original_text}</span>
            <span class="loot-status ${statusClass}">${statusText}</span>
          </div>
          <p class="loot-line"><strong>Matched:</strong> ${item.matched_generic_name || "Unknown"}</p>
          <p class="loot-line"><strong>Price:</strong> ${formatCurrency(item.estimated_price)}</p>
          <p class="loot-line"><strong>Cheaper option:</strong> ${item.cheapest_alternative_name || "None found"} (${formatCurrency(item.cheapest_alternative_price)})</p>
          ${savingsLine}
        </div>
      `;
    })
    .join("");
}

function accumulateSavings(data) {
  const gained = (data.items || []).reduce((sum, item) => sum + (item.estimated_savings || 0), 0);
  if (gained > 0) {
    totalSaved += gained;
    saveSavings(totalSaved);
    renderSavings();
  }
  return gained;
}

async function runScan(text) {
  if (!text || !text.trim()) {
    setScanState("Type or paste a prescription first!", "error");
    return;
  }
  setScanState("Scanning...", "");
  try {
    const data = await scanPrescription(text);
    renderLoot(data);
    const gained = accumulateSavings(data);
    if (gained > 0) {
      setScanState(`Found Rs ${gained.toFixed(0)} in potential savings!`, "ok");
    } else {
      setScanState("Scan complete. No extra savings found this time.", "ok");
    }
  } catch (error) {
    setScanState(`Scan failed: ${error.message}`, "error");
  }
}

el("scanBtn").addEventListener("click", () => {
  runScan(el("prescriptionText").value);
});

el("demoBtn").addEventListener("click", () => {
  el("prescriptionText").value = DEMO_TEXT;
  runScan(DEMO_TEXT);
});

renderSavings();

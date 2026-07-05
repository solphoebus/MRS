const el = (id) => document.getElementById(id);

function safeSetHtml(id, html) {
  const node = el(id);
  if (node) node.innerHTML = html;
}

/* Theme */
el("themeToggle").addEventListener("click", () => {
  document.body.classList.toggle("dark");
});

/* API helper */
async function callApi(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Request failed");
  }
  return response.json();
}

function parseCsvInput(value) {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  return `₹${Number(value).toFixed(2)}`;
}

/* Tabs */
const tabButtons = document.querySelectorAll(".segmented-btn");
tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.dataset.tab;
    tabButtons.forEach((btn) => {
      const isActive = btn === button;
      btn.classList.toggle("is-active", isActive);
      btn.setAttribute("aria-selected", String(isActive));
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.tabPanel === target);
    });
  });
});

function activateTab(name) {
  const button = document.querySelector(`.segmented-btn[data-tab="${name}"]`);
  if (button) button.click();
}

/* Confidence ring */
const RING_CIRCUMFERENCE = 169.6;

function setConfidenceRing(percent, caption) {
  const clamped = Math.max(0, Math.min(100, percent));
  const offset = RING_CIRCUMFERENCE - (RING_CIRCUMFERENCE * clamped) / 100;
  el("confidenceRingCircle").style.strokeDashoffset = String(offset);
  el("confidenceRingLabel").textContent = `${Math.round(clamped)}%`;
  el("ringCaption").textContent = caption;
}

function resetConfidenceRing() {
  el("confidenceRingCircle").style.strokeDashoffset =
    String(RING_CIRCUMFERENCE);
  el("confidenceRingLabel").textContent = "—";
  el("ringCaption").textContent = "Waiting for input";
}

/* Health check + hero stats */
async function loadHealth() {
  try {
    const data = await callApi("/health-check");
    el("healthStatus").textContent =
      `${data.status.toUpperCase()} · v${data.version}`;
    el("healthDisclaimer").textContent = data.disclaimer;
    el("apiStatusDot").className = "status-dot is-ok";
  } catch (error) {
    el("healthStatus").textContent = "Backend unavailable";
    el("healthDisclaimer").textContent =
      "Start the FastAPI server on port 8000 to use this workspace.";
    el("apiStatusDot").className = "status-dot is-error";
  }
}

async function loadHeroStats() {
  try {
    const data = await callApi("/debug/medicines");
    el("statMedicines").textContent = data.count.toLocaleString();
  } catch (error) {
    el("statMedicines").textContent = "—";
  }
}

/* Demo data */
function loadDemoData() {
  el("prescriptionText").value =
    "Tab Aceclo Plus 10'S\nParacetamol 500mg Tablet\nIbuprofen SOS";
  el("symptoms").value = "fever, pain, headache";
  el("disease").value = "Pain";
  el("age").value = 34;
  el("weight").value = 70;
  el("gender").value = "male";
  el("severity").value = "moderate";
  el("conditions").value = "hypertension";
  el("allergies").value = "penicillin";
  el("medications").value = "ibuprofen";
  el("pregnancy").checked = false;
  el("breastfeeding").checked = false;
  setRequestState("Sample data filled in", "ok");
}

el("loadDemoBtn").addEventListener("click", loadDemoData);
el("runDemoBtn").addEventListener("click", async () => {
  loadDemoData();
  activateTab("symptom");
  await runRecommendation();
});

/* Request state (symptom tab) */
function setRequestState(message, kind = "") {
  const node = el("requestState");
  node.textContent = message;
  node.className = `state-text ${kind === "error" ? "is-error" : kind === "ok" ? "is-ok" : ""}`;
}

/* Recommendation flow */
async function runRecommendation() {
  setRequestState("Generating recommendations…", "");
  safeSetHtml(
    "resultsBody",
    `<div class="empty-state"><h3>Analyzing patient profile</h3><p>Matching symptoms, checking safety, ranking recommendations…</p></div>`,
  );
  try {
    const payload = {
      symptoms: parseCsvInput(el("symptoms").value),
      diagnosed_disease: el("disease").value || null,
      age: Number(el("age").value || 0),
      weight_kg: Number(el("weight").value || 0) || null,
      gender: el("gender").value,
      pregnancy_status: el("pregnancy").checked,
      breastfeeding: el("breastfeeding").checked,
      existing_medical_conditions: parseCsvInput(el("conditions").value),
      allergies: parseCsvInput(el("allergies").value),
      current_medications: parseCsvInput(el("medications").value),
      severity: el("severity").value,
      country_region: null,
    };

    const data = await callApi("/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    renderRecommendationResults(data);
    setConfidenceRing(
      (data.confidence_score || 0) * 100,
      "Recommendation confidence",
    );
    setRequestState("Recommendations ready", "ok");
    refreshDebugData();
  } catch (error) {
    safeSetHtml(
      "resultsBody",
      `<div class="empty-state"><h3>Something went wrong</h3><p>${error.message}</p></div>`,
    );
    setRequestState("Recommendation request failed", "error");
  }
}

el("recommendBtn").addEventListener("click", runRecommendation);

function renderRecommendationResults(data) {
  const recommendations = data.recommendations || [];
  const diseaseBadges = (data.matched_disease_candidates || [])
    .map((v) => `<span class="badge">${v}</span>`)
    .join("");

  const recommendationCards = recommendations
    .map((rec) => {
      const safetyIssues = rec.safety_issues || [];
      const safetyHtml = safetyIssues.length
        ? safetyIssues
            .map((issue) => {
              const level =
                issue.severity === "high"
                  ? "badge-danger"
                  : issue.severity === "medium"
                    ? "badge-warning"
                    : "badge";
              return `<span class="badge ${level}">${issue.category}</span>`;
            })
            .join(" ")
        : `<span class="badge badge-success">No flags raised</span>`;

      return `
        <div class="result-card">
          <div class="result-card-head">
            <h3>${rec.generic_name}</h3>
            <span class="panel-tag">${Math.round(rec.confidence_score * 100)}% match</span>
          </div>
          <div class="badge-row">
            <span class="badge">${rec.recommendation_type}</span>
            <span class="badge">${rec.category}</span>
          </div>
          <p><strong>Brands:</strong> ${(rec.brand_names || []).join(", ") || "N/A"}</p>
          <p><strong>Estimated price:</strong> <span class="price">${formatCurrency(rec.estimated_price)}</span></p>
          <p><strong>Dosage:</strong> ${rec.dosage.dose} · ${rec.dosage.frequency} · ${rec.dosage.duration}</p>
          <p><strong>Why this was suggested:</strong> ${(rec.why_selected || []).join("; ")}</p>
          <p><strong>Safety review:</strong> ${safetyHtml}</p>
          <p><strong>Common side effects:</strong> ${(rec.side_effects.common || []).join(", ") || "None listed"}</p>
        </div>
      `;
    })
    .join("");

  const alternativesHtml = (data.alternatives || [])
    .map(
      (item) =>
        `<p><span class="badge">${item.type}</span> <strong>${item.name}</strong> — ${item.rationale}</p>`,
    )
    .join("");

  safeSetHtml(
    "resultsBody",
    `
    <div class="result-card">
      <h3>Summary</h3>
      <p>${data.patient_friendly_explanation || ""}</p>
      <p class="muted">${data.disclaimer || ""}</p>
    </div>
    ${diseaseBadges ? `<div class="result-card"><h4>Matched conditions</h4><div class="badge-row">${diseaseBadges}</div></div>` : ""}
    ${recommendationCards || `<div class="empty-state"><h3>No recommendations returned</h3><p>Try broader symptoms or load demo data.</p></div>`}
    ${alternativesHtml ? `<div class="result-card"><h4>Alternatives &amp; supportive care</h4>${alternativesHtml}</div>` : ""}
  `,
  );
}

/* Prescription scanning */
el("scanBtn").addEventListener("click", async () => {
  await runScan(() =>
    callApi("/scan-prescription", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prescription_text: el("prescriptionText").value }),
    }),
  );
});

el("scanImageBtn").addEventListener("click", async () => {
  const fileInput = el("prescriptionFile");
  if (!fileInput.files.length) {
    safeSetHtml(
      "resultsBody",
      `<div class="empty-state"><h3>No file selected</h3><p>Choose a prescription image or text file first.</p></div>`,
    );
    return;
  }
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  await runScan(() =>
    callApi("/scan-prescription-image", { method: "POST", body: formData }),
  );
});

async function runScan(request) {
  safeSetHtml(
    "resultsBody",
    `<div class="empty-state"><h3>Scanning</h3><p>Extracting line items and checking the catalog…</p></div>`,
  );
  try {
    const data = await request();
    renderScanResults(data);
    const matched = (data.items || []).filter(
      (item) => item.matched_generic_name,
    ).length;
    const total = (data.items || []).length || 1;
    setConfidenceRing((matched / total) * 100, "Match rate");
    refreshDebugData();
  } catch (error) {
    safeSetHtml(
      "resultsBody",
      `<div class="empty-state"><h3>Scan failed</h3><p>${error.message}</p></div>`,
    );
  }
}

function renderScanResults(data) {
  const items = data.items || [];
  const itemsHtml = items
    .map((item) => {
      const matched = Boolean(item.matched_generic_name);
      return `
        <div class="result-card">
          <div class="result-card-head">
            <h4>${item.original_text}</h4>
            <span class="badge ${matched ? "badge-success" : ""}">${matched ? "Matched" : "No match"}</span>
          </div>
          <p><strong>Matched medicine:</strong> ${item.matched_generic_name || "Not confidently matched"}</p>
          <p><strong>Current estimate:</strong> ${formatCurrency(item.estimated_price)}</p>
          <p><strong>Cheapest alternative:</strong> ${item.cheapest_alternative_name || "None found"} (${formatCurrency(item.cheapest_alternative_price)})</p>
          <p><strong>Estimated savings:</strong> <span class="price">${formatCurrency(item.estimated_savings)}</span></p>
          <p class="muted">${item.review_note}</p>
        </div>
      `;
    })
    .join("");

  safeSetHtml(
    "resultsBody",
    `
    <div class="result-card">
      <h3>Scan summary</h3>
      <p class="muted">${data.summary}</p>
      <div class="badge-row">${(data.extracted_candidates || []).map((v) => `<span class="badge">${v}</span>`).join("")}</div>
    </div>
    ${itemsHtml || `<div class="empty-state"><h3>No items detected</h3><p>Try clearer prescription text.</p></div>`}
    <div class="result-card">
      <p><strong>Important:</strong> Estimated cheaper alternatives are heuristic and must be verified for formulation, dose, route, and suitability by a licensed clinician or pharmacist.</p>
    </div>
  `,
  );
}

/* Patient auto-save + system status panel */
async function createDemoPatient() {
  const payload = {
    patient_id: `demo-${Date.now()}`,
    age: Number(el("age").value || 30),
    weight_kg: Number(el("weight").value || 70),
    gender: el("gender").value,
    pregnancy_status: el("pregnancy").checked,
    breastfeeding: el("breastfeeding").checked,
    conditions: parseCsvInput(el("conditions").value),
    allergies: parseCsvInput(el("allergies").value),
    medications: parseCsvInput(el("medications").value),
    country_region: "IN",
  };
  return callApi("/patient", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function setDebugState(message, kind = "") {
  const node = el("debugState");
  node.textContent = message;
  node.className = `state-text ${kind === "error" ? "is-error" : kind === "ok" ? "is-ok" : ""}`;
}

async function refreshDebugData() {
  setDebugState("Loading…", "");
  try {
    const [patients, history, medicines] = await Promise.all([
      callApi("/debug/patients"),
      callApi("/debug/history"),
      callApi("/debug/medicines"),
    ]);

    safeSetHtml(
      "debugPanel",
      `
      <div class="result-grid">
        <div class="kpi"><div class="kpi-label">Saved patients</div><div class="kpi-value">${patients.count}</div></div>
        <div class="kpi"><div class="kpi-label">History events</div><div class="kpi-value">${history.count}</div></div>
        <div class="kpi"><div class="kpi-label">Medicines loaded</div><div class="kpi-value">${medicines.count}</div></div>
        <div class="kpi"><div class="kpi-label">Medicines in database</div><div class="kpi-value">${medicines.db_persisted_count}</div></div>
      </div>
      <div class="result-card">
        <h4>Latest patients</h4>
        ${patients.patients.length ? patients.patients.map((p) => `<p><strong>${p.patient_id}</strong> — ${p.created_at}</p>`).join("") : '<p class="muted">No patients stored yet.</p>'}
      </div>
      <div class="result-card">
        <h4>Latest history</h4>
        ${
          history.events.length
            ? history.events
                .slice(0, 10)
                .map(
                  (e) =>
                    `<p><strong>${e.event_type}</strong> — ${e.created_at}</p>`,
                )
                .join("")
            : '<p class="muted">No history stored yet.</p>'
        }
      </div>
      `,
    );
    setDebugState("Up to date", "ok");
  } catch (error) {
    safeSetHtml(
      "debugPanel",
      `<div class="empty-state"><h3>Unable to load</h3><p>${error.message}</p></div>`,
    );
    setDebugState("Failed to load", "error");
  }
}

el("refreshDebugBtn").addEventListener("click", refreshDebugData);

/* Boot */
resetConfidenceRing();
loadHealth();
loadHeroStats();
loadDemoData();
createDemoPatient()
  .then(refreshDebugData)
  .catch(() => setDebugState("Auto-save failed", "error"));

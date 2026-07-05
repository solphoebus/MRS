const apiBase = "http://127.0.0.1:8000";

const el = (id) => document.getElementById(id);

el("themeToggle").addEventListener("click", () => {
  document.body.classList.toggle("dark");
});

async function callApi(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Request failed");
  }
  return response.json();
}

async function loadHealth() {
  try {
    const data = await callApi("/health-check");
    el("healthStatus").textContent =
      `${data.status.toUpperCase()} · v${data.version}`;
    el("healthDisclaimer").textContent = data.disclaimer;
  } catch (error) {
    el("healthStatus").textContent = "Unavailable";
    el("healthDisclaimer").textContent = "Start the backend API on port 8000.";
  }
}

function parseCsvInput(value) {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

el("recommendBtn").addEventListener("click", async () => {
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
  } catch (error) {
    el("recommendations").innerHTML =
      `<div class="result-card danger">Unable to generate recommendations. ${error.message}</div>`;
  }
});

el("scanBtn").addEventListener("click", async () => {
  try {
    const data = await callApi("/scan-prescription", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prescription_text: el("prescriptionText").value }),
    });
    renderScanResults(data);
  } catch (error) {
    el("scanResults").innerHTML =
      `<div class="result-card danger">Unable to scan prescription. ${error.message}</div>`;
  }
});

function renderRecommendationResults(data) {
  el("confidence").innerHTML = `
    <div class="result-grid">
      <div class="kpi">
        <div class="muted">Recommendation confidence</div>
        <strong>${Math.round((data.confidence_score || 0) * 100)}%</strong>
      </div>
      <div class="kpi">
        <div class="muted">Danger flags</div>
        <strong>${(data.dangerous_combinations || []).length}</strong>
      </div>
    </div>
    <div class="result-card">
      <h3>Patient-friendly explanation</h3>
      <p>${data.patient_friendly_explanation || ""}</p>
      <p class="muted">${data.disclaimer || ""}</p>
    </div>
  `;

  el("diseaseMatches").innerHTML = `
    <div class="result-card">
      <h3>Disease matches</h3>
      <div>${(data.matched_disease_candidates || []).map((v) => `<span class="badge">${v}</span>`).join("")}</div>
    </div>
  `;

  el("recommendations").innerHTML = `
    ${(data.recommendations || [])
      .map(
        (rec) => `
      <div class="result-card">
        <div class="panel-head">
          <h3>${rec.generic_name}</h3>
          <span class="panel-tag">${Math.round(rec.confidence_score * 100)}% confidence</span>
        </div>
        <div>${[rec.recommendation_type, rec.category].map((v) => `<span class="badge">${v}</span>`).join("")}</div>
        <p><strong>Brands:</strong> ${(rec.brand_names || []).join(", ") || "N/A"}</p>
        <p><strong>Estimated price:</strong> <span class="price">${formatCurrency(rec.estimated_price)}</span></p>
        <p><strong>Dosage:</strong> ${rec.dosage.dose}; ${rec.dosage.frequency}; ${rec.dosage.duration}</p>
        <p><strong>Why selected:</strong> ${(rec.why_selected || []).join("; ")}</p>
        <p><strong>Risk factors considered:</strong> ${(rec.risk_factors_considered || []).join(", ")}</p>
        <p><strong>Safety issues:</strong> ${(rec.safety_issues || []).map((i) => `${i.category}: ${i.message}`).join(" | ") || "None flagged by heuristic engine"}</p>
        <p><strong>Side effects:</strong> ${(rec.side_effects.common || []).join(", ")}</p>
      </div>
    `,
      )
      .join("")}
  `;

  el("alternatives").innerHTML = `
    <div class="result-card">
      <h3>Alternatives & supportive care</h3>
      ${(data.alternatives || []).map((item) => `<p><span class="badge">${item.type}</span> <strong>${item.name}</strong> — ${item.rationale}</p>`).join("")}
    </div>
  `;
}

function renderScanResults(data) {
  el("scanResults").innerHTML = `
    <div class="result-card">
      <h3>Scanned items</h3>
      <p class="muted">${data.summary}</p>
      <div>${(data.extracted_candidates || []).map((v) => `<span class="badge">${v}</span>`).join("")}</div>
    </div>
    ${(data.items || [])
      .map(
        (item) => `
      <div class="result-card">
        <div class="panel-head">
          <h4>${item.original_text}</h4>
          <span class="panel-tag">Scan result</span>
        </div>
        <p><strong>Matched medicine:</strong> ${item.matched_generic_name || "Not confidently matched"}</p>
        <p><strong>Current estimate:</strong> ${formatCurrency(item.estimated_price)}</p>
        <p><strong>Cheapest alternative:</strong> ${item.cheapest_alternative_name || "No alternative found"}</p>
        <p><strong>Alternative estimate:</strong> ${formatCurrency(item.cheapest_alternative_price)}</p>
        <p><strong>Estimated savings:</strong> <span class="price">${formatCurrency(item.estimated_savings)}</span></p>
        <p class="warn">${item.review_note}</p>
      </div>
    `,
      )
      .join("")}
    <div class="result-card">
      <strong>Important:</strong> Estimated cheaper alternatives are heuristic and must be verified for formulation, dose, route, indication, interactions, and patient suitability by a licensed clinician or pharmacist.
    </div>
  `;
}

function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  return `₹${Number(value).toFixed(2)}`;
}

loadHealth();

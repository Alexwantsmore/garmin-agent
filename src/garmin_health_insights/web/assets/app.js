const demoRecords = [
  { date: "2026-05-28", resting_hr: 49, hrv_ms: 64, sleep_score: 86, sleep_hours: 7.8, body_battery: 78, stress_score: 24, training_load: 320, recovery_hours: 12 },
  { date: "2026-05-29", resting_hr: 50, hrv_ms: 61, sleep_score: 82, sleep_hours: 7.4, body_battery: 73, stress_score: 29, training_load: 340, recovery_hours: 16 },
  { date: "2026-05-30", resting_hr: 52, hrv_ms: 59, sleep_score: 78, sleep_hours: 7.1, body_battery: 68, stress_score: 31, training_load: 380, recovery_hours: 20 },
  { date: "2026-05-31", resting_hr: 51, hrv_ms: 63, sleep_score: 84, sleep_hours: 7.6, body_battery: 76, stress_score: 27, training_load: 300, recovery_hours: 10 },
  { date: "2026-06-01", resting_hr: 50, hrv_ms: 62, sleep_score: 80, sleep_hours: 7.2, body_battery: 72, stress_score: 33, training_load: 360, recovery_hours: 18 },
  { date: "2026-06-02", resting_hr: 53, hrv_ms: 58, sleep_score: 74, sleep_hours: 6.9, body_battery: 64, stress_score: 38, training_load: 430, recovery_hours: 28 },
  { date: "2026-06-03", resting_hr: 57, hrv_ms: 51, sleep_score: 66, sleep_hours: 6.2, body_battery: 48, stress_score: 61, training_load: 520, recovery_hours: 42 }
];

const fileInput = document.querySelector("#file-input");
const dateInput = document.querySelector("#date-input");
const baselineInput = document.querySelector("#baseline-input");
const generateButton = document.querySelector("#generate-button");
const demoButton = document.querySelector("#demo-button");
const statusEl = document.querySelector("#status");
const reportEl = document.querySelector("#report");
const scoreEl = document.querySelector("#score");
const scoreRingEl = document.querySelector("#score-ring");
const labelEl = document.querySelector("#label");
const summaryEl = document.querySelector("#summary");
const signalsEl = document.querySelector("#signals");
const suggestionsEl = document.querySelector("#suggestions");

generateButton.addEventListener("click", async () => {
  if (!fileInput.files.length) {
    setStatus("Wybierz plik JSON z danymi Garmin albo użyj raportu demo.", true);
    return;
  }

  try {
    const text = await fileInput.files[0].text();
    const data = JSON.parse(text);
    await generateReport(data);
  } catch (error) {
    setStatus(`Nie udało się odczytać pliku: ${error.message}`, true);
  }
});

demoButton.addEventListener("click", async () => {
  await generateReport({ records: demoRecords, date: dateInput.value });
});

async function generateReport(data) {
  setStatus("Generuję raport...");
  const payload = normalizePayload(data);
  payload.date = dateInput.value || payload.date;
  payload.baseline_days = Number(baselineInput.value || 21);

  const response = await fetch("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const body = await response.json();

  if (!response.ok) {
    throw new Error(body.error || "Nieznany błąd API.");
  }

  renderReport(body);
  setStatus(`Raport gotowy dla ${body.day}.`);
}

function normalizePayload(data) {
  if (Array.isArray(data)) {
    return { records: data };
  }
  if (data && typeof data === "object") {
    return { ...data };
  }
  throw new Error("Plik musi zawierać listę rekordów albo obiekt z polem records/days/data.");
}

function renderReport(report) {
  reportEl.classList.remove("hidden");
  scoreEl.textContent = report.readiness_score;
  labelEl.textContent = report.readiness_label;
  summaryEl.textContent = report.summary;

  scoreRingEl.classList.toggle("warning", report.readiness_score >= 60 && report.readiness_score < 80);
  scoreRingEl.classList.toggle("danger", report.readiness_score < 60);

  renderList(signalsEl, report.signals);
  renderList(suggestionsEl, report.suggestions);
}

function renderList(element, items) {
  element.replaceChildren();
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    element.append(li);
  }
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#b91c1c" : "#0f766e";
}

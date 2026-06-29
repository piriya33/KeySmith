const form = document.querySelector("#search-form");
const targetInput = document.querySelector("#target");
const networkInput = document.querySelector("#network");
const networkRow = document.querySelector("#network-row");
const addressTypeInput = document.querySelector("#address-type");
const addressTypeLabel = document.querySelector("#address-type-label");
const matchModeInput = document.querySelector("#match-mode");
const patternInput = document.querySelector("#pattern");
const caseSensitiveInput = document.querySelector("#case-sensitive");
const workersInput = document.querySelector("#workers");
const preview = document.querySelector("#pattern-preview");
const validationMessage = document.querySelector("#validation-message");
const guideName = document.querySelector("#guide-name");
const guideAlphabet = document.querySelector("#guide-alphabet");
const guideCopy = document.querySelector("#guide-copy");
const caseSensitiveCopy = document.querySelector("#case-sensitive-copy");
const statusEl = document.querySelector("#status");
const attemptsEl = document.querySelector("#attempts");
const rateEl = document.querySelector("#rate");
const workerModeEl = document.querySelector("#worker-mode");
const elapsedEl = document.querySelector("#elapsed");
const chanceEl = document.querySelector("#chance");
const processStepsEl = document.querySelector("#process-steps");
const fixedPrefixEl = document.querySelector("#fixed-prefix");
const searchablePatternEl = document.querySelector("#searchable-pattern");
const expectedTimeEl = document.querySelector("#expected-time");
const resultPanel = document.querySelector("#result-panel");
const resultGrid = document.querySelector("#result-grid");
const resultWarning = document.querySelector("#result-warning");
const paperButton = document.querySelector("#paper-button");
const paperPanel = document.querySelector("#paper-panel");
const paperGrid = document.querySelector("#paper-grid");
const printButton = document.querySelector("#print-button");
const startButton = document.querySelector("#start-button");
const stopButton = document.querySelector("#stop-button");
const verifySecretInput = document.querySelector("#verify-secret");
const verifyButton = document.querySelector("#verify-button");
const verifyMessage = document.querySelector("#verify-message");
const verifyResult = document.querySelector("#verify-result");

let pollTimer = null;
let lastValidation = null;
let options = null;
let lastResult = null;

function configPayload() {
  const target = targetInput.value;
  return {
    target,
    network: target === "nostr" ? "nostr" : networkInput.value,
    address_type: target === "nostr" ? "npub" : addressTypeInput.value,
    match_mode: matchModeInput.value,
    pattern: patternInput.value,
    case_sensitive: caseSensitiveInput.checked,
    workers: Number(workersInput.value || 1),
  };
}

async function loadOptions() {
  const response = await fetch("/api/options");
  options = await response.json();
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.message || "Request failed");
    error.data = data;
    throw error;
  }
  return data;
}

async function validate() {
  const data = await postJson("/api/validate", configPayload());
  lastValidation = data;
  renderValidation(data);
  return data;
}

function renderValidation(data) {
  const invalid = new Map(data.invalid_characters.map((item) => [item.index, item.char]));
  const pattern = patternInput.value;
  preview.innerHTML = "";
  for (let index = 0; index < pattern.length; index += 1) {
    const span = document.createElement("span");
    span.textContent = pattern[index];
    if (invalid.has(index)) {
      span.className = "invalid-char";
      span.title = `${pattern[index]} is not valid for ${data.guide}`;
    }
    preview.appendChild(span);
  }
  if (!pattern) {
    preview.textContent = "Type a vanity pattern";
  }
  validationMessage.textContent = data.message;
  validationMessage.style.color = data.valid ? "#0f766e" : "#b42318";
  guideName.textContent = data.guide.startsWith("Base58") ? "Base58" : "Bech32";
  guideAlphabet.textContent = data.alphabet;
  guideCopy.textContent = data.guide;
}

function renderTargetControls() {
  const isNostr = targetInput.value === "nostr";
  networkRow.hidden = isNostr;
  addressTypeLabel.textContent = isNostr ? "Key type" : "Address type";
  addressTypeInput.innerHTML = "";

  const values = isNostr ? [["npub", "Nostr npub"]] : [["p2pkh", "P2PKH"], ["p2wpkh", "P2WPKH"], ["p2tr", "P2TR"]];
  values.forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    addressTypeInput.appendChild(option);
  });

  caseSensitiveInput.checked = !isNostr;
  caseSensitiveInput.disabled = isNostr;
  caseSensitiveCopy.textContent = isNostr ? "Nostr npub matching is lowercase Bech32" : "Case-sensitive matching for Base58";
  if (isNostr && patternInput.value === "1A") {
    patternInput.value = "npub1";
  } else if (!isNostr && patternInput.value === "npub1") {
    patternInput.value = "1A";
  }
}

function renderSnapshot(snapshot) {
  statusEl.textContent = snapshot.status;
  attemptsEl.textContent = Number(snapshot.attempts || 0).toLocaleString();
  rateEl.textContent = Math.round(snapshot.attempts_per_second || 0).toLocaleString();
  workerModeEl.textContent = snapshot.worker_mode || "-";
  elapsedEl.textContent = formatDuration(snapshot.elapsed_seconds || 0);
  chanceEl.textContent = formatPercent(snapshot.cumulative_chance || 0);

  processStepsEl.innerHTML = "";
  (snapshot.process_steps || []).forEach((step) => {
    const li = document.createElement("li");
    li.textContent = step;
    processStepsEl.appendChild(li);
  });

  const breakdown = snapshot.format_breakdown || {};
  fixedPrefixEl.textContent = breakdown.fixed_prefix || "-";
  searchablePatternEl.textContent = breakdown.searchable_pattern || "-";
  expectedTimeEl.textContent = snapshot.expected_seconds
    ? formatDuration(snapshot.expected_seconds)
    : "Waiting for speed";

  if (snapshot.result) {
    renderResult(snapshot.result);
  }

  if (["found", "stopped", "idle", "error"].includes(snapshot.status)) {
    stopPolling();
    startButton.disabled = false;
  }
}

function renderResult(result) {
  resultPanel.hidden = false;
  lastResult = result;
  const isNostr = result.address_type === "npub";
  resultWarning.textContent = isNostr
    ? "The nsec private key can control a Nostr identity. Use this result for education only."
    : "Private keys can spend funds sent to the address. Use this result for education only.";
  resultGrid.innerHTML = "";
  const fields = [
    [isNostr ? "Nostr public key" : "Address", result.address],
    [result.private_key_export_label || "WIF private key", result.nsec || result.wif],
    ["Private key hex", result.private_key_hex],
    ["Public key", result.public_key_hex],
    [isNostr ? "Nostr x-only public key" : "Taproot x-only key", result.x_only_public_key_hex],
  ].filter(([, value]) => value);

  fields.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "result-item";
    const labelEl = document.createElement("strong");
    labelEl.textContent = label;
    const valueEl = document.createElement("code");
    valueEl.textContent = value;
    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "Copy";
    copy.addEventListener("click", () => navigator.clipboard.writeText(value));
    row.append(labelEl, valueEl, copy);
    resultGrid.appendChild(row);
  });
  renderPaperView(result);
}

function renderPaperView(result) {
  const isNostr = result.address_type === "npub";
  const rows = [
    [isNostr ? "Nostr public key (npub)" : "Public address", result.address],
    [isNostr ? "Private key (nsec)" : "Private key (WIF)", result.nsec || result.wif],
    ["Raw private key hex", result.private_key_hex],
    ["Format", isNostr ? "Nostr npub" : `${result.network} ${result.address_type.toUpperCase()}`],
  ].filter(([, value]) => value);
  paperGrid.innerHTML = "";
  rows.forEach(([label, value]) => {
    const block = document.createElement("div");
    block.className = "paper-item";
    const labelEl = document.createElement("strong");
    labelEl.textContent = label;
    const valueEl = document.createElement("code");
    valueEl.textContent = value;
    block.append(labelEl, valueEl);
    paperGrid.appendChild(block);
  });
}

function startPolling() {
  stopPolling();
  pollTimer = window.setInterval(async () => {
    const response = await fetch("/api/status");
    renderSnapshot(await response.json());
  }, 500);
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

function formatPercent(value) {
  return `${(value * 100).toFixed(value < 0.01 ? 3 : 2)}%`;
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) {
    return "unknown";
  }
  if (seconds < 1) {
    return `${Math.round(seconds * 1000)}ms`;
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const validation = lastValidation || (await validate());
    if (!validation.valid) {
      renderValidation(validation);
      return;
    }
    resultPanel.hidden = true;
    resultGrid.innerHTML = "";
    startButton.disabled = true;
    renderSnapshot(await postJson("/api/start", configPayload()));
    startPolling();
  } catch (error) {
    validationMessage.textContent = error.message;
    validationMessage.style.color = "#b42318";
    startButton.disabled = false;
  }
});

stopButton.addEventListener("click", async () => {
  renderSnapshot(await postJson("/api/stop"));
});

paperButton.addEventListener("click", () => {
  if (lastResult) {
    renderPaperView(lastResult);
    paperPanel.hidden = false;
    paperPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

printButton.addEventListener("click", () => {
  paperPanel.hidden = false;
  window.print();
});

verifyButton.addEventListener("click", async () => {
  verifyResult.innerHTML = "";
  verifyMessage.textContent = "Checking locally...";
  verifyMessage.style.color = "#5c6a76";
  try {
    const data = await postJson("/api/verify-secret", {
      secret: verifySecretInput.value.trim(),
      ...configPayload(),
    });
    verifyMessage.textContent = "Secret matches the selected format.";
    verifyMessage.style.color = "#0f766e";
    renderVerification(data);
  } catch (error) {
    verifyMessage.textContent = error.data?.message || error.message;
    verifyMessage.style.color = "#b42318";
  }
});

function renderVerification(data) {
  const rows = [
    ["Derived public value", data.address],
    ["Public key", data.public_key_hex],
    ["X-only public key", data.x_only_public_key_hex],
  ].filter(([, value]) => value);
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "result-item";
    const labelEl = document.createElement("strong");
    labelEl.textContent = label;
    const valueEl = document.createElement("code");
    valueEl.textContent = value;
    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "Copy";
    copy.addEventListener("click", () => navigator.clipboard.writeText(value));
    row.append(labelEl, valueEl, copy);
    verifyResult.appendChild(row);
  });
}

[targetInput, networkInput, addressTypeInput, matchModeInput, patternInput, caseSensitiveInput, workersInput].forEach((input) => {
  input.addEventListener("input", () => {
    if (input === targetInput) {
      renderTargetControls();
    }
    lastValidation = null;
    validate().catch(() => {});
  });
});

loadOptions()
  .catch(() => {})
  .finally(() => {
    renderTargetControls();
    validate().catch(() => {});
  });

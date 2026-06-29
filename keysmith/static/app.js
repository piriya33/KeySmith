const form = document.querySelector("#search-form");
const targetInput = document.querySelector("#target");
const networkInput = document.querySelector("#network");
const networkRow = document.querySelector("#network-row");
const addressTypeInput = document.querySelector("#address-type");
const addressTypeLabel = document.querySelector("#address-type-label");
const matchModeInput = document.querySelector("#match-mode");
const patternLabel = document.querySelector("#pattern-label");
const patternInput = document.querySelector("#pattern");
const suffixPatternRow = document.querySelector("#suffix-pattern-row");
const suffixPatternInput = document.querySelector("#suffix-pattern");
const caseSensitiveInput = document.querySelector("#case-sensitive");
const workersInput = document.querySelector("#workers");
const preview = document.querySelector("#pattern-preview");
const suffixPreview = document.querySelector("#suffix-pattern-preview");
const validationMessage = document.querySelector("#validation-message");
const guideName = document.querySelector("#guide-name");
const guideAlphabet = document.querySelector("#guide-alphabet");
const guideCopy = document.querySelector("#guide-copy");
const caseSensitiveCopy = document.querySelector("#case-sensitive-copy");
const statusEl = document.querySelector("#status");
const vizStatEl = document.querySelector("#viz-stat");
const vizPond = document.querySelector("#viz-pond");
const vizRing = document.querySelector("#viz-ring");
const vizRingLabel = document.querySelector("#viz-ring-label");
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
let lastVizStatus = "idle";
let hitDropShown = false;

const DEFAULT_PATTERNS = {
  "bitcoin:mainnet:p2pkh": "1A",
  "bitcoin:mainnet:p2wpkh": "bc1q",
  "bitcoin:mainnet:p2tr": "bc1p",
  "bitcoin:testnet:p2pkh": "mA",
  "bitcoin:testnet:p2wpkh": "tb1q",
  "bitcoin:testnet:p2tr": "tb1p",
  "nostr:nostr:npub": "npub1",
};
const DEFAULT_PATTERN_VALUES = new Set(Object.values(DEFAULT_PATTERNS));

function configPayload() {
  const target = targetInput.value;
  return {
    target,
    network: target === "nostr" ? "nostr" : networkInput.value,
    address_type: target === "nostr" ? "npub" : addressTypeInput.value,
    match_mode: matchModeInput.value,
    pattern: patternInput.value,
    suffix_pattern: suffixPatternInput.value,
    case_sensitive: caseSensitiveInput.checked,
    workers: Number(workersInput.value || 1),
  };
}

function selectedPatternKey() {
  const target = targetInput.value;
  const network = target === "nostr" ? "nostr" : networkInput.value;
  const addressType = target === "nostr" ? "npub" : addressTypeInput.value;
  return `${target}:${network}:${addressType}`;
}

function updatePatternFields(force = false) {
  const nextPattern = DEFAULT_PATTERNS[selectedPatternKey()];
  if (!nextPattern) {
    return;
  }
  const combinedMode = matchModeInput.value === "prefix_suffix";
  const prefixMode = matchModeInput.value === "prefix";
  suffixPatternRow.hidden = !combinedMode;
  suffixPreview.hidden = !combinedMode;
  patternLabel.textContent = combinedMode ? "Prefix" : "Pattern";

  if (prefixMode || combinedMode) {
    patternInput.placeholder = nextPattern;
  } else {
    patternInput.placeholder = "vanity text";
  }
  if ((prefixMode || combinedMode) && (force || !patternInput.value || DEFAULT_PATTERN_VALUES.has(patternInput.value))) {
    patternInput.value = nextPattern;
  }
  if (!prefixMode && !combinedMode && (force || DEFAULT_PATTERN_VALUES.has(patternInput.value))) {
    patternInput.value = "";
  }
  if (combinedMode) {
    suffixPatternInput.placeholder = "ending text";
    if (force || DEFAULT_PATTERN_VALUES.has(suffixPatternInput.value)) {
      suffixPatternInput.value = "";
    }
  }
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
  renderPatternPreview(preview, patternInput.value, invalid, data.guide);
  const invalidSuffix = new Map((data.invalid_suffix_characters || []).map((item) => [item.index, item.char]));
  renderPatternPreview(suffixPreview, suffixPatternInput.value, invalidSuffix, data.guide);
  validationMessage.textContent = data.message;
  validationMessage.style.color = data.valid ? "#0f766e" : "#b42318";
  guideName.textContent = data.guide.startsWith("Base58") ? "Base58" : "Bech32";
  guideAlphabet.textContent = data.alphabet;
  guideCopy.textContent = data.guide;
}

function renderPatternPreview(container, pattern, invalid, guide) {
  container.innerHTML = "";
  for (let index = 0; index < pattern.length; index += 1) {
    const span = document.createElement("span");
    span.textContent = pattern[index];
    if (invalid.has(index)) {
      span.className = "invalid-char";
      span.title = `${pattern[index]} is not valid for ${guide}`;
    }
    container.appendChild(span);
  }
  if (!pattern) {
    container.textContent = "Type a vanity pattern";
  }
}

function renderTargetControls() {
  const isNostr = targetInput.value === "nostr";
  const previousType = addressTypeInput.value;
  networkRow.hidden = isNostr;
  addressTypeLabel.textContent = isNostr ? "Key type" : "Address type";
  addressTypeInput.innerHTML = "";

  const values = isNostr
    ? [["npub", "Nostr npub"]]
    : [
        ["p2pkh", "P2PKH (Legacy Bitcoin Address)"],
        ["p2wpkh", "P2WPKH (Segwit Address)"],
        ["p2tr", "P2TR (Taproot Address)"],
      ];
  values.forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    addressTypeInput.appendChild(option);
  });
  if (values.some(([value]) => value === previousType)) {
    addressTypeInput.value = previousType;
  }

  caseSensitiveInput.checked = !isNostr;
  caseSensitiveInput.disabled = isNostr;
  caseSensitiveCopy.textContent = isNostr ? "Nostr npub matching is lowercase Bech32" : "Case-sensitive matching for Base58";
  updatePatternFields();
}

function renderSnapshot(snapshot) {
  statusEl.textContent = snapshot.status;
  renderSearchVisualization(snapshot);
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

function renderSearchVisualization(snapshot) {
  const attempts = Number(snapshot.attempts || 0);
  const expectedAttempts = Number(snapshot.expected_attempts || 0);
  const status = snapshot.status || "idle";
  const targetSpace = expectedAttempts > 0 ? expectedAttempts : null;
  const searchedPattern = snapshot.estimate?.effective_pattern || "";
  const searchedLength = searchedPattern.length;
  vizStatEl.textContent = targetSpace
    ? `sampled ${attempts.toLocaleString()} / ~${formatLargeNumber(targetSpace)} target space`
    : `sampled ${attempts.toLocaleString()} / waiting for estimate`;

  const diameter = targetRingDiameter(searchedLength);
  vizRing.style.width = `${diameter}px`;
  vizRing.style.height = `${diameter}px`;
  vizRingLabel.textContent = targetSpace
    ? `${searchedLength || 0} searched ${searchedLength === 1 ? "character" : "characters"}; about 1 in ${formatLargeNumber(targetSpace)} attempts`
    : "target ring appears when the search begins";

  if (status !== lastVizStatus && status === "running") {
    hitDropShown = false;
    clearVizDrops();
  }
  lastVizStatus = status;

  if (status === "running") {
    spawnVizDrop(false);
  } else if (status === "found" && !hitDropShown) {
    clearVizDrops();
    spawnVizDrop(true);
    hitDropShown = true;
  }
}

function targetRingDiameter(searchedLength) {
  if (!searchedLength) {
    return 104;
  }
  return Math.max(12, Math.min(150, 170 - searchedLength * 20));
}

function spawnVizDrop(hit) {
  if (!vizPond || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }
  const dot = document.createElement("i");
  dot.className = hit ? "viz-drop hit" : "viz-drop";
  const width = vizPond.clientWidth || 1;
  const height = vizPond.clientHeight || 1;
  let x;
  let y;
  if (hit) {
    const ring = Math.max(28, vizRing.clientWidth || 80);
    x = width / 2 + (Math.random() - 0.5) * ring * 0.52;
    y = height / 2 + (Math.random() - 0.5) * ring * 0.52;
  } else {
    const targetRadius = Math.max(20, (vizRing.clientWidth || 80) / 2 + 10);
    const centerX = width / 2;
    const centerY = height / 2;
    for (let tries = 0; tries < 20; tries += 1) {
      x = 18 + Math.random() * Math.max(1, width - 36);
      y = 18 + Math.random() * Math.max(1, height - 36);
      if (Math.hypot(x - centerX, y - centerY) > targetRadius) {
        break;
      }
    }
  }
  dot.style.left = `${x}px`;
  dot.style.top = `${y}px`;
  vizPond.appendChild(dot);
  window.setTimeout(() => dot.remove(), hit ? 3600 : 2800);
}

function clearVizDrops() {
  vizPond.querySelectorAll(".viz-drop").forEach((drop) => drop.remove());
}

function formatLargeNumber(value) {
  if (!Number.isFinite(value) || value <= 0) {
    return "unknown";
  }
  if (value < 1_000_000) {
    return Math.round(value).toLocaleString();
  }
  return value.toExponential(2).replace("+", "");
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
  const privateExport = result.nsec || result.wif;
  const rows = [
    [isNostr ? "Nostr public key (npub)" : "Public address", result.address],
    [isNostr ? "Private key (nsec)" : "Private key (WIF)", privateExport],
    ["Raw private key hex", result.private_key_hex],
    ["Format", isNostr ? "Nostr npub" : `${result.network} ${result.address_type.toUpperCase()}`],
  ].filter(([, value]) => value);
  paperGrid.innerHTML = "";
  if (result.paper_qr_codes) {
    const qrSection = document.createElement("div");
    qrSection.className = "paper-qr-grid";
    const publicQr = createQrCard(
      isNostr ? "Public npub QR" : "Public address QR",
      result.paper_qr_codes.public,
      result.address,
      "Safe to scan for receiving or identity lookup."
    );
    const privateQr = createQrCard(
      isNostr ? "Private nsec QR" : "Private key QR",
      result.paper_qr_codes.private,
      privateExport,
      isNostr
        ? "Anyone who scans this can control the Nostr identity."
        : "Anyone who scans this can spend funds sent to the address.",
      true
    );
    qrSection.append(publicQr, privateQr);
    paperGrid.appendChild(qrSection);
  }
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

function createQrCard(label, imageSource, value, warning, sensitive = false) {
  const block = document.createElement("div");
  block.className = sensitive ? "qr-card sensitive" : "qr-card";
  const title = document.createElement("strong");
  title.textContent = label;
  const image = document.createElement("img");
  image.src = imageSource;
  image.alt = label;
  const copy = document.createElement("p");
  copy.className = sensitive ? "qr-warning" : "qr-note";
  copy.textContent = warning;
  const valueEl = document.createElement("code");
  valueEl.textContent = value;
  block.append(title, image, copy, valueEl);
  return block;
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

[targetInput, networkInput, addressTypeInput, matchModeInput, patternInput, suffixPatternInput, caseSensitiveInput, workersInput].forEach((input) => {
  input.addEventListener("input", () => {
    if (input === targetInput) {
      renderTargetControls();
    } else if (input === networkInput || input === addressTypeInput || input === matchModeInput) {
      updatePatternFields();
    }
    lastValidation = null;
    validate().catch(() => {});
  });
});

loadOptions()
  .catch(() => {})
  .finally(() => {
    renderTargetControls();
    updatePatternFields(true);
    validate().catch(() => {});
  });

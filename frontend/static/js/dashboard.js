const elements = {
  count: document.getElementById("human-count"),
  countDetail: document.getElementById("count-detail"),
  camera: document.getElementById("camera-status"),
  model: document.getElementById("model-status"),
  arduino: document.getElementById("arduino-status"),
  header: document.querySelector(".header-status"),
  headerText: document.getElementById("header-status-text"),
  liveBadge: document.getElementById("live-badge"),
  fps: document.getElementById("fps-value"),
  inference: document.getElementById("inference-value"),
  modelName: document.getElementById("model-name"),
  resolution: document.getElementById("resolution-value"),
  videoResolution: document.getElementById("video-resolution"),
  lastUpdate: document.getElementById("last-update"),
  source: document.getElementById("source-text"),
  error: document.getElementById("error-text"),
  activityCount: document.getElementById("activity-count"),
  activityFeed: document.getElementById("activity-feed"),
  image: document.getElementById("video-feed"),
  placeholder: document.getElementById("video-placeholder"),
  stateTitle: document.getElementById("video-state-title"),
  stateDetail: document.getElementById("video-state-detail"),
  stage: document.getElementById("video-stage"),
  boxes: document.getElementById("boxes-toggle"),
  labels: document.getElementById("labels-toggle"),
  fullscreen: document.getElementById("fullscreen-toggle"),
};

const controls = { boxes: true, labels: true };
let previousCount = null;

function readableStatus(status) {
  return (status || "unknown").replaceAll("_", " ");
}

function setStatus(element, status) {
  element.dataset.status = status;
  element.textContent = readableStatus(status);
}

function setHeaderStatus(status) {
  elements.header.dataset.status = status;
  elements.headerText.textContent = readableStatus(status);
  elements.liveBadge.dataset.status = status;
  elements.liveBadge.querySelector("span:last-child").textContent = status === "connected" ? "Live" : readableStatus(status);
}

function relativeTime(timestamp) {
  if (!timestamp) return "No successful detection yet";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 2) return "Updated just now";
  return `Updated ${seconds}s ago`;
}

function renderEvents(events) {
  elements.activityCount.textContent = events.length;
  elements.activityFeed.replaceChildren();
  if (!events.length) {
    const empty = document.createElement("li");
    empty.className = "activity-empty";
    empty.textContent = "Waiting for the detection worker.";
    elements.activityFeed.append(empty);
    return;
  }
  events.forEach((event) => {
    const item = document.createElement("li");
    item.dataset.level = event.level || "info";
    const message = document.createElement("span");
    message.textContent = event.message;
    const timestamp = document.createElement("time");
    timestamp.textContent = new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    item.append(message, timestamp);
    elements.activityFeed.append(item);
  });
}

function showVideoState(payload) {
  const available = payload.camera === "connected" && payload.count_valid;
  elements.placeholder.classList.toggle("is-hidden", available);
  if (available) return;
  const reconnecting = payload.camera === "connecting" || payload.camera === "reconnecting";
  elements.stateTitle.textContent = reconnecting ? "Reconnecting to CAM 01" : "CAM 01 is offline";
  elements.stateDetail.textContent = payload.last_error || (reconnecting ? "Waiting for the next annotated frame." : "The live detection worker is unavailable.");
}

function renderStatus(payload) {
  setStatus(elements.camera, payload.camera);
  setStatus(elements.model, payload.model);
  setStatus(elements.arduino, payload.arduino);
  setHeaderStatus(payload.camera);

  if (payload.count_valid && Number.isInteger(payload.human_count)) {
    const value = String(payload.human_count).padStart(2, "0");
    elements.count.textContent = value;
    elements.countDetail.textContent = "People currently visible in the camera view";
    if (previousCount !== value) {
      elements.count.classList.remove("changed");
      void elements.count.offsetWidth;
      elements.count.classList.add("changed");
      previousCount = value;
    }
  } else {
    elements.count.textContent = "—";
    elements.countDetail.textContent = payload.count_stale ? "Detection data is stale" : "No valid current detection result";
    previousCount = null;
  }

  elements.fps.textContent = payload.fps ? `${payload.fps.toFixed(1)} fps` : "—";
  elements.inference.textContent = payload.inference_ms !== null ? `${payload.inference_ms.toFixed(0)} ms` : "—";
  elements.modelName.textContent = payload.model_name || "YOLO11n";
  const resolution = payload.resolution ? `${payload.resolution.width} × ${payload.resolution.height}` : "Awaiting frame";
  elements.resolution.textContent = resolution;
  elements.videoResolution.textContent = payload.resolution ? resolution : "Awaiting stream";
  elements.lastUpdate.textContent = relativeTime(payload.last_detection_at);
  elements.source.textContent = payload.source ? `Source: ${payload.source}` : "Camera source unavailable";
  elements.error.textContent = payload.last_error || "";
  renderEvents(payload.events || []);
  showVideoState(payload);
}

function refreshVideoFeed() {
  elements.placeholder.classList.remove("is-hidden");
  elements.image.src = `/video_feed?boxes=${controls.boxes}&labels=${controls.labels}&t=${Date.now()}`;
}

async function pollStatus() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) throw new Error("Status endpoint unavailable");
    renderStatus(await response.json());
  } catch (error) {
    renderStatus({ camera: "disconnected", model: "unknown", arduino: "unknown", count_valid: false, count_stale: false, fps: 0, inference_ms: null, events: [], last_error: "Dashboard backend is unavailable." });
  }
}

function bindToggle(button, key) {
  button.addEventListener("click", () => {
    controls[key] = !controls[key];
    button.classList.toggle("is-active", controls[key]);
    button.setAttribute("aria-pressed", String(controls[key]));
    refreshVideoFeed();
  });
}

bindToggle(elements.boxes, "boxes");
bindToggle(elements.labels, "labels");
elements.fullscreen.addEventListener("click", async () => {
  if (document.fullscreenElement) await document.exitFullscreen();
  else await elements.stage.requestFullscreen();
});
elements.image.addEventListener("load", () => elements.placeholder.classList.add("is-hidden"));
elements.image.addEventListener("error", () => elements.placeholder.classList.remove("is-hidden"));

refreshVideoFeed();
pollStatus();
window.setInterval(pollStatus, 500);

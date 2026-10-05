const API_BASE = "http://127.0.0.1:8000";

let chats = [];
let activeChatId = null;
let pendingAgentEl = null;
let pendingAgentText = "";
let browseCurrentPath = null;
let activeAbortController = null;

// Activity indicator state (the "agent working" panel)
let activityEl = null;
let activityStages = [];
let activityExpanded = true;

// ---------- small helpers ----------

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ---------- chat management ----------

async function loadChatList() {
  chats = await api("/chat_list");
  renderChatList();
}

async function createChat() {
  const chat = await api("/chat", { method: "POST" });
  chats.unshift({ ...chat, created_at: new Date().toISOString() });
  renderChatList();
  await selectChat(chat.thread_id);
}

async function selectChat(threadId) {
  activeChatId = threadId;
  finishStreamingIfAny();
  clearActivity();
  renderChatList();

  messagesEl.innerHTML = "";
  const history = await api(`/chat/${threadId}`);
  history.forEach(turn => {
    if (turn.query) renderMessageBubble("user", turn.query);
    if (turn.response) renderMessageBubble("agent", turn.response, true);
  });

  updateEmptyState();
}

async function deleteChat(threadId, event) {
  event.stopPropagation();
  await api(`/chat/${threadId}`, { method: "DELETE" });
  chats = chats.filter(c => c.thread_id !== threadId);
  renderChatList();

  if (activeChatId === threadId) {
    if (chats.length > 0) {
      await selectChat(chats[0].thread_id);
    } else {
      await createChat();
    }
  }
}

// ---------- sending a message (SSE streaming) ----------

async function sendMessage(text) {
  if (!activeChatId || !text.trim()) return;

  renderMessageBubble("user", text);
  updateEmptyState();
  startActivity();
  setStreamingUI(true);

  activeAbortController = new AbortController();

  try {
    const res = await fetch(`${API_BASE}/message-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: activeChatId, message: text }),
      signal: activeAbortController.signal
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop();

      for (const raw of events) {
        if (!raw.startsWith("data: ")) continue;
        handleServerMessage(JSON.parse(raw.slice(6)));
      }
    }

    await loadChatList();
    renderChatList();

  } catch (err) {
    clearActivity();
    if (err.name === "AbortError") {
      renderSystemNote("Stopped.");
    } else {
      renderMessageBubble("error", `Error: ${err.message}`);
    }
  } finally {
    activeAbortController = null;
    setStreamingUI(false);
  }
}

function handleServerMessage(data) {
  switch (data.type) {

    case "stage":
      addActivityStage(data.content);
      break;

    case "token":
      finishActivity();
      if (!pendingAgentEl) {
        pendingAgentEl = renderMessageBubble("agent", "");
        pendingAgentText = "";
      }
      pendingAgentText += data.content;
      pendingAgentEl.textContent = pendingAgentText;
      scrollToBottom();
      break;

    case "message":
      finishActivity();
      renderMessageBubble("agent", data.content, true);
      break;

    case "interrupt":
      finishActivity();
      renderMessageBubble("interrupt", data.content, true);
      break;

    case "sources":
      renderSourcesSection(data.items);
      break;

    case "done":
      if (pendingAgentEl) {
        renderMarkdownInto(pendingAgentEl, pendingAgentText);
      }
      finishStreamingIfAny();
      clearActivity();
      break;

    case "error":
      finishActivity();
      clearActivity();
      renderMessageBubble("error", `Error: ${data.message}`);
      break;
  }
}

function finishStreamingIfAny() {
  pendingAgentEl = null;
  pendingAgentText = "";
}

// ---------- agent activity indicator ----------

function startActivity() {
  activityStages = [];
  activityExpanded = true;
  activityEl = document.createElement("div");
  activityEl.className = "activity";
  renderActivityEl();
  messagesEl.appendChild(activityEl);
  scrollToBottom();
}

function addActivityStage(label) {
  if (!activityEl) startActivity();
  activityStages.push(label);
  renderActivityEl();
  scrollToBottom();
}

function renderActivityEl() {
  if (!activityEl) return;
  const latest = activityStages[activityStages.length - 1] || "Working...";

  activityEl.innerHTML = `
    <button type="button" class="activity-toggle">
      <span class="activity-dot"></span>
      <span class="activity-label">${escapeHtml(latest)}</span>
      <span class="activity-chevron">${activityExpanded ? "\u25BE" : "\u25B8"}</span>
    </button>
    ${activityExpanded && activityStages.length > 0 ? `
      <div class="activity-steps">
        ${activityStages.map(s => `<div class="activity-step">${escapeHtml(s)}</div>`).join("")}
      </div>` : ""}
  `;

  activityEl.querySelector(".activity-toggle").onclick = () => {
    activityExpanded = !activityExpanded;
    renderActivityEl();
  };
}

function finishActivity() {
  if (activityEl) {
    activityExpanded = false;
    renderActivityEl();
  }
}

function clearActivity() {
  activityEl = null;
  activityStages = [];
}

// ---------- sources panel ----------

function renderSourcesSection(items) {
  if (!items || items.length === 0) return;

  const wrapper = document.createElement("div");
  wrapper.className = "sources";
  wrapper.innerHTML = `
    <button type="button" class="sources-toggle">Sources &middot; ${items.length}</button>
    <div class="sources-list hidden">
      ${items.map(s => s.type === "web"
        ? `<a class="source-item" href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.name || s.url)}</a>`
        : `<div class="source-item source-doc">${escapeHtml(s.name)}</div>`
      ).join("")}
    </div>
  `;

  wrapper.querySelector(".sources-toggle").onclick = () => {
    wrapper.querySelector(".sources-list").classList.toggle("hidden");
  };

  messagesEl.appendChild(wrapper);
  scrollToBottom();
}

// ---------- file upload ----------

async function uploadFile(file) {
  renderSystemNote(`Uploading ${file.name}...`);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed");
    renderSystemNote(data.message);
  } catch (err) {
    renderSystemNote(`Upload failed: ${err.message}`);
  }
}

// ---------- rendering ----------

const messagesEl = document.getElementById("messages");

function renderMarkdownInto(el, text) {
  el.innerHTML = marked.parse(text || "");
}

function renderMessageBubble(role, content, markdown = false) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  if (markdown) {
    renderMarkdownInto(div, content);
  } else {
    div.textContent = content;
  }
  messagesEl.appendChild(div);
  scrollToBottom();
  return div;
}

function renderSystemNote(text) {
  renderMessageBubble("system", text);
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateEmptyState() {
  const isEmpty = messagesEl.children.length === 0;
  document.getElementById("emptyState").classList.toggle("hidden", !isEmpty);
  messagesEl.classList.toggle("hidden", isEmpty);
}

// ---------- sidebar: chat list, search, date grouping ----------

function groupChatsByDate(list) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const weekAgo = new Date(today); weekAgo.setDate(today.getDate() - 7);

  const groups = { "Today": [], "Yesterday": [], "Previous 7 days": [], "Older": [] };

  list.forEach(chat => {
    const d = new Date(chat.created_at);
    const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    if (dayStart.getTime() === today.getTime()) groups["Today"].push(chat);
    else if (dayStart.getTime() === yesterday.getTime()) groups["Yesterday"].push(chat);
    else if (dayStart >= weekAgo) groups["Previous 7 days"].push(chat);
    else groups["Older"].push(chat);
  });

  return groups;
}

function renderChatList() {
  const listEl = document.getElementById("chatList");
  listEl.innerHTML = "";

  const query = (document.getElementById("searchInput").value || "").toLowerCase().trim();
  const filtered = query
    ? chats.filter(c => c.title.toLowerCase().includes(query))
    : chats;

  if (filtered.length === 0) {
    const empty = document.createElement("div");
    empty.className = "chat-list-empty";
    empty.textContent = query ? "No matching chats" : "No chats yet";
    listEl.appendChild(empty);
    return;
  }

  const groups = groupChatsByDate(filtered);

  Object.entries(groups).forEach(([label, group]) => {
    if (group.length === 0) return;

    const heading = document.createElement("div");
    heading.className = "chat-group-label";
    heading.textContent = label;
    listEl.appendChild(heading);

    group.forEach(chat => {
      const item = document.createElement("div");
      item.className = "chat-item" + (chat.thread_id === activeChatId ? " active" : "");

      const title = document.createElement("span");
      title.className = "chat-item-title";
      title.textContent = chat.title;
      item.appendChild(title);

      const del = document.createElement("span");
      del.className = "chat-item-delete";
      del.textContent = "\u00D7";
      del.title = "Delete chat";
      del.onclick = (e) => deleteChat(chat.thread_id, e);
      item.appendChild(del);

      item.onclick = () => selectChat(chat.thread_id);
      listEl.appendChild(item);
    });
  });
}

// ---------- composer state ----------

function setStreamingUI(isStreaming) {
  const sendBtn = document.getElementById("sendBtn");
  sendBtn.innerHTML = isStreaming ? "&#9632;" : "&#10148;";
  sendBtn.classList.toggle("stop-mode", isStreaming);
  sendBtn.title = isStreaming ? "Stop" : "Send";
  document.getElementById("textInput").disabled = isStreaming;
}

// ---------- settings ----------

async function checkFolderStatus(path) {
  const badge = document.getElementById("folderStatusBadge");

  if (!path) {
    badge.textContent = "Not configured";
    badge.className = "status-badge status-warn";
    return;
  }

  badge.textContent = "Checking\u2026";
  badge.className = "status-badge status-unknown";

  try {
    await api(`/browse-folder?path=${encodeURIComponent(path)}`);
    badge.textContent = "Ready";
    badge.className = "status-badge status-ok";
  } catch (err) {
    badge.textContent = "Error";
    badge.className = "status-badge status-error";
  }
}

async function openSettings() {
  const settings = await api("/setting");
  document.getElementById("folderPathInput").value = settings.folder_path || "";
  document.getElementById("settingsModal").classList.remove("hidden");
  checkFolderStatus(settings.folder_path);
}

function closeSettings() {
  document.getElementById("settingsModal").classList.add("hidden");
}

// ---------- folder browser (no native dialog -- works in any environment) ----------

async function openBrowseModal() {
  document.getElementById("browseModal").classList.remove("hidden");
  const startPath = document.getElementById("folderPathInput").value.trim() || null;
  await loadBrowseDirectory(startPath);
}

function closeBrowseModal() {
  document.getElementById("browseModal").classList.add("hidden");
}

async function loadBrowseDirectory(path) {
  try {
    const query = path ? `?path=${encodeURIComponent(path)}` : "";
    const data = await api(`/browse-folder${query}`);
    browseCurrentPath = data.current_path;
    renderBrowseModal(data);
  } catch (err) {
    alert(`Could not open that folder: ${err.message}`);
  }
}

function renderBrowseModal(data) {
  document.getElementById("browsePath").textContent = data.current_path;

  const listEl = document.getElementById("browseList");
  listEl.innerHTML = "";

  if (data.parent_path) {
    const up = document.createElement("div");
    up.className = "browse-item browse-up";
    up.textContent = ".. (up one level)";
    up.onclick = () => loadBrowseDirectory(data.parent_path);
    listEl.appendChild(up);
  }

  if (data.directories.length === 0) {
    const empty = document.createElement("div");
    empty.className = "browse-empty";
    empty.textContent = "No subfolders here";
    listEl.appendChild(empty);
  }

  data.directories.forEach(name => {
    const item = document.createElement("div");
    item.className = "browse-item";
    item.textContent = name;
    item.onclick = () => loadBrowseDirectory(`${data.current_path}/${name}`);
    listEl.appendChild(item);
  });
}

// ---------- sidebar collapse ----------

function setSidebarCollapsed(collapsed) {
  document.getElementById("sidebar").classList.toggle("collapsed", collapsed);
  document.getElementById("expandSidebarBtn").classList.toggle("hidden", !collapsed);
  localStorage.setItem("sidebarCollapsed", collapsed ? "1" : "0");
}

// ---------- wiring ----------

document.getElementById("newChatBtn").onclick = createChat;
document.getElementById("settingsBtn").onclick = openSettings;
document.getElementById("closeSettingsBtn").onclick = closeSettings;
document.getElementById("browseFolderBtn").onclick = openBrowseModal;
document.getElementById("cancelBrowseBtn").onclick = closeBrowseModal;
document.getElementById("collapseSidebarBtn").onclick = () => setSidebarCollapsed(true);
document.getElementById("expandSidebarBtn").onclick = () => setSidebarCollapsed(false);

document.getElementById("searchInput").addEventListener("input", renderChatList);

document.getElementById("selectBrowseBtn").onclick = () => {
  document.getElementById("folderPathInput").value = browseCurrentPath;
  closeBrowseModal();
};

document.getElementById("saveSettingsBtn").onclick = async () => {
  const folder_path = document.getElementById("folderPathInput").value.trim();
  await api("/setting", { method: "PUT", body: JSON.stringify({ folder_path }) });
  checkFolderStatus(folder_path);
  closeSettings();
};

document.getElementById("folderPathInput").addEventListener("blur", (e) => {
  checkFolderStatus(e.target.value.trim());
});

document.querySelectorAll(".suggestion-chip").forEach(chip => {
  chip.onclick = () => sendMessage(chip.dataset.prompt);
});

const textInputEl = document.getElementById("textInput");

textInputEl.addEventListener("input", () => {
  textInputEl.style.height = "auto";
  textInputEl.style.height = Math.min(textInputEl.scrollHeight, 160) + "px";
});

textInputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("composer").requestSubmit();
  }
});

document.getElementById("composer").onsubmit = (e) => {
  e.preventDefault();

  if (activeAbortController) {
    activeAbortController.abort();
    return;
  }

  const text = textInputEl.value.trim();
  if (!text) return;

  textInputEl.value = "";
  textInputEl.style.height = "auto";
  sendMessage(text);
};

document.getElementById("attachBtn").onclick = () => {
  document.getElementById("fileInput").click();
};

document.getElementById("fileInput").onchange = (e) => {
  const file = e.target.files[0];
  if (file) uploadFile(file);
  e.target.value = "";
};

// ---------- boot ----------

(async function boot() {
  if (localStorage.getItem("sidebarCollapsed") === "1") {
    setSidebarCollapsed(true);
  }

  await loadChatList();

  if (chats.length === 0) {
    await createChat();
  } else {
    await selectChat(chats[0].thread_id);
  }

  const settings = await api("/setting");
  if (!settings.folder_path) {
    // Don't force the modal open -- general chat and web-search questions
    // work without a folder. The empty state and settings status badge
    // already make it clear when one is needed.
  }
})();

const API_BASE = "http://127.0.0.1:8000";

let chats = [];
let activeChatId = null;
let pendingAgentEl = null;
let pendingAgentText = "";
let browseCurrentPath = null;

// ---------- API helpers ----------

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
  chats.unshift(chat);
  renderChatList();
  await selectChat(chat.thread_id);
}

async function selectChat(threadId) {
  activeChatId = threadId;
  finishStreamingIfAny();
  renderChatList();

  messagesEl.innerHTML = "";
  const history = await api(`/chat/${threadId}`);
  history.forEach(turn => {
    if (turn.query) renderMessageBubble("user", turn.query);
    if (turn.response) renderMessageBubble("agent", turn.response, true);
  });
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

  // No folder-path gate here -- most intents (general chat, RAG on already
  // ingested docs, DB questions) never need a folder at all. The backend's
  // own router already handles "no path set" gracefully, only when a
  // document-related query actually requires one.

  renderMessageBubble("user", text);
  setComposerEnabled(false);

  try {
    const res = await fetch(`${API_BASE}/message-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: activeChatId, message: text })
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
        const data = JSON.parse(raw.slice(6));
        handleServerMessage(data);
      }
    }

    await loadChatList();
    renderChatList();

  } catch (err) {
    finishStreamingIfAny();
    renderMessageBubble("error", `Error: ${err.message}`);
    setComposerEnabled(true);
  }
}

function handleServerMessage(data) {
  switch (data.type) {

    case "token":
      // Plain text while streaming -- re-rendered as Markdown once "done".
      if (!pendingAgentEl) {
        pendingAgentEl = renderMessageBubble("agent", "");
        pendingAgentText = "";
      }
      pendingAgentText += data.content;
      pendingAgentEl.textContent = pendingAgentText;
      scrollToBottom();
      break;

    case "message":
      finishStreamingIfAny();
      renderMessageBubble("agent", data.content, true);
      break;

    case "interrupt":
      finishStreamingIfAny();
      renderMessageBubble("interrupt", data.content, true);
      break;

    case "done":
      if (pendingAgentEl) {
        renderMarkdownInto(pendingAgentEl, pendingAgentText);
      }
      finishStreamingIfAny();
      setComposerEnabled(true);
      break;

    case "error":
      finishStreamingIfAny();
      renderMessageBubble("error", `Error: ${data.message}`);
      setComposerEnabled(true);
      break;
  }
}

function finishStreamingIfAny() {
  pendingAgentEl = null;
  pendingAgentText = "";
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

function renderChatList() {
  const listEl = document.getElementById("chatList");
  listEl.innerHTML = "";
  chats.forEach(chat => {
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
}

function setComposerEnabled(enabled) {
  document.getElementById("textInput").disabled = !enabled;
  document.querySelector(".send-btn").disabled = !enabled;
}

// ---------- settings ----------

async function openSettings() {
  const settings = await api("/setting");
  document.getElementById("folderPathInput").value = settings.folder_path || "";
  document.getElementById("settingsModal").classList.remove("hidden");
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

// ---------- wiring ----------

document.getElementById("newChatBtn").onclick = createChat;
document.getElementById("settingsBtn").onclick = openSettings;
document.getElementById("closeSettingsBtn").onclick = closeSettings;
document.getElementById("browseFolderBtn").onclick = openBrowseModal;
document.getElementById("cancelBrowseBtn").onclick = closeBrowseModal;

document.getElementById("selectBrowseBtn").onclick = () => {
  document.getElementById("folderPathInput").value = browseCurrentPath;
  closeBrowseModal();
};

document.getElementById("saveSettingsBtn").onclick = async () => {
  const folder_path = document.getElementById("folderPathInput").value.trim();
  await api("/setting", { method: "PUT", body: JSON.stringify({ folder_path }) });
  closeSettings();
};

document.getElementById("composer").onsubmit = (e) => {
  e.preventDefault();
  const input = document.getElementById("textInput");
  const text = input.value;
  input.value = "";
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
  await loadChatList();

  if (chats.length === 0) {
    await createChat();
  } else {
    await selectChat(chats[0].thread_id);
  }

  const settings = await api("/setting");
  if (!settings.folder_path) {
    openSettings();
  }
})();
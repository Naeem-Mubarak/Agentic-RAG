const API_BASE = "http://127.0.0.1:8000";
const WS_BASE = "ws://127.0.0.1:8000/RAG_application";

const SETTINGS_KEY = "agentic_rag_settings";

let chats = [];
let activeChatId = null;
let socket = null;

let pendingAgentEl = null;
let pendingAgentText = "";

let waitingForInterrupt = false;


// =========================================================
// SETTINGS
// =========================================================

function getSettings() {

  const raw =
    localStorage.getItem(
      SETTINGS_KEY
    );

  return raw
    ? JSON.parse(raw)
    : {
        folderPath: ""
      };

}


function saveSettings(settings) {

  localStorage.setItem(
    SETTINGS_KEY,
    JSON.stringify(settings)
  );

}


// =========================================================
// CHAT API
// =========================================================

async function createChatOnServer() {

  const response =
    await fetch(
      `${API_BASE}/chats`,
      {
        method: "POST"
      }
    );


  if (!response.ok) {

    throw new Error(
      "Failed to create chat"
    );

  }


  return await response.json();

}


async function loadChatsFromServer() {

  const response =
    await fetch(
      `${API_BASE}/chats`
    );


  if (!response.ok) {

    throw new Error(
      "Failed to load chats"
    );

  }


  return await response.json();

}


async function loadChatHistory(
  threadId
) {

  const response =
    await fetch(
      `${API_BASE}/chats/${encodeURIComponent(threadId)}`
    );


  if (!response.ok) {

    throw new Error(
      "Failed to load chat history"
    );

  }


  return await response.json();

}


// =========================================================
// CHAT MANAGEMENT
// =========================================================

async function createChat() {

  try {

    // -------------------------------------------------
    // Backend generates UUID
    // -------------------------------------------------

    const data =
      await createChatOnServer();


    const chat = {

      id:
        data.thread_id,

      title:
        data.title || "New chat",

      threadId:
        data.thread_id,

      messages: []

    };


    chats.unshift(
      chat
    );


    activeChatId =
      chat.id;


    waitingForInterrupt =
      false;


    renderChatList();

    renderMessages();


    connectSocket();


  } catch (error) {

    renderSystemNote(
      `Failed to create chat: ${error.message}`
    );

  }

}


async function selectChat(
  chatId
) {

  const chat =
    chats.find(
      c => c.id === chatId
    );


  if (!chat) {

    return;

  }


  activeChatId =
    chatId;


  waitingForInterrupt =
    false;


  closeSocket();

  finishStreamingIfAny();


  renderChatList();

  renderMessages();


  connectSocket(() => {

    socket.send(
      JSON.stringify({

        type:
          "select_chat",

        thread_id:
          chat.threadId

      })
    );

  });

}


function getActiveChat() {

  return chats.find(
    c => c.id === activeChatId
  );

}


function addMessage(
  role,
  content
) {

  const chat =
    getActiveChat();


  if (!chat) {

    return;

  }


  chat.messages.push({

    role,

    content

  });

}


// =========================================================
// WEBSOCKET
// =========================================================

function connectSocket(
  onOpen = null
) {

  socket =
    new WebSocket(
      WS_BASE
    );


  socket.onopen = () => {

    console.log(
      "WebSocket connected"
    );


    if (onOpen) {

      onOpen();

    }

  };


  socket.onmessage = (
    event
  ) => {

    try {

      const data =
        JSON.parse(
          event.data
        );


      handleServerMessage(
        data
      );


    } catch (error) {

      console.error(
        "Invalid server message:",
        event.data
      );

    }

  };


  socket.onerror = () => {

    renderSystemNote(
      "Connection error — is the backend running?"
    );


    setComposerEnabled(
      true
    );

  };


  socket.onclose = () => {

    console.log(
      "WebSocket disconnected"
    );

  };

}


function closeSocket() {

  if (socket) {

    socket.close();

    socket = null;

  }

}


// =========================================================
// SERVER MESSAGE HANDLER
// =========================================================

function handleServerMessage(
  data
) {

  const chat =
    getActiveChat();


  if (!chat) {

    return;

  }


  switch (data.type) {


    // -----------------------------------------------------
    // Chat history
    // -----------------------------------------------------

    case "chat_history":

      loadHistoryIntoChat(
        chat,
        data.messages || []
      );

      break;


    // -----------------------------------------------------
    // Streaming token
    // -----------------------------------------------------

    case "token":

      if (!pendingAgentEl) {

        pendingAgentEl =
          renderMessageBubble(
            "agent",
            ""
          );

        pendingAgentText =
          "";

      }


      pendingAgentText +=
        data.content;


      pendingAgentEl.textContent =
        pendingAgentText;


      scrollToBottom();

      break;


    // -----------------------------------------------------
    // Complete message
    // -----------------------------------------------------

    case "message":

      finishStreamingIfAny();


      renderMessageBubble(
        "agent",
        data.content
      );


      addMessage(
        "agent",
        data.content
      );


      break;


    // -----------------------------------------------------
    // LangGraph interrupt
    // -----------------------------------------------------

    case "interrupt":

      finishStreamingIfAny();


      renderMessageBubble(
        "interrupt",
        data.content
      );


      addMessage(
        "interrupt",
        data.content
      );


      // ---------------------------------------------
      // The next user message is a resume value
      // ---------------------------------------------

      waitingForInterrupt =
        true;


      setComposerEnabled(
        true
      );


      break;


    // -----------------------------------------------------
    // Query completed
    // -----------------------------------------------------

    case "done":

      if (
        pendingAgentEl &&
        pendingAgentText
      ) {

        addMessage(
          "agent",
          pendingAgentText
        );

      }


      finishStreamingIfAny();


      waitingForInterrupt =
        false;


      setComposerEnabled(
        true
      );


      break;


    // -----------------------------------------------------
    // Error
    // -----------------------------------------------------

    case "error":

      finishStreamingIfAny();


      waitingForInterrupt =
        false;


      renderMessageBubble(
        "error",
        `Error: ${data.message}`
      );


      setComposerEnabled(
        true
      );


      break;


    default:

      console.log(
        "Unknown server message:",
        data
      );

  }

}


// =========================================================
// HISTORY
// =========================================================

function loadHistoryIntoChat(
  chat,
  messages
) {

  chat.messages = [];


  for (
    const message of messages
  ) {

    chat.messages.push({

      role:
        message.role,

      content:
        message.content

    });

  }


  renderMessages();

}


// =========================================================
// STREAMING
// =========================================================

function finishStreamingIfAny() {

  pendingAgentEl =
    null;

  pendingAgentText =
    "";

}


// =========================================================
// SEND MESSAGE
// =========================================================

function sendMessage(
  text
) {

  const chat =
    getActiveChat();


  if (
    !chat ||
    !text.trim()
  ) {

    return;

  }


  text =
    text.trim();


  // =====================================================
  // INTERRUPT RESPONSE
  // =====================================================

  if (waitingForInterrupt) {

    renderMessageBubble(
      "user",
      text
    );


    // -------------------------------------------------
    // Do NOT save this as a normal query.
    // It is only the LangGraph resume value.
    // -------------------------------------------------

    if (
      socket &&
      socket.readyState === WebSocket.OPEN
    ) {

      socket.send(
        JSON.stringify({

          type:
            "interrupt_response",

          thread_id:
            chat.threadId,

          response:
            text

        })
      );


      waitingForInterrupt =
        false;


      setComposerEnabled(
        false
      );


      return;

    }


    renderSystemNote(
      "WebSocket is not connected."
    );


    return;

  }


  // =====================================================
  // NORMAL QUERY
  // =====================================================

  if (
    chat.messages.length === 0
  ) {

    chat.title =
      text.slice(0, 40);

  }


  // -----------------------------------------------------
  // Render user message
  // -----------------------------------------------------

  renderMessageBubble(
    "user",
    text
  );


  addMessage(
    "user",
    text
  );


  renderChatList();


  setComposerEnabled(
    false
  );


  const message =
    JSON.stringify({

      type:
        "query",

      thread_id:
        chat.threadId,

      query:
        text

    });


  // -----------------------------------------------------
  // Socket not connected
  // -----------------------------------------------------

  if (
    !socket ||
    socket.readyState !== WebSocket.OPEN
  ) {

    connectSocket(() => {

      socket.send(
        message
      );

    });

  }

  else {

    socket.send(
      message
    );

  }

}


// =========================================================
// UPLOAD
// =========================================================

async function uploadFile(
  file
) {

  if (!file) {

    return;

  }


  // -----------------------------------------------------
  // Frontend validation
  // -----------------------------------------------------

  if (
    !file.name
      .toLowerCase()
      .endsWith(".pdf")
  ) {

    renderSystemNote(
      "Only PDF files are supported."
    );

    return;

  }


  const formData =
    new FormData();


  formData.append(
    "file",
    file
  );


  renderSystemNote(
    `Uploading ${file.name}...`
  );


  try {

    const response =
      await fetch(
        `${API_BASE}/upload`,
        {

          method:
            "POST",

          body:
            formData

        }
      );


    const data =
      await response.json();


    if (!response.ok) {

      throw new Error(
        data.detail ||
        data.error ||
        "Upload failed"
      );

    }


    renderSystemNote(
      `Uploaded: ${data.filename}`
    );


  } catch (error) {

    renderSystemNote(
      `Upload failed: ${error.message}`
    );

  }

}


// =========================================================
// RENDERING
// =========================================================

const messagesEl =
  document.getElementById(
    "messages"
  );


function renderMessages() {

  messagesEl.innerHTML =
    "";


  const chat =
    getActiveChat();


  if (!chat) {

    return;

  }


  chat.messages.forEach(
    message => {

      renderMessageBubble(
        message.role,
        message.content
      );

    }
  );

}


function renderMessageBubble(
  role,
  content
) {

  const div =
    document.createElement(
      "div"
    );


  div.className =
    `message ${role}`;


  div.textContent =
    content;


  messagesEl.appendChild(
    div
  );


  scrollToBottom();


  return div;

}


function renderSystemNote(
  text
) {

  renderMessageBubble(
    "system",
    text
  );

}


function scrollToBottom() {

  messagesEl.scrollTop =
    messagesEl.scrollHeight;

}


// =========================================================
// CHAT LIST
// =========================================================

function renderChatList() {

  const listEl =
    document.getElementById(
      "chatList"
    );


  listEl.innerHTML =
    "";


  chats.forEach(
    chat => {

      const item =
        document.createElement(
          "div"
        );


      item.className =
        "chat-item" +
        (
          chat.id === activeChatId
            ? " active"
            : ""
        );


      item.textContent =
        chat.title;


      item.onclick = () => {

        selectChat(
          chat.id
        );

      };


      listEl.appendChild(
        item
      );

    }
  );

}


// =========================================================
// COMPOSER
// =========================================================

function setComposerEnabled(
  enabled
) {

  document.getElementById(
    "textInput"
  ).disabled =
    !enabled;


  document.querySelector(
    ".send-btn"
  ).disabled =
    !enabled;

}


// =========================================================
// SETTINGS
// =========================================================

function openSettings() {

  document.getElementById(
    "folderPathInput"
  ).value =
    getSettings().folderPath || "";


  document.getElementById(
    "settingsModal"
  ).classList.remove(
    "hidden"
  );

}


function closeSettings() {

  document.getElementById(
    "settingsModal"
  ).classList.add(
    "hidden"
  );

}


// =========================================================
// EVENT HANDLERS
// =========================================================

document.getElementById(
  "newChatBtn"
).onclick = () => {

  createChat();

};


document.getElementById(
  "settingsBtn"
).onclick = () => {

  openSettings();

};


document.getElementById(
  "closeSettingsBtn"
).onclick = () => {

  closeSettings();

};


document.getElementById(
  "saveSettingsBtn"
).onclick = () => {

  const folderPath =
    document.getElementById(
      "folderPathInput"
    ).value.trim();


  saveSettings({

    folderPath

  });


  closeSettings();

};


document.getElementById(
  "composer"
).onsubmit = (
  event
) => {

  event.preventDefault();


  const input =
    document.getElementById(
      "textInput"
    );


  const text =
    input.value.trim();


  if (!text) {

    return;

  }


  input.value =
    "";


  sendMessage(
    text
  );

};


document.getElementById(
  "attachBtn"
).onclick = () => {

  document.getElementById(
    "fileInput"
  ).click();

};


document.getElementById(
  "fileInput"
).onchange = (
  event
) => {

  const file =
    event.target.files[0];


  if (file) {

    uploadFile(
      file
    );

  }


  event.target.value =
    "";

};


// =========================================================
// BOOT
// =========================================================

async function initializeApp() {

  try {

    chats =
      await loadChatsFromServer();


    chats =
      chats.map(
        chat => ({

          id:
            chat.thread_id,

          threadId:
            chat.thread_id,

          title:
            chat.title ||
            "New chat",

          messages: []

        })
      );


    renderChatList();


    if (chats.length > 0) {

      await selectChat(
        chats[0].id
      );

    }

    else {

      await createChat();

    }


  } catch (error) {

    console.error(
      error
    );


    renderSystemNote(
      `Could not connect to backend: ${error.message}`
    );

  }


  // -----------------------------------------------------
  // Settings
  // -----------------------------------------------------

  if (
    !getSettings().folderPath
  ) {

    openSettings();

  }

}


initializeApp();
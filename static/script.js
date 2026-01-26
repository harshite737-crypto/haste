let studentMode = false;

// DOM elements
const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");

// =====================
// STUDENT MODE
// =====================
function toggleStudentMode() {
    studentMode = !studentMode;
    alert("Student Mode: " + (studentMode ? "ON" : "OFF"));
}

// =====================
// MESSAGE RENDERING
// =====================
function addMessage(sender, text) {
    const wrapper = document.createElement("div");
    wrapper.className = sender === "user" ? "message-user" : "message-ai";

    const label = document.createElement("div");
    label.className = "message-label";
    label.innerText = sender === "user" ? "You" : "Haste";

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerText = text;

    wrapper.appendChild(label);
    wrapper.appendChild(content);

    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
}

// =====================
// CHAT
// =====================
function sendMessage() {
    const msg = input.value.trim();
    if (!msg) return;

    addMessage("user", msg);
    input.value = "";
    thinking.style.display = "block";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: msg,
            studentMode: studentMode
        })
    })
    .then(res => res.json())
    .then(data => {
        thinking.style.display = "none";
        addMessage("haste", data.reply);
    });
}

// Send on Enter
input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

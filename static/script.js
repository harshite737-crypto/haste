const chat = document.getElementById("chat");
const input = document.getElementById("user-input");

function addMessage(sender, text) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;

    const label = document.createElement("div");
    label.className = "message-label";
    label.innerText = sender === "user" ? "You" : "Haste";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerText = text;

    msg.appendChild(label);
    msg.appendChild(bubble);
    chat.appendChild(msg);

    chat.scrollTop = chat.scrollHeight;
}

function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    addMessage("user", text);
    input.value = "";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        addMessage("ai", data.reply);
    })
    .catch(() => {
        addMessage("ai", "⚠️ Server error");
    });
}

input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");
const counter = document.getElementById("message-counter");

let messageCount = 0;

function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender;
    div.innerText = sender.toUpperCase() + ": " + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;

    // Count only user messages
    if (sender === "user") {
        messageCount++;
        counter.innerText = messageCount + " messages";
    }
}

function sendMessage() {
    const message = input.value.trim();
    if (!message) return;

    addMessage("user", message);
    input.value = "";

    thinking.style.display = "block";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    })
    .then(res => res.json())
    .then(data => {
        thinking.style.display = "none";
        addMessage("haste", data.reply);
    })
    .catch(() => {
        thinking.style.display = "none";
        addMessage("haste", "Connection error.");
    });
}

input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
        sendMessage();
    }
});

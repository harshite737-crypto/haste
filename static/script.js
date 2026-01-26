const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");

function addMessage(sender, text) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${sender}`;

    const label = document.createElement("div");
    label.className = "message-label";
    label.innerText = sender === "user" ? "You" : "Haste";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerText = text;

    wrapper.appendChild(label);
    wrapper.appendChild(bubble);
    chat.appendChild(wrapper);

    chat.scrollTop = chat.scrollHeight;
}

function sendMessage() {
    const msg = input.value.trim();
    if (!msg) return;

    addMessage("user", msg);
    input.value = "";
    thinking.style.display = "block";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    })
    .then(res => res.json())
    .then(data => {
        thinking.style.display = "none";
        addMessage("ai", data.reply);
    })
    .catch(() => {
        thinking.style.display = "none";
        addMessage("ai", "⚠️ Something went wrong.");
    });
}

input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

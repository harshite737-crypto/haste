let studentMode = false;

const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");

function toggleStudentMode() {
    studentMode = !studentMode;
    alert("Student Mode: " + (studentMode ? "ON" : "OFF"));
}

function addMessage(type, text) {
    const div = document.createElement("div");
    div.className = type === "user" ? "message-user" : "message-ai";
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
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
        body: JSON.stringify({ message, studentMode })
    })
    .then(res => res.json())
    .then(data => {
        thinking.style.display = "none";
        addMessage("ai", data.reply);
    })
    .catch(() => {
        thinking.style.display = "none";
        addMessage("ai", "Something went wrong.");
    });
}

input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

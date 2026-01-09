// GLOBAL STATE
let studentMode = true;
let messageCount = 0;

// ELEMENTS
const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");
const counter = document.getElementById("message-counter");

// ADD MESSAGE
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender;
    div.innerText = sender.toUpperCase() + ": " + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

// UPDATE COUNTER
function updateCounter() {
    messageCount++;
    counter.innerText = "💬 " + messageCount;
}

// TOGGLE STUDENT MODE
function toggleStudentMode() {
    studentMode = !studentMode;
    const btn = document.getElementById("student-toggle");
    btn.innerText = studentMode
        ? "🎓 Student Mode: ON"
        : "🌐 Student Mode: OFF";
}

// SEND MESSAGE
function sendMessage() {
    const message = input.value.trim();
    if (!message) return;

    addMessage("user", message);
    updateCounter();
    input.value = "";
    thinking.style.display = "block";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: message,
            student_mode: studentMode
        })
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

// ENTER KEY SUPPORT
input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
        sendMessage();
    }
});

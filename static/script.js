let studentMode = true;

const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");
const menu = document.getElementById("side-menu");

function toggleMenu() {
    menu.classList.toggle("open");
}

function toggleStudentMode() {
    studentMode = !studentMode;
    alert("Student Mode: " + (studentMode ? "ON" : "OFF"));
}

function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender;
    div.innerText = text;
    chat.appendChild(div);
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
        headers: {"Content-Type": "application/json"},
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

input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

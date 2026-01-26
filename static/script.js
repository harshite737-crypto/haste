let studentMode = false;

// DOM elements
const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");

// Forms & containers
const loginForm = document.getElementById("login-form-container");
const registerForm = document.getElementById("register-form-container");
const chatInputWrapper = document.getElementById("chat-input");
const authButtons = document.getElementById("auth-buttons");
const logoutBtn = document.getElementById("logout-btn");

// =====================
// AUTH FUNCTIONS
// =====================
function showLogin() {
    loginForm.style.display = "block";
    registerForm.style.display = "none";
    chatInputWrapper.style.display = "none";
}

function showRegister() {
    loginForm.style.display = "none";
    registerForm.style.display = "block";
    chatInputWrapper.style.display = "none";
}

async function login() {
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    if (res.ok) {
        loginForm.style.display = "none";
        authButtons.style.display = "none";
        logoutBtn.style.display = "block";
        chatInputWrapper.style.display = "flex";
        addMessage("haste", "✅ Logged in successfully!");
    } else {
        alert("Login failed. Check your credentials.");
    }
}

async function register() {
    const username = document.getElementById("register-username").value;
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;

    const res = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password })
    });

    if (res.ok) {
        alert("Registration successful! Please login.");
        showLogin();
    } else {
        const data = await res.json();
        alert(data.error || "Registration failed");
    }
}

async function logout() {
    const res = await fetch("/logout", { method: "POST" });
    if (res.ok) {
        addMessage("haste", "✅ Logged out successfully.");
        chatInputWrapper.style.display = "none";
        authButtons.style.display = "block";
        logoutBtn.style.display = "none";
        chat.innerHTML = "";
        showLogin();
    }
}

// =====================
// STUDENT MODE TOGGLE
// =====================
function toggleStudentMode() {
    studentMode = !studentMode;
    alert("Student Mode: " + (studentMode ? "ON" : "OFF"));
}

// =====================
// CHAT FUNCTIONS
// =====================
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender === "user" ? "message-user" : "message-ai";
    div.innerText = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function clearChat() {
    chat.innerHTML = "";
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
        body: JSON.stringify({ message: msg, studentMode: studentMode })
    })
    .then(res => res.json())
    .then(data => {
        thinking.style.display = "none";
        addMessage("haste", data.reply);
    });
}

// Enter key sends message
input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

// Show login form on first load
showLogin();

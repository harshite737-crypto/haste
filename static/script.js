let studentMode = false; // OFF by default
const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");
const menu = document.getElementById("side-menu");

function toggleMenu() {
    if (window.innerWidth <= 768) {
        menu.classList.toggle("open");
    }
}

function toggleStudentMode() {
    studentMode = !studentMode;
    alert("Student Mode: " + (studentMode ? "ON" : "OFF"));
}

function addMessage(sender, text, videoUrl = null) {
    const container = document.createElement("div");
    container.className = sender;

    // Name label
    const label = document.createElement("div");
    label.className = "message-label";
    label.innerText = sender === "user" ? "You" : "Haste";
    container.appendChild(label);

    // Text content
    if (text) {
        const content = document.createElement("div");
        content.className = "message-content";
        content.innerText = text;
        container.appendChild(content);
    }

    // Video content
    if (videoUrl) {
        const videoWrapper = document.createElement("div");
        videoWrapper.className = "video-wrapper";

        const videoEl = document.createElement("video");
        videoEl.src = videoUrl;
        videoEl.controls = true;
        videoEl.width = 400;
        videoWrapper.appendChild(videoEl);

        const downloadBtn = document.createElement("a");
        downloadBtn.href = videoUrl;
        downloadBtn.download = "haste_video.mp4";
        downloadBtn.innerText = "⬇ Download";
        downloadBtn.className = "download-btn";
        videoWrapper.appendChild(downloadBtn);

        container.appendChild(videoWrapper);
    }

    chat.appendChild(container);
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
        body: JSON.stringify({ message: msg, studentMode: studentMode })
    })
    .then(res => res.json())
    .then(data => {
        thinking.style.display = "none";
        addMessage("haste", data.reply, data.video_url || null);
    });
}

input.addEventListener("keydown", e => {
    if (e.key === "Enter") sendMessage();
});

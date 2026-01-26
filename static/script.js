const chat = document.getElementById("chat");
const input = document.getElementById("input");

function add(text, cls) {
    const div = document.createElement("div");
    div.className = "msg " + cls;
    div.innerText = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function send() {
    const msg = input.value.trim();
    if (!msg) return;

    add("You: " + msg, "user");
    input.value = "";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
    })
    .then(r => r.json())
    .then(data => {
        add(data.reply, "haste");

        if (data.video_prompt) {
            generateVideo(data.video_prompt);
        }
    });
}

function generateVideo(prompt) {
    fetch("/generate-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
    })
    .then(r => r.json())
    .then(data => {
        if (data.video_url) {
            const video = document.createElement("video");
            video.src = data.video_url;
            video.controls = true;

            const link = document.createElement("a");
            link.href = data.video_url;
            link.download = "haste-video.mp4";
            link.innerText = "⬇ Download Video";

            chat.appendChild(video);
            chat.appendChild(link);
        }
    });
}

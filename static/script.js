let studentMode = false;

const chat = document.getElementById("chat");
const input = document.getElementById("user-input");
const thinking = document.getElementById("thinking");
const video = document.getElementById("generatedVideo");
const download = document.getElementById("downloadVideo");

function toggleStudentMode(){ studentMode = !studentMode; alert("Student Mode: "+(studentMode?"ON":"OFF")); }

function addMessage(sender, text){
    const div = document.createElement("div");
    div.className = sender;
    div.innerText = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function sendMessage(){
    const msg = input.value.trim();
    if(!msg) return;
    addMessage("message-user", msg);
    input.value = "";
    thinking.style.display = "block";
    video.style.display = "none";
    download.style.display = "none";

    fetch("/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({message:msg, studentMode:studentMode})
    })
    .then(res=>res.json())
    .then(data=>{
        thinking.style.display="none";
        addMessage("message-ai", data.reply);
        if(data.video_url){
            video.src=data.video_url;
            video.style.display="block";
            download.href=data.video_url;
            download.style.display="block";
        }
    });
}

input.addEventListener("keydown",e=>{if(e.key==="Enter")sendMessage();});

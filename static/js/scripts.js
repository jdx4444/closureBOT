const responseMessage = document.getElementById('response_message');
const botAudio = document.getElementById('botAudio');
const indicator = document.getElementById('indicator');
let mediaRecorder;
let audioChunks = [];
let silenceStarted = null;
let debounceTimeout = null;
let isConversationActive = false;

function toggleConversation() {
    if (isConversationActive) {
        endConversation();
    } else {
        startConversation();
    }
}

function startConversation() {
    isConversationActive = true;
    document.getElementById('conversationButton').src = "/static/images/end_conversation_button.GIF";
    startRecording();
}

function endConversation() {
    isConversationActive = false;
    document.getElementById('conversationButton').src = "/static/images/start_conversation_button.GIF";
    stopRecording();
    clearIndicator();
}

function showListeningIndicator() {
    indicator.innerHTML = "🎙️ Listening...";
}

async function startRecording() {
    showListeningIndicator();
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    
    const options = { threshold: -60, interval: 50 };
    const speechEvents = hark(stream, options);

    speechEvents.on('speaking', function() {
        silenceStarted = null;
        if (debounceTimeout) {
            clearTimeout(debounceTimeout);
            debounceTimeout = null;
        }
    });

    speechEvents.on('stopped_speaking', function() {
        if (!silenceStarted) {
            silenceStarted = Date.now();
        }
        if (debounceTimeout) {
            clearTimeout(debounceTimeout);
        }
        debounceTimeout = setTimeout(() => {
            const elapsedSilenceTime = Date.now() - silenceStarted;
            if (elapsedSilenceTime >= 1000) {
                stopRecording();
            }
        }, 1000);
    });

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = sendVoiceMessage;
    mediaRecorder.start(100);
}

function sendVoiceMessage() {
    clearIndicator();
    const audioData = new Blob(audioChunks, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append('audio_file', audioData);
    fetch('/send_voice', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(error => Promise.reject(error));
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            // Display error message to the user
            responseMessage.innerHTML = data.error;
        } else {
            botAudio.src = '/static/audio/' + data.audio_file;
            responseMessage.innerHTML = data.text_response;
            botAudio.play();
        }
    })
    .catch(error => {
        // Display the error message to the user
        responseMessage.innerHTML = error.detail || "Sorry, one or both of your API keys was invalid:( Please go back and try entering the correct API keys.";
    });
}


function clearIndicator() {
    indicator.innerHTML = "";
}

botAudio.onended = function() {
    if (isConversationActive) {
        showListeningIndicator();
        startRecording();
    }
};

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    if (mediaRecorder && mediaRecorder.stream) {
        const tracks = mediaRecorder.stream.getTracks();
        tracks.forEach(track => track.stop());
    }
    if (debounceTimeout) {
        clearTimeout(debounceTimeout);
    }
}

let audioContext;
let analyser;
let dataArray;
let bufferLength;
let canvas;
let canvasCtx;

function setupAudioVisualizer() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaElementSource(botAudio);
    source.connect(analyser);
    analyser.connect(audioContext.destination);
    analyser.fftSize = 256;
    bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);
    canvas = document.getElementById("audioVisualizer");
    canvasCtx = canvas.getContext("2d");
}

function draw() {
    requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
    
    const barWidth = (canvas.width / bufferLength) * 2.5;
    let barHeight;
    let x = 0;

    // Determine the maximum value in dataArray
    let maxValue = Math.max(...dataArray);

    // Set the stroke style for the peak line
    canvasCtx.strokeStyle = '#000';  // Black color
    canvasCtx.lineWidth = 2;        // Line width

    canvasCtx.beginPath();
    for(let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / maxValue) * (canvas.height - 10);

        // Draw a short line for the peak
        canvasCtx.moveTo(x, canvas.height);
        canvasCtx.lineTo(x, canvas.height - barHeight);
        
        // Move the drawing position forward by one bar width to create a gap
        x += barWidth;

        // Now, move the drawing position forward by an additional bar width to position for the next peak
        x += barWidth;
    }
    canvasCtx.stroke();
}

botAudio.onplay = function() {
    if (!audioContext) {
        setupAudioVisualizer();
    }
    if (audioContext.state === "suspended") {
        audioContext.resume();
    }
    draw();
};
window.addEventListener('beforeunload', function (e) {
    // Your fetch to logout endpoint
    fetch('/logout', { method: 'POST', keepalive: true });

    // The following two lines are standard boilerplate for `beforeunload` event
    e.preventDefault();
    e.returnValue = '';
});

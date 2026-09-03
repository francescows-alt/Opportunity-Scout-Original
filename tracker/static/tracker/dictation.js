document.addEventListener("DOMContentLoaded", () => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let activeRecognition = null;
    let activeButton = null;

    function resetButton() {
        if (activeButton) {
            activeButton.classList.remove("listening");
            activeButton.innerHTML = "<span>🎙</span> Dictate";
            activeButton = null;
        }
        activeRecognition = null;
    }

    document.querySelectorAll("textarea[data-dictation='true']").forEach((textarea) => {
        const wrapper = document.createElement("div");
        wrapper.className = "dictation-wrap";
        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.appendChild(textarea);

        const button = document.createElement("button");
        button.type = "button";
        button.className = "mic-button";
        button.innerHTML = "<span>🎙</span> Dictate";
        button.setAttribute("aria-label", "Start voice dictation");
        wrapper.appendChild(button);

        if (!Recognition) {
            button.classList.add("unsupported");
            button.title = "Browser dictation is unavailable here. On macOS, click the text box and press Fn twice.";
        }

        button.addEventListener("click", () => {
            if (!Recognition) {
                window.alert("This browser does not provide speech recognition. Try Chrome, or click the text box and press Fn twice for macOS Dictation.");
                return;
            }

            if (activeRecognition) {
                activeRecognition.stop();
                return;
            }

            const recognition = new Recognition();
            const originalText = textarea.value.trim();
            let finalTranscript = "";
            recognition.lang = document.documentElement.lang || navigator.language || "en-US";
            recognition.continuous = true;
            recognition.interimResults = true;

            recognition.onstart = () => {
                activeRecognition = recognition;
                activeButton = button;
                button.classList.add("listening");
                button.innerHTML = "<span>●</span> Stop";
            };

            recognition.onresult = (event) => {
                let interimTranscript = "";
                for (let index = event.resultIndex; index < event.results.length; index += 1) {
                    const words = event.results[index][0].transcript;
                    if (event.results[index].isFinal) finalTranscript += words;
                    else interimTranscript += words;
                }
                const separator = originalText ? " " : "";
                textarea.value = `${originalText}${separator}${finalTranscript}${interimTranscript}`.trimStart();
                textarea.dispatchEvent(new Event("input", { bubbles: true }));
            };

            recognition.onerror = (event) => {
                resetButton();
                if (event.error === "not-allowed") {
                    window.alert("Microphone permission was denied. Allow microphone access for 127.0.0.1 in your browser settings, then try again.");
                }
            };
            recognition.onend = resetButton;
            recognition.start();
        });
    });
});

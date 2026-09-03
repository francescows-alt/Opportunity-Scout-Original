document.addEventListener("DOMContentLoaded", () => {
    const config = document.querySelector("#dictation-config");
    const transcriptionUrl = config?.dataset.transcriptionUrl;
    let active = null;

    function csrfToken(textarea) {
        return textarea.closest("form")?.querySelector("input[name='csrfmiddlewaretoken']")?.value || "";
    }

    function reset(session) {
        session.stream?.getTracks().forEach((track) => track.stop());
        session.button.classList.remove("listening", "processing");
        session.button.innerHTML = "<span>🎙</span> Dictate";
        session.button.disabled = false;
        if (active === session) active = null;
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

        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            button.classList.add("unsupported");
            button.title = "Audio recording is unavailable in this browser.";
        }

        button.addEventListener("click", async () => {
            if (active) {
                if (active.button === button && active.recorder.state === "recording") active.recorder.stop();
                return;
            }
            if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
                window.alert("This browser cannot record audio here. Try current Chrome or Safari, or use macOS Dictation by clicking the text box and pressing Fn twice.");
                return;
            }

            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (error) {
                window.alert("The microphone is blocked. Allow microphone access for 127.0.0.1 in your browser settings, then try again.");
                return;
            }

            const preferredType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
            const recorder = new MediaRecorder(stream, preferredType ? { mimeType: preferredType } : undefined);
            const session = { recorder, stream, button, textarea, chunks: [], startedAt: Date.now() };
            active = session;

            recorder.addEventListener("dataavailable", (event) => {
                if (event.data.size) session.chunks.push(event.data);
            });
            recorder.addEventListener("stop", async () => {
                button.classList.remove("listening");
                button.classList.add("processing");
                button.innerHTML = "<span>•••</span> Transcribing";
                button.disabled = true;
                stream.getTracks().forEach((track) => track.stop());
                try {
                    const blob = new Blob(session.chunks, { type: recorder.mimeType || "audio/webm" });
                    const formData = new FormData();
                    formData.append("audio", blob, "dictation.webm");
                    formData.append("duration_seconds", String((Date.now() - session.startedAt) / 1000));
                    const response = await fetch(transcriptionUrl, {
                        method: "POST",
                        headers: { "X-CSRFToken": csrfToken(textarea) },
                        body: formData,
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || "Transcription failed.");
                    const existing = textarea.value.trim();
                    textarea.value = `${existing}${existing ? " " : ""}${result.text.trim()}`;
                    textarea.dispatchEvent(new Event("input", { bubbles: true }));
                    textarea.focus();
                } catch (error) {
                    window.alert(error.message);
                } finally {
                    reset(session);
                }
            });
            recorder.addEventListener("error", () => {
                reset(session);
                window.alert("The audio recording stopped because of a browser error. Please try again.");
            });
            recorder.start(1000);
            button.classList.add("listening");
            button.innerHTML = "<span>●</span> Stop recording";
        });
    });
});

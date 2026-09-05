document.addEventListener("DOMContentLoaded", () => {
    const launcher = document.querySelector(".robert-launcher");
    const panel = document.querySelector(".robert-panel");
    const close = document.querySelector(".robert-close");
    if (!launcher || !panel || !close) return;

    function setOpen(open) {
        panel.classList.toggle("open", open);
        launcher.setAttribute("aria-expanded", String(open));
        if (open) {
            const body = panel.querySelector(".robert-body");
            body.scrollTop = body.scrollHeight;
        }
    }
    launcher.addEventListener("click", () => setOpen(!panel.classList.contains("open")));
    close.addEventListener("click", () => setOpen(false));
    setOpen(panel.classList.contains("open"));

    panel.querySelectorAll(".chat-message").forEach((message, index) => {
        message.style.animationDelay = `${Math.min(index, 6) * 45}ms`;
    });
    const robertComposer = panel.querySelector(".robert-composer");
    if (robertComposer) {
        robertComposer.addEventListener("submit", () => {
            const sendButton = robertComposer.querySelector("button[type='submit']");
            if (sendButton) {
                sendButton.disabled = true;
                sendButton.textContent = "Robert is thinking…";
            }
            const typing = document.createElement("div");
            typing.className = "chat-message assistant typing-message";
            typing.innerHTML = "<span>R</span><p><i></i><i></i><i></i></p>";
            panel.querySelector(".robert-body")?.appendChild(typing);
        });
    }

    const backgroundDialog = document.querySelector(".background-notes-dialog");
    const backgroundButton = document.querySelector(".background-notes-open");
    if (backgroundDialog && backgroundButton) {
        backgroundButton.addEventListener("click", () => backgroundDialog.showModal());
        backgroundDialog.addEventListener("click", (event) => {
            if (event.target === backgroundDialog) backgroundDialog.close();
        });
    }

    const jobForms = Array.from(document.querySelectorAll("[data-background-job-form]"));
    const progressPanel = document.querySelector("[data-search-progress]");
    if (jobForms.length && progressPanel) {
        const stageText = progressPanel.querySelector("[data-search-stage]");
        const percentText = progressPanel.querySelector("[data-search-percent]");
        const bar = progressPanel.querySelector("[data-search-bar]");
        const buttonsOf = (form) => form.querySelector("button[type='submit']");
        const allButtons = () => jobForms.map(buttonsOf).filter(Boolean);
        const resumeUrl = jobForms.map((form) => form.dataset.activeStatusUrl).find(Boolean);
        let statusUrl = resumeUrl || "";
        let jobId = statusUrl?.match(/search\/(\d+)\/status/)?.[1] || "";
        let polling = false;

        const stopButton = progressPanel.querySelector("[data-search-stop]");
        if (stopButton) {
            stopButton.addEventListener("click", () => {
                if (!jobId) return;
                const token = document.querySelector("[name=csrfmiddlewaretoken]");
                stopButton.disabled = true;
                fetch(`/applications/search/${jobId}/stop/`, {
                    method: "POST",
                    headers: { "X-CSRFToken": token ? token.value : "" },
                }).finally(() => window.location.reload());
            });
        }

        function renderProgress(data) {
            progressPanel.hidden = false;
            if (stopButton) stopButton.hidden = !(data.status === "running" || data.status === "queued");
            progressPanel.classList.remove("idle");
            progressPanel.classList.add("active");
            stageText.textContent = data.message;
            percentText.textContent = `${data.progress}%`;
            bar.style.width = `${Math.max(3, data.progress)}%`;
            const stages = ["searching", "checking", "researching", "saving", "complete"];
            const currentIndex = stages.indexOf(data.stage);
            progressPanel.querySelectorAll("[data-stage]").forEach((item) => {
                const index = stages.indexOf(item.dataset.stage);
                item.classList.toggle("current", index === currentIndex);
                item.classList.toggle("done", index < currentIndex || data.status === "complete");
            });
        }

        function setButtonsDisabled(disabled) {
            allButtons().forEach((button) => { button.disabled = disabled; });
        }

        async function pollSearch(onSettled) {
            if (!statusUrl || polling) return;
            polling = true;
            try {
                const response = await fetch(statusUrl, {headers: {"Accept": "application/json"}});
                const data = await response.json();
                renderProgress(data);
                if (data.status === "complete" || data.status === "failed") {
                    onSettled(data.status === "complete");
                    return;
                }
            } catch (_) {
                stageText.textContent = "Reconnecting to Robert…";
            } finally {
                polling = false;
            }
            window.setTimeout(() => pollSearch(onSettled), 1200);
        }

        function onSettled(activeButton, success) {
            setButtonsDisabled(false);
            if (success) {
                activeButton.textContent = "Research complete";
                window.setTimeout(() => window.location.assign(`/applications/?search_complete=${jobId}`), 1800);
            } else {
                activeButton.textContent = "Try again";
            }
        }

        jobForms.forEach((form) => {
            const button = buttonsOf(form);
            if (!button) return;
            const workingLabel = form.dataset.workingLabel || "Robert is working…";
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                setButtonsDisabled(true);
                button.textContent = "Starting Robert…";
                progressPanel.hidden = false;
                renderProgress({message: "Preparing…", progress: 3, stage: "searching", status: "running"});
                try {
                    const response = await fetch(form.action, {
                        method: "POST",
                        body: new FormData(form),
                        headers: {"Accept": "application/json"},
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || "Could not start.");
                    statusUrl = data.status_url;
                    jobId = String(data.job_id);
                    button.textContent = workingLabel;
                    pollSearch((success) => onSettled(button, success));
                } catch (error) {
                    stageText.textContent = error.message;
                    setButtonsDisabled(false);
                    button.textContent = "Try again";
                }
            });
        });

        if (statusUrl) {
            const resumeForm = jobForms.find((form) => form.dataset.activeStatusUrl === resumeUrl);
            const resumeButton = resumeForm ? buttonsOf(resumeForm) : allButtons()[0];
            setButtonsDisabled(true);
            if (resumeButton) resumeButton.textContent = (resumeForm && resumeForm.dataset.workingLabel) || "Robert is working…";
            pollSearch((success) => onSettled(resumeButton || allButtons()[0], success));
        }
    }
});

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

    document.querySelectorAll("[data-discovery-form]").forEach((discoveryForm) => {
        discoveryForm.addEventListener("submit", () => {
            const button = discoveryForm.querySelector("button[type='submit']");
            const progress = discoveryForm.querySelector(".discovery-progress");
            if (button) {
                button.disabled = true;
                button.textContent = "Robert is searching…";
            }
            if (progress) progress.hidden = false;
        });
    });

    const searchForm = document.querySelector("[data-complete-search]");
    const progressPanel = document.querySelector("[data-search-progress]");
    if (searchForm && progressPanel) {
        const button = searchForm.querySelector("button[type='submit']");
        const stageText = progressPanel.querySelector("[data-search-stage]");
        const percentText = progressPanel.querySelector("[data-search-percent]");
        const bar = progressPanel.querySelector("[data-search-bar]");
        let statusUrl = searchForm.dataset.activeStatusUrl;
        let jobId = statusUrl?.match(/search\/(\d+)\/status/)?.[1] || "";
        let polling = false;

        function renderProgress(data) {
            progressPanel.hidden = false;
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

        async function pollSearch() {
            if (!statusUrl || polling) return;
            polling = true;
            try {
                const response = await fetch(statusUrl, {headers: {"Accept": "application/json"}});
                const data = await response.json();
                renderProgress(data);
                if (data.status === "complete") {
                    button.textContent = "Research complete";
                    window.setTimeout(() => window.location.assign(`/applications/?search_complete=${jobId}`), 1800);
                    return;
                }
                if (data.status === "failed") {
                    button.disabled = false;
                    button.textContent = "Try search again";
                    return;
                }
            } catch (_) {
                stageText.textContent = "Reconnecting to Robert…";
            } finally {
                polling = false;
            }
            window.setTimeout(pollSearch, 1200);
        }

        searchForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            button.disabled = true;
            button.textContent = "Starting Robert…";
            progressPanel.hidden = false;
            renderProgress({message: "Preparing a new search strategy…", progress: 3, stage: "searching", status: "running"});
            try {
                const response = await fetch(searchForm.action, {
                    method: "POST",
                    body: new FormData(searchForm),
                    headers: {"Accept": "application/json"},
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || "Could not start search.");
                statusUrl = data.status_url;
                jobId = String(data.job_id);
                button.textContent = "Robert is working…";
                pollSearch();
            } catch (error) {
                stageText.textContent = error.message;
                button.disabled = false;
                button.textContent = "Try search again";
            }
        });

        if (statusUrl) {
            button.disabled = true;
            button.textContent = "Robert is working…";
            pollSearch();
        }
    }
});

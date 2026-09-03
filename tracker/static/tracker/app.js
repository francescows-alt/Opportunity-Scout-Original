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

    const backgroundDialog = document.querySelector(".background-notes-dialog");
    const backgroundButton = document.querySelector(".background-notes-open");
    if (backgroundDialog && backgroundButton) {
        backgroundButton.addEventListener("click", () => backgroundDialog.showModal());
        backgroundDialog.addEventListener("click", (event) => {
            if (event.target === backgroundDialog) backgroundDialog.close();
        });
    }

    const discoveryForm = document.querySelector("[data-discovery-form]");
    if (discoveryForm) {
        discoveryForm.addEventListener("submit", () => {
            const button = discoveryForm.querySelector("button[type='submit']");
            const progress = discoveryForm.querySelector(".discovery-progress");
            if (button) {
                button.disabled = true;
                button.textContent = "Robert is searching…";
            }
            if (progress) progress.hidden = false;
        });
    }
});

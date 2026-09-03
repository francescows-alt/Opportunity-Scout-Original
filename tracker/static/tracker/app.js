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
});

document.addEventListener("DOMContentLoaded", () => {
    const textarea = document.querySelector("#document-profile-proposal");
    const preview = document.querySelector("#profile-proposal-preview");
    const editor = document.querySelector(".proposal-editor");
    if (!textarea || !preview || !editor) return;

    const headings = [
        "Professional identity",
        "Education and graduation requirements",
        "Relevant experience and results",
        "Skills and languages",
        "Career direction",
        "Practical constraints",
    ];

    function renderPreview() {
        preview.replaceChildren();
        let section = null;
        textarea.value.split(/\n/).forEach((rawLine) => {
            const line = rawLine.trim();
            if (!line) return;
            const cleanHeading = line.replace(/^#{1,6}\s*/, "").replaceAll("**", "");
            if (headings.includes(cleanHeading)) {
                section = document.createElement("section");
                const title = document.createElement("h3");
                title.textContent = cleanHeading;
                section.appendChild(title);
                preview.appendChild(section);
                return;
            }
            if (!section) {
                section = document.createElement("section");
                preview.appendChild(section);
            }
            const paragraph = document.createElement("p");
            paragraph.textContent = line.replace(/^[-•]\s*/, "");
            if (/^[-•]\s*/.test(line)) paragraph.className = "profile-point";
            section.appendChild(paragraph);
        });
    }

    function setView(view) {
        const editing = view === "edit";
        preview.hidden = editing;
        editor.hidden = !editing;
        document.querySelectorAll("[data-profile-view]").forEach((button) => {
            button.classList.toggle("active", button.dataset.profileView === view);
        });
        if (editing) textarea.focus();
    }

    document.querySelectorAll("[data-profile-view]").forEach((button) => {
        button.addEventListener("click", () => setView(button.dataset.profileView));
    });
    textarea.addEventListener("input", renderPreview);
    renderPreview();
    setView("preview");
});

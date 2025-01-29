document.addEventListener("DOMContentLoaded", () => {
    const inputs = document.querySelectorAll("form input");
    inputs.forEach((input) => {
        input.addEventListener("focus", () => {
            input.style.boxShadow = "0 0 8px rgba(255, 255, 255, 0.5)";
        });
        input.addEventListener("blur", () => {
            input.style.boxShadow = "none";
        });
    });
});

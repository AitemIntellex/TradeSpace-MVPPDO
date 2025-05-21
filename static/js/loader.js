document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    const loader = document.getElementById("loader");
    const resultContainer = document.getElementById("ai-analysis-text");

    form.addEventListener("submit", function (event) {
        event.preventDefault(); // Предотвращаем стандартное поведение

        // Показать лоадер
        loader.style.display = "block";
        resultContainer.textContent = ""; // Очищаем предыдущий результат

        // Отправка данных с помощью fetch
        const formData = new FormData(form);
        fetch(form.action, {
            method: "POST",
            body: formData,
        })
            .then((response) => response.json())
            .then((data) => {
                // Скрыть лоадер
                loader.style.display = "none";

                // Показать результат
                if (data.analysis) {
                    resultContainer.innerHTML = data.analysis;
                } else {
                    resultContainer.textContent = "Ошибка при выполнении анализа.";
                }
            })
            .catch((error) => {
                console.error("Ошибка:", error);
                loader.style.display = "none";
                resultContainer.textContent = "Не удалось выполнить анализ.";
            });
    });
});

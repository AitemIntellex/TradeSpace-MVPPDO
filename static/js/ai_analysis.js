document.addEventListener("DOMContentLoaded", function () {
  // ======================= Утилиты =======================
  /**
   * Включение копирования по клику для элементов, найденных по селектору
   */
  function enableCopyOnClick(selector) {
    document.querySelectorAll(selector).forEach((element) => {
      element.addEventListener("click", function () {
        let valueToCopy = element.getAttribute("data-value") || element.textContent;
        valueToCopy = valueToCopy.trim().replace(",", ".");
        navigator.clipboard
          .writeText(valueToCopy)
          .then(() => {
            element.style.color = "#28a745";
            element.style.fontWeight = "bold";
            setTimeout(() => {
              element.style.color = "";
              element.style.fontWeight = "";
            }, 1000);
          })
          .catch((err) => console.error("Ошибка копирования:", err));
      });
    });
  }

  /**
   * Включение вставки по клику в поля ввода
   */
  function enablePasteToForms(selector) {
    document.querySelectorAll(selector).forEach((input) => {
      input.addEventListener("click", async function () {
        try {
          const clipboardText = await navigator.clipboard.readText();
          if (clipboardText) {
            this.value = clipboardText.replace(".", ",");
          }
        } catch (err) {
          console.error("Ошибка при чтении из буфера обмена:", err);
        }
      });
    });
  }

  /**
   * Подсветка ключевых слов
   */
  function formatAnalysisText(selector) {
    document.querySelectorAll(selector).forEach((element) => {
      element.innerHTML = element.innerHTML
        .replace(/Тейк-профит/gi, '<span style="color: yellow; font-weight: bold;">Тейк-профит</span>')
        .replace(/Стоп-лосс/gi, '<span style="color: red; font-weight: bold;">Стоп-лосс</span>');
    });
  }

  /**
   * Добавление класса .copyable к числам
   */
  function markNumbersAsCopyable(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
      element.innerHTML = element.innerHTML.replace(/(\d+\.\d+|\d+)/g, (match) => {
        return `<span class="copyable" data-value="${match}">${match}</span>`;
      });
    }
  }

  /**
   * Замена запятых на точки в форме
   */
  function convertCommasToDotsInForm(form) {
    form.querySelectorAll("input, textarea").forEach((input) => {
      input.value = input.value.replace(",", ".");
    });
  }

  /**
   * Замена точек на запятые при вводе
   */
  function replaceDotWithCommaOnInput(form) {
    form.querySelectorAll(".input-corrected").forEach((input) => {
      input.addEventListener("input", function () {
        this.value = this.value.replace(/\./g, ",");
      });
    });
  }

  // ======================= Обработка форм =======================
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => convertCommasToDotsInForm(form));
    replaceDotWithCommaOnInput(form);
  });

  // ======================= Копирование и вставка =======================
  enableCopyOnClick(".copyable");
  enablePasteToForms("input.form-control:not(#volume_pending):not(#volume_market)");

  // ======================= Работа с анализом =======================
  function handleAnalysis(buttonId, url, resultId, bodyData) {
    const button = document.getElementById(buttonId);
    const resultDiv = document.getElementById(resultId);

    if (!button || !resultDiv) return;

    button.disabled = true;
    button.textContent = "Анализ выполняется...";

    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(bodyData),
    })
      .then((response) => response.json())
      .then((data) => {
        resultDiv.innerHTML = data.analysis || "Ошибка анализа.";
        formatAnalysisText(`#${resultId}`);
        markNumbersAsCopyable(resultId);
        enableCopyOnClick(".copyable");
      })
      .catch((error) => {
        console.error("Ошибка анализа:", error);
        resultDiv.innerHTML = "Ошибка выполнения анализа.";
      })
      .finally(() => {
        button.disabled = false;
        button.textContent = "Глубокий анализ";
      });
  }

  // Кнопки анализа
  document.getElementById("analyzeWithAIButton")?.addEventListener("click", () =>
    handleAnalysis("analyzeWithAIButton", "/analyze-with-ai/", "ai-analysis-text", { analyze: "ai" })
  );

  document.getElementById("analyzeWithAIx3Button")?.addEventListener("click", () =>
    handleAnalysis("analyzeWithAIx3Button", "/analyze-x3/", "x3-analysis-text", { analyze: "x3" })
  );

  document.getElementById("analyzeWithAIWithHistoricalButton").addEventListener("click", function () {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

    const requestData = {
        symbol: "EURUSD",
        timeframe: "1d",
        num_bars: 10,
    };

    fetch("/analyze-with-historical-data/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(requestData),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.analysis) {
                console.log("AI Analysis:", data.analysis);
                // Здесь можно обновить UI с результатами анализа
            } else {
                alert(data.error || "Ошибка анализа.");
            }
        })
        .catch((error) => console.error("Ошибка:", error));
});



  // ======================= Калькулятор прибыли/убытка =======================
  const pipValueFromBroker = {{ tick_value }};

  function calculateProfitAndLoss(volume, price, takeProfit, stopLoss, profitField, lossField) {
    const vol = parseFloat(volume.replace(",", "."));
    const entryPrice = parseFloat(price.replace(",", "."));
    const tp = parseFloat(takeProfit.replace(",", "."));
    const sl = parseFloat(stopLoss.replace(",", "."));

    if (vol && entryPrice && tp && sl) {
      const profit = (tp - entryPrice) * vol * pipValueFromBroker;
      const loss = (entryPrice - sl) * vol * pipValueFromBroker;

      document.getElementById(profitField).textContent = profit.toFixed(2);
      document.getElementById(lossField).textContent = loss.toFixed(2);
    } else {
      document.getElementById(profitField).textContent = "-";
      document.getElementById(lossField).textContent = "-";
    }
  }

  // Обработчики ввода для калькуляторов
  document.getElementById("pendingOrderForm")?.addEventListener("input", () => {
    calculateProfitAndLoss(
      document.getElementById("volume_pending").value,
      document.getElementById("price_pending").value,
      document.getElementById("take_profit_pending").value,
      document.getElementById("stop_loss_pending").value,
      "profit_pending",
      "loss_pending"
    );
  });

  document.getElementById("marketPositionForm")?.addEventListener("input", () => {
    calculateProfitAndLoss(
      document.getElementById("volume_market").value,
      document.getElementById("price_pending").value,
      document.getElementById("take_profit_market").value,
      document.getElementById("stop_loss_market").value,
      "profit_market",
      "loss_market"
    );
  });
});

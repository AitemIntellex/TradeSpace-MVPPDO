// Обработчик выбора пары
  const handlePairChange = function () {
    const selectedPair = this.value;
    setCookie("selected_pair", selectedPair, 7); // Сохраняем символ в cookie на 7 дней

    // Изменяем текущий URL и обновляем страницу
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set("symbol", selectedPair);
    window.location.href = currentUrl.toString();
  };

  // Проверка сохраненного символа при загрузке страницы
  const checkSavedPair = () => {
    const savedPair = getCookie("selected_pair");
    if (savedPair) {
      const pairSelect = document.getElementById("pair-select");
      if (pairSelect) {
        pairSelect.value = savedPair;

        // Обновляем URL, если символ не совпадает с текущим параметром в URL
        const currentUrl = new URL(window.location.href);
        if (currentUrl.searchParams.get("symbol") !== savedPair) {
          currentUrl.searchParams.set("symbol", savedPair);
          window.history.replaceState(null, "", currentUrl.toString());
        }
      } else {
        console.warn("Элемент с ID 'pair-select' не найден.");
      }
    }
  };

  // Добавляем обработчик на выбор пары
  const pairSelect = document.getElementById("pair-select");
  if (pairSelect) {
    pairSelect.addEventListener("change", handlePairChange);
  } else {
    console.warn("Элемент с ID 'pair-select' не найден.");
  }

  // Выполняем проверку сохраненной пары
  checkSavedPair();

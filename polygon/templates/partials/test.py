<!-- Карточка для глубокого анализа -->


<!-- Контейнер для всех кнопок -->
<div id="buttons-container" class="rec-container">
  <!-- Кнопка: Анализ -->
  <button form="form-analyze" type="submit" class="btn btn-ghost btn-dark">
    Анализ
  </button>

  <!-- Кнопка: Анализ x3 -->
  <button form="form-analyze-x3" type="submit" class="btn btn-ghost btn-dark">
    Анализ x3
  </button>

  <!-- Кнопка: Анализ с Историей -->
  <button form="form-historical-analyze" type="submit" class="btn btn-ghost btn-dark">
    Анализ х50 (история)
  </button>

  <!-- Кнопки: Тех. Анализ и Новостной обозреватель -->
  <button form="form-tech-news-overview" name="deep_tech_analyst" type="submit" class="btn btn-ghost btn-dark">
    Тех. Анализ
  </button>

  <button form="form-tech-news-overview" name="news_overview" type="submit" class="btn btn-ghost btn-dark">
    Новостной обозреватель
  </button>

  <button form="form-tech-news-overview" name="deep_tech_analyst_history" type="submit" class="btn btn-ghost btn-dark">
    Технический аналитик (с историей)
  </button>
</div>

<!-- Общий контейнер для всех форм -->
<div id="forms-container" class="rec-container">

  <!-- Форма 1: Анализ -->
  <form method="POST" id="form-analyze" class="inline-form">
    {% csrf_token %}
  </form>
<div id="ai-analysis-container" class="rec-container">
  <h5>Анализ #1</h5>
  <div id="ai-analysis-text">
    {% if ai_analysis %} {{ ai_analysis|safe }} {% else %}
    <p>Нет данных для отображения.</p>
    {% endif %}
  </div>
</div>
  <!-- Форма 2: Анализ x3 -->
  <form method="POST" action="{% url 'analyze_with_ai_x3' %}" id="form-analyze-x3" class="inline-form">
    {% csrf_token %}
  </form>

  <!-- Форма 3: Анализ с Историей -->
  <form method="GET" action="{% url 'analyze_with_historical_data' %}" id="form-historical-analyze" class="inline-form">
    <input type="hidden" name="symbol" value="{{ selected_pair }}">
    <input type="hidden" name="timeframe" value="D1">
    <input type="hidden" name="candles" value="50">
  </form>

  <!-- Форма 4: Технический анализ и Новостной обозреватель -->
  <form method="post" id="form-tech-news-overview" class="inline-form">
    {% csrf_token %}
  </form>

</div>

<!-- Карточка для глубокого анализа x3 -->
<div id="x3-analysis-container" class="rec-container">
  <h5>Анализ x3</h5>
  <div id="x3-analysis-text">
    <p>Нет данных для отображения.</p>
  </div>
</div>

<!-- Карточка для глубокого анализа с историей -->
<div id="historical-analysis-container" class="rec-container">
  <h5>Анализ с Историей х50</h5>
  <div id="historical-analysis-text">
    <p>Нет данных для отображения.</p>
  </div>
</div>

<!-- Карточка для вывода результата Тех. Анализа -->
<div id="tech-data-analysis-container" class="rec-container">
  <h5>Тех. Анализ</h5>
  <div id="tech-data-analysis-text">
    <p>Нет данных для отображения.</p>
  </div>
</div>

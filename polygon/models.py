# В файле models.py
from django.db import models


class Recommendation(models.Model):
    symbol = models.CharField(max_length=10)  # Символ валютной пары
    analysis = models.TextField()  # Результат анализа AI
    created_at = models.DateTimeField(auto_now_add=True)  # Время создания записи

    def __str__(self):
        return f"Recommendation for {self.symbol} at {self.created_at}"

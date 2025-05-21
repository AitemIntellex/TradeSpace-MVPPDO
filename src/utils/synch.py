class TradingAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ("MT4", "MetaTrader 4"),
        ("MT5", "MetaTrader 5"),
    ]

    name = models.CharField(max_length=255)  # Название аккаунта
    account_type = models.CharField(max_length=3, choices=ACCOUNT_TYPE_CHOICES)
    login = models.CharField(max_length=50)
    password = models.CharField(max_length=255)
    server = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.account_type})"

# Generated by Django 5.1.3 on 2025-02-05 03:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("polygon", "0002_accountinfo_historicaldata_openposition_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="tradingprofithistory",
            name="account",
        ),
        migrations.RemoveField(
            model_name="historicaldata",
            name="account",
        ),
        migrations.DeleteModel(
            name="OpenPosition",
        ),
        migrations.DeleteModel(
            name="TradingProfitHistory",
        ),
        migrations.DeleteModel(
            name="AccountInfo",
        ),
        migrations.DeleteModel(
            name="HistoricalData",
        ),
    ]

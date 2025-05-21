
# TradeSpace - Git Push Helper
Write-Host "📦 Добавление всех изменений..."
git add .

Write-Host "📝 Введите сообщение для коммита:"
$commitMessage = Read-Host "Commit message"

if (-not $commitMessage) {
    $commitMessage = "Обновление проекта"
}

Write-Host "✅ Выполняем коммит: $commitMessage"
git commit -m "$commitMessage"

Write-Host "🔄 Подтягиваем изменения с GitHub..."
git pull --rebase

Write-Host "🚀 Загружаем изменения в репозиторий..."
git push

Write-Host "✅ Готово! Проект обновлён."

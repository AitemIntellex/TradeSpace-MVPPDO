import os

# Укажите основной путь директории
base_path = r"C:\Projects\TradeSpace_v5"

# Укажите список папок, которые нужно исключить
exclude_dirs = {
    ".venv",
    ".git",
    "Jafar-TradeSpace",
    "Temp",
    "temp",
    "node_modules",
    "__pycache__",
    "Temp",
    "staticfiles",
    "i18n",
    "technical_analysis2",
}

# Укажите путь для сохранения выходного файла
output_file = os.path.join(base_path, "logs", "output-folder-structure2.txt")


# Функция для создания структуры дерева
def get_folder_tree(path, indent=""):
    tree = []
    try:
        # Получаем список всех элементов в директории
        items = sorted(os.listdir(path))
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path) and item not in exclude_dirs:
                tree.append(f"{indent}{item}/")
                tree.extend(get_folder_tree(full_path, indent=indent + "  "))
            elif os.path.isfile(full_path):
                tree.append(f"{indent}{item}")
    except PermissionError:
        tree.append(f"{indent}[ACCESS DENIED]")
    return tree


# Генерируем дерево проекта
folder_structure = get_folder_tree(base_path)

# Убедимся, что папка для логов существует
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Записываем дерево в файл
with open(output_file, "w", encoding="utf-8") as file:
    file.write("\n".join(folder_structure))

print(f"Структура папок записана в файл: {output_file}")

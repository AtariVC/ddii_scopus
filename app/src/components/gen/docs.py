from pathlib import Path
from bs4 import BeautifulSoup

# Папка с документацией относительно файла скрипта
docs_path = Path(__file__).parents[1].joinpath("docs/ddii_scopus")

# Файл для объединённого текста
output_file = Path(__file__).parents[1].joinpath("docs/docs_text.txt")

all_text = []

# Рекурсивно проходим по всем HTML-файлам
for html_file in docs_path.rglob("*.html"):
    with html_file.open(encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        
        # Убираем скрипты, стили и навигацию
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()
        
        # Берём основной контент
        main_content = soup.find("main") or soup
        
        # Получаем текст и убираем лишние пробелы и пустые строки
        text = main_content.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)
        
        all_text.append(clean_text)

# Объединяем текст из всех файлов и сохраняем
output_file.write_text("\n\n".join(all_text), encoding="utf-8")

print(f"Текст всей документации собран в {output_file}")

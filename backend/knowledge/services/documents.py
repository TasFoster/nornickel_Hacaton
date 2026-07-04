"""
Чтение и чанкинг документов корпуса. Поддержка txt/md/pdf/docx/csv/xlsx — покрывает
типы источников кейса: статьи и обзоры (pdf/docx), отчёты и протоколы (pdf/docx),
патенты (pdf), справочники по материалам/оборудованию/единицам (csv/xlsx).
Тяжёлые парсеры (pypdf/python-docx/openpyxl) импортируются лениво.
"""
import csv
from pathlib import Path

SUPPORTED = ('.txt', '.md', '.pdf', '.docx', '.csv', '.xlsx')


def read_document(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in ('.txt', '.md'):
        return path.read_text(encoding='utf-8', errors='ignore')
    if ext == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return '\n'.join((page.extract_text() or '') for page in reader.pages)
    if ext == '.docx':
        import docx
        return '\n'.join(p.text for p in docx.Document(str(path)).paragraphs)
    if ext == '.csv':
        return _read_csv(path)
    if ext == '.xlsx':
        return _read_xlsx(path)
    return ''


def _read_csv(path: Path) -> str:
    """Таблицу (справочник) читаем построчно, ячейки склеиваем через ' | '. Разделитель
    определяем автоматически (',' или ';' — частый случай для русских выгрузок)."""
    text = path.read_text(encoding='utf-8', errors='ignore')
    sample = text[:2000]
    delim = ';' if sample.count(';') > sample.count(',') else ','
    lines: list[str] = []
    for row in csv.reader(text.splitlines(), delimiter=delim):
        cells = [c.strip() for c in row if c and c.strip()]
        if cells:
            lines.append(' | '.join(cells))
    return '\n'.join(lines)


def _read_xlsx(path: Path) -> str:
    """Каждый лист — заголовком, строки — ячейки через ' | '. read_only для больших файлов."""
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    out: list[str] = []
    for ws in wb.worksheets:
        out.append(f'# Лист: {ws.title}')
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                out.append(' | '.join(cells))
    wb.close()
    return '\n'.join(out)


def iter_documents(root: Path):
    """Обойти все поддерживаемые документы в каталоге (рекурсивно)."""
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.suffix.lower() in SUPPORTED:
            yield p


def chunk_text(text: str, size: int = 2500, overlap: int = 200) -> list[str]:
    """Разбить текст на перекрывающиеся чанки по смысловому объёму."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks, i = [], 0
    step = max(1, size - overlap)
    while i < len(text):
        chunks.append(text[i:i + size])
        i += step
    return chunks

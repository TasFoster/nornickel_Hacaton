"""
Чтение и чанкинг документов корпуса. Поддержка txt/md/pdf/docx. Тяжёлые парсеры
(pypdf/python-docx) импортируются лениво — нужны только при наличии таких файлов.
"""
from pathlib import Path

SUPPORTED = ('.txt', '.md', '.pdf', '.docx')


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
    return ''


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

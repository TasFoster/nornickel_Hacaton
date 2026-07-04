"""
Загрузка корпуса кейса «Научный клубок» с публичного Яндекс.Диска в data/corpus/.

Скачивает файлы (PDF/DOCX/…) с сохранением структуры папок, идемпотентно
(пропускает уже скачанные файлы того же размера). После загрузки корпус подаётся
в пайплайн извлечения:

    python scripts/download_corpus.py                      # весь корпус
    python scripts/download_corpus.py --path "/Источники информации/Статьи"  # только статьи
    python scripts/download_corpus.py --limit 20           # первые 20 файлов
    cd backend && python manage.py ingest --source ../data/corpus --limit 20

Публичная ссылка задаётся --public-key или переменной окружения CORPUS_PUBLIC_KEY.
"""
import argparse
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://cloud-api.yandex.net/v1/disk/public/resources"
DL = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
DEFAULT_PUBLIC_KEY = os.environ.get(
    "CORPUS_PUBLIC_KEY", "https://disk.yandex.ru/d/npigiuw4Rbe9Pg"
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "corpus")


def _get(url, params, retries=4):
    q = urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f"{url}?{q}", timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001 — сеть/лимиты: ретраим с паузой
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last


def walk(public_key, path):
    """Рекурсивно обходит публичную папку, возвращает список файлов (path, size)."""
    import json
    files = []
    body = _get(API, {"public_key": public_key, "path": path, "limit": 1000})
    data = json.loads(body)
    for item in data.get("_embedded", {}).get("items", []):
        if item["type"] == "dir":
            files.extend(walk(public_key, item["path"]))
        else:
            files.append((item["path"], item.get("size", 0)))
    return files


def download_file(public_key, path, dest):
    import json
    body = _get(DL, {"public_key": public_key, "path": path})
    href = json.loads(body)["href"]
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(href, timeout=300) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)


def main():
    ap = argparse.ArgumentParser(description="Загрузка корпуса с Яндекс.Диска")
    ap.add_argument("--public-key", default=DEFAULT_PUBLIC_KEY)
    ap.add_argument("--path", default="/", help="Подпапка для выборочной загрузки")
    ap.add_argument("--limit", type=int, default=0, help="Ограничить число файлов")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args()

    print(f"Индексирую {args.public_key} :: {args.path} …")
    files = walk(args.public_key, args.path)
    if args.limit:
        files = files[: args.limit]
    print(f"Файлов к загрузке: {len(files)}")

    done = skipped = 0
    for i, (path, size) in enumerate(files, 1):
        rel = path.lstrip("/")
        dest = os.path.join(args.out, *rel.split("/"))
        if os.path.exists(dest) and os.path.getsize(dest) == size:
            skipped += 1
            continue
        try:
            download_file(args.public_key, path, dest)
            done += 1
            print(f"[{i}/{len(files)}] {rel}  ({round(size/1e6, 1)} МБ)")
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}/{len(files)}] ОШИБКА {rel}: {exc}", file=sys.stderr)
    print(f"Готово. Скачано: {done}, пропущено (уже есть): {skipped}. Папка: {args.out}")


if __name__ == "__main__":
    main()

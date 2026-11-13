"""Download reviewed demo product images and optionally link existing MongoDB products.

Run with .venv (requirements-dev.txt). Assets are local: the web never hotlinks sources.
Only image fields of matching product codes/names are updated with --apply-db.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / 'data/demo/product-images.json'


def download(row):
    dest = ROOT / 'static/img/products' / (row['productCode'] + '.webp')
    cache = ROOT / 'backup/image-download-records' / (row['productCode'] + '.json')
    if cache.exists() and dest.exists():
        record = json.loads(cache.read_text(encoding='utf-8'))
        expected = {c['url'] for c in row.get('candidates', [])} or {row.get('originalImage')}
        if record['originalImage'] in expected and record['sha256'] == sha256(dest.read_bytes()).hexdigest():
            return record
    candidates = row.get('candidates') or [{'url': row['originalImage'], 'source': row['source']}]
    errors = []
    for candidate in candidates:
        try:
            parts = urlsplit(candidate['url'])
            if parts.scheme != 'https' or not parts.hostname:
                raise ValueError('HTTPS image required')
            url = urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe='/%:@'),
                             quote(parts.query, safe='=&%:,/+?'), ''))
            request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/*'})
            with urlopen(request, timeout=18) as response:
                data = response.read(12 * 1024 * 1024 + 1)
            if len(data) > 12 * 1024 * 1024:
                raise ValueError('Image exceeds 12 MiB')
            with Image.open(BytesIO(data)) as source:
                if min(source.size) < 100 or source.width * source.height > 40_000_000:
                    raise ValueError('Unexpected image dimensions')
                image = ImageOps.exif_transpose(source).convert('RGBA')
                image.thumbnail((800, 800))
                background = Image.new('RGB', image.size, 'white')
                background.paste(image, mask=image.getchannel('A'))
                dest.parent.mkdir(parents=True, exist_ok=True)
                background.save(dest, 'WEBP', quality=86, method=6)
            record = {'productCode': row['productCode'], 'name': row['name'],
                    'image': '/' + dest.relative_to(ROOT).as_posix(),
                    'source': candidate.get('source') or candidate['url'],
                    'originalImage': candidate['url'], 'sha256': sha256(dest.read_bytes()).hexdigest()}
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            return record
        except Exception as error:
            errors.append(type(error).__name__)
    raise RuntimeError(row['productCode'] + ': download failed (' + ', '.join(errors) + ')')


def apply_database(rows):
    from dotenv import load_dotenv
    from pymongo import MongoClient
    import os

    load_dotenv(ROOT / '.env')
    client = MongoClient(os.environ['MONGO_URI'], serverSelectionTimeoutMS=5000)
    db = client[os.environ.get('MONGO_DB', 'QL_KHUYENMAI_DANHGIA')]
    previous = []
    for row in rows:
        product = db.products.find_one({'productCode': row['productCode'], 'name': row['name']},
                                      {'productCode': 1, 'image': 1, 'imageSource': 1, '_id': 0})
        if product:
            previous.append(product)
    folder = ROOT / 'backup'
    folder.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (folder / f'product-images-before-{stamp}.json').write_text(
        json.dumps(previous, ensure_ascii=False, indent=2), encoding='utf-8')
    matched = 0
    for row in rows:
        matched += db.products.update_one(
            {'productCode': row['productCode'], 'name': row['name']},
            {'$set': {'image': row['image'], 'imageSource': row['source']}}).matched_count
    print(f'Linked images to {matched} existing products; no products inserted.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, help='Reviewed image search candidates JSON')
    parser.add_argument('--apply-db', action='store_true')
    args = parser.parse_args()
    source = args.candidates or MANIFEST
    rows = json.loads(source.read_text(encoding='utf-8'))
    downloaded, errors = [], []
    with ThreadPoolExecutor(max_workers=5) as pool:
        for future in as_completed([pool.submit(download, row) for row in rows]):
            try:
                downloaded.append(future.result())
            except Exception as error:
                errors.append(str(error))
    if errors:
        raise RuntimeError('; '.join(errors))
    rows = downloaded
    rows.sort(key=lambda row: row['productCode'])
    MANIFEST.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    products_file = ROOT / 'data/demo/products.json'
    products = json.loads(products_file.read_text(encoding='utf-8'))
    images = {row['productCode']: row['image'] for row in rows}
    for product in products:
        if product['productCode'] in images:
            product['image'] = images[product['productCode']]
    products_file.write_text(json.dumps(products, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Downloaded and validated {len(rows)} local images.')
    if args.apply_db:
        apply_database(rows)


if __name__ == '__main__':
    main()

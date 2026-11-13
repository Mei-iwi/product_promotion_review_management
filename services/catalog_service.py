import re
from urllib.parse import urlsplit
from repositories import public_repository as repo
from services.helpers import ValidationError


def image_url(value):
    if isinstance(value, str) and len(value) <= 2000:
        if value.startswith('/static/') and not value.startswith('//'):
            return value
        try:
            parts = urlsplit(value)
        except ValueError:
            return '/static/img/product-placeholder.svg'
        if parts.scheme in {'https', 'http'} and parts.netloc and not parts.username and not parts.password:
            return value
    return '/static/img/product-placeholder.svg'


def decorate(rows):
    ratings = repo.ratings([row['productCode'] for row in rows])
    for row in rows:
        stats = ratings.get(row['productCode'], {})
        row['avgRating'] = round(stats.get('avgRating', 0), 1)
        row['reviewCount'] = stats.get('reviewCount', 0)
        row['image'] = image_url(row.get('image'))
        if 'attributes' in row and isinstance(row['attributes'], dict):
            row['attributes'] = {key: value for key, value in row['attributes'].items()
                                 if isinstance(value, (str, int, float, bool))}
        elif 'attributes' in row:
            row['attributes'] = {}
    return rows


def listing(filters=None):
    filters = filters if filters is not None else {}
    allowed = {'q', 'category', 'brand', 'sort', 'page', 'per_page'}
    if set(filters) - allowed or any(not isinstance(v, str) for v in filters.values()):
        raise ValidationError('Bộ lọc danh mục không hợp lệ')
    if hasattr(filters, 'getlist') and any(len(filters.getlist(k)) != 1 for k in filters):
        raise ValidationError('Không được lặp bộ lọc')
    clean = {k: filters.get(k, '').strip() for k in ['q', 'category', 'brand']}
    if any(len(value) > 100 for value in clean.values()):
        raise ValidationError('Bộ lọc tối đa 100 ký tự')
    sort = filters.get('sort', 'name')
    if sort not in {'name', 'price_asc', 'price_desc'}:
        raise ValidationError('Cách sắp xếp không hợp lệ')
    try:
        number, size = filters.get('page', '1'), filters.get('per_page', '12')
        if not re.fullmatch(r'[0-9]{1,6}', number) or not re.fullmatch(r'[0-9]{1,2}', size):
            raise ValueError()
        number, size = int(number), int(size)
        if not 1 <= number <= 100000 or not 1 <= size <= 48:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValidationError('Trang hoặc số sản phẩm mỗi trang không hợp lệ')
    query = {'status': 'active'}
    if clean['q']:
        query['name'] = {'$regex': re.escape(clean['q']), '$options': 'i'}
    if clean['category']:
        query['category.categoryCode'] = clean['category']
    if clean['brand']:
        query['brand'] = clean['brand']
    ordering = [('name', 1)] if sort == 'name' else [('price', -1 if sort == 'price_desc' else 1)]
    rows, total = repo.page(query, ordering + [('productCode', 1)], number, size)
    return {'rows': decorate(rows), 'total': total, 'page': number, 'per_page': size,
            'pages': max(1, (total + size - 1) // size), 'filters': {**clean, 'sort': sort, 'per_page': size}, **repo.options()}


def product(code):
    row = repo.product(code)
    if row:
        row.setdefault('attributes', {})
    return decorate([row])[0] if row else None

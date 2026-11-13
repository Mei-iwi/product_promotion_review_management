"""HTTP authentication, deny-by-default endpoint registry and synchronizer CSRF."""
from functools import wraps
import secrets
from flask import abort, current_app, g, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException
from pymongo.errors import PyMongoError
from services import auth_service as auth
from services.access_policy import has_permission, LANDINGS, REPORT_PERMISSIONS, ROLE_LABELS, USER_STATUS_LABELS
from services.helpers import ValidationError

ENDPOINT_POLICIES = {}


def register(endpoint, methods, permission):
    for method in methods.split():
        ENDPOINT_POLICIES[(endpoint, method)] = permission


for group, read, create, update in [
    ('product', 'products.read_internal', 'products.create', 'products.update'),
    ('promotion', 'promotions.read', 'promotions.create', 'promotions.update'),
    ('customer', 'customers.read', 'customers.create', 'customers.update'),
]:
    for endpoint in [f'web.{group}s', f'web.{group}_detail', f'api.{group}s', f'api.{group}']:
        register(endpoint, 'GET', read)
    register(f'web.{group}_create_form', 'GET POST', create)
    register(f'web.{group}_edit_form', 'GET POST', update)
    register(f'api.create_{group}', 'POST', create)
    register(f'api.update_{group}', 'PUT', update)
register('api.product_status', 'PATCH', 'products.update')
register('api.product_tags', 'PATCH', 'products.update')
register('api.delete_product', 'DELETE', 'products.delete_test')
for prefix in ['api', 'web']:
    register(f'{prefix}.reviews', 'GET', 'reviews.read_moderation_queue')
    register(f'{prefix}.create_review', 'POST', 'reviews.create_own')
    register(f'{prefix}.review_status', 'PATCH' if prefix == 'api' else 'POST', 'reviews.moderate')
    register(f'{prefix}.orders', 'GET', 'orders.read_all')
register('api.order', 'GET', 'orders.read_all')
register('web.order_detail', 'GET', 'orders.read_all')
register('web.home', 'GET', 'reports.read_sensitive')
register('web.dashboard', 'GET', 'reports.read_aggregate')
register('web.query_demo', 'GET', 'reports.read_aggregate')
for endpoint in ['summary', 'ratings', 'promotions', 'sales']:
    register('api.dashboard_' + endpoint, 'GET', 'reports.read_aggregate')
register('auth.login', 'GET POST', None)
register('auth.logout', 'POST', 'account.logout')
register('auth.change_password', 'GET POST', 'account.change_own_password')
register('auth.users', 'GET', 'users.read')
register('auth.create_user', 'GET POST', 'users.create')
register('auth.edit_user', 'GET POST', 'users.update')
register('auth.account', 'GET', 'customers.read_own')
register('auth.profile', 'POST', 'customers.update_own_profile')
register('auth.own_orders', 'GET', 'orders.read_own')
register('auth.own_order', 'GET', 'orders.read_own')
register('auth.own_reviews', 'GET', 'reviews.read_own')
register('auth.order_review', 'POST', 'reviews.create_own')
register('auth.catalog', 'GET', None)
register('auth.public_product', 'GET', None)
register('auth.public_reviews', 'GET', None)
register('auth.api_catalog', 'GET', None)
register('auth.api_public_reviews', 'GET', None)
register('auth.api_profile', 'GET PUT', 'customers.read_own')
register('auth.api_profile', 'PUT', 'customers.update_own_profile')
register('auth.api_orders', 'GET', 'orders.read_own')
register('auth.api_order', 'GET', 'orders.read_own')
register('auth.api_reviews', 'GET', 'reviews.read_own')
register('auth.api_users', 'GET', 'users.read')
register('auth.api_create_user', 'POST', 'users.create')
register('auth.api_update_user', 'PUT', 'users.update')
register('static', 'GET', None)
register('auth.health', 'GET', None)
for endpoint in ['cart', 'api_cart']:
    register('shop.' + endpoint, 'GET', 'cart.read_own')
for endpoint in ['add', 'set_quantity', 'remove', 'apply_promo', 'clear_promo', 'api_add']:
    register('shop.' + endpoint, 'POST', 'cart.manage_own')
register('shop.api_set', 'PUT', 'cart.manage_own')
register('shop.api_remove', 'DELETE', 'cart.manage_own')
register('shop.api_apply', 'PUT', 'cart.manage_own')
register('shop.api_clear', 'DELETE', 'cart.manage_own')
register('shop.vouchers', 'GET', 'promotions.view_offers')
register('shop.checkout_promotion', 'POST', 'orders.create_own')
register('shop.quote', 'POST', 'orders.create_own')
register('shop.api_quote', 'POST', 'orders.create_own')
register('shop.checkout', 'GET POST', 'orders.create_own')
register('shop.api_checkout', 'POST', 'orders.create_own')
register('shop.confirmation', 'GET', 'orders.read_own')
register('shop.cancel', 'POST', 'orders.cancel_own')
register('shop.api_cancel', 'POST', 'orders.cancel_own')
register('shop.order_status', 'POST', 'orders.manage_status')
register('shop.api_order_status', 'PATCH', 'orders.manage_status')


def is_api():
    return request.path.startswith('/api/')


def load_current_user():
    g.request_id = secrets.token_hex(16)
    g.auth_session, g.current_user = auth.resolve_session(request.cookies.get(current_app.config['AUTH_COOKIE_NAME']))


def csrf_token():
    if not g.get('auth_session'):
        g.session_token, g.auth_session = auth.issue_session(g.get('current_user'))
    return g.auth_session['csrfToken']


def denied(status):
    auth.audit('access.denied', 'denied', actor=(g.get('current_user') or {}).get('_id'),
               resource_type='endpoint', resource_id=request.endpoint, metadata={'method': request.method, 'status': status})
    if status == 401 and not is_api():
        return redirect(url_for('auth.login'))
    abort(status)


def permission_required(permission):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not g.get('current_user'):
                return denied(401)
            if not has_permission(g.current_user, permission):
                return denied(403)
            return func(*args, **kwargs)
        return wrapped
    return decorator


def login_required(func):
    return permission_required('account.logout')(func)


def validate_input(value):
    """Reject query operators, dot paths, oversized strings and non-finite numbers."""
    import math
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or key.startswith('$') or '.' in key:
                raise ValidationError('Tên trường không hợp lệ')
            validate_input(item)
    elif isinstance(value, list):
        for item in value:
            validate_input(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValidationError('Số không hợp lệ')
    elif isinstance(value, str) and len(value) > 10000:
        raise ValidationError('Giá trị quá dài')


def init_security(app):
    @app.before_request
    def enforce():
        load_current_user()
        if app.config['APP_ENV'] == 'production' and not request.is_secure and not (
            request.endpoint == 'auth.health' and request.remote_addr in {'127.0.0.1', '::1'}):
            abort(400, description='Yêu cầu HTTPS')
        if not request.endpoint:
            abort(404)
        method = 'GET' if request.method == 'HEAD' else request.method
        if method == 'OPTIONS':
            methods = sorted(m for ep, m in ENDPOINT_POLICIES if ep == request.endpoint)
            method = 'GET' if 'GET' in methods else (methods[0] if methods else 'OPTIONS')
        key = (request.endpoint, method)
        if key not in ENDPOINT_POLICIES:
            return denied(403)
        permission = ENDPOINT_POLICIES[key]
        if permission:
            if not g.current_user:
                return denied(401)
            if not has_permission(g.current_user, permission):
                return denied(403)
        if request.endpoint == 'web.query_demo':
            code = request.args.get('report', 'NC05')
            if code not in REPORT_PERMISSIONS:
                abort(400, description='Mã báo cáo không hợp lệ')
            if not has_permission(g.current_user, REPORT_PERMISSIONS[code]):
                return denied(403)
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not g.auth_session or not isinstance(token, str) or not secrets.compare_digest(token.encode('utf-8'), g.auth_session['csrfToken'].encode('utf-8')):
                auth.audit('csrf.denied', 'denied', actor=(g.current_user or {}).get('_id'))
                abort(400, description='CSRF token không hợp lệ; hãy tải lại trang')
            if request.is_json:
                value = request.get_json(silent=True)
                if not isinstance(value, dict):
                    raise ValidationError('Dữ liệu JSON không hợp lệ')
                validate_input(value)
                if request.endpoint.startswith('api.'):
                    allowed = {
                        'api.product_status': {'status'}, 'api.product_tags': {'tag', 'action'},
                        'api.review_status': {'status'},
                    }.get(request.endpoint)
                    if allowed is not None and (set(value) - allowed or any(not isinstance(v, str) for v in value.values())):
                        raise ValidationError('Trường hoặc kiểu dữ liệu không được phép')
            else:
                validate_input(request.form.to_dict())

    @app.context_processor
    def security_context():
        return {'current_user': g.get('current_user'), 'can': lambda permission: has_permission(g.get('current_user'), permission),
                'csrf_token': csrf_token, 'role_labels': ROLE_LABELS, 'user_status_labels': USER_STATUS_LABELS,
                'landing': LANDINGS.get((g.get('current_user') or {}).get('role'), '/catalog')}

    @app.after_request
    def security_headers(response):
        if g.get('session_token'):
            response.set_cookie(app.config['AUTH_COOKIE_NAME'], g.session_token, secure=app.config['AUTH_COOKIE_SECURE'],
                                httponly=True, samesite='Lax', path='/')
        if g.get('clear_auth_cookie'):
            response.delete_cookie(app.config['AUTH_COOKIE_NAME'], secure=app.config['AUTH_COOKIE_SECURE'], httponly=True, samesite='Lax', path='/')
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' https: data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers['X-Request-ID'] = g.get('request_id', '')
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and response.status_code < 400 and request.endpoint and any(x in request.endpoint for x in ['promotion', 'review_status']):
            auth.audit(request.endpoint, actor=(g.get('current_user') or {}).get('_id'), resource_type='business', resource_id=(request.view_args or {}).get('code'))
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = {400: 'Yêu cầu không hợp lệ', 401: 'Cần đăng nhập', 403: 'Bạn không có quyền truy cập', 404: 'Không tìm thấy dữ liệu', 405: 'Phương thức không được phép', 413: 'Yêu cầu quá lớn', 429: 'Vui lòng thử lại sau'}.get(error.code, 'Không thể xử lý yêu cầu')
        if is_api():
            return jsonify(success=False, message=message, data=None), error.code
        return render_template('error.html', message=message), error.code

    @app.errorhandler(ValidationError)
    def invalid(error):
        if is_api():
            return jsonify(success=False, message=str(error), data=None), 400
        return render_template('error.html', message=str(error)), 400

    @app.errorhandler(BlockingIOError)
    def busy(error):
        if is_api():
            return jsonify(success=False, message=str(error), data=None), 409
        return render_template('error.html', message=str(error)), 409

    @app.errorhandler(PyMongoError)
    def database_error(error):
        if is_api():
            return jsonify(success=False, message='Không thể xử lý dữ liệu', data=None), 503
        return render_template('error.html', message='Không thể xử lý dữ liệu'), 503

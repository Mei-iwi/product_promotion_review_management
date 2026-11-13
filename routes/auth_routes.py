from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from db.mongo import get_db
from repositories import public_repository
from services import auth_service as auth, user_service, customer_account_service as own, review_service, catalog_service
from services.access_policy import ROLE_PERMISSIONS, LANDINGS
from services.helpers import ValidationError
from routes.api_routes import response, body

bp = Blueprint('auth', __name__)


@bp.get('/health')
def health():
    get_db().command('ping')
    return response(None, 'OK')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    status = 200
    if request.method == 'POST':
        user, status = auth.authenticate(request.form.get('email'), request.form.get('password'), request.remote_addr)
        if user:
            auth.revoke_session(g.auth_session)
            g.session_token, g.auth_session = auth.issue_session(user)
            g.current_user = user
            # All roles start at the public catalog; never trust a client-supplied next URL.
            return redirect(LANDINGS[user['role']])
        error = auth.LOGIN_ERROR
    return render_template('auth/login.html', error=error), status


@bp.post('/logout')
def logout():
    auth.revoke_session(g.auth_session)
    auth.audit('logout', actor=g.current_user['_id'])
    g.clear_auth_cookie = True
    return redirect('/login')


@bp.route('/account/change-password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        auth.change_password(g.current_user, request.form.get('currentPassword'), request.form.get('newPassword'))
        g.clear_auth_cookie = True
        return redirect('/login')
    return render_template('auth/password.html')


@bp.get('/admin/users')
def users():
    result = user_service.list_users(g.current_user, request.args, paginate=True)
    def page_url(page):
        return url_for('auth.users', **{**result['filters'], 'page': page})
    return render_template('auth/users.html', **result, page_url=page_url)


def user_form_data():
    if any(len(request.form.getlist(key)) != 1 for key in request.form):
        raise ValidationError('Không được lặp lại trường biểu mẫu')
    return {key: value for key, value in request.form.items()
            if key != 'csrf_token' and (value != '' or key in {'email', 'role', 'customerCode'})}


def account_form(item=None, values=None, error=None, status=200):
    from services.access_policy import has_permission
    roles = ROLE_PERMISSIONS if has_permission(g.current_user, 'users.assign_role') else {'CUSTOMER': ROLE_PERMISSIONS['CUSTOMER']}
    return render_template('auth/user_form.html', item=item, roles=roles, values=values or {}, error=error), status


@bp.route('/admin/users/create', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        try:
            auth.create_user(user_form_data(), g.current_user)
        except (ValidationError, BlockingIOError) as error:
            return account_form(values=user_service.form_values(request.form, g.current_user), error=str(error),
                                status=409 if isinstance(error, BlockingIOError) else 400)
        flash('Đã tạo tài khoản thành công', 'success')
        return redirect('/admin/users')
    return account_form()


@bp.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    item = user_service.managed_user(g.current_user, user_id)
    if request.method == 'POST':
        try:
            user_service.update_user(g.current_user, user_id, user_form_data())
        except (ValidationError, BlockingIOError) as error:
            return account_form(item=user_service.public_user(item), values=user_service.form_values(request.form, g.current_user),
                                error=str(error), status=409 if isinstance(error, BlockingIOError) else 400)
        flash('Đã cập nhật tài khoản thành công', 'success')
        return redirect('/admin/users')
    return account_form(item=user_service.public_user(item))


@bp.get('/api/users')
def api_users():
    result = user_service.list_users(g.current_user, request.args)
    reply, status = response(result['rows'])
    reply.headers['X-Total-Count'] = str(result['total'])
    if result['paged']:
        reply.headers['X-Page'] = str(result['page'])
        reply.headers['X-Per-Page'] = str(result['per_page'])
    return reply, status


@bp.post('/api/users')
def api_create_user():
    return response(user_service.public_user(auth.create_user(body(), g.current_user)), message='Đã tạo tài khoản thành công', status=201)


@bp.put('/api/users/<user_id>')
def api_update_user(user_id):
    return response(user_service.public_user(user_service.update_user(g.current_user, user_id, body())), message='Đã cập nhật tài khoản thành công')


@bp.get('/account')
def account():
    return render_template('auth/account.html', item=own.profile(g.current_user))


@bp.post('/account/profile')
def profile():
    own.update_profile(g.current_user, request.form.to_dict())
    return redirect('/account')


@bp.get('/account/orders')
def own_orders():
    status = request.args.get('status', '')
    return render_template('auth/orders.html', rows=own.orders(g.current_user, status), selected_status=status)


@bp.get('/account/orders/<code>')
def own_order(code):
    row = own.order(g.current_user, code)
    return render_template('orders/detail.html', item=row, subtotal=sum(r['quantity'] * r['unitPrice'] for r in row['items']), own=True)


@bp.get('/account/reviews')
def own_reviews():
    return render_template('auth/reviews.html', rows=own.review_history(g.current_user))


@bp.post('/account/orders/<code>/reviews')
def order_review(code):
    row = own.order(g.current_user, code)
    try:
        if any(len(request.form.getlist(k)) != 1 for k in request.form):
            raise ValidationError('Không được lặp lại trường biểu mẫu')
        data = request.form.to_dict()
        data.pop('csrf_token', None)
        if set(data) - {'productCode', 'rating', 'title', 'content'}:
            raise ValidationError('Trường đánh giá không được phép')
        review_service.create_own(g.current_user, data, order_code=code)
        flash('Đã gửi đánh giá sản phẩm, đang chờ duyệt', 'success')
        return redirect(url_for('auth.own_order', code=code))
    except ValidationError as error:
        values = {key: request.form.get(key, '')[:5000] for key in ['productCode', 'rating', 'title', 'content']}
        return render_template('orders/detail.html', item=row, own=True,
                               subtotal=sum(r['quantity'] * r['unitPrice'] for r in row['items']),
                               review_error=str(error), review_values=values), 400


@bp.route('/api/account/profile', methods=['GET', 'PUT'])
def api_profile():
    return response(own.update_profile(g.current_user, body()) if request.method == 'PUT' else own.profile(g.current_user))


@bp.get('/api/account/orders')
def api_orders():
    return response(own.orders(g.current_user, request.args.get('status', '')))


@bp.get('/api/account/orders/<code>')
def api_order(code):
    return response(own.order(g.current_user, code))


@bp.get('/api/account/reviews')
def api_reviews():
    return response(own.reviews(g.current_user))


@bp.get('/catalog')
def catalog():
    result = catalog_service.listing(request.args)
    return render_template('auth/catalog.html', **result, page_url=lambda p: url_for('auth.catalog', **{**result['filters'], 'page': p}))


@bp.get('/catalog/<code>')
def public_product(code):
    item = catalog_service.product(code)
    if not item:
        abort(404)
    return render_template('auth/public_product.html', item=item, reviews=public_repository.reviews(code),
                           can_review=review_service.can_review(g.current_user, code))


@bp.get('/catalog/<code>/reviews')
def public_reviews(code):
    return public_product(code)


@bp.get('/api/public/products')
def api_catalog():
    result = catalog_service.listing(request.args)
    reply, status = response(result['rows'])
    reply.headers['X-Total-Count'] = str(result['total'])
    return reply, status


@bp.get('/api/public/products/<code>/reviews')
def api_public_reviews(code):
    rows = public_repository.reviews(code)
    if rows is None:
        abort(404)
    return response(rows)

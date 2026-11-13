from flask import Blueprint, g, request, render_template, redirect, url_for, flash
from services import cart_service, checkout_service, customer_account_service as own, order_service, promotion_offer_service
from services.shopping_common import ShoppingError
from services.helpers import ValidationError
from routes.api_routes import body, response

bp = Blueprint('shop', __name__)


def data(fields):
    value = body() if request.is_json else {k: v for k, v in request.form.items() if k != 'csrf_token'}
    if set(value) - set(fields) or (not request.is_json and any(len(request.form.getlist(k)) > 1 for k in request.form)):
        raise ValidationError('Trường yêu cầu không được phép')
    return value


def cart_page(error=None, status=200, attempted_promo=None):
    return render_template('auth/cart.html', cart=cart_service.view(g.current_user), error=error,
                           offers=promotion_offer_service.for_cart(g.current_user),
                           attempted_promo=attempted_promo, unavailable=checkout_service.availability()), status


@bp.errorhandler(ShoppingError)
def error_response(error):
    if request.path.startswith('/api/'):
        return response(None, str(error), error.status, False)
    return render_template('error.html', message=str(error)), error.status


@bp.get('/cart')
def cart():
    return cart_page()


@bp.get('/vouchers')
def vouchers():
    offers = promotion_offer_service.for_cart(g.current_user) if g.current_user and g.current_user['role'] == 'CUSTOMER' else []
    return render_template('auth/vouchers.html', **promotion_offer_service.listing(request.args),
                           eligible={offer['promoCode']: offer['discount'] for offer in offers})


def change(action, product_code=None):
    fields = {'productCode', 'quantity'} if action == 'add' else ({'quantity'} if action == 'set' else ({'promoCode'} if action == 'apply' else set()))
    value = data(fields)
    if action == 'apply' and value.get('promoCode') == '':
        action = 'clear_promo'
    try:
        result = cart_service.change(g.current_user, action, product_code or value.get('productCode'), value.get('quantity'), value.get('promoCode'))
    except ShoppingError as error:
        if request.path.startswith('/api/'):
            raise
        return cart_page(str(error), error.status, value.get('promoCode'))
    if request.path.startswith('/api/'):
        return response({k: v for k, v in result.items() if k != 'fingerprint'})
    flash('Đã cập nhật giỏ hàng', 'success')
    return redirect(url_for('shop.cart'))


@bp.post('/cart/items')
def add(): return change('add')


@bp.post('/cart/items/<code>')
def set_quantity(code): return change('set', code)


@bp.post('/cart/items/<code>/remove')
def remove(code): return change('remove', code)


@bp.post('/cart/promotion')
def apply_promo(): return change('apply')


@bp.post('/cart/promotion/remove')
def clear_promo(): return change('clear_promo')


@bp.get('/api/account/cart')
def api_cart():
    return response({k: v for k, v in cart_service.view(g.current_user).items() if k != 'fingerprint'})


@bp.post('/api/account/cart/items')
def api_add(): return change('add')


@bp.put('/api/account/cart/items/<code>')
def api_set(code): return change('set', code)


@bp.delete('/api/account/cart/items/<code>')
def api_remove(code): return change('remove', code)


@bp.put('/api/account/cart/promotion')
def api_apply(): return change('apply')


@bp.delete('/api/account/cart/promotion')
def api_clear(): return change('clear_promo')


@bp.post('/checkout/quote')
def quote():
    data(set())
    try:
        row = checkout_service.create_quote(g.current_user)
        return redirect(url_for('shop.checkout', key=row['_id']))
    except ShoppingError as error:
        return cart_page(str(error), error.status)


@bp.post('/api/account/checkout/quotes')
def api_quote():
    data(set())
    row = checkout_service.create_quote(g.current_user)
    return response({'checkoutKey': row['_id'], **{k: row[k] for k in ['lines', 'subtotal', 'discount', 'shippingFee', 'total', 'expiresAt']}}, status=201)


def checkout_page(key, values=None, error=None, status=200):
    quote = checkout_service.get_quote(g.current_user, key)
    profile = own.profile(g.current_user)
    values = values if values is not None else {'fullName': profile['fullName'], 'address': profile.get('address', ''), 'phone': ''}
    return render_template('auth/checkout.html', quote=quote, values=values, error=error,
                           offers=promotion_offer_service.for_cart(g.current_user)), status


@bp.post('/checkout/<key>/promotion')
def checkout_promotion(key):
    values = data({'fullName', 'address', 'phone', 'promoCode'})
    promo_code = values.pop('promoCode', '')
    safe = {k: v[:500] for k, v in values.items() if isinstance(v, str)}
    try:
        quote = checkout_service.change_promotion(g.current_user, key, promo_code)
        flash('Đã cập nhật mã giảm giá. Vui lòng kiểm tra tổng tiền trước khi đặt hàng.', 'success')
        return checkout_page(quote['_id'], safe)
    except ShoppingError as error:
        return checkout_page(key, safe, error, error.status)


@bp.route('/checkout/<key>', methods=['GET', 'POST'])
def checkout(key):
    if request.method == 'POST':
        values = data({'fullName', 'address', 'phone', 'promoCode'})
        selected = values.pop('promoCode', None)
        try:
            if selected is not None and selected != checkout_service.get_quote(g.current_user, key).get('promoCode', ''):
                raise ShoppingError('Bạn vừa chọn mã khác. Hãy nhấn Áp dụng mã để cập nhật tổng tiền trước khi đặt hàng.')
            order = checkout_service.place_order(g.current_user, key, values)
            return redirect(url_for('shop.confirmation', code=order['orderCode']))
        except ShoppingError as error:
            safe = {k: v[:500] for k, v in values.items() if isinstance(v, str)}
            return checkout_page(key, safe, error, error.status)
    return checkout_page(key)


@bp.post('/api/account/checkout')
def api_checkout():
    values = data({'checkoutKey', 'fullName', 'address', 'phone'})
    key = values.pop('checkoutKey', None)
    return response(checkout_service.safe_order(checkout_service.place_order(g.current_user, key, values)), 'Đã ghi nhận đơn COD', 201)


@bp.get('/account/orders/<code>/confirmation')
def confirmation(code):
    return render_template('auth/order_confirmation.html', item=own.order(g.current_user, code))


@bp.post('/account/orders/<code>/cancel')
def cancel(code):
    data(set())
    try:
        order_service.transition(g.current_user, code, 'cancelled', own=True)
        flash('Đã hủy đơn hàng; tồn kho và lượt mã đã được xử lý đúng một lần', 'success')
        return redirect(url_for('auth.own_order', code=code))
    except ShoppingError as error:
        row = own.order(g.current_user, code)
        return render_template('orders/detail.html', item=row, own=True,
                               subtotal=sum(r['quantity'] * r['unitPrice'] for r in row['items']), order_error=str(error)), error.status


@bp.post('/api/account/orders/<code>/cancel')
def api_cancel(code):
    data(set())
    return response(checkout_service.safe_order(order_service.transition(g.current_user, code, 'cancelled', own=True)))


@bp.post('/don-hang/<code>/trang-thai')
def order_status(code):
    value = data({'status'})
    try:
        order_service.transition(g.current_user, code, value.get('status'))
        flash('Đã cập nhật trạng thái đơn hàng', 'success')
        return redirect(url_for('web.order_detail', code=code))
    except ShoppingError as error:
        row = order_service.get_order(code)
        return render_template('orders/detail.html', item=row, order_error=str(error),
                               subtotal=sum(r['quantity'] * r['unitPrice'] for r in row['items'])), error.status


@bp.patch('/api/orders/<code>/status')
def api_order_status(code):
    value = data({'status'})
    return response(checkout_service.safe_order(order_service.transition(g.current_user, code, value.get('status'))))

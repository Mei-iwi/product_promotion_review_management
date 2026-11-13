from repositories import order_repository as repo
from services.helpers import ValidationError
from services.access_policy import has_permission


def list_orders(filters=None):
    try: return repo.find_orders(filters)
    except ValueError as exc: raise ValidationError('Bộ lọc ngày không hợp lệ') from exc
def get_order(code): return repo.find_by_code(code)


def transition(principal, code, desired, own=False):
    from db.mongo import get_db
    from repositories import shopping_repository as shopping
    from repositories.security_repository import utcnow
    from services import checkout_service
    from services.shopping_common import ShoppingError
    from werkzeug.exceptions import Forbidden, NotFound
    permission = 'orders.cancel_own' if own else 'orders.manage_status'
    if not has_permission(principal, permission) or (own and desired != 'cancelled'):
        raise Forbidden()
    if not isinstance(desired, str) or desired not in {'confirmed', 'completed', 'cancelled'}:
        raise ShoppingError('Trạng thái đơn hàng không hợp lệ')
    # Check ownership before feature availability to avoid leaking other orders.
    query = {'orderCode': code}
    if own:
        query['customerCode'] = principal['customerCode']
    if not get_db().orders.find_one(query):
        raise NotFound()
    checkout_service.require_ready(require_enabled=False)

    def run(session):
        db = get_db()
        if not shopping.fence(session):
            raise ShoppingError('Cần đối soát lượt mã', 'checkout_unavailable', 503)
        if own:
            checkout_service.validate_principal(principal, session)
        else:
            actor = db.users.find_one({'_id': principal['_id'], 'status': 'active', 'authVersion': principal['authVersion']}, session=session)
            if not has_permission(actor, 'orders.manage_status'):
                raise Forbidden()
        row = db.orders.find_one(query, session=session)
        if not row:
            raise NotFound()
        if row['status'] == desired:
            return row
        if desired not in {'pending': {'confirmed', 'cancelled'}, 'confirmed': {'completed'}}.get(row['status'], set()):
            raise ShoppingError('Đơn đã chuyển trạng thái; thao tác này không còn hợp lệ', 'order_state_conflict', 409)
        changes = {'status': desired}
        if desired == 'cancelled':
            if row.get('inventoryReserved') and row.get('commerceVersion') == 1:
                for item in row['items']:
                    if db.products.update_one({'productCode': item['productCode']}, {'$inc': {'stock': item['quantity']}}, session=session).matched_count != 1:
                        raise ShoppingError('Không thể hoàn tồn; cần kiểm tra sản phẩm bị thiếu', 'inventory_conflict', 409)
                changes['inventoryReserved'] = False
            if row.get('promotionUsageAccounted') and row.get('appliedPromotion'):
                promo_code = row['appliedPromotion']['promoCode']
                if db.promotions.update_one({'promoCode': promo_code, 'commerceUsed': {'$gte': 1}}, {'$inc': {'commerceUsed': -1}}, session=session).modified_count != 1:
                    raise ShoppingError('Lượt mã chưa nhất quán; cần đối soát lại', 'usage_conflict', 409)
                changes.update(promotionReserved=False, promotionUsageAccounted=False)
        now = utcnow()
        event = {'status': desired, 'at': now, 'actorUserId': principal['_id'], 'actorRole': principal['role']}
        changes['statusHistory'] = (row.get('statusHistory') or []) + [event]
        result = db.orders.update_one({**query, 'status': row['status']}, {'$set': changes}, session=session)
        if result.modified_count != 1:
            raise ShoppingError('Trạng thái đơn vừa thay đổi', 'order_state_conflict', 409)
        db.audit_logs.insert_one({'actorUserId': principal['_id'], 'action': 'orders.' + desired, 'resourceType': 'orders',
                                  'resourceId': code, 'timestamp': now, 'result': 'success', 'metadata': {'from': row['status'], 'to': desired}}, session=session)
        return db.orders.find_one(query, session=session)
    return shopping.transaction(run)


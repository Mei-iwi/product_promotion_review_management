"""Single source of role permissions; roles have no implicit hierarchy."""
PUBLIC_PERMISSIONS = frozenset({'products.public_read', 'reviews.public_read_approved'})
ACCOUNT = {'account.change_own_password', 'account.logout', 'promotions.view_offers',
           'account.read_own_profile', 'account.update_own_profile'}
PRODUCT_READ = {'products.read_internal'}
PRODUCT_WRITE = {'products.create', 'products.update', 'products.delete_test'}
PROMOTIONS = {'promotions.read', 'promotions.create', 'promotions.update'}
CUSTOMERS = {'customers.read', 'customers.create', 'customers.update'}
MODERATION = {'reviews.read_moderation_queue', 'reviews.moderate'}
REPORTS = {'reports.read_aggregate', 'reports.read_sensitive'}
USERS = {'users.read', 'users.create', 'users.update', 'users.assign_role', 'users.disable', 'users.reset_password', 'users.manage_all'}
SHOPPING = {'cart.read_own', 'cart.manage_own', 'orders.create_own', 'orders.cancel_own'}
OWN = {'customers.read_own', 'customers.update_own_profile', 'orders.read_own', 'reviews.create_own', 'reviews.read_own'}
ROLE_PERMISSIONS = {
    'ADMIN': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | PRODUCT_READ | PRODUCT_WRITE | PROMOTIONS | CUSTOMERS | MODERATION | REPORTS | USERS | {'orders.read_all', 'orders.manage_status'}),
    'ACCOUNT_MANAGER': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | (USERS - {'users.assign_role', 'users.manage_all'}) | {'users.manage_customers'}),
    'PRODUCT_STAFF': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | PRODUCT_READ | PRODUCT_WRITE),
    'MARKETING_STAFF': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | PRODUCT_READ | PROMOTIONS),
    'SUPPORT_STAFF': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | PRODUCT_READ | CUSTOMERS | {'orders.read_all'}),
    'REVIEW_MODERATOR': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | PRODUCT_READ | MODERATION),
    'ANALYST': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | {'reports.read_aggregate'}),
    'CUSTOMER': frozenset(PUBLIC_PERMISSIONS | ACCOUNT | OWN | SHOPPING),
}
PERMISSIONS = frozenset().union(*ROLE_PERMISSIONS.values())
LANDINGS = {role: '/catalog' for role in ROLE_PERMISSIONS}
SENSITIVE_REPORTS = frozenset({'CB08', 'CB09', 'CB11', 'CB12', 'NC04', 'NC10'})
ROLE_LABELS = {
    'ADMIN': 'Admin', 'ACCOUNT_MANAGER': 'Quản trị viên tài khoản',
    'PRODUCT_STAFF': 'Nhân viên sản phẩm', 'MARKETING_STAFF': 'Nhân viên khuyến mãi',
    'SUPPORT_STAFF': 'Nhân viên hỗ trợ', 'REVIEW_MODERATOR': 'Kiểm duyệt viên',
    'ANALYST': 'Chuyên viên phân tích', 'CUSTOMER': 'Khách hàng',
}
USER_STATUS_LABELS = {'active': 'Đang hoạt động', 'disabled': 'Vô hiệu hóa', 'locked': 'Đang khóa'}
# Detail product queries expose internal inventory; analysts receive aggregate reports only.
REPORT_PERMISSIONS = {
    **{f'CB{i:02}': 'reports.read_sensitive' for i in range(1, 13)},
    **{f'NC{i:02}': ('reports.read_sensitive' if f'NC{i:02}' in SENSITIVE_REPORTS else 'reports.read_aggregate') for i in range(1, 11)},
}


def has_permission(principal, permission):
    return permission in PERMISSIONS and permission in (ROLE_PERMISSIONS.get(principal.get('role'), frozenset()) if principal else PUBLIC_PERMISSIONS)


def authorize_object(principal, action, obj):
    if not principal or not obj or not has_permission(principal, action):
        return False
    if action in {'account.read_own_profile', 'account.update_own_profile'}:
        return obj.get('_id') == principal.get('_id')
    if action in OWN | SHOPPING:
        owner = obj.get('customerCode') or obj.get('customer', {}).get('customerCode')
        if action.startswith('cart.') and obj.get('userId') != principal['_id']:
            return False
        return bool(principal.get('customerCode')) and owner == principal['customerCode']
    if action == 'reviews.moderate':
        return obj.get('createdByUserId') != principal['_id'] and not (
            principal.get('customerCode') and obj.get('customer', {}).get('customerCode') == principal['customerCode'])
    return True

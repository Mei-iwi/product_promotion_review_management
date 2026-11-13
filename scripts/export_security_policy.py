"""Export reviewable route/method and permission matrices from the real registry."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import mongomock
from app import create_app
from services.access_policy import ROLE_PERMISSIONS, PERMISSIONS, REPORT_PERMISSIONS
from services.security import ENDPOINT_POLICIES


def main():
    app = create_app({'TESTING': True, 'APP_ENV': 'development'}, mongomock.MongoClient())
    lines = ['# Route / method / permission', '', 'Generated from Flask URL map and ENDPOINT_POLICIES.', '',
             '| Route | Method | Endpoint | Permission |', '|---|---|---|---|']
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, r.endpoint)):
        for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
            permission = ENDPOINT_POLICIES.get((rule.endpoint, method), 'DENY (undeclared)')
            lines.append(f'| `{rule.rule}` | {method} | `{rule.endpoint}` | `{permission or "PUBLIC"}` |')
    lines += ['', 'HEAD follows GET authorization. OPTIONS follows an explicitly declared method policy.',
              'All undeclared endpoints are denied. Mutations also require synchronizer CSRF.',
              'Public health only reports readiness, without application data.', '', '## Report code checks', '',
              '| Code | Additional permission |', '|---|---|']
    lines += [f'| {code} | `{permission}` |' for code, permission in sorted(REPORT_PERMISSIONS.items())]
    lines += ['', '## Account object scope (Web and API)', '',
              '`/admin/users`, `/admin/users/create`, `/admin/users/<user_id>/edit`, GET/POST `/api/users` and PUT `/api/users/<user_id>` retain their method permissions above.',
              'ADMIN has users.manage_all. ACCOUNT_MANAGER has users.manage_customers: lists AND counts include role=CUSTOMER in MongoDB; target reads outside scope return 404.',
              'ACCOUNT_MANAGER creation forces CUSTOMER (a different submitted role is 403); role/customerCode updates and manual locking are forbidden (403).',
              'Mutations reread actor and target inside user_mutation_lock. ADMIN/ACCOUNT_MANAGER creation/grant/revocation and privileged-account changes require actorPassword.',
              'GET /api/users keeps data as an array; q/role/status filters and optional page/per_page use a server-built query. X-Total-Count exposes the scoped count; page headers are returned when pagination is requested.',
              'See [ACCOUNT_MANAGEMENT.md](ACCOUNT_MANAGEMENT.md) for bounds, reauthentication and UI behavior.']
    lines += ['', '## Shopping object scope', '',
              'CUSTOMER owns carts by userId + customerCode. Checkout quotes are user-bound; order reads/cancellation include customerCode in the MongoDB query (404 outside scope).',
              'cart.read_own/cart.manage_own and orders.create_own/orders.cancel_own are CUSTOMER only. orders.manage_status is ADMIN only; SUPPORT_STAFF remains read-only.',
              'Every mutation requires CSRF. Checkout/cancel/status run on a real replica-set transaction, guarded by promotion-usage reconciliation; standalone checkout returns 503 before inventory/order writes.',
              'GET /vouchers requires login and promotions.view_offers with customer-facing projection. POST /checkout/<key>/promotion requires CSRF and quote ownership/current cart version; it creates a new confirmation without placing an order or reserving usage.',
              'GET /account/reviews is read-only own review history with product information. POST /account/orders/<code>/reviews checks owned confirmed/completed order and product membership, then records a pending verified review.',
              'See [SHOPPING.md](SHOPPING.md) for idempotency, pricing rules and deployment.']
    (ROOT / 'docs/SECURITY_ROUTES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    roles = list(ROLE_PERMISSIONS)
    lines = ['# Final permission matrix', '', 'Single source: services/access_policy.py. Guest only has public read permissions.', '',
             '| Permission | ' + ' | '.join(roles) + ' |', '|---|' + '---|' * len(roles)]
    for permission in sorted(PERMISSIONS):
        lines.append('| `' + permission + '` | ' + ' | '.join('Y' if permission in ROLE_PERMISSIONS[role] else '-' for role in roles) + ' |')
    lines += ['', '## Account management scope', '',
              'ADMIN: all accounts and valid roles, including granting/revoking ACCOUNT_MANAGER.',
              'ACCOUNT_MANAGER (Quản trị viên tài khoản): CUSTOMER accounts only; create, read, activate, disable, unlock and reset password. No role assignment, customer relinking, manual locking or business permissions.',
              'All roles land at /catalog after login. Route permission alone never grants access outside its target scope.',
              'See [ACCOUNT_MANAGEMENT.md](ACCOUNT_MANAGEMENT.md).']
    lines += ['', '## Shopping permissions', '',
              'Guest: active catalog and approved anonymous reviews only. CUSTOMER: own cart, COD checkout and pending cancellation. ADMIN: internal order confirmation/completion/pending cancellation. No checkout impersonation by staff.',
              'See [SHOPPING.md](SHOPPING.md).']
    (ROOT / 'docs/RBAC_MATRIX.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    lines = ['# Security MongoDB indexes', '', '| Collection | Index name | Definition |', '|---|---|---|']
    for name in ['users', 'sessions', 'audit_logs', 'security_limits', 'security_locks', 'carts', 'checkout_quotes', 'orders']:
        for index_name, info in app.extensions['mongo_db'][name].index_information().items():
            lines.append(f'| {name} | `{index_name}` | `{json.dumps(info, default=str, ensure_ascii=False)}` |')
    (ROOT / 'docs/SECURITY_INDEXES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    results = [p for p in [ROOT / 'docs/security-test-results.xml', ROOT / 'docs/account-management-test-results.xml', ROOT / 'docs/shopping-unit-results.xml'] if p.exists()]
    if results:
        result = max(results, key=lambda p: p.stat().st_mtime)
        tree = ET.parse(result)
        lines = ['# Test evidence', '', f'Source: docs/{result.name}. Opt-in integration tests may be skipped; see each result and reason.', '',
                 '| Test | Result | Reason |', '|---|---|---|']
        for case in tree.iter('testcase'):
            failure = case.find('failure')
            error = case.find('error')
            skipped = case.find('skipped')
            status = 'FAIL' if failure is not None or error is not None else ('SKIP' if skipped is not None else 'PASS')
            reason = skipped.get('message', '') if skipped is not None else ''
            lines.append(f'| `{case.get("classname")}.{case.get("name")}` | {status} | {reason} |')
        (ROOT / 'docs/SECURITY_TESTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    shopping_results = [ROOT / 'docs/shopping-unit-results.xml', ROOT / 'docs/shopping-replica-results.xml']
    if all(p.exists() for p in shopping_results):
        lines = ['# Shopping test evidence', '', 'Standard suite and isolated real replica-set suite are recorded separately.', '']
        for result in shopping_results:
            lines += ['## ' + result.name, '', '| Test | Result | Reason |', '|---|---|---|']
            for case in ET.parse(result).iter('testcase'):
                skipped = case.find('skipped')
                status = 'FAIL' if case.find('failure') is not None or case.find('error') is not None else ('SKIP' if skipped is not None else 'PASS')
                lines.append(f'| `{case.get("classname")}.{case.get("name")}` | {status} | {skipped.get("message", "") if skipped is not None else ""} |')
            lines.append('')
        (ROOT / 'docs/SHOPPING_TESTS.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()

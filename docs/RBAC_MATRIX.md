# Final permission matrix

Single source: services/access_policy.py. Guest only has public read permissions.

| Permission | ADMIN | ACCOUNT_MANAGER | PRODUCT_STAFF | MARKETING_STAFF | SUPPORT_STAFF | REVIEW_MODERATOR | ANALYST | CUSTOMER |
|---|---|---|---|---|---|---|---|---|
| `account.read_own_profile` | Y | Y | Y | Y | Y | Y | Y | Y |
| `account.update_own_profile` | Y | Y | Y | Y | Y | Y | Y | Y |
| `account.change_own_password` | Y | Y | Y | Y | Y | Y | Y | Y |
| `account.logout` | Y | Y | Y | Y | Y | Y | Y | Y |
| `cart.manage_own` | - | - | - | - | - | - | - | Y |
| `cart.read_own` | - | - | - | - | - | - | - | Y |
| `customers.create` | Y | - | - | - | Y | - | - | - |
| `customers.read` | Y | - | - | - | Y | - | - | - |
| `customers.read_own` | - | - | - | - | - | - | - | Y |
| `customers.update` | Y | - | - | - | Y | - | - | - |
| `customers.update_own_profile` | - | - | - | - | - | - | - | Y |
| `orders.cancel_own` | - | - | - | - | - | - | - | Y |
| `orders.create_own` | - | - | - | - | - | - | - | Y |
| `orders.manage_status` | Y | - | - | - | - | - | - | - |
| `orders.read_all` | Y | - | - | - | Y | - | - | - |
| `orders.read_own` | - | - | - | - | - | - | - | Y |
| `products.create` | Y | - | Y | - | - | - | - | - |
| `products.delete_test` | Y | - | Y | - | - | - | - | - |
| `products.public_read` | Y | Y | Y | Y | Y | Y | Y | Y |
| `products.read_internal` | Y | - | Y | Y | Y | Y | - | - |
| `products.update` | Y | - | Y | - | - | - | - | - |
| `promotions.create` | Y | - | - | Y | - | - | - | - |
| `promotions.view_offers` | Y | Y | Y | Y | Y | Y | Y | Y |
| `promotions.read` | Y | - | - | Y | - | - | - | - |
| `promotions.update` | Y | - | - | Y | - | - | - | - |
| `reports.read_aggregate` | Y | - | - | - | - | - | Y | - |
| `reports.read_sensitive` | Y | - | - | - | - | - | - | - |
| `reviews.create_own` | - | - | - | - | - | - | - | Y |
| `reviews.moderate` | Y | - | - | - | - | Y | - | - |
| `reviews.public_read_approved` | Y | Y | Y | Y | Y | Y | Y | Y |
| `reviews.read_moderation_queue` | Y | - | - | - | - | Y | - | - |
| `reviews.read_own` | - | - | - | - | - | - | - | Y |
| `users.assign_role` | Y | - | - | - | - | - | - | - |
| `users.create` | Y | Y | - | - | - | - | - | - |
| `users.disable` | Y | Y | - | - | - | - | - | - |
| `users.manage_all` | Y | - | - | - | - | - | - | - |
| `users.manage_customers` | - | Y | - | - | - | - | - | - |
| `users.read` | Y | Y | - | - | - | - | - | - |
| `users.reset_password` | Y | Y | - | - | - | - | - | - |
| `users.update` | Y | Y | - | - | - | - | - | - |

## Account management scope

ADMIN: all accounts and valid roles, including granting/revoking ACCOUNT_MANAGER.
ACCOUNT_MANAGER (Quản trị viên tài khoản): CUSTOMER accounts only; create, read, activate, disable, unlock and reset password. No role assignment, customer relinking, manual locking or business permissions.
All roles land at /catalog after login. Route permission alone never grants access outside its target scope.
See [ACCOUNT_MANAGEMENT.md](ACCOUNT_MANAGEMENT.md).

## Shopping permissions

Guest: active catalog and approved anonymous reviews only. CUSTOMER: own cart, COD checkout and pending cancellation. ADMIN: internal order confirmation/completion/pending cancellation. No checkout impersonation by staff.
See [SHOPPING.md](SHOPPING.md).

## Own profile for all roles

Every authenticated role has account.read_own_profile and account.update_own_profile. These grant only the current user's personal profile and private avatar. Staff profile fields are stored in users.profile; CUSTOMER continues to use its linked customers document. No cart, customer-business, order, review or other management permissions were added. Profile updates cannot change role/status/email/authVersion/customerCode.

# Route / method / permission

Generated from Flask URL map and ENDPOINT_POLICIES.

| Route | Method | Endpoint | Permission |
|---|---|---|---|
| `/` | GET | `web.home` | `reports.read_sensitive` |
| `/account` | GET | `auth.account` | `customers.read_own` |
| `/account/change-password` | GET | `auth.change_password` | `account.change_own_password` |
| `/account/change-password` | POST | `auth.change_password` | `account.change_own_password` |
| `/account/orders` | GET | `auth.own_orders` | `orders.read_own` |
| `/account/orders/<code>` | GET | `auth.own_order` | `orders.read_own` |
| `/account/orders/<code>/cancel` | POST | `shop.cancel` | `orders.cancel_own` |
| `/account/orders/<code>/confirmation` | GET | `shop.confirmation` | `orders.read_own` |
| `/account/orders/<code>/reviews` | POST | `auth.order_review` | `reviews.create_own` |
| `/account/profile` | POST | `auth.profile` | `customers.update_own_profile` |
| `/account/reviews` | GET | `auth.own_reviews` | `reviews.read_own` |
| `/admin/users` | GET | `auth.users` | `users.read` |
| `/admin/users/<user_id>/edit` | GET | `auth.edit_user` | `users.update` |
| `/admin/users/<user_id>/edit` | POST | `auth.edit_user` | `users.update` |
| `/admin/users/create` | GET | `auth.create_user` | `users.create` |
| `/admin/users/create` | POST | `auth.create_user` | `users.create` |
| `/api/account/cart` | GET | `shop.api_cart` | `cart.read_own` |
| `/api/account/cart/items` | POST | `shop.api_add` | `cart.manage_own` |
| `/api/account/cart/items/<code>` | DELETE | `shop.api_remove` | `cart.manage_own` |
| `/api/account/cart/items/<code>` | PUT | `shop.api_set` | `cart.manage_own` |
| `/api/account/cart/promotion` | PUT | `shop.api_apply` | `cart.manage_own` |
| `/api/account/cart/promotion` | DELETE | `shop.api_clear` | `cart.manage_own` |
| `/api/account/checkout` | POST | `shop.api_checkout` | `orders.create_own` |
| `/api/account/checkout/quotes` | POST | `shop.api_quote` | `orders.create_own` |
| `/api/account/orders` | GET | `auth.api_orders` | `orders.read_own` |
| `/api/account/orders/<code>` | GET | `auth.api_order` | `orders.read_own` |
| `/api/account/orders/<code>/cancel` | POST | `shop.api_cancel` | `orders.cancel_own` |
| `/api/account/profile` | GET | `auth.api_profile` | `customers.read_own` |
| `/api/account/profile` | PUT | `auth.api_profile` | `customers.update_own_profile` |
| `/api/account/reviews` | GET | `auth.api_reviews` | `reviews.read_own` |
| `/api/customers` | POST | `api.create_customer` | `customers.create` |
| `/api/customers` | GET | `api.customers` | `customers.read` |
| `/api/customers/<code>` | GET | `api.customer` | `customers.read` |
| `/api/customers/<code>` | PUT | `api.update_customer` | `customers.update` |
| `/api/dashboard/promotions` | GET | `api.dashboard_promotions` | `reports.read_aggregate` |
| `/api/dashboard/ratings` | GET | `api.dashboard_ratings` | `reports.read_aggregate` |
| `/api/dashboard/sales` | GET | `api.dashboard_sales` | `reports.read_aggregate` |
| `/api/dashboard/summary` | GET | `api.dashboard_summary` | `reports.read_aggregate` |
| `/api/orders` | GET | `api.orders` | `orders.read_all` |
| `/api/orders/<code>` | GET | `api.order` | `orders.read_all` |
| `/api/orders/<code>/status` | PATCH | `shop.api_order_status` | `orders.manage_status` |
| `/api/products` | POST | `api.create_product` | `products.create` |
| `/api/products` | GET | `api.products` | `products.read_internal` |
| `/api/products/<code>` | DELETE | `api.delete_product` | `products.delete_test` |
| `/api/products/<code>` | GET | `api.product` | `products.read_internal` |
| `/api/products/<code>` | PUT | `api.update_product` | `products.update` |
| `/api/products/<code>/status` | PATCH | `api.product_status` | `products.update` |
| `/api/products/<code>/tags` | PATCH | `api.product_tags` | `products.update` |
| `/api/promotions` | POST | `api.create_promotion` | `promotions.create` |
| `/api/promotions` | GET | `api.promotions` | `promotions.read` |
| `/api/promotions/<code>` | GET | `api.promotion` | `promotions.read` |
| `/api/promotions/<code>` | PUT | `api.update_promotion` | `promotions.update` |
| `/api/public/products` | GET | `auth.api_catalog` | `PUBLIC` |
| `/api/public/products/<code>/reviews` | GET | `auth.api_public_reviews` | `PUBLIC` |
| `/api/reviews` | POST | `api.create_review` | `reviews.create_own` |
| `/api/reviews` | GET | `api.reviews` | `reviews.read_moderation_queue` |
| `/api/reviews/<code>/status` | PATCH | `api.review_status` | `reviews.moderate` |
| `/api/users` | POST | `auth.api_create_user` | `users.create` |
| `/api/users` | GET | `auth.api_users` | `users.read` |
| `/api/users/<user_id>` | PUT | `auth.api_update_user` | `users.update` |
| `/bao-cao` | GET | `web.query_demo` | `reports.read_aggregate` |
| `/cart` | GET | `shop.cart` | `cart.read_own` |
| `/cart/items` | POST | `shop.add` | `cart.manage_own` |
| `/cart/items/<code>` | POST | `shop.set_quantity` | `cart.manage_own` |
| `/cart/items/<code>/remove` | POST | `shop.remove` | `cart.manage_own` |
| `/cart/promotion` | POST | `shop.apply_promo` | `cart.manage_own` |
| `/cart/promotion/remove` | POST | `shop.clear_promo` | `cart.manage_own` |
| `/catalog` | GET | `auth.catalog` | `PUBLIC` |
| `/catalog/<code>` | GET | `auth.public_product` | `PUBLIC` |
| `/catalog/<code>/reviews` | GET | `auth.public_reviews` | `PUBLIC` |
| `/checkout/<key>` | GET | `shop.checkout` | `orders.create_own` |
| `/checkout/<key>` | POST | `shop.checkout` | `orders.create_own` |
| `/checkout/<key>/promotion` | POST | `shop.checkout_promotion` | `orders.create_own` |
| `/checkout/quote` | POST | `shop.quote` | `orders.create_own` |
| `/danh-gia` | POST | `web.create_review` | `reviews.create_own` |
| `/danh-gia` | GET | `web.reviews` | `reviews.read_moderation_queue` |
| `/danh-gia/<code>/trang-thai` | POST | `web.review_status` | `reviews.moderate` |
| `/don-hang` | GET | `web.orders` | `orders.read_all` |
| `/don-hang/<code>` | GET | `web.order_detail` | `orders.read_all` |
| `/don-hang/<code>/trang-thai` | POST | `shop.order_status` | `orders.manage_status` |
| `/health` | GET | `auth.health` | `PUBLIC` |
| `/khach-hang` | GET | `web.customers` | `customers.read` |
| `/khach-hang/<code>` | GET | `web.customer_detail` | `customers.read` |
| `/khach-hang/<code>/sua` | GET | `web.customer_edit_form` | `customers.update` |
| `/khach-hang/<code>/sua` | POST | `web.customer_edit_form` | `customers.update` |
| `/khach-hang/them` | GET | `web.customer_create_form` | `customers.create` |
| `/khach-hang/them` | POST | `web.customer_create_form` | `customers.create` |
| `/khuyen-mai` | GET | `web.promotions` | `promotions.read` |
| `/khuyen-mai/<code>` | GET | `web.promotion_detail` | `promotions.read` |
| `/khuyen-mai/<code>/sua` | GET | `web.promotion_edit_form` | `promotions.update` |
| `/khuyen-mai/<code>/sua` | POST | `web.promotion_edit_form` | `promotions.update` |
| `/khuyen-mai/them` | GET | `web.promotion_create_form` | `promotions.create` |
| `/khuyen-mai/them` | POST | `web.promotion_create_form` | `promotions.create` |
| `/login` | GET | `auth.login` | `PUBLIC` |
| `/login` | POST | `auth.login` | `PUBLIC` |
| `/logout` | POST | `auth.logout` | `account.logout` |
| `/san-pham` | GET | `web.products` | `products.read_internal` |
| `/san-pham/<code>` | GET | `web.product_detail` | `products.read_internal` |
| `/san-pham/<code>/sua` | GET | `web.product_edit_form` | `products.update` |
| `/san-pham/<code>/sua` | POST | `web.product_edit_form` | `products.update` |
| `/san-pham/them` | GET | `web.product_create_form` | `products.create` |
| `/san-pham/them` | POST | `web.product_create_form` | `products.create` |
| `/static/<path:filename>` | GET | `static` | `PUBLIC` |
| `/thong-ke` | GET | `web.dashboard` | `reports.read_aggregate` |
| `/vouchers` | GET | `shop.vouchers` | `promotions.view_offers` |

HEAD follows GET authorization. OPTIONS follows an explicitly declared method policy.

`GET /vouchers` (`shop.vouchers`) requires login and `promotions.view_offers`, returning only customer-facing promotion information.
Changing a promotion at checkout requires CSRF and an owned, unexpired quote matching the cart version.
All undeclared endpoints are denied. Mutations also require synchronizer CSRF.
Public health only reports readiness, without application data.

## Report code checks

| Code | Additional permission |
|---|---|
| CB01 | `reports.read_sensitive` |
| CB02 | `reports.read_sensitive` |
| CB03 | `reports.read_sensitive` |
| CB04 | `reports.read_sensitive` |
| CB05 | `reports.read_sensitive` |
| CB06 | `reports.read_sensitive` |
| CB07 | `reports.read_sensitive` |
| CB08 | `reports.read_sensitive` |
| CB09 | `reports.read_sensitive` |
| CB10 | `reports.read_sensitive` |
| CB11 | `reports.read_sensitive` |
| CB12 | `reports.read_sensitive` |
| NC01 | `reports.read_aggregate` |
| NC02 | `reports.read_aggregate` |
| NC03 | `reports.read_aggregate` |
| NC04 | `reports.read_sensitive` |
| NC05 | `reports.read_aggregate` |
| NC06 | `reports.read_aggregate` |
| NC07 | `reports.read_aggregate` |
| NC08 | `reports.read_aggregate` |
| NC09 | `reports.read_aggregate` |
| NC10 | `reports.read_sensitive` |

## Account object scope (Web and API)

`/admin/users`, `/admin/users/create`, `/admin/users/<user_id>/edit`, GET/POST `/api/users` and PUT `/api/users/<user_id>` retain their method permissions above.
ADMIN has users.manage_all. ACCOUNT_MANAGER has users.manage_customers: lists AND counts include role=CUSTOMER in MongoDB; target reads outside scope return 404.
ACCOUNT_MANAGER creation forces CUSTOMER (a different submitted role is 403); role/customerCode updates and manual locking are forbidden (403).
Mutations reread actor and target inside user_mutation_lock. ADMIN/ACCOUNT_MANAGER creation/grant/revocation and privileged-account changes require actorPassword.
GET /api/users keeps data as an array; q/role/status filters and optional page/per_page use a server-built query. X-Total-Count exposes the scoped count; page headers are returned when pagination is requested.
See [ACCOUNT_MANAGEMENT.md](ACCOUNT_MANAGEMENT.md) for bounds, reauthentication and UI behavior.

## Shopping object scope

CUSTOMER owns carts by userId + customerCode. Checkout quotes are user-bound; order reads/cancellation include customerCode in the MongoDB query (404 outside scope).
cart.read_own/cart.manage_own and orders.create_own/orders.cancel_own are CUSTOMER only. orders.manage_status is ADMIN only; SUPPORT_STAFF remains read-only.
Every mutation requires CSRF. Checkout/cancel/status run on a real replica-set transaction, guarded by promotion-usage reconciliation; standalone checkout returns 503 before inventory/order writes.
See [SHOPPING.md](SHOPPING.md) for idempotency, pricing rules and deployment.

# Security MongoDB indexes

| Collection | Index name | Definition |
|---|---|---|
| users | `_id_` | `{"key": [["_id", 1]], "v": 2}` |
| users | `security_email` | `{"key": [["emailNormalized", 1]], "unique": true, "v": 2}` |
| users | `security_customer_link` | `{"key": [["customerCode", 1]], "unique": true, "partialFilterExpression": {"role": "CUSTOMER", "customerCode": {"$type": "string"}}, "v": 2}` |
| sessions | `_id_` | `{"key": [["_id", 1]], "v": 2}` |
| sessions | `security_session_token` | `{"key": [["sessionIdHash", 1]], "unique": true, "v": 2}` |
| sessions | `security_session_user` | `{"key": [["userId", 1]], "v": 2}` |
| sessions | `security_session_ttl` | `{"key": [["absoluteExpiresAt", 1]], "expireAfterSeconds": 0, "v": 2}` |
| audit_logs | `_id_` | `{"key": [["_id", 1]], "v": 2}` |
| audit_logs | `security_audit_time` | `{"key": [["timestamp", -1]], "v": 2}` |
| audit_logs | `security_audit_actor` | `{"key": [["actorUserId", 1], ["timestamp", -1]], "v": 2}` |
| security_limits | `_id_` | `{"key": [["_id", 1]], "v": 2}` |
| security_limits | `security_limit_ttl` | `{"key": [["expiresAt", 1]], "expireAfterSeconds": 0, "v": 2}` |
| checkout_quotes | `_id_` | `{"key": [["_id", 1]], "v": 2}` |
| checkout_quotes | `shopping_quote_ttl` | `{"key": [["expiresAt", 1]], "expireAfterSeconds": 0, "v": 2}` |
| orders | `_id_` | `{"key": [["_id", 1]], "v": 2}` |
| orders | `shopping_checkout_unique` | `{"key": [["customerCode", 1], ["checkoutKey", 1]], "unique": true, "partialFilterExpression": {"checkoutKey": {"$type": "string"}}, "v": 2}` |
| orders | `shopping_order_code` | `{"key": [["orderCode", 1]], "unique": true, "partialFilterExpression": {"orderCode": {"$type": "string"}}, "v": 2}` |

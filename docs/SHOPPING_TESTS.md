# Shopping test evidence

Standard suite and isolated real replica-set suite are recorded separately.

## shopping-unit-results.xml

| Test | Result | Reason |
|---|---|---|
| `tests.test_account_security.test_login_unknown_and_bad_password_same_response` | PASS |  |
| `tests.test_account_security.test_cannot_login_disabled_locked[disabled]` | PASS |  |
| `tests.test_account_security.test_cannot_login_disabled_locked[locked]` | PASS |  |
| `tests.test_account_security.test_inactive_customer_loses_access_and_cannot_relogin` | PASS |  |
| `tests.test_account_security.test_logout_replay_and_fixation` | PASS |  |
| `tests.test_account_security.test_http_session_expiration[idleExpiresAt]` | PASS |  |
| `tests.test_account_security.test_http_session_expiration[absoluteExpiresAt]` | PASS |  |
| `tests.test_account_security.test_change_password_revokes_other_browser` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[POST-/api/products]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[PUT-/api/products/SANPHAM2026090007]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[PATCH-/api/products/SANPHAM2026090007/status]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[DELETE-/api/products/SANPHAM2026090007]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[POST-/logout]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[POST-/san-pham/them]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[POST-/admin/users/create]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[POST-/account/change-password]` | PASS |  |
| `tests.test_account_security.test_missing_wrong_csrf[POST-/danh-gia/DANHGIA2026090001/trang-thai]` | PASS |  |
| `tests.test_account_security.test_login_csrf_is_required` | PASS |  |
| `tests.test_account_security.test_role_change_disable_revoke_immediately` | PASS |  |
| `tests.test_account_security.test_shared_session_store_two_apps` | PASS |  |
| `tests.test_account_security.test_last_admin_guard_reauth_and_concurrent_updates` | PASS |  |
| `tests.test_account_security.test_profile_mass_assignment_and_injection[payload0]` | PASS |  |
| `tests.test_account_security.test_profile_mass_assignment_and_injection[payload1]` | PASS |  |
| `tests.test_account_security.test_profile_mass_assignment_and_injection[payload2]` | PASS |  |
| `tests.test_account_security.test_profile_mass_assignment_and_injection[payload3]` | PASS |  |
| `tests.test_account_security.test_profile_mass_assignment_and_injection[payload4]` | PASS |  |
| `tests.test_account_security.test_no_operator_injection_or_product_delete_flag` | PASS |  |
| `tests.test_account_security.test_review_server_fields_cannot_be_supplied[status-approved]` | PASS |  |
| `tests.test_account_security.test_review_server_fields_cannot_be_supplied[verifiedPurchase-True]` | PASS |  |
| `tests.test_account_security.test_review_server_fields_cannot_be_supplied[helpfulCount-999]` | PASS |  |
| `tests.test_account_security.test_review_server_fields_cannot_be_supplied[createdAt-2020-01-01]` | PASS |  |
| `tests.test_account_security.test_moderator_cannot_self_moderate` | PASS |  |
| `tests.test_account_security.test_public_projection_and_xss` | PASS |  |
| `tests.test_account_security.test_open_redirect_headers_cookie_and_no_secret_leak` | PASS |  |
| `tests.test_account_security.test_production_fails_fast_and_enforces_https` | PASS |  |
| `tests.test_account_security.test_auth_pages_load_and_role_navigation` | PASS |  |
| `tests.test_account_security.test_body_size_limit_and_json_errors` | PASS |  |
| `tests.test_account_security.test_all_reports_regression_with_admin` | PASS |  |
| `tests.test_account_security.test_cli_bootstrap_interactive_once` | PASS |  |
| `tests.test_account_security.test_deactivate_customer_revokes_even_after_reactivation` | PASS |  |
| `tests.test_account_security.test_real_business_http_crud_regression` | PASS |  |
| `tests.test_account_security.test_admin_account_http_create_reset_and_status` | PASS |  |
| `tests.test_account_security.test_weak_password_rejected[short]` | PASS |  |
| `tests.test_account_security.test_weak_password_rejected[123456789012345]` | PASS |  |
| `tests.test_account_security.test_weak_password_rejected[password123456789]` | PASS |  |
| `tests.test_account_security.test_weak_password_rejected[aaaaaaaaaaaaaaaaaaaa]` | PASS |  |
| `tests.test_account_security.test_weak_password_rejected[first first first first]` | PASS |  |
| `tests.test_account_security.test_invalid_filters_return_validation_error[/api/products?page=abc]` | PASS |  |
| `tests.test_account_security.test_invalid_filters_return_validation_error[/api/products?min_price=oops]` | PASS |  |
| `tests.test_account_security.test_invalid_filters_return_validation_error[/api/orders?from_date=bad]` | PASS |  |
| `tests.test_account_security.test_invalid_filters_return_validation_error[/api/reviews?rating=abc]` | PASS |  |
| `tests.test_account_security.test_admin_creates_and_manages_account_manager` | PASS |  |
| `tests.test_account_security.test_manager_create_customer_web_api_and_duplicate_links` | PASS |  |
| `tests.test_account_security.test_manager_requires_active_existing_customer[]` | PASS |  |
| `tests.test_account_security.test_manager_requires_active_existing_customer[MISSING]` | PASS |  |
| `tests.test_account_security.test_manager_requires_active_existing_customer[KHACHHANG20260002]` | PASS |  |
| `tests.test_account_security.test_manager_customer_lifecycle_revokes_sessions[disable]` | PASS |  |
| `tests.test_account_security.test_manager_customer_lifecycle_revokes_sessions[unlock]` | PASS |  |
| `tests.test_account_security.test_manager_customer_lifecycle_revokes_sessions[reset]` | PASS |  |
| `tests.test_account_security.test_manager_web_errors_keep_values_clear_passwords_and_csrf` | PASS |  |
| `tests.test_account_security.test_account_filters_pagination_and_original_api_contract` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[page=0]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[page=-1]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[page=1.5]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[page=100001]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[per_page=0]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[per_page=101]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[role=INVALID]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[status=INVALID]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[permissions=x]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[sort=passwordHash]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[q=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[role[$ne]=CUSTOMER]` | PASS |  |
| `tests.test_account_security.test_account_filter_validation[page=1&page=2]` | PASS |  |
| `tests.test_account_security.test_account_scope_rechecked_inside_lock` | PASS |  |
| `tests.test_account_security.test_manager_actions_are_audited_without_secrets` | PASS |  |
| `tests.test_account_security.test_admin_customer_relink_and_last_admin_not_replaced_by_manager` | PASS |  |
| `tests.test_account_security.test_account_filter_types_rejected[filters0]` | PASS |  |
| `tests.test_account_security.test_account_filter_types_rejected[filters1]` | PASS |  |
| `tests.test_account_security.test_account_filter_types_rejected[filters2]` | PASS |  |
| `tests.test_account_security.test_account_filter_types_rejected[filters3]` | PASS |  |
| `tests.test_application.test_01_mongo_connection` | PASS |  |
| `tests.test_application.test_02_product_list` | PASS |  |
| `tests.test_application.test_03_product_category_filter` | PASS |  |
| `tests.test_application.test_04_product_price_filter` | PASS |  |
| `tests.test_application.test_05_product_create_validation` | PASS |  |
| `tests.test_application.test_06_product_update` | PASS |  |
| `tests.test_application.test_07_duplicate_product_code` | PASS |  |
| `tests.test_application.test_08_promotion_date_validation` | PASS |  |
| `tests.test_application.test_09_customer_duplicate_email` | PASS |  |
| `tests.test_application.test_10_review_rating_invalid` | PASS |  |
| `tests.test_application.test_11_create_review_valid` | PASS |  |
| `tests.test_application.test_12_verified_purchase` | PASS |  |
| `tests.test_application.test_13_review_approve_reject` | PASS |  |
| `tests.test_application.test_14_dashboard_nc01` | PASS |  |
| `tests.test_application.test_15_dashboard_nc05` | PASS |  |
| `tests.test_application.test_16_dashboard_nc07` | PASS |  |
| `tests.test_application.test_17_lookup_nc09` | PASS |  |
| `tests.test_application.test_18_route_404` | PASS |  |
| `tests.test_application.test_19_api_envelope` | PASS |  |
| `tests.test_application.test_20_empty_collections_do_not_crash` | PASS |  |
| `tests.test_application.test_21_dashboard_uses_semantic_fields` | PASS |  |
| `tests.test_application.test_22_dashboard_page_loads_offline_svg_script` | PASS |  |
| `tests.test_application.test_23_business_report_renders_as_table` | PASS |  |
| `tests.test_application.test_24_navigation_has_no_index_numbers` | PASS |  |
| `tests.test_application.test_25_deep_pages_have_back_button` | PASS |  |
| `tests.test_auth_service.test_eight_character_password_account_and_change` | PASS |  |
| `tests.test_auth_service.test_password_length_bounds_and_common_passwords[T8k!r9V]` | PASS |  |
| `tests.test_auth_service.test_password_length_bounds_and_common_passwords[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` | PASS |  |
| `tests.test_auth_service.test_password_length_bounds_and_common_passwords[12345678]` | PASS |  |
| `tests.test_auth_service.test_password_length_bounds_and_common_passwords[password]` | PASS |  |
| `tests.test_auth_service.test_argon_session_login_and_revoke` | PASS |  |
| `tests.test_auth_service.test_session_expiration[idleExpiresAt]` | PASS |  |
| `tests.test_auth_service.test_session_expiration[absoluteExpiresAt]` | PASS |  |
| `tests.test_auth_service.test_password_revokes_all_and_bootstrap_once` | PASS |  |
| `tests.test_auth_service.test_login_lock_auto_expiry_and_shared_ip_limit` | PASS |  |
| `tests.test_authorization.test_every_endpoint_method_has_explicit_policy` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[ADMIN]` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[ACCOUNT_MANAGER]` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[PRODUCT_STAFF]` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[MARKETING_STAFF]` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[SUPPORT_STAFF]` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[REVIEW_MODERATOR]` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[ANALYST]` | PASS |  |
| `tests.test_authorization.test_role_endpoint_method_matrix[CUSTOMER]` | PASS |  |
| `tests.test_authorization.test_guest_and_undeclared_endpoint` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB01-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB02-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB03-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB04-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB05-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB06-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB07-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB08-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB09-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB10-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB11-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[CB12-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC01-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC02-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC03-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC04-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC05-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC06-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC07-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC08-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC09-reports.read_aggregate]` | PASS |  |
| `tests.test_authorization.test_analyst_report_code_enforcement[NC10-reports.read_sensitive]` | PASS |  |
| `tests.test_authorization.test_analyst_dashboard_has_no_customer_details` | PASS |  |
| `tests.test_authorization.test_customer_ownership_and_forged_review` | PASS |  |
| `tests.test_authorization.test_admin_cannot_impersonate_and_customer_verified_purchase` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_target_privileged_accounts[ADMIN]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_target_privileged_accounts[ACCOUNT_MANAGER]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_target_privileged_accounts[PRODUCT_STAFF]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_target_privileged_accounts[MARKETING_STAFF]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_target_privileged_accounts[SUPPORT_STAFF]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_target_privileged_accounts[REVIEW_MODERATOR]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_target_privileged_accounts[ANALYST]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_create_other_roles[ADMIN]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_create_other_roles[ACCOUNT_MANAGER]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_create_other_roles[PRODUCT_STAFF]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_create_other_roles[MARKETING_STAFF]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_create_other_roles[SUPPORT_STAFF]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_create_other_roles[REVIEW_MODERATOR]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_create_other_roles[ANALYST]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload0]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload1]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload2]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload3]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload4]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload5]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload6]` | PASS |  |
| `tests.test_authorization.test_account_manager_cannot_change_role_link_or_lock[payload7]` | PASS |  |
| `tests.test_authorization.test_manager_list_scope_count_and_permissions` | PASS |  |
| `tests.test_real_mongo.test_real_unique_partial_index_and_explicit_session_expiry` | SKIP | Requires isolated real MongoDB: scripts/verify_security_runtime.py |
| `tests.test_real_mongo.test_real_rate_reservations_multiworker` | SKIP | Requires isolated real MongoDB: scripts/verify_security_runtime.py |
| `tests.test_real_mongo.test_real_last_admin_concurrency` | SKIP | Requires isolated real MongoDB: scripts/verify_security_runtime.py |
| `tests.test_security_storage.test_security_indexes_and_unique_links` | PASS |  |
| `tests.test_security_storage.test_atomic_limit_and_lock` | PASS |  |
| `tests.test_shopping.test_promotion_mixed_cart_example_and_or_not_double_counted` | PASS |  |
| `tests.test_shopping.test_promotion_types_caps_and_unlimited[promo0-500000]` | PASS |  |
| `tests.test_shopping.test_promotion_types_caps_and_unlimited[promo1-40000]` | PASS |  |
| `tests.test_shopping.test_promotion_types_caps_and_unlimited[promo2-80000]` | PASS |  |
| `tests.test_shopping.test_promotion_types_caps_and_unlimited[promo3-40000]` | PASS |  |
| `tests.test_shopping.test_promotion_round_half_up_to_dong` | PASS |  |
| `tests.test_shopping.test_promotion_failures[changes0-promo_inactive]` | PASS |  |
| `tests.test_shopping.test_promotion_failures[changes1-promo_expired]` | PASS |  |
| `tests.test_shopping.test_promotion_failures[changes2-promo_not_started]` | PASS |  |
| `tests.test_shopping.test_promotion_failures[changes3-promo_expired]` | PASS |  |
| `tests.test_shopping.test_promotion_failures[changes4-promo_exhausted]` | PASS |  |
| `tests.test_shopping.test_promotion_failures[changes5-promo_minimum]` | PASS |  |
| `tests.test_shopping.test_promotion_failures[changes6-promo_no_eligible]` | PASS |  |
| `tests.test_shopping.test_promotion_utc_boundaries_and_missing` | PASS |  |
| `tests.test_shopping.test_admin_promotion_date_roundtrip_vietnam` | PASS |  |
| `tests.test_shopping.test_catalog_search_filters_pagination_and_privacy` | PASS |  |
| `tests.test_shopping.test_cart_persists_and_merges_without_cross_account_access` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[0]` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[-1]` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[100]` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[True]` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[1.5]` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[1.0]` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[quantity6]` | PASS |  |
| `tests.test_shopping.test_cart_bad_quantities[None]` | PASS |  |
| `tests.test_shopping.test_cart_limit_stock_and_preview_does_not_reserve` | PASS |  |
| `tests.test_shopping.test_standalone_checkout_no_partial_writes` | PASS |  |
| `tests.test_shopping.test_shopping_ownership_csrf_and_review_prefill` | PASS |  |
| `tests.test_shopping.test_legacy_order_details_still_render` | PASS |  |
| `tests.test_shopping_replica.test_replica_last_product_and_exact_replay` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_last_promotion_use` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_concurrent_duplicate_key_and_conflicting_payload` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_cancel_versus_confirm_and_terminal_states` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_failure_rolls_back_every_collection[orders]` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_failure_rolls_back_every_collection[carts]` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_changed_quote_requires_new_confirmation[products-changes0]` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_changed_quote_requires_new_confirmation[products-changes1]` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_changed_quote_requires_new_confirmation[promotions-changes2]` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_legacy_reconciliation_is_rerunnable_and_no_invented_stock` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_review_verification_and_snapshot_money` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |
| `tests.test_shopping_replica.test_replica_quote_ownership_expiry_and_reconciliation_gate` | SKIP | Run scripts/verify_shopping_replica.py for a real isolated replica set |

## shopping-replica-results.xml

| Test | Result | Reason |
|---|---|---|
| `tests.test_shopping_replica.test_replica_last_product_and_exact_replay` | PASS |  |
| `tests.test_shopping_replica.test_replica_last_promotion_use` | PASS |  |
| `tests.test_shopping_replica.test_replica_concurrent_duplicate_key_and_conflicting_payload` | PASS |  |
| `tests.test_shopping_replica.test_replica_cancel_versus_confirm_and_terminal_states` | PASS |  |
| `tests.test_shopping_replica.test_replica_failure_rolls_back_every_collection[orders]` | PASS |  |
| `tests.test_shopping_replica.test_replica_failure_rolls_back_every_collection[carts]` | PASS |  |
| `tests.test_shopping_replica.test_replica_changed_quote_requires_new_confirmation[products-changes0]` | PASS |  |
| `tests.test_shopping_replica.test_replica_changed_quote_requires_new_confirmation[products-changes1]` | PASS |  |
| `tests.test_shopping_replica.test_replica_changed_quote_requires_new_confirmation[promotions-changes2]` | PASS |  |
| `tests.test_shopping_replica.test_replica_legacy_reconciliation_is_rerunnable_and_no_invented_stock` | PASS |  |
| `tests.test_shopping_replica.test_replica_review_verification_and_snapshot_money` | PASS |  |
| `tests.test_shopping_replica.test_replica_quote_ownership_expiry_and_reconciliation_gate` | PASS |  |
| `tests.test_real_mongo.test_real_unique_partial_index_and_explicit_session_expiry` | PASS |  |
| `tests.test_real_mongo.test_real_rate_reservations_multiworker` | PASS |  |
| `tests.test_real_mongo.test_real_last_admin_concurrency` | PASS |  |

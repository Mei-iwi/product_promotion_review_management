EXPECTED_INDEXES = {
    "products": ["idx_products_productCode", "idx_products_category_price", "idx_products_text_search"],
    "customers": ["idx_customers_customerCode", "idx_customers_email", "idx_customers_level_joinedAt"],
    "promotions": ["idx_promotions_promoCode", "idx_promotions_status_period"],
    "reviews": ["idx_reviews_reviewCode", "idx_reviews_product_rating_date", "idx_reviews_customer_date"],
    "orders": ["idx_orders_orderCode", "idx_orders_customer_date", "idx_orders_product_date"],
}


def inspect_indexes(db):
    return {
        collection: {
            "expected": names,
            "actual": list(db[collection].index_information()),
            "missing": [name for name in names if name not in db[collection].index_information()],
        }
        for collection, names in EXPECTED_INDEXES.items()
    }


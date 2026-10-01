from repositories import order_repository as repo


def list_orders(filters=None): return repo.find_orders(filters)
def get_order(code): return repo.find_by_code(code)


from repositories import report_repository as reports
from flask import g, has_request_context
from services.access_policy import has_permission


def sensitive():
    return not has_request_context() or has_permission(g.get('current_user'), 'reports.read_sensitive')


def get_summary(): return reports.summary()
def get_ratings():
    result = {"NC01": reports.nc01(), "NC02": reports.nc02(), "NC03": reports.nc03(), "NC09": reports.nc09()}
    if sensitive(): result['NC10'] = reports.nc10()
    return result
def get_promotions(): return {"NC07": reports.nc07()}
def get_sales():
    result = {"NC05": reports.nc05(), "NC06": reports.nc06(), "NC08": reports.nc08()}
    if sensitive(): result['NC04'] = reports.nc04()
    return result


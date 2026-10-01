from repositories import report_repository as reports


def get_summary(): return reports.summary()
def get_ratings(): return {"NC01": reports.nc01(), "NC02": reports.nc02(), "NC03": reports.nc03(), "NC09": reports.nc09(), "NC10": reports.nc10()}
def get_promotions(): return {"NC07": reports.nc07()}
def get_sales(): return {"NC04": reports.nc04(), "NC05": reports.nc05(), "NC06": reports.nc06(), "NC08": reports.nc08()}


from flask import Flask, render_template
from pymongo.errors import PyMongoError
from config import Config
from db.mongo import init_mongo


def create_app(config=None, mongo_client=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config: app.config.update(config)
    app.json.ensure_ascii = False
    try:
        init_mongo(app, mongo_client)
    except PyMongoError as error:
        raise RuntimeError("Không thể kết nối MongoDB. Hãy kiểm tra dịch vụ MongoDB và MONGO_URI.") from error
    from routes.api_routes import bp as api_bp
    from routes.web_routes import bp as web_bp
    app.register_blueprint(web_bp); app.register_blueprint(api_bp)

    @app.after_request
    def disable_development_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.template_filter("money")
    def money(value): return f"{float(value or 0):,.0f} ₫".replace(",", ".")

    @app.template_filter("datevn")
    def datevn(value): return value.strftime("%d/%m/%Y %H:%M") if hasattr(value, "strftime") else "Chưa có"

    @app.template_filter("status_vi")
    def status_vi(value):
        return {"active": "Đang hoạt động", "inactive": "Ngừng hoạt động", "expired": "Hết hạn", "pending": "Chờ duyệt", "approved": "Đã duyệt", "rejected": "Từ chối", "confirmed": "Đã xác nhận", "completed": "Hoàn tất", "cancelled": "Đã hủy"}.get(value, value or "Chưa có")

    @app.template_filter("status_class")
    def status_class(value):
        return {"active": "success", "approved": "success", "completed": "success", "confirmed": "primary", "pending": "warning", "expired": "secondary", "inactive": "secondary", "rejected": "danger", "cancelled": "danger"}.get(value, "secondary")

    @app.template_filter("level_vi")
    def level_vi(value): return {"normal": "Thường", "silver": "Bạc", "gold": "Vàng"}.get(value, value)

    @app.errorhandler(404)
    def not_found(error): return render_template("error.html", message="Không tìm thấy dữ liệu"), 404

    @app.errorhandler(500)
    def server_error(error): return render_template("error.html", message="Có lỗi khi xử lý yêu cầu"), 500
    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host=flask_app.config["FLASK_HOST"], port=flask_app.config["FLASK_PORT"], debug=False, use_reloader=False)


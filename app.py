from flask import Flask, render_template
from pymongo.errors import PyMongoError
from config import Config
from db.mongo import init_mongo


def create_app(config=None, mongo_client=None):
    import mimetypes
    # Windows registry entries may map .webp to an empty MIME type.
    mimetypes.add_type('image/webp', '.webp')
    app = Flask(__name__)
    app.config.from_object(Config)
    if config: app.config.update(config)
    import secrets
    if app.config['APP_ENV'] not in {'development', 'production'}:
        raise RuntimeError('APP_ENV phải là development hoặc production')
    if app.config['APP_ENV'] == 'production':
        key = app.config.get('SECRET_KEY') or ''
        if len(key) < 32 or len(set(key)) < 12:
            raise RuntimeError('Production yêu cầu SECRET_KEY ngẫu nhiên tối thiểu 32 ký tự')
        app.config.update(AUTH_COOKIE_SECURE=True, AUTH_COOKIE_NAME='__Host-auth', SESSION_COOKIE_SECURE=True)
    elif not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = secrets.token_hex(32)
    app.json.ensure_ascii = False
    try:
        init_mongo(app, mongo_client)
    except PyMongoError as error:
        raise RuntimeError("Không thể kết nối MongoDB. Hãy kiểm tra dịch vụ MongoDB và MONGO_URI.") from error
    from routes.api_routes import bp as api_bp
    from routes.web_routes import bp as web_bp
    from routes.auth_routes import bp as auth_bp
    app.register_blueprint(web_bp); app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    from routes.shopping_routes import bp as shopping_bp
    app.register_blueprint(shopping_bp)
    from repositories.security_repository import ensure_indexes
    with app.app_context():
        ensure_indexes()
        from repositories.shopping_repository import ensure_indexes as shopping_indexes
        shopping_indexes()
    from services.security import init_security
    init_security(app)
    from services.user_service import register_cli
    register_cli(app)
    from services.shopping_cli import register_cli as shopping_cli
    shopping_cli(app)
    from services.avatar_service import register_cli as avatar_cli
    avatar_cli(app)

    @app.after_request
    def disable_development_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.template_filter("money")
    def money(value): return f"{float(value or 0):,.0f} ₫".replace(",", ".")

    @app.template_filter('product_image')
    def product_image(value):
        from services.catalog_service import image_url
        return image_url(value)

    @app.template_filter("datevn")
    def datevn(value):
        from datetime import datetime
        from services.shopping_common import utc, VIETNAM
        return utc(value).astimezone(VIETNAM).strftime("%d/%m/%Y %H:%M") if isinstance(value, datetime) else "Chưa có"

    @app.template_filter('datetime_local')
    def datetime_local(value):
        from services.shopping_common import utc, VIETNAM
        return utc(value).astimezone(VIETNAM).strftime('%Y-%m-%dT%H:%M')

    @app.template_filter("status_vi")
    def status_vi(value):
        return {"active": "Đang hoạt động", "inactive": "Ngừng hoạt động", "expired": "Hết hạn", "pending": "Chờ duyệt", "approved": "Đã duyệt", "rejected": "Từ chối", "confirmed": "Đã xác nhận", "completed": "Hoàn tất", "cancelled": "Đã hủy"}.get(value, value or "Chưa có")

    @app.template_filter("status_class")
    def status_class(value):
        return {"active": "success", "approved": "success", "completed": "success", "confirmed": "primary", "pending": "warning", "expired": "secondary", "inactive": "secondary", "rejected": "danger", "cancelled": "danger"}.get(value, "secondary")

    @app.template_filter("level_vi")
    def level_vi(value): return {"normal": "Thường", "silver": "Bạc", "gold": "Vàng"}.get(value, value)

    @app.errorhandler(500)
    def server_error(error):
        from flask import request, jsonify
        if request.path.startswith('/api/'):
            return jsonify(success=False, message='Có lỗi khi xử lý yêu cầu', data=None), 500
        return render_template("error.html", message="Có lỗi khi xử lý yêu cầu"), 500
    return app


if __name__ == "__main__":
    import os
    import socket
    import sys

    # The reloader child inherits the listening socket; only probe in its parent.
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                probe.bind((Config.FLASK_HOST, Config.FLASK_PORT))
        except OSError:
            print(
                f"Không thể mở cổng {Config.FLASK_PORT}. "
                "Cổng có thể đang được bản Python khác hoặc Docker sử dụng, hoặc bị Windows chặn.\n"
                f"Nếu web đã chạy, mở http://127.0.0.1:{Config.FLASK_PORT}\n"
                "Để chạy trong terminal này, dừng bản Python cũ bằng Ctrl+C ở terminal cũ.\n"
                "Nếu bản đang chạy là Docker, dùng: docker compose stop app\n"
                "Sau khi cổng trống, chạy lại: python app.py",
                file=sys.stderr,
            )
            sys.exit(1)
    flask_app = create_app()
    flask_app.run(host=flask_app.config["FLASK_HOST"], port=flask_app.config["FLASK_PORT"],
                  debug=False, use_reloader=flask_app.config['APP_ENV'] == 'development')


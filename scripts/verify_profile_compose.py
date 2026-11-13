"""Verify profile/avatar persistence in a NEW disposable credentialed Compose project.

Never imports, resets, or reuses the user's database/volumes. Requires Docker.
"""
from http.cookiejar import CookieJar
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    from PIL import Image

    project = 'profile-verify-' + uuid.uuid4().hex[:12]
    assert re.fullmatch(r'profile-verify-[a-f0-9]{12}', project)
    env = {**os.environ, 'APP_ENV': 'development', 'MONGO_ROOT_USERNAME': 'verification_root',
           'MONGO_ROOT_PASSWORD': secrets.token_hex(32), 'MONGO_APP_USERNAME': 'verification_app',
           'MONGO_APP_PASSWORD': secrets.token_hex(32), 'MONGO_DB': 'PROFILE_COMPOSE_TEST',
           'SECRET_KEY': secrets.token_hex(32), 'FLASK_PORT': '0', 'MONGO_DOCKER_PORT': '0'}
    prefix = ['docker', 'compose', '-p', project, '-f', 'docker-compose.yml']
    evidence = []
    password = 'orchid lantern ' + secrets.token_urlsafe(24)
    new_password = 'ocean violet ' + secrets.token_urlsafe(24)

    def run(args, code=None):
        result = subprocess.run(prefix + args, cwd=ROOT, env=env, input=code,
                                text=True, encoding='utf-8', capture_output=True)
        if result.returncode:
            # Compose build/health logs contain no test credential values by design.
            tail = (result.stderr or result.stdout)[-3500:]
            for value in [password, new_password, env['MONGO_ROOT_PASSWORD'], env['MONGO_APP_PASSWORD'], env['SECRET_KEY']]:
                tail = tail.replace(value, '[redacted]')
            raise RuntimeError(f'Compose {args[0]} failed: {tail}')
        return result.stdout.strip()

    def record(message):
        evidence.append('PASS ' + message)
        print('PASS ' + message, flush=True)

    try:
        run(['config', '--quiet'])
        print('Building and starting an isolated profile verification stack…', flush=True)
        run(['up', '--build', '-d', '--wait', '--wait-timeout', '180'])
        base = 'http://' + run(['port', 'app', '5001'])
        assert run(['exec', '-T', 'app', 'id', '-u']) != '0'
        seed = '''from app import create_app
from db.mongo import get_db
from services import auth_service
app = create_app()
with app.app_context():
    db = get_db()
    db.customers.insert_one({'customerCode':'C-PERSIST','fullName':'Test customer','email':'business@example.test','level':'normal','status':'active'})
    admin = auth_service.create_user({'email':'owner@example.test','password':SECRET,'role':'ADMIN'}, bootstrap=True)
    auth_service.create_user({'email':'persist@example.test','password':SECRET,'role':'CUSTOMER','customerCode':'C-PERSIST'}, admin)
'''.replace('SECRET', repr(password))
        run(['exec', '-T', 'app', 'python', '-'], seed)
        record('app runs as a non-root user; synthetic customer seeded only in the disposable DB')
        first = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        second = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

        def request(client, path, data=None, content_type=None):
            if isinstance(data, dict):
                data = urllib.parse.urlencode(data).encode()
                content_type = 'application/x-www-form-urlencoded'
            req = urllib.request.Request(base + path, data=data,
                                         headers={'Content-Type': content_type} if content_type else {})
            try:
                return client.open(req, timeout=30)
            except urllib.error.HTTPError as error:
                return error

        def token(client):
            with request(client, '/login') as reply:
                return re.search(r'name="csrf-token" content="([^"]+)"', reply.read().decode())[1]

        def login(client, secret, email='persist@example.test'):
            with request(client, '/login', {'csrf_token': token(client), 'email': email, 'password': secret}) as reply:
                return reply.status, reply.read().decode()

        assert login(first, password)[0] == 200
        assert login(second, password)[0] == 200
        with request(first, '/account') as reply:
            html = reply.read().decode()
            assert 'C-PERSIST' not in html and 'business@example.test' not in html and 'persist@example.test' in html
        with request(first, '/account/profile', {'csrf_token': token(first), 'fullName': 'Updated customer',
                                                'phone': '0912345678', 'dateOfBirth': '2000-02-29', 'bio': 'Persistence test'}) as reply:
            assert reply.status == 200 and 'Updated customer' in reply.read().decode()

        def upload(kind='PNG', color='teal', client=None):
            client = client or first
            source = BytesIO()
            Image.new('RGB', (900, 600), color).save(source, kind)
            boundary = 'avatar-' + secrets.token_hex(16)
            suffix = 'jpg' if kind == 'JPEG' else kind.lower()
            data = (f'--{boundary}\r\nContent-Disposition: form-data; name="csrf_token"\r\n\r\n{token(client)}\r\n'
                    f'--{boundary}\r\nContent-Disposition: form-data; name="avatar"; filename="portrait.{suffix}"\r\n'
                    f'Content-Type: image/{suffix}\r\n\r\n').encode() + source.getvalue() + f'\r\n--{boundary}--\r\n'.encode()
            with request(client, '/account/avatar', data, f'multipart/form-data; boundary={boundary}') as reply:
                assert reply.status == 200

        upload()
        with request(first, '/account/avatar') as reply:
            assert reply.status == 200 and reply.headers['Content-Type'].startswith('image/webp')
            digest = hashlib.sha256(reply.read()).hexdigest()
        staff = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        assert login(staff, password, 'owner@example.test')[0] == 200
        with request(staff, '/account/profile', {'csrf_token': token(staff), 'fullName': 'Private admin profile', 'phone': '0987654321'}) as reply:
            assert reply.status == 200
        upload('PNG', 'red', staff)
        with request(staff, '/account/avatar') as reply:
            staff_digest = hashlib.sha256(reply.read()).hexdigest()
            assert staff_digest != digest
        run(['exec', '-T', 'app', 'python', '-'], '''import os
from pathlib import Path
root = Path('/app/instance/avatars')
files = list(root.glob('*.webp'))
assert len(files) == 2 and all(file.stat().st_uid == os.getuid() for file in files)
assert os.access(root, os.R_OK | os.W_OK)
''')
        record('HTTP profile update and avatar upload write to MongoDB and the appuser-owned named volume')
        old_container = run(['ps', '-q', 'app'])
        run(['up', '-d', '--force-recreate', '--no-deps', '--wait', '--wait-timeout', '120', 'app'])
        assert old_container != run(['ps', '-q', 'app'])
        base = 'http://' + run(['port', 'app', '5001'])
        with request(first, '/account/avatar') as reply:
            assert reply.status == 200 and hashlib.sha256(reply.read()).hexdigest() == digest
        with request(first, '/account') as reply:
            html = reply.read().decode()
            assert 'value="0912345678"' in html and 'Persistence test' in html
        with request(staff, '/account/avatar') as reply:
            assert reply.status == 200 and hashlib.sha256(reply.read()).hexdigest() == staff_digest
        with request(staff, '/account') as reply:
            assert 'Private admin profile' in reply.read().decode()
        record('force-recreated app keeps separate CUSTOMER and ADMIN avatars, profile fields and sessions')
        upload('JPEG', 'blue')
        upload('WEBP', 'pink')
        run(['exec', '-T', 'app', 'python', '-c', "from pathlib import Path; assert len(list(Path('/app/instance/avatars').glob('*.webp'))) == 2"])
        with request(first, '/account/avatar/delete', {'csrf_token': token(first)}) as reply:
            assert reply.status == 200
        with request(first, '/account/avatar') as reply:
            assert reply.headers['Content-Type'].startswith('image/svg+xml')
        with request(staff, '/account/avatar') as reply:
            assert hashlib.sha256(reply.read()).hexdigest() == staff_digest
        record('customer avatar replacement/deletion preserves the separate staff avatar')
        with request(first, '/account/change-password', {'csrf_token': token(first), 'currentPassword': password,
                                                        'newPassword': new_password, 'confirmPassword': new_password}) as reply:
            assert reply.status == 200 and 'Đã đổi mật khẩu thành công' in reply.read().decode()
        with request(second, '/api/account/profile') as reply:
            assert reply.status == 401
        assert login(first, password)[0] == 401
        assert login(first, new_password)[0] == 200
        record('password change revokes the other real MongoDB session, rejects the old password and accepts the new one')
        output = ROOT / 'docs/profile-compose-results.json'
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        # Only the random project just created, never the user's running stack.
        run(['down', '--volumes', '--remove-orphans'])
    print('PASS isolated Docker profile/avatar persistence verification', flush=True)


if __name__ == '__main__':
    main()

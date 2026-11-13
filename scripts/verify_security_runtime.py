"""Build separately, then verify Docker/Gunicorn with a NEW authenticated MongoDB.

Creates only labeled, randomly named disposable containers/network. No existing
database, Compose stack or volume is touched. Secrets remain in process memory.
"""
from concurrent.futures import ThreadPoolExecutor
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def docker(*args, env=None):
    result = subprocess.run(['docker', *args], cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        # Do not echo arguments/environment, which can contain credentials.
        raise RuntimeError('Docker operation failed: ' + args[0] + ': ' + result.stderr[:1000])
    return (result.stdout + (result.stderr if args[0] == 'logs' else '')).strip()


def browser():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar)), jar


def get(opener, url):
    with opener.open(url, timeout=10) as response:
        return response.read().decode('utf-8'), response.status


def post(opener, url, data, csrf):
    import urllib.parse
    request = urllib.request.Request(url, data=urllib.parse.urlencode({**data, 'csrf_token': csrf}).encode())
    return get(opener, request)


def main():
    tag = 'rbac-verify-' + uuid.uuid4().hex[:12]
    db_name = 'RBAC_SECURITY_TEST_' + uuid.uuid4().hex
    network, mongo_name = tag + '-net', tag + '-mongo'
    apps = [tag + '-app1', tag + '-app2']
    containers = []
    env = dict(os.environ)
    env.update(MONGO_INITDB_ROOT_USERNAME='verification_root', MONGO_INITDB_ROOT_PASSWORD=secrets.token_hex(32),
               MONGO_APP_USERNAME='verification_app', MONGO_APP_PASSWORD=secrets.token_hex(32), MONGO_DB=db_name)
    try:
        # Validate the canonical Compose file without printing expanded secrets.
        compose_env = {**env, 'MONGO_ROOT_USERNAME': env['MONGO_INITDB_ROOT_USERNAME'],
                       'MONGO_ROOT_PASSWORD': env['MONGO_INITDB_ROOT_PASSWORD'], 'SECRET_KEY': secrets.token_hex(32),
                       'MONGO_URI': 'mongodb://placeholder:placeholder@host.docker.internal:27017/test'}
        for compose in ['docker-compose.yml']:
            docker('compose', '-f', compose, 'config', '--quiet', env=compose_env)
        print('PASS: canonical Compose configuration', flush=True)
        docker('network', 'create', '--label', 'rbac.verification=true', network)
        docker('run', '-d', '--name', mongo_name, '--label', 'rbac.verification=true', '--network', network,
               '-p', '127.0.0.1::27017',
               '--mount', f'type=bind,source={ROOT / "db" / "docker-init-user.js"},target=/docker-entrypoint-initdb.d/10-app-user.js,readonly',
               *[arg for key in ['MONGO_INITDB_ROOT_USERNAME', 'MONGO_INITDB_ROOT_PASSWORD', 'MONGO_APP_USERNAME', 'MONGO_APP_PASSWORD', 'MONGO_DB'] for arg in ['-e', key]],
               'mongo:7.0', '--auth', env=env)
        containers.append(mongo_name)
        port = docker('port', mongo_name, '27017/tcp').rsplit(':', 1)[1]
        from pymongo import MongoClient
        uri = f'mongodb://{env["MONGO_APP_USERNAME"]}:{env["MONGO_APP_PASSWORD"]}@127.0.0.1:{port}/{db_name}?authSource={db_name}'
        mongo = MongoClient(uri, serverSelectionTimeoutMS=1000)
        for _ in range(45):
            try:
                mongo.admin.command('ping')
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Isolated MongoDB did not become ready')
        # The scoped credential must not read another database.
        from pymongo.errors import OperationFailure
        try:
            mongo['unrelated_database'].customers.find_one({})
            raise AssertionError('Application credential can read another database')
        except OperationFailure:
            pass
        print('PASS: authenticated MongoDB and database-scoped credential', flush=True)
        test_env = {**env, 'SECURITY_TEST_MONGO_URI': uri, 'SECURITY_TEST_MONGO_DB': db_name}
        result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--junitxml=docs/security-test-results.xml'], cwd=ROOT, env=test_env)
        if result.returncode:
            raise RuntimeError('Real MongoDB integration tests failed')
        # Provision a separate HTTP demo account; do not expose the password.
        from app import create_app
        from services import auth_service as auth
        app = create_app({'TESTING': True, 'APP_ENV': 'development', 'MONGO_DB': db_name, 'SECRET_KEY': secrets.token_hex(32)}, mongo)
        password = 'runtime phrase ' + secrets.token_hex(24)
        with app.app_context():
            actor = mongo[db_name].users.find_one({'role': 'ADMIN', 'status': 'active'})
            # Reset is unnecessary: create a non-privileged account under the known
            # actor in a new test-only store, preserving real service checks.
            user = auth.create_user({'email': 'runtime-' + uuid.uuid4().hex + '@example.test', 'password': password, 'role': 'PRODUCT_STAFF'}, actor)
        bases = []
        env['MONGO_URI'] = f'mongodb://{env["MONGO_APP_USERNAME"]}:{env["MONGO_APP_PASSWORD"]}@{mongo_name}:27017/{db_name}?authSource={db_name}'
        env['APP_ENV'] = 'development'
        for name in apps:
            env['SECRET_KEY'] = secrets.token_hex(32)
            docker('run', '-d', '--name', name, '--label', 'rbac.verification=true', '--network', network,
                   '-p', '127.0.0.1::5001', '-e', 'MONGO_URI', '-e', 'MONGO_DB', '-e', 'APP_ENV', '-e', 'SECRET_KEY', 'promotion-rbac:verify', env=env)
            containers.append(name)
            port = docker('port', name, '5001/tcp').rsplit(':', 1)[1]
            bases.append('http://127.0.0.1:' + port)
        for base in bases:
            for _ in range(30):
                try:
                    if get(urllib.request.build_opener(), base + '/health')[1] == 200:
                        break
                except Exception:
                    time.sleep(1)
            else:
                raise RuntimeError('Gunicorn did not become ready')
        opener, jar = browser()
        html, _ = get(opener, bases[0] + '/login')
        csrf = re.search(r'name="csrf-token" content="([^"]+)"', html)[1]
        html, status = post(opener, bases[0] + '/login', {'email': user['email'], 'password': password}, csrf)
        assert status == 200 and 'runtime-' in html
        for base in bases:
            data, status = get(opener, base + '/api/products')
            assert status == 200 and json.loads(data)['success']
        # Send requests across two containers, each running two Gunicorn workers.
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(lambda i: get(opener, bases[i % 2] + '/api/products')[1], range(32)))
        assert set(statuses) == {200}
        for name in apps:
            logs = docker('logs', name)
            assert logs.count('Booting worker with pid:') == 2
        print('PASS: two Gunicorn workers per container; shared session across independent apps', flush=True)
        html, _ = get(opener, bases[1] + '/catalog')
        csrf = re.search(r'name="csrf-token" content="([^"]+)"', html)[1]
        cookie_value = next(cookie.value for cookie in jar if cookie.name == 'dev-auth')
        post(opener, bases[1] + '/logout', {}, csrf)
        replay = urllib.request.Request(bases[0] + '/api/products', headers={'Cookie': 'dev-auth=' + cookie_value})
        try:
            get(urllib.request.build_opener(), replay)
            raise AssertionError('Revoked session was accepted')
        except urllib.error.HTTPError as error:
            assert error.code == 401
        print('PASS: logout revocation and session replay across workers', flush=True)
        print('PASS: Docker runtime verification complete', flush=True)
        mongo.close()
    finally:
        for name in reversed(containers):
            # Random names and labels created above only; -v removes their own
            # anonymous volumes, never the application Compose volume.
            docker('rm', '-f', '-v', name)
        try:
            docker('network', 'rm', network)
        except RuntimeError:
            pass


if __name__ == '__main__':
    main()

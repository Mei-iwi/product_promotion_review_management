"""Isolated real replica-set tests. Creates/deletes only a new random container."""
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Docker ' + args[0] + ' failed: ' + result.stderr[:1500])
    return result.stdout.strip()


def main():
    from pymongo import MongoClient
    name = 'shopping-test-' + uuid.uuid4().hex[:12]
    created = False
    try:
        docker('run', '-d', '--name', name, '--label', 'shopping.verification=true',
               '-p', '127.0.0.1::27017', 'mongo:7.0', '--replSet', 'rs0', '--bind_ip_all')
        created = True
        port = docker('port', name, '27017/tcp').rsplit(':', 1)[1]
        uri = f'mongodb://127.0.0.1:{port}/?replicaSet=rs0&directConnection=true'
        client = MongoClient(f'mongodb://127.0.0.1:{port}/?directConnection=true', serverSelectionTimeoutMS=1000)
        for _ in range(45):
            try:
                client.admin.command('ping')
                break
            except Exception:
                time.sleep(1)
        else: raise RuntimeError('Test MongoDB did not start')
        client.admin.command('replSetInitiate', {'_id': 'rs0', 'members': [{'_id': 0, 'host': 'localhost:27017'}]})
        for _ in range(45):
            if client.admin.command('hello').get('isWritablePrimary'):
                break
            time.sleep(1)
        else: raise RuntimeError('Test replica did not elect a primary')
        client.close()
        env = {**os.environ, 'SHOPPING_TEST_MONGO_URI': uri, 'SECURITY_TEST_MONGO_URI': uri,
               'SECURITY_TEST_MONGO_DB': 'RBAC_SECURITY_TEST_' + uuid.uuid4().hex}
        result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_shopping_replica.py', 'tests/test_real_mongo.py',
                                 '-q', '-p', 'no:cacheprovider', '--tb=short', '--junitxml=docs/shopping-replica-results.xml'], cwd=ROOT, env=env)
        if result.returncode: raise RuntimeError('Replica integration tests failed')
        result = subprocess.run([sys.executable, 'scripts/verify_shopping_browser.py'], cwd=ROOT, env=env)
        if result.returncode: raise RuntimeError('Shopping browser verification failed')
        print('PASS: replica concurrency, atomic rollback, retries and desktop/mobile shopping flow', flush=True)
    finally:
        if created:
            # Only this explicitly random, newly created container and its own
            # anonymous volumes. Never a user Compose volume or existing server.
            docker('rm', '-f', '-v', name)


if __name__ == '__main__':
    main()

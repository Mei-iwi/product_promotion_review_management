"""Verify the credentialed development replica Compose in a disposable project."""
import os
from pathlib import Path
import secrets
import subprocess
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    project = 'shopping-compose-verify-' + uuid.uuid4().hex[:12]
    env = {**os.environ, 'MONGO_ROOT_USERNAME': 'verification_root', 'MONGO_ROOT_PASSWORD': secrets.token_hex(32),
           'MONGO_APP_USERNAME': 'verification_app', 'MONGO_APP_PASSWORD': secrets.token_hex(32),
           'MONGO_DB': 'SHOPPING_COMPOSE_VERIFY', 'SECRET_KEY': secrets.token_hex(32),
           'FLASK_PORT': '0', 'MONGO_DOCKER_PORT': '0'}
    prefix = ['docker', 'compose', '-p', project, '-f', 'docker-compose.yml']
    def run(args, capture=False):
        result = subprocess.run(prefix + args, cwd=ROOT, env=env, text=True, capture_output=capture)
        if result.returncode:
            raise RuntimeError('Compose verification failed: ' + args[0])
        return result.stdout.strip() if capture else None
    try:
        run(['config', '--quiet'])
        run(['up', '--build', '-d', '--wait', '--wait-timeout', '150'])
        address = run(['port', 'app', '5001'], capture=True)
        base = 'http://' + address
        for path in ['/health', '/catalog', '/login']:
            with urllib.request.urlopen(base + path, timeout=10) as response:
                assert response.status == 200
        run(['exec', '-T', 'app', 'python', '-m', 'flask', '--app', 'app:create_app', 'reconcile-promotion-usage'])
        print('PASS: credentialed replica Compose, keyfile, initialization, app health/catalog/login and reconciliation CLI', flush=True)
    finally:
        # Only the random project created above; no user stack or existing volume.
        run(['down', '--volumes', '--remove-orphans'])


if __name__ == '__main__': main()

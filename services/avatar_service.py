"""Private, normalized avatar storage. User-supplied names never become paths."""
from io import BytesIO
import os
from pathlib import Path
import re
import secrets
import tempfile
import warnings

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import NotFound

from db.mongo import get_db
from repositories import security_repository as store
from services import account_profile_service as own
from services.helpers import ValidationError

MAX_BYTES = 800 * 1024
MAX_PIXELS = 16_000_000
KEY = re.compile(r'[a-f0-9]{64}\.webp', re.ASCII)


def avatar_key(row):
    metadata = (row or {}).get('avatar')
    return metadata.get('key') if isinstance(metadata, dict) else None


def storage_root():
    return Path(current_app.config['AVATAR_STORAGE_DIR']).resolve()


def storage_path(key):
    if not isinstance(key, str) or not KEY.fullmatch(key):
        raise ValidationError('Tham chiếu ảnh không hợp lệ')
    root = storage_root()
    path = root / key
    if path.is_symlink() or path.resolve().parent != root:
        raise ValidationError('Tham chiếu ảnh không hợp lệ')
    return path


def normalize(upload):
    name = upload.filename or ''
    suffix = re.fullmatch(r'[^/\\\x00:]+\.(jpg|jpeg|png|webp)', name, re.I)
    if not suffix:
        raise ValidationError('Chọn tệp JPG, PNG hoặc WebP với tên tệp hợp lệ')
    content = upload.stream.read(MAX_BYTES + 1)
    if not content or len(content) > MAX_BYTES:
        raise ValidationError('Ảnh đại diện phải nhỏ hơn hoặc bằng 800 KiB')
    expected = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'webp': 'WEBP'}[suffix[1].lower()]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.format != expected or image.width * image.height > MAX_PIXELS or max(image.size) > 8192:
                    raise ValidationError('Ảnh sai định dạng hoặc vượt giới hạn 16 triệu pixel / 8192px mỗi cạnh')
                if getattr(image, 'n_frames', 1) != 1:
                    raise ValidationError('Vui lòng chọn ảnh tĩnh')
                image.verify()
            with Image.open(BytesIO(content)) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                rgba = image.convert('RGBA')
                # A fresh canvas drops EXIF, ICC, comments and other input metadata.
                clean = Image.new('RGB', rgba.size, 'white')
                clean.paste(rgba, mask=rgba.getchannel('A'))
                output = BytesIO()
                clean.save(output, format='WEBP', quality=85, method=4)
                return output.getvalue(), clean.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError('Không thể đọc ảnh; tệp có thể bị lỗi hoặc không phải ảnh hợp lệ') from error


def remove_file(key):
    if not key:
        return
    try:
        storage_path(key).unlink(missing_ok=True)
    except (OSError, ValidationError):
        # The DB reference is already committed. A failed cleanup must not undo it.
        current_app.logger.warning('Avatar file cleanup deferred; run cleanup-avatar-orphans')


def replace(principal, upload):
    content, (width, height) = normalize(upload)
    with store.user_mutation_lock():
        collection, selector, row, field = own.avatar_target(principal, mutable=True)
        root = storage_root()
        root.mkdir(parents=True, exist_ok=True)
        key = secrets.token_hex(32) + '.webp'
        path = storage_path(key)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=root, prefix='.avatar-', suffix='.tmp', delete=False) as target:
                temporary = Path(target.name)
                target.write(content)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, path)
        except OSError as error:
            raise ValidationError('Chưa thể lưu ảnh; vui lòng thử lại sau') from error
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
        metadata = {'key': key, 'mediaType': 'image/webp', 'width': width, 'height': height, 'updatedAt': store.utcnow()}
        try:
            result = collection.update_one(selector, {'$set': {field: metadata}})
            if not result.matched_count:
                raise NotFound()
        except Exception:
            # A network error can arrive after MongoDB committed the update. Only
            # delete the new file if a fresh read proves it is not referenced.
            try:
                current = collection.find_one(selector)
                if field == 'profile.avatar':
                    current = own.personal_data(current or {})
                if avatar_key(current) != key:
                    remove_file(key)
            except Exception:
                current_app.logger.warning('Avatar commit uncertain; file retained for reconciliation')
            raise
        remove_file(avatar_key(row))
        return metadata


def delete(principal):
    with store.user_mutation_lock():
        collection, selector, row, field = own.avatar_target(principal, mutable=True)
        result = collection.update_one(selector, {'$unset': {field: ''}})
        if not result.matched_count:
            raise NotFound()
        remove_file(avatar_key(row))


def image_path(principal):
    _, _, row, _ = own.avatar_target(principal)
    try:
        path = storage_path(avatar_key(row))
        if path.is_file():
            return path
    except ValidationError:
        pass
    return None


def register_cli(app):
    import click
    import time

    @app.cli.command('cleanup-avatar-orphans')
    @click.option('--apply', is_flag=True, help='Remove unreferenced files older than 24 hours; default is dry-run.')
    def cleanup(apply):
        """Reconcile crash leftovers, without removing any referenced avatar."""
        count = 0
        with store.user_mutation_lock():
            root = storage_root()
            referenced = {r['avatar']['key'] for r in get_db().customers.find({'avatar.key': {'$exists': True}}, {'avatar.key': 1})
                          if isinstance(r.get('avatar'), dict) and isinstance(r['avatar'].get('key'), str)}
            for user in get_db().users.find({'profile.avatar.key': {'$exists': True}}, {'profile.avatar.key': 1}):
                key = avatar_key(own.personal_data(user))
                if isinstance(key, str):
                    referenced.add(key)
            for path in root.iterdir() if root.exists() else []:
                if (path.is_symlink() or not path.is_file() or path.name in referenced
                        or (not KEY.fullmatch(path.name) and not re.fullmatch(r'\.avatar-[\w-]+\.tmp', path.name))
                        or time.time() - path.stat().st_mtime < 86400):
                    continue
                if apply:
                    path.unlink()
                count += 1
        click.echo(f'{count} orphan file(s); ' + ('removed' if apply else 'dry-run, use --apply to remove'))

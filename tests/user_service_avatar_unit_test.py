import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from PIL import Image

from Andromeda.api.errors import AndromedaError
from Andromeda.api.routes.users import MAX_UPLOAD_BYTES, enforce_upload_size
from Andromeda.models.user import User
from Andromeda.schemas.user import UserPublic
from Andromeda.services import user_service
from Andromeda.services.user_service import set_user_avatar, reset_user_avatar


class OneResult:
    """Wraps a single item to support .one_or_none() on a mocked exec() call."""
    def __init__(self, item):
        self._item = item

    def one_or_none(self):
        return self._item


def make_png_bytes(size: tuple[int, int] = (100, 100), color: str = "red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def make_upload(data: bytes, filename: str = "avatar.png", declared_size: int | None = None) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=filename, size=declared_size)


def make_user() -> User:
    return User(id=uuid4(), name="Test User", email="test@example.com")


def as_public(user: User) -> UserPublic:
    return UserPublic.model_validate(user)


def session_with_user(user: User) -> MagicMock:
    session = MagicMock()
    session.exec = AsyncMock(return_value=OneResult(user))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_rejects_missing_filename():
    upload = make_upload(b"irrelevant", filename="")
    session = session_with_user(make_user())

    with pytest.raises(AndromedaError) as exc_info:
        await set_user_avatar(upload, as_public(make_user()), session)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_rejects_declared_size_over_limit():
    upload = make_upload(b"irrelevant", declared_size=user_service.MAX_AVATAR_SIZE + 1)
    session = session_with_user(make_user())

    with pytest.raises(AndromedaError) as exc_info:
        await set_user_avatar(upload, as_public(make_user()), session)

    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_raises_not_found_when_user_missing():
    upload = make_upload(make_png_bytes())
    session = session_with_user(None) # type: ignore

    with pytest.raises(AndromedaError) as exc_info:
        await set_user_avatar(upload, as_public(make_user()), session)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_rejects_stream_exceeding_max_size_even_without_declared_size():
    oversized = b"\x00" * (user_service.MAX_AVATAR_SIZE + 1)
    upload = make_upload(oversized)  # no declared `size`, so the streaming check must catch it
    session = session_with_user(make_user())

    with pytest.raises(AndromedaError) as exc_info:
        await set_user_avatar(upload, as_public(make_user()), session)

    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_rejects_non_image_payload():
    upload = make_upload(b"<script>alert(1)</script>", filename="avatar.png")
    session = session_with_user(make_user())

    with pytest.raises(AndromedaError) as exc_info:
        await set_user_avatar(upload, as_public(make_user()), session)

    assert exc_info.value.status_code == 400
    assert "not a valid image" in exc_info.value.message


@pytest.mark.asyncio
async def test_rejects_svg_polyglot_disguised_as_image():
    """A client-controlled extension must not let non-raster content (e.g. SVG/XML) through."""
    svg_payload = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'
    upload = make_upload(svg_payload, filename="payload.svg")
    session = session_with_user(make_user())

    with pytest.raises(AndromedaError) as exc_info:
        await set_user_avatar(upload, as_public(make_user()), session)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_rejects_oversized_resolution(tmp_path):
    huge = Image.new("RGB", (6000, 6000), "blue")
    buf = io.BytesIO()
    huge.save(buf, "PNG")
    upload = make_upload(buf.getvalue())
    session = session_with_user(make_user())

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        with pytest.raises(AndromedaError) as exc_info:
            await set_user_avatar(upload, as_public(make_user()), session)

    assert exc_info.value.status_code == 400
    assert "resolution" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_saves_valid_image_as_server_chosen_jpeg(tmp_path):
    upload = make_upload(make_png_bytes(), filename="../../etc/passwd.png")
    user = make_user()
    session = session_with_user(user)

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        result = await set_user_avatar(upload, as_public(user), session)

    assert result.avatar.startswith("https://cdn.galacti.org/avatars/")
    assert result.avatar.endswith(".jpg")

    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1

    saved = Image.open(saved_files[0])
    assert saved.format == "JPEG"
    assert saved.size == (512, 512)

    session.add.assert_called_once_with(user)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ignores_client_supplied_extension():
    upload = make_upload(make_png_bytes(), filename="payload.html")
    user = make_user()
    session = session_with_user(user)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch.object(user_service.settings, "avatar_dir", tmp_dir):
            result = await set_user_avatar(upload, as_public(user), session)

    assert ".html" not in result.avatar
    assert result.avatar.endswith(".jpg")


# ---------------------------------------------------------------------------
# pre-parse Content-Length guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("content_length", [None, 0, -1, MAX_UPLOAD_BYTES + 1])
async def test_enforce_upload_size_rejects_bad_content_length(content_length):
    with pytest.raises(AndromedaError) as exc_info:
        await enforce_upload_size(content_length)

    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
@pytest.mark.parametrize("content_length", [1, MAX_UPLOAD_BYTES])
async def test_enforce_upload_size_allows_valid_content_length(content_length):
    await enforce_upload_size(content_length)


# ---------------------------------------------------------------------------
# old avatar cleanup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_user_avatar_deletes_previous_owned_file(tmp_path):
    old_file = tmp_path / "old-avatar.jpg"
    old_file.write_bytes(b"old image bytes")

    user = make_user()
    user.avatar = f"{user_service.AVATAR_CDN_PREFIX}old-avatar.jpg"
    session = session_with_user(user)

    upload = make_upload(make_png_bytes())

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        result = await set_user_avatar(upload, as_public(user), session)

    assert not old_file.exists()
    remaining = list(tmp_path.iterdir())
    assert len(remaining) == 1
    assert remaining[0].name in result.avatar


@pytest.mark.asyncio
async def test_set_user_avatar_does_not_delete_default_avatar(tmp_path):
    default_file = tmp_path / "default.png"
    default_file.write_bytes(b"default image bytes")

    user = make_user()
    user.avatar = user_service.DEFAULT_AVATAR_URL
    session = session_with_user(user)

    upload = make_upload(make_png_bytes())

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        await set_user_avatar(upload, as_public(user), session)

    assert default_file.exists()


@pytest.mark.asyncio
async def test_set_user_avatar_does_not_touch_external_oauth_avatar(tmp_path):
    user = make_user()
    user.avatar = "https://lh3.googleusercontent.com/a/some-google-avatar"
    session = session_with_user(user)

    upload = make_upload(make_png_bytes())

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        result = await set_user_avatar(upload, as_public(user), session)

    assert result.avatar.endswith(".jpg")
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.asyncio
async def test_reset_user_avatar_deletes_previous_owned_file(tmp_path):
    old_file = tmp_path / "old-avatar.jpg"
    old_file.write_bytes(b"old image bytes")

    user = make_user()
    user.avatar = f"{user_service.AVATAR_CDN_PREFIX}old-avatar.jpg"
    session = session_with_user(user)

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        result = await reset_user_avatar(as_public(user), session)

    assert not old_file.exists()
    assert result.avatar == user_service.DEFAULT_AVATAR_URL


@pytest.mark.asyncio
async def test_reset_user_avatar_does_not_delete_default_avatar(tmp_path):
    default_file = tmp_path / "default.png"
    default_file.write_bytes(b"default image bytes")

    user = make_user()
    user.avatar = user_service.DEFAULT_AVATAR_URL
    session = session_with_user(user)

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        await reset_user_avatar(as_public(user), session)

    assert default_file.exists()


@pytest.mark.asyncio
async def test_reset_user_avatar_does_not_touch_external_oauth_avatar(tmp_path):
    user = make_user()
    user.avatar = "https://avatars.githubusercontent.com/u/12345"
    session = session_with_user(user)

    with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
        result = await reset_user_avatar(as_public(user), session)

    assert result.avatar == user_service.DEFAULT_AVATAR_URL
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_set_user_avatar_ignores_traversal_in_stored_old_url(tmp_path):
    """Even if a stored avatar URL somehow contained path segments, deletion
    must be confined to avatar_dir via Path(...).name — never escape it."""
    sentinel = tmp_path.parent / "sentinel.txt"
    sentinel.write_text("must survive")

    user = make_user()
    user.avatar = f"{user_service.AVATAR_CDN_PREFIX}../sentinel.txt"
    session = session_with_user(user)

    upload = make_upload(make_png_bytes())

    try:
        with patch.object(user_service.settings, "avatar_dir", str(tmp_path)):
            await set_user_avatar(upload, as_public(user), session)

        assert sentinel.exists()
    finally:
        sentinel.unlink(missing_ok=True)

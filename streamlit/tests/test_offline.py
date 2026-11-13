"""The app must not request a font from outside at run time."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "static" / "fonts"
EXTERNAL = re.compile(
    r"fonts\.googleapis\.com|fonts\.gstatic\.com|use\.typekit\.net|"
    r"fonts\.adobe\.com|cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com|"
    r"unpkg\.com|use\.fontawesome\.com|bunny\.net",
    re.I,
)


def test_config_has_no_external_url():
    text = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert not re.search(r"https?://", text)


def test_font_files_and_licence_exist():
    for name in ("SourceSans3-Regular.woff2", "SourceSans3-Semibold.woff2", "OFL.txt", "README.md"):
        assert (FONTS / name).is_file(), name
    for name in ("SourceSans3-Regular.woff2", "SourceSans3-Semibold.woff2"):
        assert (FONTS / name).read_bytes()[:4] == b"wOF2"


def test_font_faces_point_at_local_files():
    text = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "enableStaticServing = true" in text
    assert text.count("[[theme.fontFaces]]") == 2
    for url in re.findall(r'url = "([^"]+)"', text):
        assert url.startswith("app/static/fonts/")
        assert (ROOT / url.removeprefix("app/")).is_file()


def test_no_external_font_reference_in_app_code():
    files = [ROOT / "app.py", ROOT / ".streamlit" / "config.toml"]
    files += list((ROOT / "quadrant").rglob("*.py"))
    files += list((ROOT / "quadrant").rglob("*.css"))
    for f in files:
        assert not EXTERNAL.search(f.read_text(encoding="utf-8")), f

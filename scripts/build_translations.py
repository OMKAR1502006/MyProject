#!/usr/bin/env python
"""
Build django.po / django.mo for hi, mr, te, kn without requiring system gettext.
Run: python scripts/build_translations.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOCALE = BASE / 'locale'
sys.path.insert(0, str(BASE))

from agro.translations_catalog import CATALOG, LANGS  # noqa: E402


def generate_po(lang: str, translations: dict) -> str:
    lines = [
        'msgid ""',
        'msgstr ""',
        f'"Language: {lang}\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '',
    ]
    for msgid, langs in translations.items():
        msgstr = (langs.get(lang) or msgid).replace('"', '\\"')
        mid = msgid.replace('"', '\\"')
        lines.append(f'msgid "{mid}"')
        lines.append(f'msgstr "{msgstr}"')
        lines.append('')
    return '\n'.join(lines)


def compile_mo(po_path: Path, mo_path: Path):
    """Compile PO to MO using polib (GNU gettext-compatible binary)."""
    try:
        import polib
    except ImportError as exc:
        raise RuntimeError(
            'polib is required. Run: pip install polib'
        ) from exc

    po = polib.pofile(str(po_path), encoding='utf-8')
    po.save_as_mofile(str(mo_path))


def main():
    for lang in LANGS:
        lc_dir = LOCALE / lang / 'LC_MESSAGES'
        lc_dir.mkdir(parents=True, exist_ok=True)
        po_path = lc_dir / 'django.po'
        mo_path = lc_dir / 'django.mo'
        po_path.write_text(generate_po(lang, CATALOG), encoding='utf-8')
        try:
            compile_mo(po_path, mo_path)
            print(f'OK {lang}: {len(CATALOG)} strings -> {mo_path}')
        except Exception as exc:
            print(f'PO written {lang}, MO failed: {exc}')


if __name__ == '__main__':
    main()

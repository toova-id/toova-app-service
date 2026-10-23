#!/usr/bin/env python3
"""Delete Odoo PO files not present in explicit locale allowlist."""
import argparse
from pathlib import Path


def prune(root, locales, apply=False):
    removed = []
    for path in Path(root).rglob('*.po'):
        if path.parent.name in {'i18n', 'i18n_extra'} and path.stem not in locales:
            removed.append(path)
            if apply:
                path.unlink()
    return removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--locales', required=True, help='Comma-separated PO stems, for example id,en_US')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    locales = {locale.strip() for locale in args.locales.split(',') if locale.strip()}
    if not locales:
        parser.error('locale allowlist cannot be empty')
    removed = prune(args.root, locales, apply=False)
    size = sum(path.stat().st_size for path in removed)
    if args.apply:
        for path in removed:
            path.unlink()
    print(f'{"removed" if args.apply else "would remove"}: {len(removed)} files, {size / 1024 / 1024:.1f} MiB')


if __name__ == '__main__':
    main()

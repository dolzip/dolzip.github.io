#!/usr/bin/env python3
"""Build the static website with Python 3's standard library only."""
import argparse
import html
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'site'
ORIGIN = 'https://dolzip.github.io'
TOKEN = re.compile(r'\{\{([a-z][a-z0-9_]*)\}\}')
GENERATED = {'lang', 'direction', 'issue_lang', 'alternates', 'language_links'}


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'{path}: duplicate key {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def load_source(source=SOURCE):
    locales = read_json(source / 'locales.json')
    if (not isinstance(locales, list) or len(locales) != 31
            or any(not isinstance(code, str) or not re.fullmatch(r'[a-z]{2}(?:-[A-Za-z]{2,4})?', code)
                   for code in locales) or len(set(locales)) != len(locales)):
        raise ValueError('locales.json must contain 31 unique locale codes')
    if {p.stem for p in (source / 'i18n').glob('*.json')} != set(locales):
        raise ValueError('Translation files must match locales.json')
    templates = {name: (source / 'templates' / f'{name}.html').read_text(encoding='utf-8')
                 for name in ('page', 'index')}
    keys = set(TOKEN.findall(templates['page'])) - GENERATED
    keys.add('native')
    strings = {}
    for code in locales:
        values = read_json(source / 'i18n' / f'{code}.json')
        if not isinstance(values, dict) or set(values) != keys:
            raise ValueError(f'{code}: translation keys must match the page template: {sorted(keys)}')
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise ValueError(f'{code}: every translation must be a nonempty string')
        strings[code] = values
    return locales, strings, templates


def render(template, values):
    # One substitution pass: translated text is never interpreted as a template.
    return TOKEN.sub(lambda match: values[match[1]], template)


def pages(source=SOURCE):
    locales, strings, templates = load_source(source)
    alternates = ''.join(f'<link rel="alternate" hreflang="{code}" href="{ORIGIN}/{code}/">'
                         for code in locales)
    alternates += f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/">'

    def links(current=None):
        return ''.join(f'<a href="/{code}/" lang="{code}" hreflang="{code}"'
                       + (' aria-current="page"' if code == current else '')
                       + f'>{html.escape(strings[code]["native"])}</a>' for code in locales)

    result = {'index.html': render(templates['index'], {
        'alternates': alternates, 'language_links': links(),
    })}
    for code in locales:
        values = {key: html.escape(value) for key, value in strings[code].items()}
        values.update(lang=code, direction=' dir="rtl"' if code == 'ar' else '',
                      issue_lang='ko' if code == 'ko' else 'en',
                      alternates=alternates, language_links=links(code))
        result[f'{code}/index.html'] = render(templates['page'], values)
    result['robots.txt'] = f'User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n'
    result['sitemap.xml'] = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                             + f'<url><loc>{ORIGIN}/</loc></url>\n'
                             + ''.join(f'<url><loc>{ORIGIN}/{code}/</loc></url>\n' for code in locales)
                             + '</urlset>\n')
    result['.nojekyll'] = ''
    result['.gitignore'] = '*\n'
    return result


def build(output=ROOT / '_site', source=SOURCE):
    # Validate and render before touching an existing build. Only _site is disposable.
    rendered = pages(source)
    if output.is_symlink():
        raise ValueError('Output cannot be a symlink')
    output = output.resolve()
    if output.name != '_site' or output.is_symlink() or source.resolve().is_relative_to(output):
        raise ValueError('Output must be a disposable directory named _site outside site/')
    if output.is_relative_to(source.resolve()):
        raise ValueError('Output cannot be inside site/')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, content in rendered.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    shutil.copytree(source / 'assets', output / 'assets')
    shutil.copyfile(source / 'third-party-notices.txt', output / 'third-party-notices.txt')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site',
                        help='destination directory, named _site (default: repository/_site)')
    args = parser.parse_args()
    print(f'Built 31 locales and language home: {build(args.output)}')

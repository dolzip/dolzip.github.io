"""Regression tests for the published URL, locale and asset contract."""
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import build


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def select(self, tag, **attrs):
        return [a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in attrs.items())]


class SiteBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / '_site'

    def test_all_locale_urls_assets_downloads_and_navigation(self):
        build.build(self.output)
        locales, strings, _ = build.load_source()
        for code in locales:
            with self.subTest(locale=code):
                doc = Document((self.output / code / 'index.html').read_text())
                self.assertEqual(doc.select('html')[0].get('lang'), code)
                self.assertEqual(doc.select('html')[0].get('dir'), 'rtl' if code == 'ar' else None)
                self.assertEqual(doc.select('link', rel='canonical')[0]['href'], f'{build.ORIGIN}/{code}/')
                links = [a for a in doc.select('a') if 'hreflang' in a]
                self.assertEqual([a['hreflang'] for a in links], locales)
                self.assertEqual([a['lang'] for a in links if a.get('aria-current') == 'page'], [code])
                alternates = doc.select('link', rel='alternate')
                self.assertEqual([a['hreflang'] for a in alternates], locales + ['x-default'])
                downloads = [a['href'] for a in doc.select('a') if 'release-download' in a.get('class', '').split()]
                release = 'https://github.com/dolzip/dolzip.github.io/releases/download/v0.1.0/'
                self.assertEqual(downloads, [release + 'DolUnzip-0.1.0.dmg'] * 2 + [release + 'dz-0.1.0.pkg'])
                self.assertEqual(len([a for a in doc.select('button') if 'disabled' in a]), 2)
                self.assertIn(html.escape(strings[code]['native']), (self.output / code / 'index.html').read_text())
                ids = {a['id'] for _, a in doc.tags if 'id' in a}
                for _, attrs in doc.tags:
                    for key in ('href', 'src'):
                        value = attrs.get(key, '')
                        if value.startswith('/'):
                            path = self.output / value.lstrip('/')
                            self.assertTrue(path.exists(), value)
                        elif value.startswith('#'):
                            self.assertIn(value[1:], ids)
        root = Document((self.output / 'index.html').read_text())
        self.assertEqual([a['lang'] for a in root.select('a') if 'hreflang' in a], locales)
        sitemap = ET.parse(self.output / 'sitemap.xml')
        urls = [e.text for e in sitemap.findall('.//{*}loc')]
        self.assertEqual(urls, [build.ORIGIN + '/'] + [f'{build.ORIGIN}/{code}/' for code in locales])
        self.assertIn(f'Sitemap: {build.ORIGIN}/sitemap.xml', (self.output / 'robots.txt').read_text())
        for asset in (build.SOURCE / 'assets').iterdir():
            self.assertEqual(asset.read_bytes(), (self.output / 'assets' / asset.name).read_bytes())
        self.assertEqual((build.SOURCE / 'third-party-notices.txt').read_bytes(),
                         (self.output / 'third-party-notices.txt').read_bytes())
        self.assertFalse((self.output / 'i18n').exists())
        self.assertFalse((self.output / 'templates').exists())

    def test_rebuild_removes_stale_files_and_is_deterministic(self):
        build.build(self.output)
        before = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        (self.output / 'stale.html').write_text('old output')
        build.build(self.output)
        after = {p.relative_to(self.output): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_missing_extra_empty_and_duplicate_translations_fail_before_output_changes(self):
        source = Path(self.temp.name) / 'site'
        shutil.copytree(build.SOURCE, source)
        path = source / 'i18n' / 'ko.json'
        original = path.read_text()
        data = json.loads(original)
        variants = [dict(data, extra='extra'), dict(data, hero_title='')]
        missing = dict(data)
        del missing['hero_title']
        variants.append(missing)
        self.output.mkdir()
        sentinel = self.output / 'keep.txt'
        sentinel.write_text('previous build')
        for values in variants:
            path.write_text(json.dumps(values))
            with self.assertRaises(ValueError):
                build.build(self.output, source)
            self.assertEqual(sentinel.read_text(), 'previous build')
        path.write_text(original[:-2] + ', "native": "duplicate"}')
        with self.assertRaisesRegex(ValueError, 'duplicate key'):
            build.build(self.output, source)

    def test_translation_text_is_escaped_without_template_evaluation(self):
        locales, strings, templates = build.load_source()
        value = '<script>"&\'{{lang}}</script>'
        strings['ko']['hero_title'] = value
        with patch.object(build, 'load_source', return_value=(locales, strings, templates)):
            page = build.pages()['ko/index.html']
        self.assertIn('<h1>' + html.escape(value) + '</h1>', page)
        self.assertNotIn('<script>"', page)

    def test_output_cannot_replace_sources_or_follow_symlinks(self):
        with self.assertRaises(ValueError):
            build.build(build.SOURCE)
        with self.assertRaises(ValueError):
            build.build(build.SOURCE / '_site')
        target = Path(self.temp.name) / 'keep'
        target.mkdir()
        self.output.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            build.build(self.output)
        self.assertTrue(target.exists())


if __name__ == '__main__':
    unittest.main()

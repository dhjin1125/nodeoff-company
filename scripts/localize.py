"""Generate English pages from the same HTML and explicit, reviewed translations.

Korean copy remains the source of truth. Unknown Korean strings fail the build,
so product updates cannot silently ship an untranslated English page.
"""
import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name('en.json').read_text())
ORIGIN = 'https://nodeoff.kr'
KOREAN = re.compile('[가-힣]')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'link', 'meta', 'param', 'source', 'track', 'wbr'}


def translate(text, context=''):
    key = text.strip()
    if not KOREAN.search(key):
        return text
    if f'{context}:{key}' in CATALOG:
        key = f'{context}:{key}'
    if key not in CATALOG:
        raise ValueError(f'Missing English translation: {key}')
    return text[:len(text) - len(text.lstrip())] + CATALOG[key] + text[len(text.rstrip()):]


class LocalizedPage(HTMLParser):
    def __init__(self, locale, route):
        super().__init__(convert_charrefs=True)
        self.locale, self.route = locale, route
        self.output, self.stack = [], []

    def handle_decl(self, decl):
        self.output.append(f'<!{decl}>')

    def handle_comment(self, data):
        self.output.append(f'<!--{data}-->')

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if self.locale == 'en':
            for name in ('aria-label', 'alt', 'title', 'content'):
                if values.get(name):
                    values[name] = translate(values[name])
            if tag == 'html':
                values['lang'] = 'en'
            if tag == 'a' and values.get('href', '').startswith('/'):
                values['href'] = '/en' + values['href']
            if tag == 'link' and values.get('rel') == 'canonical':
                values['href'] = ORIGIN + '/en' + self.route
            if tag == 'meta' and values.get('property') == 'og:url':
                values['content'] = ORIGIN + '/en' + self.route
            if tag == 'meta' and values.get('property') == 'og:locale':
                values['content'] = 'en_US'
        attributes = ''.join(f' {key}' if val is None else
                             f' {key}="{escape(val, quote=True)}"'
                             for key, val in values.items())
        self.output.append(f'<{tag}{attributes}>')
        if tag not in VOID:
            self.stack.append((tag, values))

    def handle_endtag(self, tag):
        values = self.stack[-1][1] if self.stack else {}
        if tag == 'head':
            for locale, path in [('ko', self.route), ('en', '/en' + self.route), ('x-default', self.route)]:
                self.output.append(f'<link rel="alternate" hreflang="{locale}" href="{ORIGIN}{path}">')
            alternate = 'ko_KR' if self.locale == 'en' else 'en_US'
            self.output.append(f'<meta property="og:locale:alternate" content="{alternate}">')
        if tag == 'nav':
            label = 'Language' if self.locale == 'en' else '언어 선택'
            self.output.append(f'<span class="language-switch" role="group" aria-label="{label}">')
            for locale, name, route in [('ko', '한국어', self.route), ('en', 'EN', '/en' + self.route)]:
                active = ' aria-current="page"' if locale == self.locale else ''
                self.output.append(f'<a lang="{locale}" hreflang="{locale}" href="{route}"{active}>{name}</a>')
            self.output.append('</span>')
        if self.locale == 'en' and tag == 'p' and values.get('class') == 'access-note':
            if self.route in ('/products/nurse-board', '/products/jjikgo', '/products/yeoun'):
                self.output.append('<span class="service-language">The linked web service is currently available in Korean. This page is its English product guide.</span>')
        self.output.append(f'</{tag}>')
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        context = self.stack[-1][0] if self.stack else ''
        self.output.append(escape(translate(data, context) if self.locale == 'en' else data, quote=False))


def generate(out, product_ids):
    routes = ['/'] + [f'/products/{pid}' for pid in product_ids]
    rendered = []
    for route in routes:
        relative = 'index.html' if route == '/' else route.lstrip('/') + '.html'
        source = (out / relative).read_text()
        for locale in ('ko', 'en'):
            parser = LocalizedPage(locale, route)
            parser.feed(source)
            parser.close()
            target = out / ('en/' if locale == 'en' else '') / relative
            rendered.append((target, ''.join(parser.output)))
    # Validate all translations before writing either language.
    for target, document in rendered:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document)
    entries = []
    for route in routes:
        alternatives = ''.join(f'<xhtml:link rel="alternate" hreflang="{lang}" href="{ORIGIN}{path}"/>'
                               for lang, path in [('ko', route), ('en', '/en' + route), ('x-default', route)])
        for path in (route, '/en' + route):
            entries.append(f'<url><loc>{ORIGIN}{path}</loc>{alternatives}</url>')
    (out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + ''.join(entries) + '</urlset>')

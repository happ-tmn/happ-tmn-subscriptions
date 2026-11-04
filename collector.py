#!/usr/bin/env python3
"""@happ_tmn subscription collector. Sources only from private runtime secret.

This does not test the reachability of downstream proxy servers. It validates
format/filters and publishes normalized, name-labelled subscription URLs.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote, unquote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BRAND = '@happ_tmn'
SUPPORTED = {'vless', 'vmess', 'trojan', 'ss', 'ssr', 'hy2', 'hysteria', 'hysteria2', 'tuic', 'socks', 'socks5', 'http', 'https'}
URI_RE = re.compile(r'^([a-zA-Z][\w+.-]*)://', re.I)
FLAG_RE = re.compile(r'[\U0001f1e6-\U0001f1ff]{2}')
MAX_SOURCE_BYTES = 64_000_000
MAX_NODES = 130_000
FETCH_TIMEOUT = 35
PAGE_LIMIT = 2_100_000
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / 'sub'

GROUPS = (
    'all', 'vless', 'vmess', 'trojan', 'ss', 'ssr', 'hysteria2', 'tuic',
    'tls', 'reality', 'none', 'ws', 'xhttp', 'grpc', 'tcp', 'httpupgrade', 'h2',
    'vless/tls/ws', 'vless/reality', 'vless/reality-vision', 'vless/xhttp',
    'trojan/tls', 'vmess/tls/ws',
)


def b64decode_utf8(value: str) -> str:
    value = re.sub(r'\s+', '', value).replace('-', '+').replace('_', '/')
    if not value or re.search(r'[^A-Za-z0-9+/=]', value):
        raise ValueError('not base64')
    return base64.b64decode(value + '=' * (-len(value) % 4), validate=True).decode('utf-8-sig')


def b64encode_utf8(value: str, *, padding: bool = True) -> str:
    encoded = base64.b64encode(value.encode('utf-8')).decode('ascii')
    return encoded if padding else encoded.rstrip('=')


def country_flags(name: str) -> str:
    seen = set()
    result = []
    for flag in FLAG_RE.findall(name):
        if flag not in seen:
            result.append(flag)
            seen.add(flag)
    return ' '.join(result[:2])


def display_name(old_name: str, fingerprint: str) -> str:
    flags = country_flags(old_name)
    return f'{flags} {BRAND} {fingerprint[:6]}'.strip()


def opts_from_query(query: str) -> dict[str, str]:
    return {k.lower(): v for k, v in parse_qsl(query, keep_blank_values=True)}



def canonical_url_key(scheme: str, url) -> str:
    """Canonical comparison only; NEVER changes the exported URI itself.

    Avoids duplicate nodes when donors use reordered query arguments, a
    different name/fragment, percent-encoding variations or mixed-case hosts.
    Identity still contains account credentials, address, port, transport,
    security and every non-label parameter; distinct servers are not merged.
    """
    pairs = []
    for key, val in parse_qsl(url.query, keep_blank_values=True):
        k = key.lower()
        # These are metadata fields, not connection settings. They are still
        # preserved in the *published* URI for the chosen representative.
        if k in {'remarks', 'remark', 'name', 'ps'}:
            continue
        if k in {'sni', 'server_name', 'servername', 'host', 'security', 'type',
                 'network', 'net', 'tls', 'fp', 'fingerprint'}:
            val = val.lower()
        pairs.append((k, val))
    pairs.sort()
    # For the host, DNS names are case-insensitive. Userinfo/password remain
    # case-sensitive: both can distinguish otherwise identical endpoints.
    identity = [scheme.lower(), url.username or '', url.password or '',
                (url.hostname or '').lower(), url.port, url.path,
                sorted(pairs)]
    return scheme.lower() + ':' + json.dumps(identity, ensure_ascii=False, separators=(',', ':'))


def normalize(raw: str) -> dict | None:
    line = raw.strip().strip('\ufeff')
    # Support lines wrapped in markdown quotes without changing URI internals.
    if not line or len(line) > 250_000:
        return None
    match = URI_RE.match(line)
    if not match:
        return None
    scheme = match.group(1).lower()
    if scheme not in SUPPORTED:
        return None
    protocol = {'hy2':'hysteria2', 'hysteria':'hysteria2', 'socks5':'socks', 'https':'http'}.get(scheme, scheme)
    security = 'none'
    transport = 'tcp'
    old_name = ''
    if scheme == 'vmess' and '@' not in line.split('?', 1)[0]:
        try:
            source_json = json.loads(b64decode_utf8(line[len(match.group(0)):].split('#', 1)[0]))
            if not isinstance(source_json, dict) or not source_json.get('add') or not source_json.get('port'):
                return None
            old_name = str(source_json.get('ps') or '')
            no_name = dict(source_json)
            no_name['ps'] = ''
            # VMess often uses '443' and 443 interchangeably.
            if 'port' in no_name:
                no_name['port'] = str(no_name['port'])
            for field in ('add', 'sni', 'tls', 'net'):
                if isinstance(no_name.get(field), str):
                    no_name[field] = no_name[field].lower()
            dedup = 'vmess-json:' + json.dumps(no_name, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            fingerprint = hashlib.sha256(dedup.encode()).hexdigest()
            source_json['ps'] = display_name(old_name, fingerprint)
            result = 'vmess://' + b64encode_utf8(json.dumps(source_json, ensure_ascii=False, separators=(',', ':')))
            tls = str(source_json.get('tls') or source_json.get('security') or '').lower()
            security = 'reality' if tls == 'reality' else ('tls' if tls in ('tls','true','1') else 'none')
            transport = str(source_json.get('net') or source_json.get('type') or 'tcp').lower()
            return dict(line=result, key=dedup, protocol=protocol, security=security, transport=transport, vision=False)
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            return None
    if scheme == 'ssr':
        try:
            decoded = b64decode_utf8(line[len(match.group(0)):].split('#', 1)[0])
            core, sep, query = decoded.partition('/?')
            if len(core.split(':')) < 6:
                return None
            params = query.split('&') if sep else []
            old_name = ''
            kept = []
            for item in params:
                if item.startswith('remarks='):
                    try:
                        old_name = b64decode_utf8(unquote(item[len('remarks='):]))
                    except (ValueError, UnicodeError):
                        old_name = ''
                else:
                    kept.append(item)
            dedup = 'ssr:' + core + '/?' + '&'.join(sorted(kept))
            fingerprint = hashlib.sha256(dedup.encode()).hexdigest()
            kept.append('remarks=' + b64encode_utf8(display_name(old_name, fingerprint), padding=False))
            rebuilt = core + '/?' + '&'.join(kept)
            return dict(line='ssr://' + b64encode_utf8(rebuilt, padding=False), key=dedup, protocol=protocol, security='none', transport='tcp', vision=False)
        except (ValueError, UnicodeError):
            return None
    try:
        url = urlsplit(line)
        if not url.netloc:
            return None
        # Reject source URLs or web pages accidentally parsed as proxy links.
        if protocol in {'http', 'socks'} and url.port is None:
            return None
    except ValueError:
        return None
    original_without_remark = line.split('#', 1)[0]
    old_name = unquote(url.fragment)
    try:
        dedup = canonical_url_key(protocol, url)
    except ValueError:
        return None
    fingerprint = hashlib.sha256(dedup.encode('utf-8')).hexdigest()
    new_name = quote(display_name(old_name, fingerprint), safe='')
    result = original_without_remark + '#' + new_name
    params = opts_from_query(url.query)
    security = (params.get('security') or params.get('tls') or 'none').lower()
    if security in ('true', '1'):
        security = 'tls'
    transport = (params.get('type') or params.get('network') or params.get('net') or 'tcp').lower()
    vision = protocol == 'vless' and security == 'reality' and params.get('flow', '').lower() == 'xtls-rprx-vision'
    return dict(line=result, key=dedup, protocol=protocol, security=security, transport=transport, vision=vision)


def extract_lines(text: str) -> list[str]:
    text = text.lstrip('\ufeff').strip()
    if text[:200].lower().startswith(('<!doctype html', '<html', '{"error"', '{"message"')):
        raise ValueError('response is HTML/error page')
    if not re.search(r'(?im)^\s*(?:vless|vmess|trojan|ss|ssr|hy2|hysteria2?|tuic|socks5?|https?)://', text):
        # Conventional subscription may be one base64-wrapped plain list.
        try:
            decoded = b64decode_utf8(text)
            if '://' in decoded:
                text = decoded
        except (ValueError, UnicodeError):
            pass
    return [l.strip() for l in text.splitlines() if l.strip()]


def download_source(url: str) -> list[str]:
    if urlsplit(url).scheme.lower() != 'https':
        raise ValueError('only HTTPS sources are accepted')
    request = Request(url, headers={'User-Agent':'HappTMN-SubscriptionCollector/1.0 (+GitHub Actions)', 'Accept':'text/plain, */*'})
    last_err = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=FETCH_TIMEOUT) as response:
                content = response.read(MAX_SOURCE_BYTES + 1)
                if len(content) > MAX_SOURCE_BYTES:
                    raise ValueError('source over size limit')
                txt = content.decode('utf-8-sig', errors='replace')
                result = extract_lines(txt)
                if not result:
                    raise ValueError('empty response')
                return result
        except Exception as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(type(last_err).__name__) from last_err


def source_urls() -> list[str]:
    raw = os.environ.get('SOURCES_TXT', '')
    if not raw and os.environ.get('HAPP_TMN_SOURCE_FILE'):
        raw = Path(os.environ['HAPP_TMN_SOURCE_FILE']).read_text(encoding='utf-8')
    urls = []
    for item in raw.splitlines():
        item = item.strip()
        if not item or item.startswith('#'):
            continue
        if urlsplit(item).scheme.lower() != 'https':
            raise ValueError('Source URL must be HTTPS')
        if item not in urls:
            urls.append(item)
    return urls


def in_group(node: dict, group: str) -> bool:
    p, s, t = node['protocol'], node['security'], node['transport']
    if group == 'all': return True
    if group in ('vless','vmess','trojan','ss','ssr','hysteria2','tuic'):
        return p == group
    if group == 'vless/reality-vision': return bool(node['vision'])
    if group == 'vless/reality': return p == 'vless' and s == 'reality'
    if group == 'vless/xhttp': return p == 'vless' and t == 'xhttp'
    if group == 'vless/tls/ws': return p == 'vless' and s == 'tls' and t == 'ws'
    if group == 'trojan/tls': return p == 'trojan' and s == 'tls'
    if group == 'vmess/tls/ws': return p == 'vmess' and s == 'tls' and t == 'ws'
    if group in ('tls','reality','none'): return s == group
    return t == group



# Friendly README table gets regenerated together with status.json.
GROUP_TITLES = {
    'all': '🌍 Все конфигурации',
    'vless': '⚡ VLESS', 'vmess': '📡 VMess', 'trojan': '🛡️ Trojan',
    'ss': '🌪️ Shadowsocks', 'ssr': '🌊 ShadowsocksR',
    'hysteria2': '🚀 Hysteria2', 'tuic': '✨ TUIC',
    'tls': '🔒 TLS', 'reality': '🔐 Reality', 'none': '🔓 Без TLS / Reality',
    'ws': '🌐 WebSocket', 'xhttp': '📦 XHTTP', 'grpc': '🧩 gRPC',
    'tcp': '🔌 TCP', 'httpupgrade': '🔗 HTTPUpgrade', 'h2': '📨 HTTP/2',
    'vless/tls/ws': '⚡ VLESS TLS WS',
    'vless/reality': '🔐 VLESS Reality',
    'vless/reality-vision': '💎 VLESS Reality Vision',
    'vless/xhttp': '📦 VLESS XHTTP',
    'trojan/tls': '🛡️ Trojan TLS',
    'vmess/tls/ws': '📡 VMess TLS WS',
}


def update_readme_counts(counts: dict[str, int], *, updated_at: str,
                         duplicates_removed: int = 0) -> bool:
    """Replace only the subscriptions section, preserving the rest of README.

    Requires the README in a supported human-facing layout. The source list,
    passwords and account info are deliberately not included in the table.
    """
    readme = BASE_DIR / 'README.md'
    if not readme.is_file():
        return False
    text = readme.read_text(encoding='utf-8')
    start_match = re.search(r'(?m)^## 📥 (?:Выбери подписку|Подписки)\s*$', text)
    if not start_match:
        print('README counters: subscription heading not found; leaving README unchanged')
        return False
    tail = text[start_match.end():]
    end_match = re.search(r'(?m)^## (?:📲 Как подключить|🫶 Наш Telegram|❓ Полезно знать)', tail)
    if not end_match:
        print('README counters: following section not found; leaving README unchanged')
        return False
    end = start_match.end() + end_match.start()
    when = updated_at.replace('T', ' ').replace('+00:00', ' UTC')
    table = [
        '## 📥 Выбери подписку',
        '',
        f'**Всего конфигураций: {counts.get("all", 0):,}** · '
        f'удалено повторов за сборку: **{duplicates_removed:,}** · '
        f'обновлено: **{when}**.',
        '',
        'Нажми «Открыть TXT» или скопируй адрес ссылки в Nekobox.',
        '',
        '<!-- HAPP_TMN_COUNTS_START -->',
        '| Подписка | Конфигураций | Ссылка |',
        '|:--|--:|:--|',
    ]
    # Important groups first, other filters below.
    order = ('all', 'vless/reality-vision', 'vless/reality', 'vless',
             'vmess', 'trojan', 'ss', 'ssr', 'hysteria2', 'tuic',
             'ws', 'xhttp', 'grpc', 'tls', 'reality', 'none', 'tcp',
             'httpupgrade', 'h2', 'vless/tls/ws', 'vless/xhttp',
             'trojan/tls', 'vmess/tls/ws')
    for g in order:
        path = g + '.txt'
        url = 'https://raw.githubusercontent.com/happ-tmn/happ-tmn-subscriptions/main/sub/' + path
        table.append(f'| {GROUP_TITLES[g]} | **{counts.get(g, 0):,}** | [Открыть TXT]({url}) |')
    table.extend([
        '<!-- HAPP_TMN_COUNTS_END -->', '',
        '> Цифры показывают число записей, **не** количество проверенных работающих серверов. '
        'Одна конфигурация может входить в несколько тематических подборок.',
        '',
    ])
    updated = text[:start_match.start()] + '\n'.join(table) + '\n' + text[end:]
    if updated != text:
        readme.write_text(updated, encoding='utf-8')
    return True


def write_group(group: str, nodes: list[dict]) -> int:
    target = OUTPUT_DIR.joinpath(*group.split('/')).with_suffix('.txt')
    target.parent.mkdir(parents=True, exist_ok=True)
    body = ''.join(n['line'] + '\n' for n in nodes)
    target.write_text(body, encoding='utf-8')
    if group == 'all':
        page_dir = OUTPUT_DIR / 'pages'
        page_dir.mkdir(parents=True, exist_ok=True)
        for old in page_dir.glob('all-*.txt'):
            old.unlink()
        parts = []
        chunk = []
        size = 0
        for n in nodes:
            element = n['line'] + '\n'
            el_size = len(element.encode('utf-8'))
            if chunk and size + el_size > PAGE_LIMIT:
                parts.append(''.join(chunk)); chunk = []; size = 0
            chunk.append(element); size += el_size
        if chunk:
            parts.append(''.join(chunk))
        for i, part in enumerate(parts, 1):
            (page_dir / f'all-{i:03}.txt').write_text(part, encoding='utf-8')
    return len(nodes)


def run() -> int:
    sources = source_urls()
    if not sources:
        print('ERROR: SOURCES_TXT secret is missing or empty', file=sys.stderr)
        return 2
    seen: dict[str, dict] = {}
    errors = 0
    succeeded = 0
    duplicates_removed = 0
    valid_inputs = 0
    for index, url in enumerate(sources, 1):
        try:
            lines = download_source(url)
            new = 0
            for raw in lines:
                item = normalize(raw)
                if item:
                    valid_inputs += 1
                    if item['key'] in seen:
                        duplicates_removed += 1
                    elif len(seen) < MAX_NODES:
                        seen[item['key']] = item
                        new += 1
            succeeded += 1
            # Never print original URLs or node content in CI logs.
            print(f'Source {index}/{len(sources)}: fetched {len(lines)} entries, added {new} unique')
        except Exception as exc:
            errors += 1
            print(f'Source {index}/{len(sources)}: unavailable ({type(exc).__name__})', file=sys.stderr)
    if not seen:
        print('ERROR: no valid nodes. Previous published subscriptions remain intact.', file=sys.stderr)
        return 2
    if errors and (OUTPUT_DIR / 'all.txt').exists() and (OUTPUT_DIR / 'all.txt').stat().st_size > 0:
        print('ERROR: partial fetch; preserving previous published snapshot.', file=sys.stderr)
        return 3
    OUTPUT_DIR.mkdir(exist_ok=True)
    nodes = list(seen.values())
    counts = {}
    for group in GROUPS:
        selected = [node for node in nodes if in_group(node, group)]
        counts[group] = write_group(group, selected)
    updated_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    status = dict(updated_at=updated_at, total=len(nodes),
                  valid_entries=valid_inputs, duplicates_removed=duplicates_removed,
                  sources_total=len(sources), sources_ok=succeeded,
                  partial=bool(errors), groups=counts,
                  note='Protocol match only; network reachability is not verified')
    (BASE_DIR / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    update_readme_counts(counts, updated_at=updated_at, duplicates_removed=duplicates_removed)
    print(f'Published {len(nodes)} unique nodes (removed {duplicates_removed} duplicates) across {len(GROUPS)} subscriptions; Reality Vision: {counts["vless/reality-vision"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())

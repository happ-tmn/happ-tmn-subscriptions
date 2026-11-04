import base64
import json
import pathlib
import sys
import unittest
from urllib.parse import unquote

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import collector


class SubscriptionTests(unittest.TestCase):
    def test_vless_preserves_all_flags_and_sets_country(self):
        uri = ('vless://bb5c63ae-b5f1-414b-802c-625e8b761bf6@31.210.173.126:443?'
               'path=%2Fjx-aarup88tmqca66&security=tls&encryption=none&insecure=0&'
               'host=jyfrj1cims.dev.onappjet.com&type=ws&allowInsecure=0&'
               'sni=jyfrj1cims.dev.onappjet.com#%F0%9F%87%BA%F0%9F%87%B8%20United%20States')
        got = collector.normalize(uri)
        self.assertIsNotNone(got)
        self.assertEqual(got['line'].split('#')[0], uri.split('#')[0])
        self.assertEqual(unquote(got['line'].split('#')[1]), '🇺🇸 @happ_tmn')
        self.assertTrue(collector.in_group(got, 'vless/tls/ws'))
        self.assertFalse(collector.in_group(got, 'vless/reality-vision'))

    def test_reality_vision_strict_and_preserved(self):
        uri = ('vless://c0ffeeee-1111-2222-3333-444444444444@node.example:443?'
               'security=reality&encryption=none&flow=xtls-rprx-vision&'
               'sni=example.org&pbk=abcdef&sid=012345&fp=chrome&type=tcp#%F0%9F%87%B8%F0%9F%87%AC%20SG')
        got = collector.normalize(uri)
        self.assertEqual(got['line'].split('#')[0], uri.split('#')[0])
        self.assertTrue(collector.in_group(got, 'vless/reality'))
        self.assertTrue(collector.in_group(got, 'vless/reality-vision'))
        self.assertEqual(unquote(got['line'].split('#')[1]), '🇸🇬 @happ_tmn')
        not_vision = collector.normalize(uri.replace('flow=xtls-rprx-vision', 'flow='))
        self.assertFalse(collector.in_group(not_vision, 'vless/reality-vision'))

    def test_bad_port_does_not_crash_collector(self):
        self.assertIsNone(collector.normalize("vless://uuid@server.example:INVALID?security=tls#bad"))

    def test_dedup_ignores_old_label(self):
        a = collector.normalize('vless://u@1.2.3.4:443?security=tls#A')
        b = collector.normalize('vless://u@1.2.3.4:443?security=tls#B')
        self.assertEqual(a['key'], b['key'])

    def test_vmess_ps_only_changes(self):
        src = {'v': '2', 'ps': '🇩🇪 Germany 34', 'add': 'host.example', 'port': '443',
               'id': 'abc', 'aid': '0', 'net': 'ws', 'type': 'none', 'host': 'test.example',
               'path': '/abc?foo=bar', 'tls': 'tls', 'sni': 'sni.example', 'alpn': 'h2'}
        coded = 'vmess://' + base64.b64encode(json.dumps(src).encode('utf-8')).decode('ascii')
        got = collector.normalize(coded)
        self.assertIsNotNone(got)
        decoded = json.loads(collector.b64decode_utf8(got['line'][8:]))
        self.assertEqual(decoded['ps'], '🇩🇪 @happ_tmn')
        self.assertEqual({k:v for k,v in decoded.items() if k != 'ps'}, {k:v for k,v in src.items() if k != 'ps'})
        self.assertTrue(collector.in_group(got, 'vmess/tls/ws'))

    def test_ssr_keeps_parameters(self):
        src = 'example.org:443:origin:aes-256-cfb:plain:cGFzcw/?obfsparam=YWJj&remarks=' + collector.b64encode_utf8('🇯🇵 JP', padding=False) + '&group=Z3JvdXA'
        coded = 'ssr://' + collector.b64encode_utf8(src, padding=False)
        got = collector.normalize(coded)
        self.assertIsNotNone(got)
        decoded = collector.b64decode_utf8(got['line'][6:])
        self.assertIn('obfsparam=YWJj', decoded)
        self.assertIn('group=Z3JvdXA', decoded)
        self.assertIn('remarks=', decoded)
        self.assertIn('@happ_tmn', collector.b64decode_utf8(decoded.split('remarks=')[1].split('&')[0]))

    def test_base64_wrapper(self):
        lines = 'vless://u@host:443?security=tls#label\nss://abc@host:1234#label\n'
        text = collector.b64encode_utf8(lines)
        self.assertEqual(collector.extract_lines(text), lines.splitlines())

    def test_dedup_matches_reordered_params_and_encoding_but_preserves_flags(self):
        first = 'vless://id@NODE.example:443?path=%2Fa&security=reality&flow=xtls-rprx-vision&pbk=secret&sni=EXAMPLE.com#🇩🇪 old'
        second = 'vless://id@node.example:443?sni=example.com&pbk=secret&flow=xtls-rprx-vision&security=reality&path=/a#🇺🇸 new'
        a, b = collector.normalize(first), collector.normalize(second)
        self.assertEqual(a['key'], b['key'])
        self.assertEqual(a['line'].split('#')[0], first.split('#')[0])
        self.assertEqual(b['line'].split('#')[0], second.split('#')[0])

    def test_dedup_does_not_combine_different_connection_params(self):
        base = 'vless://uuid@host.example:443?security=reality&pbk=key1&sni=one.example&flow=xtls-rprx-vision'
        a = collector.normalize(base + '#one')
        for alternative in (
            base.replace('pbk=key1', 'pbk=key2'),
            base.replace('sni=one.example', 'sni=two.example'),
            base.replace(':443?', ':8443?'),
            base.replace('uuid@', 'other-uuid@'),
            base.replace('flow=xtls-rprx-vision', 'flow='),
        ):
            self.assertNotEqual(a['key'], collector.normalize(alternative + '#two')['key'])

    def test_readme_counts_replace_only_subscription_section(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            src = '# Intro\n\n## 📥 Выбери подписку\n\nOLD TABLE\n\n## 📲 Как подключить в Nekobox\n\nSECRET NO\n'
            (base/'README.md').write_text(src, encoding='utf-8')
            with patch.object(collector, 'BASE_DIR', base):
                self.assertTrue(collector.update_readme_counts({'all': 17, 'vless/reality-vision': 4}, updated_at='2026-11-04T17:00:00+00:00', duplicates_removed=3))
                self.assertTrue(collector.update_readme_counts({'all': 21, 'vless/reality-vision': 5}, updated_at='2026-11-04T20:00:00+00:00', duplicates_removed=7))
            output = (base/'README.md').read_text(encoding='utf-8')
            self.assertIn('**21**', output)
            self.assertIn('**5**', output)
            self.assertIn('**7**', output)
            self.assertEqual(output.count('<!-- HAPP_TMN_COUNTS_START -->'), 1)
            self.assertIn('SECRET NO', output)
            self.assertNotIn('OLD TABLE', output)

    def test_query_values_unchanged(self):
        uri = 'trojan://p@host.example:2053?security=tls&type=ws&path=%2Fpath%3Fa%3Db&sni=host.example#remark'
        obj = collector.normalize(uri)
        self.assertEqual(obj['line'].split('#')[0], uri.split('#')[0])


if __name__ == '__main__':
    unittest.main()

class LiveWorkflowLikeTests(unittest.TestCase):
    def test_writes_full_and_reality_vision_txt_without_sources(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            (root/'sub').mkdir()
            sources = ['https://donor.example/test']
            examples = [
                'vless://uuid@host.example:443?security=reality&flow=xtls-rprx-vision&pbk=123&sid=42&type=tcp#%F0%9F%87%B9%F0%9F%87%B7',
                'vless://uuid2@host.example:443?security=tls&type=ws&host=cdn.example#Europe',
                'trojan://secret@host.example:443?security=tls#SG',
            ]
            with patch.object(collector, 'BASE_DIR', root), patch.object(collector, 'OUTPUT_DIR', root/'sub'), patch.object(collector, 'source_urls', return_value=sources), patch.object(collector, 'download_source', return_value=examples):
                self.assertEqual(collector.run(), 0)
            text = (root/'sub/vless/reality-vision.txt').read_text()
            self.assertEqual(len(text.splitlines()), 1)
            self.assertIn('flow=xtls-rprx-vision&pbk=123&sid=42', text)
            self.assertIn('sub', str(root/'sub'))
            self.assertIn('%40happ_tmn', (root/'sub/all.txt').read_text())
            status = (root/'status.json').read_text()
            self.assertNotIn(sources[0], status)
            self.assertEqual(json.loads(status)['groups']['vless/reality-vision'], 1)

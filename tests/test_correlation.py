"""Contrato de correlação: referências sintéticas, sem prova de invasão."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from temporal import detect, parse_events
from test_temporal_window import ROOT, scenario_lines

CASES = json.loads(Path(__file__).with_name('correlation_scenarios.json').read_text(encoding='utf-8'))


class CorrelationTests(unittest.TestCase):
    def test_reference_scenarios(self):
        for case in CASES['cases']:
            with self.subTest(case=case['name']):
                case = dict(case)
                if 'actions' not in case:
                    case['actions'] = ['Failed password'] * (len(case['seconds']) - 1) + ['Accepted password']
                events, rejected = parse_events(scenario_lines(case), year=2026, offset='+00:00')
                self.assertEqual(rejected, [])
                alerts = detect(events, threshold=CASES['threshold'], window_seconds=CASES['window_seconds'],
                                login_window_seconds=case.get('login_window_seconds'))
                logins = [a for a in alerts if a.rule == 'success_after_failures']
                self.assertEqual([[e.line_number for e in a.evidence] for a in logins], case['expected_login_evidence'])
                if 'expected_brute_count' in case:
                    self.assertEqual(sum(a.rule == 'brute_force' for a in alerts), case['expected_brute_count'])
                for alert in logins:
                    self.assertEqual(alert.trigger.kind, 'success')
                    self.assertTrue(all((e.host, e.ip, e.user) == (alert.host, alert.ip, alert.trigger.user) for e in alert.evidence))

    def test_invalid_login_window(self):
        for value in [0, -1, 1.5, True]:
            with self.assertRaises(ValueError):
                detect([], login_window_seconds=value)

    def test_json_and_compatibility_command(self):
        with tempfile.TemporaryDirectory() as folder:
            outputs = []
            for script, options in [('soc_analyzer.py', ['--ano', '2026', '--fuso=-03:00']),
                                    ('temporal_analyzer.py', ['--year', '2026', '--utc-offset=-03:00'])]:
                path = Path(folder) / (script + '.json')
                command = [sys.executable, str(ROOT / script), *options, '--limite', '3', '--json', str(path)]
                result = subprocess.run(command, cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(path.read_text(encoding='utf-8'))
                # Saída de console e arquivo têm exatamente o mesmo objeto JSON.
                self.assertEqual(json.loads(result.stdout), payload)
                outputs.append(payload)
                original = path.read_bytes()
                repeated = subprocess.run(command, cwd=ROOT, capture_output=True)
                self.assertEqual(repeated.returncode, 2)
                self.assertEqual(path.read_bytes(), original)
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0]['schema_version'], '0.2')
            self.assertEqual(outputs[0]['parameters']['login_window_seconds'], 300)
            self.assertEqual(outputs[0]['events_count'], 26)
            self.assertEqual([a['rule'] for a in outputs[0]['alerts']],
                             ['brute_force', 'success_after_failures', 'brute_force'])
            login = outputs[0]['alerts'][1]
            self.assertEqual(login['user'], 'admin')
            self.assertEqual(login['trigger']['line_number'], 19)
            self.assertTrue(all(e['timestamp'].endswith('+00:00') for e in login['evidence']))

    def test_export_destinations_preserve_input_and_avoid_conflicts(self):
        command = [sys.executable, str(ROOT / 'soc_analyzer.py'), '--ano', '2026', '--fuso=+00:00']
        sample = ROOT / 'sample_logs/auth.log'
        original = sample.read_bytes()
        bad_input = subprocess.run(command + ['--json', str(sample)], cwd=ROOT, capture_output=True)
        self.assertEqual(bad_input.returncode, 2)
        self.assertEqual(sample.read_bytes(), original)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'same.txt'
            conflict = subprocess.run(command + ['--relatorio', str(target), '--json', str(target)], cwd=ROOT, capture_output=True)
            self.assertEqual(conflict.returncode, 2)
            self.assertFalse(target.exists())
            existing = Path(folder) / 'exists.json'
            existing.write_text('preservar', encoding='utf-8')
            conflict = subprocess.run(command + ['--relatorio', str(target), '--json', str(existing)], cwd=ROOT, capture_output=True)
            self.assertEqual(conflict.returncode, 2)
            self.assertFalse(target.exists())
            self.assertEqual(existing.read_text(encoding='utf-8'), 'preservar')
            success = subprocess.run(command + ['--limite', '3', '--relatorio', str(target), '--json', str(Path(folder) / 'new.json')], cwd=ROOT, capture_output=True)
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertIn('success_after_failures', target.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

"""Referências sintéticas de desenvolvimento; não são teste final de eficácia."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from temporal import detect, fixed_timezone, parse_events
from soc_analyzer import analisar

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = json.loads((Path(__file__).with_name('scenarios.json')).read_text(encoding='utf-8'))


def line(stamp='Nov 01 00:00:00', host='lab-a', ip='192.0.2.1', user='ana', action='Failed password'):
    return f'{stamp} {host} sshd[123]: {action} for {user} from {ip} port 50000 ssh2'


def scenario_lines(case):
    result = []
    for i, seconds in enumerate(case['seconds']):
        dt = datetime(2026, 11, 1) + timedelta(seconds=seconds)
        # Mês explícito: fixture independente do locale do sistema.
        stamp = f'Nov {dt.day:02} {dt.hour:02}:{dt.minute:02}:{dt.second:02}'
        options = {key: case[field][i] for key, field in
                   [('host', 'hosts'), ('ip', 'ips'), ('user', 'users'), ('action', 'actions')]
                   if field in case}
        result.append(line(stamp, **options))
    return result


class TemporalTests(unittest.TestCase):
    def parse(self, lines, **options):
        return parse_events(lines, year=options.pop('year', 2026), offset=options.pop('offset', '+00:00'), **options)

    def test_reference_scenarios(self):
        for case in SCENARIOS['cases']:
            with self.subTest(case=case['name']):
                events, rejected = self.parse(scenario_lines(case))
                alerts = detect(events, threshold=SCENARIOS['threshold'], window_seconds=SCENARIOS['window_seconds'])
                self.assertEqual(rejected, [])
                self.assertEqual([[e.line_number for e in a.evidence] for a in alerts], case['expected_evidence'])
                self.assertEqual([a.rule for a in alerts], case.get('expected_rules', ['brute_force'] * len(case['expected_evidence'])))
                for alert in alerts:
                    self.assertEqual(alert.timestamp, alert.trigger.timestamp)
                    self.assertLessEqual(alert.evidence[-1].timestamp, alert.timestamp)
                    self.assertEqual(alert.host, alert.evidence[-1].host)
                    self.assertEqual(alert.ip, alert.evidence[-1].ip)

    def test_configuration_changes_detection(self):
        events, _ = self.parse([line('Nov 01 00:00:00'), line('Nov 01 00:00:30'), line('Nov 01 00:01:01')])
        self.assertEqual(len(detect(events, threshold=3, window_seconds=60)), 0)
        self.assertEqual(len(detect(events, threshold=3, window_seconds=61)), 1)
        # Em t=61 a falha de t=0 expirou; a nova falha volta a atingir 2.
        self.assertEqual(len(detect(events, threshold=2, window_seconds=60)), 2)

    def test_baseline_counts_sparse_failures_as_suspicious(self):
        case = next(c for c in SCENARIOS['cases'] if c['name'] == 'falhas_esparsas')
        lines = scenario_lines(case)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.log'
            path.write_text('\n'.join(lines), encoding='utf-8')
            failures, _ = analisar(path, 3)
        self.assertEqual(failures['192.0.2.1']['total'], 3)
        events, _ = self.parse(lines)
        self.assertEqual(detect(events, threshold=3, window_seconds=60), [])

    def test_fixed_offset_and_source(self):
        raw = line()
        events, _ = self.parse([raw], offset='-03:00', source='synthetic.log')
        self.assertEqual(events[0].timestamp, datetime(2026, 11, 1, 3, tzinfo=timezone.utc))
        self.assertEqual((events[0].source, events[0].line_number, events[0].raw), ('synthetic.log', 1, raw))

    def test_rollover_opt_in(self):
        lines = [line('Dec 31 23:59:40'), line('Dec 31 23:59:50'), line('Jan 01 00:00:00')]
        events, rejected = self.parse(lines, rollover=True)
        self.assertEqual(rejected, [])
        self.assertEqual([e.timestamp.year for e in events], [2026, 2026, 2027])
        self.assertEqual(len(detect(events, threshold=3, window_seconds=20)), 1)
        same_year, _ = self.parse(lines)
        self.assertTrue(all(e.timestamp.year == 2026 for e in same_year))

    def test_invalid_and_unrecognized_lines_are_visible(self):
        events, rejected = self.parse(['noise', line('Feb 30 00:00:00'), line(ip='999.1.1.1'), line('Xxx 01 00:00:00'), line()])
        self.assertEqual([e.line_number for e in events], [5])
        self.assertEqual([r.line_number for r in rejected], [1, 2, 3, 4])

    def test_leap_day(self):
        self.assertEqual(len(self.parse([line('Feb 29 00:00:00')], year=2024)[0]), 1)
        self.assertEqual(len(self.parse([line('Feb 29 00:00:00')], year=2026)[1]), 1)

    def test_invalid_line_does_not_advance_year(self):
        events, rejected = self.parse([line('Dec 31 23:59:59'), line('Jan 01 00:00:00', ip='invalid'), line('Jan 01 00:00:01')], rollover=True)
        self.assertEqual(events[-1].timestamp.year, 2027)
        self.assertEqual(len(rejected), 1)

    def test_ipv6_and_invalid_user(self):
        events, rejected = self.parse([line(ip='2001:db8::1', user='invalid user root')])
        self.assertEqual(rejected, [])
        self.assertEqual((events[0].ip, events[0].user), ('2001:db8::1', 'root'))

    def test_empty(self):
        self.assertEqual(self.parse([]), ([], []))
        self.assertEqual(detect([]), [])

    def test_invalid_configuration(self):
        for threshold, window in [(0, 60), (-1, 60), (3, 0), (3, -1)]:
            with self.assertRaises(ValueError):
                detect([], threshold=threshold, window_seconds=window)
        for offset in ['UTC', '+24:00', '+03:60', '03:00']:
            with self.assertRaises(ValueError):
                fixed_timezone(offset)
        with self.assertRaises(ValueError):
            self.parse([], year=0)

    def test_cli_sample_and_missing_year(self):
        command = [sys.executable, str(ROOT / 'soc_analyzer.py')]
        result = subprocess.run(command + ['--ano', '2026', '--fuso=-03:00', '--janela', '300'], cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'alertas: 2', result.stdout)
        self.assertIn(b'linhas rejeitadas: 0', result.stdout)
        missing = subprocess.run(command, cwd=ROOT, capture_output=True)
        self.assertEqual(missing.returncode, 2)

    def test_cli_report_preserves_existing_files(self):
        command = [sys.executable, str(ROOT / 'soc_analyzer.py'), '--ano', '2026', '--fuso=+00:00']
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'report.txt'
            result = subprocess.run(command + ['--relatorio', str(target)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            contents = target.read_bytes()
            repeated = subprocess.run(command + ['--relatorio', str(target)], cwd=ROOT, capture_output=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(target.read_bytes(), contents)
            sample = ROOT / 'sample_logs/auth.log'
            original = sample.read_bytes()
            same_file = subprocess.run(command + ['--relatorio', str(sample)], cwd=ROOT, capture_output=True)
            self.assertEqual(same_file.returncode, 2)
            self.assertEqual(sample.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()

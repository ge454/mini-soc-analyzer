"""Análise offline SSH/syslog. Não executa nem acessa os hosts dos eventos."""

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
import json
from pathlib import Path
import re
import sys


MONTHS = {name: i for i, name in enumerate(
    'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), 1)}
LINE = re.compile(
    r'^(?P<month>[A-Z][a-z]{2})\s+(?P<day>\d{1,2}) '
    r'(?P<clock>\d{2}:\d{2}:\d{2})\s+(?P<host>\S+) '
    r'sshd\[\d+\]: (?P<action>Failed password|Accepted password|Accepted publickey) '
    r'for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+) port \d+\b.*$'
)


@dataclass(frozen=True)
class Event:
    timestamp: datetime  # sempre aware, em UTC
    host: str
    ip: str
    user: str
    kind: str  # failure | success
    source: str
    line_number: int
    raw: str


@dataclass(frozen=True)
class RejectedLine:
    line_number: int
    reason: str
    raw: str


@dataclass(frozen=True)
class Alert:
    host: str
    ip: str
    timestamp: datetime
    evidence: tuple[Event, ...]
    rule: str = 'brute_force'
    trigger: Event | None = None


def fixed_timezone(value):
    """Offset explícito: não consulta relógio/fuso do computador."""
    if not re.fullmatch(r'[+-](?:[01]\d|2[0-3]):[0-5]\d', value):
        raise ValueError('fuso deve usar +HH:MM ou -HH:MM')
    minutes = int(value[1:3]) * 60 + int(value[4:])
    return timezone(timedelta(minutes=minutes if value[0] == '+' else -minutes))


def parse_events(lines, *, year, offset, source='<memory>', rollover=False):
    """Ano inicial explícito; virada opcional exige ordem Dez->Jan no arquivo.

    Rejeições de conteúdo são observáveis; configuração inválida falha a execução.
    Sem virada, todos os eventos pertencem ao ano informado e podem vir fora de ordem.
    """
    if not 1 <= year <= 9999:
        raise ValueError('ano deve estar entre 1 e 9999')
    tz = fixed_timezone(offset)
    events, rejected = [], []
    current_year, previous_month = year, None
    for number, raw in enumerate(lines, 1):
        raw = raw.rstrip('\r\n')
        match = LINE.fullmatch(raw)
        if not match:
            rejected.append(RejectedLine(number, 'formato não suportado', raw))
            continue
        try:
            month = MONTHS[match['month']]
            candidate_year = current_year
            if rollover and previous_month == 12 and month == 1:
                candidate_year += 1
            hour, minute, second = map(int, match['clock'].split(':'))
            stamp = datetime(candidate_year, month, int(match['day']), hour,
                             minute, second, tzinfo=tz).astimezone(timezone.utc)
            ip = str(ip_address(match['ip']))
        except (ValueError, KeyError, OverflowError):
            rejected.append(RejectedLine(number, 'data ou IP inválido', raw))
            continue
        current_year, previous_month = candidate_year, month
        events.append(Event(stamp, match['host'], ip, match['user'],
                            'failure' if match['action'].startswith('Failed') else 'success',
                            source, number, raw))
    return sorted(events, key=lambda e: (e.timestamp, e.line_number)), rejected


def detect(events, *, threshold=5, window_seconds=300, login_window_seconds=None):
    """Falhas por host/IP; sucesso exige limiar por host/IP/usuário.

    Janelas inclusivas. Empates seguem a linha original. Cada sucesso elegível
    gera correlação; sucesso não apaga nem consome falhas.
    """
    if type(threshold) is not int or threshold <= 0:
        raise ValueError('limite deve ser inteiro positivo')
    if type(window_seconds) is not int or window_seconds <= 0:
        raise ValueError('janela deve ser inteiro positivo em segundos')
    if login_window_seconds is None:
        login_window_seconds = window_seconds
    if type(login_window_seconds) is not int or login_window_seconds <= 0:
        raise ValueError('janela de login deve ser inteiro positivo em segundos')
    window = timedelta(seconds=window_seconds)
    login_window = timedelta(seconds=login_window_seconds)
    queues = defaultdict(deque)
    login_queues = defaultdict(deque)
    alerts = []
    for event in sorted(events, key=lambda e: (e.timestamp, e.line_number)):
        if event.kind not in ('failure', 'success'):
            raise ValueError(f'tipo de evento desconhecido: {event.kind}')
        login_queue = login_queues[event.host, event.ip, event.user]
        while login_queue and login_queue[0].timestamp < event.timestamp - login_window:
            login_queue.popleft()
        if event.kind == 'success':
            if len(login_queue) >= threshold:
                alerts.append(Alert(event.host, event.ip, event.timestamp,
                                    tuple(login_queue), 'success_after_failures', event))
            continue
        login_queue.append(event)
        queue = queues[event.host, event.ip]
        while queue and queue[0].timestamp < event.timestamp - window:
            queue.popleft()
        was_below = len(queue) < threshold
        queue.append(event)
        if was_below and len(queue) >= threshold:
            alerts.append(Alert(event.host, event.ip, event.timestamp, tuple(queue), trigger=event))
    return alerts


def report(events, rejected, alerts, *, year, offset, rollover, threshold, window_seconds, login_window_seconds=None):
    login_window_seconds = window_seconds if login_window_seconds is None else login_window_seconds
    text = ['=== MINI SOC ANALYZER v2 ===',
            f'Ano inicial assumido: {year}; offset assumido: {offset}; virada: {rollover}',
            f'Regra: >= {threshold} falhas por host/IP em {window_seconds}s (bordas inclusivas)',
            f'Login posterior: >= {threshold} falhas do mesmo host/IP/usuário em {login_window_seconds}s',
            f'Eventos: {len(events)}; linhas rejeitadas: {len(rejected)}; alertas: {len(alerts)}',
            'Alertas indicam suspeita; não comprovam comprometimento.']
    for alert in alerts:
        text.append(f'[SUSPEITA:{alert.rule}] {alert.host} {alert.ip} em {alert.timestamp.isoformat()}')
        if alert.rule == 'success_after_failures':
            text.append(f'  Login após falhas para {alert.trigger.user}; investigar.')
        text.append(f'  Motivo: {len(alert.evidence)} falhas na janela da regra; usuários: '
                    + ', '.join(sorted({e.user for e in alert.evidence})))
        for event in alert.evidence:
            text.append(f'  {event.source}:{event.line_number}: {event.raw}')
        if alert.rule == 'success_after_failures':
            event = alert.trigger
            text.append(f'  Login: {event.source}:{event.line_number}: {event.raw}')
    for item in rejected:
        text.append(f'[REJEITADA] linha {item.line_number}: {item.reason}: {item.raw}')
    return '\n'.join(text)


def json_report(events, rejected, alerts, *, source, year, offset, rollover,
                threshold, window_seconds, login_window_seconds=None):
    """Esquema 0.2: evidências e parâmetros, sem linha do tempo completa."""
    def reference(event):
        return {'source': event.source, 'line_number': event.line_number,
                'timestamp': event.timestamp.isoformat(), 'host': event.host,
                'ip': event.ip, 'user': event.user, 'kind': event.kind, 'raw': event.raw}

    return {
        'schema_version': '0.2', 'source': source,
        'parameters': {'initial_year': year, 'assumed_utc_offset': offset,
                       'allow_year_rollover': rollover, 'threshold': threshold,
                       'window_seconds': window_seconds,
                       'login_window_seconds': window_seconds if login_window_seconds is None else login_window_seconds},
        'events_count': len(events),
        'rejected_lines': [{'line_number': r.line_number, 'reason': r.reason, 'raw': r.raw} for r in rejected],
        'alerts': [{'rule': a.rule, 'timestamp': a.timestamp.isoformat(),
                    'host': a.host, 'ip': a.ip,
                    'user': a.trigger.user if a.rule == 'success_after_failures' else None,
                    'reason': ('login após falhas do mesmo host/IP/usuário; investigar'
                               if a.rule == 'success_after_failures' else 'limiar de falhas por host/IP na janela'),
                    'failure_count': len(a.evidence),
                    'evidence': [reference(e) for e in a.evidence],
                    'trigger': reference(a.trigger)} for a in alerts],
        'limitation': 'Alertas indicam suspeita; não comprovam comprometimento.'}


def main():
    parser = argparse.ArgumentParser(description='Detecção temporal offline de falhas SSH/syslog.')
    parser.add_argument('--log', default='sample_logs/auth.log')
    parser.add_argument('--ano', '--year', required=True, type=int, help='ano inicial do arquivo, sem inferência do relógio')
    parser.add_argument('--fuso', '--utc-offset', required=True, help='offset fixo do log; ex.: --fuso=-03:00')
    parser.add_argument('--virada-ano', '--allow-year-rollover', action='store_true', help='inferir Dez->Jan em arquivo ordenado entre anos')
    parser.add_argument('--limite', type=int, default=5)
    parser.add_argument('--janela', type=int, default=300, help='segundos, inteiro positivo')
    parser.add_argument('--janela-login', type=int, help='segundos para correlação; padrão: mesmo valor de --janela')
    parser.add_argument('--relatorio')
    parser.add_argument('--json', dest='json_path', help='salvar JSON em arquivo novo; também mostrar JSON na saída')
    args = parser.parse_args()
    try:
        with open(args.log, encoding='utf-8', errors='strict') as stream:
            events, rejected = parse_events(stream, year=args.ano, offset=args.fuso,
                                            source=args.log, rollover=args.virada_ano)
        config = dict(year=args.ano, offset=args.fuso, rollover=args.virada_ano,
                      threshold=args.limite, window_seconds=args.janela,
                      login_window_seconds=args.janela_login)
        alerts = detect(events, threshold=args.limite, window_seconds=args.janela,
                        login_window_seconds=args.janela_login)
        text = report(events, rejected, alerts, **config)
        output = json.dumps(json_report(events, rejected, alerts, source=args.log, **config),
                            ensure_ascii=False, indent=2) if args.json_path else text
        # Confira todos os destinos antes de criar qualquer um.
        destinations = [Path(p).resolve() for p in (args.relatorio, args.json_path) if p]
        if len(destinations) != len(set(destinations)):
            raise ValueError('relatório e JSON devem ter destinos diferentes')
        for destination in destinations:
            if destination == Path(args.log).resolve():
                raise ValueError('saída não pode sobrescrever o log de entrada')
            if destination.exists():
                raise ValueError(f'arquivo de saída já existe: {destination}')
        if args.relatorio:
            with open(args.relatorio, 'x', encoding='utf-8') as target:
                target.write(text + '\n')
        if args.json_path:
            with open(args.json_path, 'x', encoding='utf-8') as target:
                target.write(output + '\n')
    except (OSError, ValueError, OverflowError) as error:
        parser.error(str(error))
    if args.json_path and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

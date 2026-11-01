"""Gera um log de autenticação SSH FICTÍCIO para testar o Mini SOC Analyzer.

Todos os IPs são de faixas reservadas para documentação (RFC 5737),
então não pertencem a ninguém de verdade.
"""

import os
import random
from datetime import datetime, timedelta

random.seed(42)  # mesma saída toda vez que rodar

ATACANTE_1 = "203.0.113.45"   # força bruta e depois consegue entrar
ATACANTE_2 = "198.51.100.23"  # força bruta que não consegue entrar
USUARIO_OK = "192.0.2.10"     # usuário legítimo
USUARIO_ERRO = "192.0.2.11"   # usuário legítimo que errou a senha duas vezes

eventos = []


def ts(dt):
    return dt.strftime("%b %d %H:%M:%S")


def pid():
    return random.randint(1000, 9999)


def porta():
    return random.randint(40000, 60000)


def falha(dt, ip, user, invalido=True):
    prefixo = "invalid user " if invalido else ""
    eventos.append((dt, f"{ts(dt)} servidor sshd[{pid()}]: Failed password for {prefixo}{user} from {ip} port {porta()} ssh2"))


def sucesso(dt, ip, user):
    eventos.append((dt, f"{ts(dt)} servidor sshd[{pid()}]: Accepted password for {user} from {ip} port {porta()} ssh2"))


inicio = datetime(2026, 11, 1, 8, 0, 0)

# Usuário legítimo entra normalmente
sucesso(inicio + timedelta(minutes=5), USUARIO_OK, "geovani")

# Usuário legítimo erra a senha duas vezes e depois acerta
falha(inicio + timedelta(minutes=20), USUARIO_ERRO, "maria", invalido=False)
falha(inicio + timedelta(minutes=20, seconds=15), USUARIO_ERRO, "maria", invalido=False)
sucesso(inicio + timedelta(minutes=20, seconds=40), USUARIO_ERRO, "maria")

# Atacante 1: 14 tentativas em cerca de 2 minutos e depois entra como admin
alvos = ["admin", "root", "test", "oracle", "ubuntu"]
for i in range(14):
    falha(inicio + timedelta(minutes=45, seconds=i * 9), ATACANTE_1, random.choice(alvos))
sucesso(inicio + timedelta(minutes=47, seconds=10), ATACANTE_1, "admin")

# Atacante 2: 7 tentativas, sem sucesso
for i in range(7):
    falha(inicio + timedelta(hours=2, seconds=i * 20), ATACANTE_2, random.choice(alvos))

eventos.sort(key=lambda e: e[0])

os.makedirs("sample_logs", exist_ok=True)
with open("sample_logs/auth.log", "w", encoding="utf-8") as f:
    f.write("\n".join(linha for _, linha in eventos) + "\n")

print(f"Log de exemplo criado em sample_logs/auth.log ({len(eventos)} linhas)")
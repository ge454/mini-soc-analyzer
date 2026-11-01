"""Mini SOC Analyzer
Analisa logs de autenticação SSH e detecta possíveis ataques de força bruta.
"""

import argparse
import re

# Linha de falha: "... sshd[...]: Failed password for [invalid user] USER from IP port ..."
FALHA_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d{1,2}\s[\d:]{8}).*sshd.*"
    r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"
)
# Linha de sucesso: "... sshd[...]: Accepted password for USER from IP port ..."
SUCESSO_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d{1,2}\s[\d:]{8}).*sshd.*"
    r"Accepted \w+ for (?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"
)


def analisar(caminho, limite):
    """Lê o log e devolve (falhas por IP, logins bem-sucedidos após muitas falhas)."""
    falhas = {}
    comprometimentos = []

    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        for linha in arquivo:
            m = FALHA_RE.search(linha)
            if m:
                dados = falhas.setdefault(
                    m["ip"], {"total": 0, "usuarios": set(), "primeira": m["ts"], "ultima": m["ts"]}
                )
                dados["total"] += 1
                dados["usuarios"].add(m["user"])
                dados["ultima"] = m["ts"]
                continue

            m = SUCESSO_RE.search(linha)
            if m and m["ip"] in falhas and falhas[m["ip"]]["total"] >= limite:
                comprometimentos.append(
                    {"ip": m["ip"], "usuario": m["user"], "hora": m["ts"], "falhas_antes": falhas[m["ip"]]["total"]}
                )

    return falhas, comprometimentos


def severidade(total, limite, ip, ips_comprometidos):
    if ip in ips_comprometidos:
        return "CRITICA"
    if total >= limite * 3:
        return "ALTA"
    return "MEDIA"


def montar_relatorio(falhas, comprometimentos, limite):
    ips_comprometidos = {c["ip"] for c in comprometimentos}
    suspeitos = {ip: d for ip, d in falhas.items() if d["total"] >= limite}

    linhas = ["=== MINI SOC ANALYZER ===", ""]
    linhas.append(f"IPs com falhas de login: {len(falhas)}")
    linhas.append(f"IPs suspeitos (>= {limite} falhas): {len(suspeitos)}")
    linhas.append("")

    if not suspeitos:
        linhas.append("Nenhuma atividade suspeita encontrada.")
        return "\n".join(linhas)

    linhas.append("--- Suspeitos (do mais ativo para o menos ativo) ---")
    for ip, d in sorted(suspeitos.items(), key=lambda x: x[1]["total"], reverse=True):
        sev = severidade(d["total"], limite, ip, ips_comprometidos)
        linhas.append(f"[{sev}] {ip}")
        linhas.append(f"    tentativas: {d['total']} | de {d['primeira']} ate {d['ultima']}")
        linhas.append(f"    usuarios testados: {', '.join(sorted(d['usuarios']))}")

    if comprometimentos:
        linhas.append("")
        linhas.append("--- ALERTA: login bem-sucedido apos varias falhas ---")
        for c in comprometimentos:
            linhas.append(
                f"{c['ip']} entrou como '{c['usuario']}' as {c['hora']} "
                f"depois de {c['falhas_antes']} falhas. Investigar."
            )

    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(description="Detecta tentativas de força bruta em logs SSH.")
    parser.add_argument("--log", default="sample_logs/auth.log", help="caminho do arquivo de log")
    parser.add_argument("--limite", type=int, default=5, help="falhas por IP para considerar suspeito")
    parser.add_argument("--relatorio", help="salva o relatório neste arquivo de texto")
    args = parser.parse_args()

    falhas, comprometimentos = analisar(args.log, args.limite)
    texto = montar_relatorio(falhas, comprometimentos, args.limite)
    print(texto)

    if args.relatorio:
        with open(args.relatorio, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
        print(f"\nRelatorio salvo em {args.relatorio}")


if __name__ == "__main__":
    main()

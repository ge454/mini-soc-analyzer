# Mini SOC Analyzer

> **Evolução v2 em andamento:** acompanhe o [checklist do projeto](CHECKLIST.md)
> e os [comandos atuais da v2](README-v2.md). O conteúdo abaixo descreve a versão
> inicial acumulada; para a CLI atual, use os parâmetros de ano e fuso da v2.

Ferramenta em Python que analisa logs de autenticação SSH e detecta possíveis
ataques de força bruta. Projeto de estudo, feito para praticar análise de
eventos de segurança (visão de SOC / blue team).

## O que ela faz

- Lê um log de autenticação SSH (formato syslog do Linux)
- Conta as falhas de login por IP
- Marca como suspeito o IP que atinge um limite de falhas (padrão: 5)
- Lista os usuários testados por cada IP suspeito
- Classifica a severidade: **MÉDIA**, **ALTA** (3x o limite) ou **CRÍTICA**
- Alerta quando um IP **consegue entrar depois de várias falhas**, sinal de
  possível invasão
- Salva o relatório em arquivo de texto, se pedido

## Como usar

Requer Python 3. Não tem dependências externas.

```bash
# 1. Gere um log de exemplo (dados fictícios)
python geradorlog.py

# 2. Analise o log
python soc_analyzer.py

# Opções
python soc_analyzer.py --log caminho/do/auth.log --limite 10
python soc_analyzer.py --relatorio relatorio.txt
```

## Exemplo de saída

```text
=== MINI SOC ANALYZER ===

IPs com falhas de login: 3
IPs suspeitos (>= 5 falhas): 2

--- Suspeitos (do mais ativo para o menos ativo) ---
[CRITICA] 203.0.113.45
    tentativas: 14 | de Nov 01 08:45:00 ate Nov 01 08:46:57
    usuarios testados: admin, oracle, root, test, ubuntu
[MEDIA] 198.51.100.23
    tentativas: 7 | de Nov 01 10:00:00 ate Nov 01 10:02:00
    usuarios testados: admin, oracle, root, test

--- ALERTA: login bem-sucedido apos varias falhas ---
203.0.113.45 entrou como 'admin' as Nov 01 08:47:10 depois de 14 falhas. Investigar.
```

## Como funciona

1. Expressões regulares extraem hora, usuário e IP de cada linha do log.
2. Um dicionário guarda, por IP, o total de falhas, os usuários testados e o
   intervalo de tempo.
3. IPs acima do limite são listados como suspeitos e ordenados por atividade.
4. Se um IP suspeito aparece depois com login aceito, o alerta crítico é gerado.

## Estrutura

```text
mini-soc-analyzer/
├── soc_analyzer.py      # analisador
├── geradorlog.py        # gera o log de exemplo
└── sample_logs/
    └── auth.log         # log fictício
```

Os IPs do exemplo pertencem às faixas reservadas para documentação (RFC 5737)
e não representam sistemas reais.

## Limitações

- Só reconhece mensagens do `sshd` em formato syslog
- Não considera janela de tempo (10 falhas em 1 minuto e em 1 dia contam igual)
- O log não traz o ano, então só mostra data e hora como estão no arquivo

## Próximos passos

- [ ] Janela de tempo para detectar rajadas de tentativas
- [ ] Testes automáticos
- [ ] Gráfico dos IPs mais ativos
- [ ] Suporte a outros tipos de log

## Aviso

Projeto educacional. Use apenas com logs de sistemas seus ou com autorização.

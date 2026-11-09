# Contrato unificado: datas e detecção temporal

Atualizado em 08/11/2026 após conciliação das variantes. Núcleo: `temporal.py`.
Comandos e acompanhamento: [README-v2](../README-v2.md) e [checklist](../CHECKLIST.md).

- Dados exclusivamente sintéticos nos testes; casos de desenvolvimento, sem conjunto final independente. Aceitação desta etapa: todos os casos abaixo passam. Não medir eficácia em produção.
- Entrada: syslog tradicional com mês em inglês, host, `sshd[PID]`, falha por senha ou sucesso por senha/chave. IPv4/IPv6 validados. Cada evento preserva número e conteúdo da linha.
- Ano inicial e deslocamento UTC fixo são obrigatórios. Não consultar o relógio do computador. Deslocamento informado é uma hipótese do operador, não evidência do log; horário de verão não é inferido.
- Sem virada, eventos recebem o ano informado e são ordenados por timestamp, com desempate pela linha. Dezembro → janeiro só avança o ano com opção explícita; esse modo exige arquivo ordenado entre anos. Não é possível inferir anos de arquivos misturados com segurança. Sem a opção, não há inferência de virada.
- Janela inclusiva `[t - janela, t]`, em segundos positivos; limite inteiro positivo. Eventos empatados seguem a ordem das linhas. Duplicatas contam: não há identificador confiável para deduplicação.
- Força bruta: falhas agrupadas por `(host, IP)`; emitir alerta ao cruzar o limite. Novo alerta só após o total cair abaixo do limite. Evidência contém as linhas da janela que disparou o alerta.
- Login posterior: mesmo host, IP **e usuário**, com pelo menos o limite de falhas ainda na janela do sucesso. `--janela-login` é independente; se omitida, usa `--janela`. Uma falha de outro usuário não sustenta essa correlação. Cada sucesso elegível gera alerta. Sucesso não apaga falhas. O limiar é o mesmo configurado por `--limite`.
- Linhas não reconhecidas ou com IP/data inválidos são contabilizadas e referenciadas; não alteram a inferência do ano. Relatório informa rejeições e evidências originais. UTF-8 inválido interrompe a leitura.
- Alertas indicam necessidade de investigação; não comprovam invasão. Tráfego lento, distribuído e falhas de outros métodos ficam fora desta etapa.

## Casos e resultados esperados

Com limite 3 e janela 60 s, salvo indicação contrária:

| Caso | Esperado |
|---|---|
| Duas falhas | Sem alerta |
| Falhas em 0, 30 e 60 s | Um alerta de força bruta |
| Falhas em 0, 30 e 61 s | Sem alerta |
| Três falhas espaçadas por 61 s | Sem alerta temporal; baseline acumulada marca suspeito |
| Três usuários no mesmo host/IP | Um alerta de força bruta |
| IPs ou hosts diferentes | Não somar grupos |
| Sucesso do mesmo usuário após três falhas | Força bruta e login posterior |
| Sucesso de outro usuário | Só força bruta |
| Sucesso 61 s após a última falha | Só força bruta |
| Sucesso antes das falhas | Só força bruta |
| Rajada contínua e segunda rajada após expiração | Dois alertas de força bruta |
| Dezembro/janeiro autorizado | Datas em anos consecutivos |
| Sem opção de virada | Todos os eventos no ano informado |
| Evento fora de ordem dentro do ano | Ordenação por timestamp e linha |
| Data impossível, IP inválido, linha desconhecida | Rejeição com referência da linha |
| Ano bissexto, IPv6 e empate de horários | Parsing válido e ordem das linhas preservada |
| Limite/janela inválidos | Erro explícito |

Referências oficiais consultadas: [datetime](https://docs.python.org/3.14/library/datetime.html) e [ipaddress](https://docs.python.org/3.14/library/ipaddress.html). Sem dependências externas.

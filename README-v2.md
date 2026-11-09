# Mini SOC Analyzer v2 — base unificada e correlação

Detecção offline de rajadas de falhas SSH e login posterior com janelas configuráveis.
**Acompanhe o progresso e as pendências em [CHECKLIST.md](CHECKLIST.md).**
O README original foi preservado, inclusive sua edição local; ele descreve a versão
acumulada. Este documento descreve a execução atual da CLI.

## Reproduzir

Python 3.14.3 foi usado na validação. Somente biblioteca padrão; sem instalação de
pacotes e sem acesso à rede durante análise/testes. Execute na raiz deste checkout:

```console
python soc_analyzer.py --log sample_logs/auth.log --ano 2026 --fuso=-03:00 --limite 5 --janela 300
python soc_analyzer.py --ano 2026 --fuso=-03:00 --relatorio relatorio-v2.txt
python soc_analyzer.py --ano 2026 --fuso=-03:00 --limite 3 --janela 300 --janela-login 300 --json resultado-v2.json
python -m unittest discover -s tests -v
```

`--janela` é um inteiro positivo em segundos; `--limite` também deve ser positivo.
Ano e offset são obrigatórios. Use `--fuso=-03:00` com sinal de igualdade.
O arquivo de relatório deve ser novo: a CLI recusa sobrescrever arquivos existentes
ou o log de entrada.
Não execute o gerador para reproduzir os testes: os cenários são determinísticos
e não sobrescrevem o log existente.

## Evento normalizado e política de datas

| Campo | Conteúdo |
|---|---|
| timestamp | datetime com fuso, normalizado em UTC; saída ISO 8601 |
| host | nome presente no cabeçalho syslog |
| ip | IPv4/IPv6 validado e normalizado por ipaddress |
| user | usuário extraído, sem o prefixo `invalid user` |
| kind | `failure` ou `success` |
| source | caminho informado, sem resolução ou leitura de outros arquivos |
| line_number | número da linha original, começando em 1 |
| raw | linha original sem terminador, preservada como evidência |

O formato aceito é `Nov 01 08:45:00 servidor sshd[123]: Failed password for
invalid user root from 192.0.2.1 port 50000 ssh2`. Reconhece falhas de senha e
sucessos `password`/`publickey`. Outros formatos são rejeitados de forma visível.
Meses usam abreviações em inglês explícitas, independentemente do locale do Windows.
Datas impossíveis e IPs inválidos são rejeitados; UTF-8 inválido interrompe a execução.

Ano e offset são **suposições fornecidas pelo operador**, registrados no relatório.
Não se usa o relógio, a data de modificação do arquivo ou o fuso do computador.
Um offset fixo evita dependência de uma base de fusos no Windows, mas não representa
mudanças de horário de verão. A conversão UTC pode mudar dia e ano do evento.

Sem `--virada-ano`, todos os eventos recebem o mesmo ano informado; eventos fora
de ordem são ordenados por timestamp e, nos empates, pela linha original.
Se o arquivo cruza anos, forneça `--ano` para o primeiro ano e `--virada-ano`:
uma transição Dez->Jan entre eventos válidos incrementa o ano. Esse modo exige
arquivo em ordem cronológica entre anos. Misturar arquivos/hosts fora de ordem
perto da virada pode produzir anos errados. A política não consegue distinguir
rotação, lacunas de anos e desordem: separe e confira esses arquivos previamente.

## Regra temporal e evidências

Cada par `(host, IP)` tem uma fila de falhas. Ao chegar uma falha em `t`, removem-se
as anteriores a `t - janela`. A borda é inclusiva: com janela de 60s, falhas em
0, 30 e 60 atingem limite 3; em 0, 30 e 61 não atingem.

Emite um alerta quando a contagem passa de abaixo do limite para o limite. Falhas
adicionais enquanto a contagem permanece acima não repetem o alerta. Após expiração
reduzir a contagem, outra subida pode emitir novo alerta, inclusive com parte das
mesmas evidências. O alerta registra as falhas presentes **no momento do disparo**,
não o pico nem todo o episódio. O relatório mostra motivo, usuários e linhas de origem.

Sucessos não entram na contagem nem apagam as falhas. A regra `success_after_failures`
exige pelo menos `--limite` falhas do **mesmo host/IP/usuário** na janela do login.
`--janela-login` usa `--janela` quando omitida; ambas têm bordas inclusivas. Cada
sucesso elegível gera um alerta com as falhas e a linha do login. Empates seguem
a ordem original das linhas; um sucesso anterior não usa falhas futuras.
O alerta indica "login após falhas; investigar", sem comprovar comprometimento.
O código acumulado em `soc_analyzer.analisar` permanece como baseline; seu antigo
relatório e sua função `main_baseline` não representam a regra temporal.

## Cenários de referência

`tests/scenarios.json` identifica os dados como sintéticos e fixa entradas, parâmetros
e linhas esperadas de evidência. As entradas são deslocamentos em segundos a partir
de 01/11/2026 00:00:00; o teste constrói linhas syslog determinísticas. Os IPs de
exemplo são de documentação. É um conjunto de desenvolvimento, sem teste final
independente nem validação de eficácia em produção.

| Cenário (limite 3, janela 60s) | Alertas esperados |
|---|---:|
| Benigno com duas falhas | 0 |
| Falhas esparsas em 0, 61, 122s | 0 |
| Rajada / vários usuários / borda inclusiva | 1 por cenário |
| Terceira falha fora por um segundo | 0 |
| Eventos fora de ordem | 1, com referências na ordem temporal |
| IPs separados / hosts separados | 0 por cenário |
| Rajada contínua | 1 |
| Segunda rajada após expiração | 2 |
| Duas falhas e um sucesso | 0 |
| Rajada do mesmo usuário seguida de sucesso | 1 alerta de falhas e 1 correlação |
| Três falhas no mesmo instante | 1 |

Outros testes cobrem offset, virada de ano, ano bissexto, IPv6, rejeições,
configurações inválidas, arquivo vazio, CLI e comparação com o baseline.
`tests/correlation_scenarios.json` acrescenta 13 cenários de correlação: identidade,
expiração, empates, ordem, janelas independentes e sucessos repetidos. A suíte atual
tem 17 métodos, incluindo os 27 cenários sintéticos dos dois arquivos JSON.
No caso esparso, o baseline soma 3 e classifica o IP como suspeito; a regra temporal
não alerta com limite 3/60s. Isso demonstra uma diferença de comportamento no
laboratório, sem estimar taxa de falsos positivos no mundo real.

## Limitações e próximo marco

- Todo o arquivo é carregado e ordenado: custo O(n log n), memória O(n).
  Ainda não houve medição de desempenho nem teste de volume.
- Não há deduplicação: linhas duplicadas contam como eventos distintos.
- Mensagens não suportadas aparecem como rejeitadas, inclusive mensagens benignas
  do sshd; rejeição não significa evento malicioso.
- Offset único por arquivo; não suporta mudanças de fuso, leap seconds ou ISO/syslog
  com ano explícito. Hosts sem identificação no cabeçalho não são aceitos.
- A regra pode alertar erros legítimos repetidos e perder tentativas lentas ou
  distribuídas entre IPs. Não comprova ataque nem comprometimento.
- Pendente: linha do tempo completa, CSV, avaliação independente, desempenho e
  preparação de release. Veja o checklist para acompanhar esses itens.
- Nenhuma IA/modelo/API nesta etapa; a referência determinística é o próprio baseline.

Base técnica consultada: documentação oficial Python
[datetime](https://docs.python.org/3.14/library/datetime.html),
[deque](https://docs.python.org/3.14/library/collections.html#collections.deque).

## JSON e compatibilidade

`--json arquivo-novo.json` grava JSON e mostra o mesmo objeto na saída padrão em
UTF-8. Com `--relatorio`, também pode salvar texto em um destino diferente. A CLI
recusa destinos iguais, existentes ou que coincidam com a entrada. Falhas de escrita
por falta de permissão ou espaço ainda podem deixar uma saída parcial; não há
transação entre dois arquivos de saída.

O esquema `0.2` registra parâmetros, quantidade de eventos, rejeições e alertas.
Cada alerta inclui regra, motivo, horário UTC, host/IP, usuário na correlação,
quantidade de falhas, evidências com conteúdo original e evento disparador.
Ainda não contém todos os eventos da linha do tempo. É um esquema em desenvolvimento,
com mudanças em relação à variante anterior `0.1`.

`soc_analyzer.py`, `temporal.py` e `temporal_analyzer.py` usam o mesmo núcleo.
O último é um comando de compatibilidade e aceita `--year`, `--utc-offset` e
`--allow-year-rollover` como aliases de `--ano`, `--fuso` e `--virada-ano`.
O padrão unificado de janela é **300s** (a variante antiga usava 60s); informe
`--janela 60` explicitamente para reproduzir aquele parâmetro.
A ordenação segue a política deste documento, em vez da rejeição de todo recuo
na variante anterior. A compatibilidade é de CLI, sem garantia da antiga API Python.
A implementação anterior está preservada em `docs/archive/temporal_analyzer-v0.py.txt`.

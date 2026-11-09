# Checklist de evolução — Mini SOC Analyzer v2

Atualizado em: 08/11/2026. Este é o acompanhamento principal **deste projeto**.

**Onde estamos:** etapas 1 e 2 concluídas no laboratório sintético; etapa 3 parcialmente
implementada. Próxima tarefa: linha do tempo completa e exportação CSV.
O MVP completo ainda não está concluído.

Marque `[x]` somente quando houver implementação, verificação e evidência. `[ ]`
indica trabalho pendente; algo escrito sem validação continua pendente. Ao encerrar
uma sessão, atualize este arquivo e `planejamento/STATUS.md` na central do portfólio.

## 1. Consolidar a base — concluída nesta etapa

- [x] Conferir branch, remoto e alterações locais; preservar o checkout original.
- [x] Definir evento com UTC, host, IP, usuário, tipo e referência da linha original.
- [x] Documentar ano/offset assumidos, ordenação e passagem de ano optativa.
- [x] Implementar janela inclusiva e configurável por host/IP.
- [x] Cobrir falhas esparsas, rajadas, vários usuários, fronteiras e isolamento de hosts/IPs.
- [x] Comparar a janela com a contagem acumulada no cenário esparso.
- [x] Conciliar as variantes em um núcleo: `temporal.py` e CLI principal `soc_analyzer.py`.
- [x] Preservar a variante anterior em `docs/archive/temporal_analyzer-v0.py.txt`.
- [x] Manter `temporal_analyzer.py` como comando de compatibilidade com aliases antigos.
- [x] Reexecutar os testes após a unificação.

Evidências: [contrato](docs/temporal-policy.md), `tests/test_temporal_window.py`
e `tests/scenarios.json` (14 cenários sintéticos).

## 2. Correlacionar login após falhas — concluída nesta etapa

- [x] Exigir mesmo host, IP e usuário; manter o limiar de falhas configurável.
- [x] Definir `--janela-login`; quando omitida, usar o valor de `--janela`.
- [x] Preservar falhas e linha do login como evidências do alerta.
- [x] Testar sucesso elegível e sucesso de outro usuário, IP ou host.
- [x] Testar borda inclusiva, expiração parcial/total, sucesso anterior e empates.
- [x] Testar janela de login independente e sucessos repetidos sem consumir falhas.
- [x] Usar linguagem de investigação; não afirmar comprometimento.

Evidências: `tests/correlation_scenarios.json` (13 cenários sintéticos) e
`tests/test_correlation.py`. Cada sucesso elegível gera seu próprio alerta.

## 3. Explicar e exportar resultados — em andamento

- [x] Relatório em texto com parâmetros, motivos, usuários, linhas rejeitadas e evidências.
- [x] Exportação JSON unificada, esquema `0.2`, com suposições de datas e evidências.
- [x] Testar equivalência dos dois comandos e preservação dos arquivos de entrada/saída.
- [ ] Exibir linha do tempo completa, incluindo eventos que não geraram alerta.
- [ ] Definir colunas e implementar CSV de alertas com referência às evidências.
- [ ] Validar JSON/CSV em arquivo vazio, rejeições e múltiplos alertas; documentar o esquema para consumidores.
- [ ] Preparar exemplo completo para o futuro SOC Copilot.

## 4. Avaliar qualidade e desempenho — pendente

- [ ] Definir critérios de avaliação e separar dados de desenvolvimento e avaliação antes de medir.
- [ ] Criar conjunto independente com rótulos esperados, incluindo erros legítimos e casos difíceis.
- [ ] Avaliar tentativas lentas, distribuídas e duplicatas; registrar falsos positivos e casos perdidos.
- [ ] Comparar baseline e versão temporal no conjunto independente, sem ajustar ao teste final.
- [ ] Medir tempo e memória em volumes definidos, registrando ambiente e parâmetros.
- [ ] Registrar resultados observados, limitações e contribuição autoral.

Os 27 cenários atuais são **de desenvolvimento**. Eles não demonstram eficácia em
produção. Não há benchmark ou métricas de qualidade independentes nesta etapa.

## 5. Preparar a demonstração e entrega — parcialmente iniciada

- [x] Documentar execução e comando único de testes em [README-v2.md](README-v2.md).
- [x] Demonstrar alerta de falhas e correlação de login com dados sintéticos.
- [ ] Consolidar o README principal da v2, preservando o histórico da versão inicial.
- [ ] Preparar demonstração de ponta a ponta com relatório, linha do tempo e exportações.
- [ ] Preparar release e rascunho de post com resultados verificados.
- [ ] Revisar dados e artefatos que serão compartilhados.
- [x] Obter autorização para enviar esta etapa ao GitHub (pedido do usuário em 08/11/2026).
- [ ] Enviar a branch `feat/temporal-detection` e confirmar o commit no remoto.
- [ ] Obter autorização específica para release ou post, se forem solicitados depois.

## Última verificação

Comando na raiz do repositório: `python -m unittest discover -s tests -v`.

Resultado em 08/11/2026: **17 métodos aprovados, incluindo 27 cenários sintéticos**,
em Python 3.14.3. JSON e compatibilidade entre CLIs também foram verificados.
No log versionado: limite 5/300s gera dois alertas de falhas; limite 3/300s gera
dois alertas de falhas e uma correlação de login. Envio ao GitHub autorizado pelo
usuário; ainda pendente porque este ambiente não conseguiu conectar à porta 443
do GitHub. A validação de autenticação do `gh` também falhou; não é possível
concluir por esta verificação isolada se a credencial funcionaria com a rede liberada.

## Validação manual relatada pelo usuário — 08/11/2026

- [x] Usuário confirmou que os testes manuais orientados na conversa deram certo,
  incluindo login com usuário diferente, login de root após falhas de root e linha
  com mensagem desconhecida.

Origem da evidência: relato do usuário na conversa, sem arquivos de saída anexados
ou inspeção independente desta execução manual. A confirmação não substitui os
testes automatizados nem uma avaliação independente. Nenhuma mudança de código
foi necessária. Próxima tarefa de desenvolvimento: linha do tempo completa e CSV.

## Depois do MVP — fora do escopo atual

- [ ] Considerar interface gráfica após concluir a avaliação e as exportações.
- [ ] Avaliar apoio de IA comparando suas saídas com a referência determinística.
- [ ] Considerar outros formatos de logs a partir de uma necessidade demonstrada.

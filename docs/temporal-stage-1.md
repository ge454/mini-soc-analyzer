# Demonstração temporal unificada

Implementação: `temporal.py`; comando principal: `soc_analyzer.py`.
`temporal_analyzer.py` usa o mesmo núcleo. Acompanhe as etapas no [checklist](../CHECKLIST.md).

Python 3, biblioteca padrão, sem instalação de pacotes. Verificado com Python 3.14.3 em Windows em 08/11/2026.

```console
python -m unittest discover -s tests -v
python soc_analyzer.py --log sample_logs/auth.log --ano 2026 --fuso=-03:00 --limite 5 --janela 300
python soc_analyzer.py --log sample_logs/auth.log --ano 2026 --fuso=-03:00 --limite 3 --janela 300 --janela-login 300 --json resultado-temporal.json
```

O arquivo JSON de saída deve ser novo. O programa recusa sobrescrever arquivos existentes e o próprio log. Ano e deslocamento são parâmetros assumidos para esta demonstração sintética; o syslog original não fornece esses dados.

Resultados observados: 17 métodos de teste aprovados, incluindo 27 cenários sintéticos de desenvolvimento. No log versionado: 26 eventos e nenhuma rejeição. Com limite 5 e janela 300s há dois alertas `brute_force`, sem correlação de sucesso: só três falhas eram para `admin`. Com limite 3 e janela 300s há dois alertas de falhas e uma correlação `success_after_failures`, usando falhas das linhas 5, 6 e 8 e login da linha 19. O parâmetro 3 serve para demonstrar a regra e não foi escolhido por avaliação independente de eficácia.

Consulte o [contrato temporal](temporal-policy.md) para critérios e casos. O JSON inclui parâmetros, motivo, linhas de evidência e linha que disparou cada alerta. Não inclui a linha do tempo completa dos eventos.

## Pendências

- CSV e linha do tempo completa; texto e JSON já estão integrados.
- Ampliar a comparação com a baseline para um conjunto independente e avaliar volumes. O caso esparso já foi comparado em teste.
- Consolidar README principal, preparar release e post após avaliação. Nenhuma publicação realizada.

Os testes são cenários sintéticos de desenvolvimento, não evidência de eficácia em produção. A detecção carrega o arquivo em memória; não foi avaliada em grandes volumes. Não há IA nesta etapa: ela constrói a referência determinística para projetos posteriores.

# Exemplo sintético de correlação

Artefatos locais gerados com Python 3.14.3 em 08/11/2026, a partir do log sintético
versionado. Não representam incidente real nem avaliação independente.

Na raiz do repositório:

```console
python soc_analyzer.py --ano 2026 --fuso=-03:00 --limite 3 --janela 300 --janela-login 300 --relatorio docs/examples/correlacao.txt --json docs/examples/correlacao.json
```

Os destinos devem ser novos. Para reproduzir sem sobrescrever estes artefatos,
escolha outros nomes de saída. O limiar 3 demonstra a correlação para as três falhas
de `admin`; ele não é uma recomendação de configuração de produção.

Arquivos: [texto](correlacao.txt) e [JSON](correlacao.json). São 26 eventos, nenhuma
rejeição, dois alertas de falhas e uma correlação de login. A linha do tempo completa
e CSV ainda estão no [checklist](../../CHECKLIST.md).

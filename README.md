# Lei Rouanet em números

Projeto em andamento. Etapa atual é a coleta de dados.

## Pergunta

Quanto do valor aprovado pela Lei Rouanet vira captação de fato, e como essa captação se distribui entre regiões, segmentos culturais e proponentes? A captação é concentrada em poucos projetos?

## Fonte

API de dados abertos do SALIC, do Ministério da Cultura (`http://api.salic.cultura.gov.br/api/v1/projetos/`).

A API devolve 63.674 projetos com 34 campos, entre eles PRONAC, segmento, UF, município, proponente, valor solicitado, valor aprovado e valor captado. Ela cobre projetos de 2019 em diante. O histórico anterior não está disponível por essa via.

## Método

1. Coleta paginada da API (100 projetos por página, limite do servidor), com download em paralelo, novas tentativas em caso de falha e retomada de onde parou.
2. Cada página é guardada como JSON bruto em `dados/brutos/` e nunca é editada.
3. As páginas são juntadas em `dados/projetos_salic.csv`.

Próximas etapas são limpeza, análise da relação entre aprovado e captado, concentração da captação e um painel em Power BI.

## Como rodar

```bash
pip install -r requirements.txt
python coletar_salic.py --teste   # baixa só 2 páginas para conferir
python coletar_salic.py           # coleta completa, leva perto de uma hora
```

No Windows com Miniconda, use `rodar_teste.bat` ou ative o ambiente antes (`conda activate base`). Sem isso o Python não encontra o módulo SSL.

Os dados não ficam no repositório. O script recria tudo a partir da API.

# Painel em Power BI

O painel usa a base `dados/painel/projetos_powerbi.csv`, gerada por `analisar.py`. Ela tem uma linha por projeto (2019 a 2026), separador `;`, vírgula decimal e codificação UTF-8, o padrão do Power BI em português.

## Como carregar

1. Rode `python limpar.py` e depois `python analisar.py`.
2. No Power BI Desktop, use Obter dados, Texto/CSV e escolha `dados/painel/projetos_powerbi.csv`.
3. Confira os tipos das colunas. Valores (`valor_*`, `taxa_captacao`) como número decimal, `ano` como número inteiro, `data_inicio` e `data_termino` como data, `aprovado` e `captou` como verdadeiro ou falso.

## Medidas DAX

```dax
Projetos = COUNTROWS ( projetos_powerbi )

Projetos aprovados = CALCULATE ( [Projetos], projetos_powerbi[aprovado] = TRUE () )

Valor aprovado = CALCULATE ( SUM ( projetos_powerbi[valor_aprovado] ), projetos_powerbi[aprovado] = TRUE () )

Valor captado = CALCULATE ( SUM ( projetos_powerbi[valor_captado] ), projetos_powerbi[aprovado] = TRUE () )

Taxa de captação = DIVIDE ( [Valor captado], [Valor aprovado] )

% que captaram =
DIVIDE (
    CALCULATE ( [Projetos], projetos_powerbi[aprovado] = TRUE (), projetos_powerbi[captou] = TRUE () ),
    [Projetos aprovados]
)

Participação no captado =
DIVIDE ( [Valor captado], CALCULATE ( [Valor captado], ALLSELECTED ( projetos_powerbi ) ) )
```

## Páginas sugeridas

1. Visão geral. Cartões com projetos aprovados, valor aprovado, valor captado e taxa de captação. Colunas de valor aprovado e captado por ano.
2. Território. Mapa por UF com o valor captado e tabela por região com participação nos projetos e no captado.
3. Áreas e segmentos. Barras da taxa de captação por área, com detalhamento para segmento.
4. Proponentes. Tabela dos maiores captadores e comparação entre pessoa física, MEI e pessoa jurídica.

Filtros de ano, região, área e tipo de proponente numa única linha no topo de todas as páginas.

Atenção ao comparar anos. Projetos de 2023 em diante ainda estão captando, então a taxa de captação desses anos ainda vai subir. Para comparar áreas, regiões e proponentes, filtre os anos de 2019 a 2022, como na análise em Python.

"""
Gera o painel da Lei Rouanet como projeto do Power BI (.pbip), em arquivos de texto.

O projeto tem duas partes
    Rouanet.SemanticModel   modelo de dados em TMDL (tabela, tipos, consulta Power Query e medidas DAX)
    Rouanet.Report          relatório em PBIR (tema, páginas e visuais em JSON)

Uso
    python painel/gerar_pbip.py [pagina]
    depois abra painel/Rouanet.pbip no Power BI Desktop e clique em Atualizar
    pagina é opcional (visao_geral, territorio, areas, proponentes ou desigualdade) e define a página que abre primeiro

A consulta lê dados/painel/projetos_powerbi.csv (gerado por analisar.py). O caminho fica no
parâmetro PastaDados, preenchido com a pasta deste repositório na hora de gerar.
"""

import json
import shutil
import subprocess
import uuid
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
NOME = "Rouanet"
MODELO = AQUI / f"{NOME}.SemanticModel"
RELATORIO = AQUI / f"{NOME}.Report"
TEMA_BASE = "CY24SU10"

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
TABELA = "projetos"

AZUL, LARANJA, VERDE = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA_2, APAGADO, GRADE, SUPERFICIE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"


def local_power_bi():
    """Pasta do Power BI Desktop instalado. O tema base do relatório é copiado de lá."""
    for fixo in (Path(r"C:\Program Files\Microsoft Power BI Desktop"),):
        if fixo.exists():
            return fixo
    saida = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-AppxPackage Microsoft.MicrosoftPowerBIDesktop).InstallLocation"],
                           capture_output=True, text=True, check=True).stdout.strip()
    if not saida:
        raise SystemExit("Power BI Desktop não encontrado")
    return Path(saida)


def tag(*partes):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "rouanet/" + "/".join(partes)))


def escrever(caminho, conteudo):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(conteudo, str):
        conteudo = json.dumps(conteudo, ensure_ascii=False, indent=2)
    caminho.write_text(conteudo, encoding="utf-8")


# ---------------------------------------------------------------- modelo

COLUNAS = [  # nome, tipo no Power Query, tipo no modelo, resumo padrão
    ("pronac", "type text", "string", "none"),
    ("nome", "type text", "string", "none"),
    ("ano", "Int64.Type", "int64", "none"),
    ("data_inicio", "type date", "dateTime", "none"),
    ("data_termino", "type date", "dateTime", "none"),
    ("uf", "type text", "string", "none"),
    ("regiao", "type text", "string", "none"),
    ("municipio", "type text", "string", "none"),
    ("area", "type text", "string", "none"),
    ("segmento", "type text", "string", "none"),
    ("tipologia", "type text", "string", "none"),
    ("tipicidade", "type text", "string", "none"),
    ("enquadramento", "type text", "string", "none"),
    ("mecanismo", "type text", "string", "none"),
    ("etapa", "type text", "string", "none"),
    ("situacao_salic", "type text", "string", "none"),
    ("proponente", "type text", "string", "none"),
    ("cpf_cnpj", "type text", "string", "none"),
    ("tipo_proponente", "type text", "string", "none"),
    ("valor_proposta", "type number", "double", "sum"),
    ("valor_solicitado", "type number", "double", "sum"),
    ("valor_aprovado", "type number", "double", "sum"),
    ("valor_projeto", "type number", "double", "sum"),
    ("valor_captado", "type number", "double", "sum"),
    ("outras_fontes", "type number", "double", "sum"),
    ("aprovado", "type logical", "boolean", "none"),
    ("captou", "type logical", "boolean", "none"),
    ("taxa_captacao", "type number", "double", "none"),
    ("alerta_valor", "type text", "string", "none"),
    ("local_realizacao", "type text", "string", "none"),
]

MEDIDAS = [  # nome, DAX, formato
    ("Projetos aprovados", f"CALCULATE ( COUNTROWS ( {TABELA} ), {TABELA}[aprovado] = TRUE () )", "#,0"),
    ("Valor aprovado", f"CALCULATE ( SUM ( {TABELA}[valor_aprovado] ), {TABELA}[aprovado] = TRUE () )", "#,0"),
    ("Valor captado", f"CALCULATE ( SUM ( {TABELA}[valor_captado] ), {TABELA}[aprovado] = TRUE () )", "#,0"),
    ("Taxa de captação", "DIVIDE ( [Valor captado], [Valor aprovado] )", "0.0%"),
    ("% que captaram", f"DIVIDE ( CALCULATE ( [Projetos aprovados], {TABELA}[captou] = TRUE () ), [Projetos aprovados] )", "0.0%"),
    ("Participação no captado", f"DIVIDE ( [Valor captado], CALCULATE ( [Valor captado], ALLSELECTED ( {TABELA} ) ) )", "0.0%"),
    ("Projetos aprovados 2019-2022", f"CALCULATE ( [Projetos aprovados], {TABELA}[ano] <= 2022 )", "#,0"),
    ("Valor captado 2019-2022", f"CALCULATE ( [Valor captado], {TABELA}[ano] <= 2022 )", "#,0"),
    ("Taxa de captação 2019-2022", f"CALCULATE ( [Taxa de captação], {TABELA}[ano] <= 2022 )", "0.0%"),
    ("% que captaram 2019-2022", f"CALCULATE ( [% que captaram], {TABELA}[ano] <= 2022 )", "0.0%"),
    # Indicadores da comparação com a literatura (ver README do projeto)
    ("Proponentes", f"CALCULATE ( DISTINCTCOUNT ( {TABELA}[chave_proponente] ), {TABELA}[aprovado] = TRUE () )", "#,0"),
    ("Parcela pelo Artigo 18",
     f'DIVIDE ( CALCULATE ( [Valor captado], {TABELA}[enquadramento] = "Artigo 18" ), [Valor captado] )', "0.0%"),
    # A tabela ufs não tem relação com projetos. População e PIB seguem só os filtros de UF e região.
    ("População", f"CALCULATE ( SUM ( ufs[populacao] ), TREATAS ( CALCULATETABLE ( VALUES ( {TABELA}[uf] ), "
                  f"ALLEXCEPT ( {TABELA}, {TABELA}[uf], {TABELA}[regiao] ) ), ufs[uf] ) )", "#,0"),
    ("PIB", f"CALCULATE ( SUM ( ufs[pib] ), TREATAS ( CALCULATETABLE ( VALUES ( {TABELA}[uf] ), "
            f"ALLEXCEPT ( {TABELA}, {TABELA}[uf], {TABELA}[regiao] ) ), ufs[uf] ) )", "#,0"),
    ("Parcela da população", "DIVIDE ( [População], SUM ( ufs[populacao] ) )", "0.0%"),
    ("Parcela do PIB", "DIVIDE ( [PIB], SUM ( ufs[pib] ) )", "0.0%"),
    ("Captado por habitante", "DIVIDE ( [Valor captado], [População] )", "#,0"),
    ("Parcela dos 20 maiores", f'VAR t = ADDCOLUMNS ( VALUES ( {TABELA}[chave_proponente] ), "@v", [Valor captado] ) '
                               'RETURN DIVIDE ( SUMX ( TOPN ( 20, t, [@v] ), [@v] ), [Valor captado] )', "0.0%"),
    ("Parcela dos 82 maiores", f'VAR t = ADDCOLUMNS ( VALUES ( {TABELA}[chave_proponente] ), "@v", [Valor captado] ) '
                               'RETURN DIVIDE ( SUMX ( TOPN ( 82, t, [@v] ), [@v] ), [Valor captado] )', "0.0%"),
]

EXTRAS = [  # colunas criadas no Power Query: nome, tipo, ordenar por
    ("periodo_captacao", "string", None),
    ("chave_proponente", "string", None),
    ("faixa_valor", "string", "faixa_ordem"),
    ("faixa_ordem", "int64", None),
]

UFS = [("uf", "type text", "string", "none"), ("regiao", "type text", "string", "none"),
       ("populacao", "Int64.Type", "int64", "sum"), ("pib", "type number", "double", "sum")]


def nome_tmdl(nome):
    return nome if nome.replace("_", "").isalnum() else "'" + nome.replace("'", "''") + "'"


def gerar_modelo(pasta_dados):
    if MODELO.exists():
        shutil.rmtree(MODELO)
    escrever(MODELO / "definition.pbism", {
        "$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2",
        "settings": {},
    })
    escrever(MODELO / "definition" / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    escrever(MODELO / "definition" / "model.tmdl", "\n".join([
        "model Model",
        "\tculture: pt-BR",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: pt-BR",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        f"ref table {TABELA}",
        "ref table ufs",
        "",
    ]))
    caminho_m = str(pasta_dados).replace('"', '""')
    escrever(MODELO / "definition" / "expressions.tmdl", "\n".join([
        f'expression PastaDados = "{caminho_m}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {tag('PastaDados')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
    ]))

    linhas = [f"table {TABELA}", f"\tlineageTag: {tag(TABELA)}", ""]
    for nome, dax, formato in MEDIDAS:
        linhas += [f"\tmeasure {nome_tmdl(nome)} = {dax}", f"\t\tformatString: {formato}",
                   f"\t\tlineageTag: {tag('medida', nome)}", ""]
    ordem = {n: o for n, _, o in EXTRAS if o}
    for nome, _, tipo, resumo in COLUNAS + [(n, None, t, "none") for n, t, _ in EXTRAS]:
        linhas += [f"\tcolumn {nome}", f"\t\tdataType: {tipo}"]
        if nome in ordem:
            linhas.append(f"\t\tsortByColumn: {ordem[nome]}")
        if tipo == "dateTime":
            linhas.append("\t\tformatString: dd/mm/yyyy")
        elif tipo == "double" and nome.startswith("valor") or nome == "outras_fontes":
            linhas.append("\t\tformatString: #,0")
        elif nome == "taxa_captacao":
            linhas.append("\t\tformatString: 0.0%")
        linhas += [f"\t\tlineageTag: {tag('coluna', nome)}", f"\t\tsummarizeBy: {resumo}",
                   f"\t\tsourceColumn: {nome}", ""]
        if nome == "uf":
            linhas.insert(-1, "\t\tdataCategory: StateOrProvince")

    tipos = ", ".join(f'{{"{n}", {t}}}' for n, t, _, _ in COLUNAS)
    m = [
        "let",
        '\tFonte = Csv.Document(File.Contents(PastaDados & "\\projetos_powerbi.csv"), [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "\tCabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),",
        f'\tTipos = Table.TransformColumnTypes(Cabecalhos, {{{tipos}}}, "pt-BR"),',
        '\tPeriodo = Table.AddColumn(Tipos, "periodo_captacao", each if [ano] <= 2022 then "Captação encerrada (2019 a 2022)" else "Ainda captando (2023 a 2026)", type text),',
        '\tChave = Table.AddColumn(Periodo, "chave_proponente", each ([cpf_cnpj] ?? "") & "|" & ([proponente] ?? ""), type text),',
        '\tFaixa = Table.AddColumn(Chave, "faixa_valor", each let v = [valor_aprovado] in if v = null or v <= 0 then null else if v <= 100000 then "até 100 mil" else if v <= 300000 then "100 a 300 mil" else if v <= 1000000 then "300 mil a 1 mi" else if v <= 3000000 then "1 a 3 mi" else "acima de 3 mi", type text),',
        '\tOrdem = Table.AddColumn(Faixa, "faixa_ordem", each if [faixa_valor] = null then null else List.PositionOf({"até 100 mil", "100 a 300 mil", "300 mil a 1 mi", "1 a 3 mi", "acima de 3 mi"}, [faixa_valor]) + 1, Int64.Type)',
        "in",
        "\tOrdem",
    ]
    linhas += [f"\tpartition {TABELA} = m", "\t\tmode: import", "\t\tsource ="]
    linhas += ["\t\t\t\t" + l for l in m]
    linhas += ["", "\tannotation PBI_ResultType = Table", ""]
    escrever(MODELO / "definition" / "tables" / f"{TABELA}.tmdl", "\n".join(linhas))

    # População (Censo 2022) e PIB (2023) por UF, gravados por analisar.py
    linhas = ["table ufs", f"\tlineageTag: {tag('ufs')}", ""]
    for nome, _, tipo, resumo in UFS:
        linhas += [f"\tcolumn {nome}", f"\t\tdataType: {tipo}"]
        if tipo != "string":
            linhas.append("\t\tformatString: #,0")
        linhas += [f"\t\tlineageTag: {tag('ufs', nome)}", f"\t\tsummarizeBy: {resumo}", f"\t\tsourceColumn: {nome}", ""]
    tipos = ", ".join(f'{{"{n}", {t}}}' for n, t, _, _ in UFS)
    m = [
        "let",
        '\tFonte = Csv.Document(File.Contents(PastaDados & "\\ufs_powerbi.csv"), [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "\tCabecalhos = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true]),",
        f'\tTipos = Table.TransformColumnTypes(Cabecalhos, {{{tipos}}}, "pt-BR")',
        "in",
        "\tTipos",
    ]
    linhas += ["\tpartition ufs = m", "\t\tmode: import", "\t\tsource ="]
    linhas += ["\t\t\t\t" + l for l in m]
    linhas += ["", "\tannotation PBI_ResultType = Table", ""]
    escrever(MODELO / "definition" / "tables" / "ufs.tmdl", "\n".join(linhas))


# ---------------------------------------------------------------- relatório

def lit(valor):
    if isinstance(valor, bool):
        v = "true" if valor else "false"
    elif isinstance(valor, (int, float)):
        v = f"{valor}D"
    else:
        v = "'" + str(valor).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def cor(hexa):
    return {"solid": {"color": lit(hexa)}}


def campo(nome, medida=False, rotulo=None):
    tipo = "Measure" if medida else "Column"
    proj = {
        "field": {tipo: {"Expression": {"SourceRef": {"Entity": TABELA}}, "Property": nome}},
        "queryRef": f"{TABELA}.{nome}",
        "nativeQueryRef": nome,
    }
    if rotulo:
        proj["displayName"] = rotulo
    return proj


def titulo(texto, sub=None):
    props = {"show": lit(True), "text": lit(texto), "fontSize": lit(12), "bold": lit(True), "fontColor": cor(TINTA)}
    obj = {"title": [{"properties": props}]}
    if sub:
        obj["subTitle"] = [{"properties": {"show": lit(True), "text": lit(sub), "fontColor": cor(TINTA_2)}}]
    return obj


class Pagina:
    def __init__(self, nome, exibicao):
        self.nome, self.exibicao, self.visuais = nome, exibicao, []

    def add(self, x, y, w, h, visual, objetos_container=None):
        nome = tag(self.nome, str(len(self.visuais)))[:20].replace("-", "")
        self.visuais.append({
            "$schema": f"{SCHEMA}/item/report/definition/visualContainer/1.0.0/schema.json",
            "name": nome,
            "position": {"x": x, "y": y, "z": len(self.visuais) * 1000, "width": w, "height": h,
                         "tabOrder": len(self.visuais) * 1000},
            "visual": {**visual, **({"visualContainerObjects": objetos_container} if objetos_container else {})},
        })

    # tipos de visual
    def texto(self, x, y, w, h, linhas):
        paragrafos = [{"textRuns": [{"value": t, "textStyle": {"fontSize": f"{tam}pt", "fontWeight": "bold" if neg else "normal",
                                                             "color": TINTA if neg else TINTA_2}}]}
                      for t, tam, neg in linhas]
        self.add(x, y, w, h, {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paragrafos}}]}})

    def cartao(self, x, y, w, h, medida, rotulo, unidades=0):
        self.add(x, y, w, h, {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": [campo(medida, True)]}}},
            "objects": {"labels": [{"properties": {"color": cor(TINTA), "fontSize": lit(26),
                                                   "labelDisplayUnits": lit(unidades)}}],
                        "categoryLabels": [{"properties": {"show": lit(False)}}]},
        }, titulo(rotulo))

    def segmentacao(self, x, y, w, h, coluna, rotulo):
        self.add(x, y, w, h, {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [campo(coluna) | {"active": True}]}}},
            "objects": {"data": [{"properties": {"mode": lit("Dropdown")}}],
                        "header": [{"properties": {"show": lit(True), "text": lit(rotulo), "fontColor": cor(TINTA_2)}}]},
        })

    def barras(self, x, y, w, h, tipo, categoria, medidas, tit, sub=None, ordenar=None, crescente=False, rotulos=True,
               unidades=None):
        consulta = {"queryState": {
            "Category": {"projections": [campo(categoria) | {"active": True}]},
            "Y": {"projections": [campo(m, True) for m in medidas]},
        }}
        if ordenar:
            consulta["sortDefinition"] = {"sort": [{"field": campo(ordenar, ordenar != categoria)["field"],
                                                    "direction": "Ascending" if crescente else "Descending"}],
                                          "isDefaultSort": True}
        cores = [{"properties": {"fill": cor(c)}, "selector": {"metadata": f"{TABELA}.{m}"}}
                 for m, c in zip(medidas, (AZUL, LARANJA, VERDE))]
        if unidades is None:  # contagens por extenso, valores em R$ no automático
            unidades = 1 if all(m.startswith(("Projetos", "Proponentes")) for m in medidas) else 0
        objetos = {
            "dataPoint": cores,
            "labels": [{"properties": {"show": lit(rotulos), "color": cor(TINTA_2), "fontSize": lit(8),
                                       "labelDisplayUnits": lit(unidades)}}],
            "legend": [{"properties": {"show": lit(len(medidas) > 1), "position": lit("Top")}}],
            "valueAxis": [{"properties": {"gridlineColor": cor(GRADE), "showAxisTitle": lit(False),
                                          **({"labelDisplayUnits": lit(unidades)} if unidades > 1 else {})}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit(False), "maxMarginFactor": lit(45)}}],
        }
        self.add(x, y, w, h, {"visualType": tipo, "query": consulta, "objects": objetos}, titulo(tit, sub))

    def tabela(self, x, y, w, h, colunas, medidas, tit, ordenar, sub=None, larguras=None):
        """colunas e medidas são pares (campo, rótulo). larguras fixa a largura de colunas, {campo: px}."""
        consulta = {"queryState": {"Values": {"projections": [campo(c, False, r) for c, r in colunas]
                                                             + [campo(m, True, r) for m, r in medidas]}},
                    "sortDefinition": {"sort": [{"field": campo(ordenar, True)["field"], "direction": "Descending"}],
                                       "isDefaultSort": True}}
        objetos = {"grid": [{"properties": {"gridHorizontalColor": cor(GRADE), "rowPadding": lit(3)}}],
                   "columnHeaders": [{"properties": {"fontColor": cor(TINTA), "bold": lit(True), "wordWrap": lit(True)}}],
                   "values": [{"properties": {"wordWrap": lit(False)}}]}
        if larguras:
            objetos["columnWidth"] = [{"properties": {"value": lit(px)}, "selector": {"metadata": f"{TABELA}.{c}"}}
                                      for c, px in larguras.items()]
        self.add(x, y, w, h, {"visualType": "tableEx", "query": consulta, "objects": objetos}, titulo(tit, sub))


def filtros_topo(p):
    p.segmentacao(640, 12, 150, 64, "ano", "Ano")
    p.segmentacao(800, 12, 150, 64, "regiao", "Região")
    p.segmentacao(960, 12, 150, 64, "area", "Área cultural")
    p.segmentacao(1120, 12, 144, 64, "tipo_proponente", "Proponente")


def paginas():
    nota = "Projetos de 2023 em diante ainda estão captando, então as taxas desses anos ainda vão subir."

    p1 = Pagina("visao_geral", "Visão geral")
    p1.texto(16, 12, 610, 64, [("Lei Rouanet em números", 18, True), ("Projetos do SALIC, 2019 a 2026", 10, False)])
    filtros_topo(p1)
    for i, (medida, rotulo, unidades) in enumerate([
            ("Projetos aprovados", "Projetos aprovados", 1), ("Valor aprovado", "Valor aprovado (R$)", 0),
            ("Valor captado", "Valor captado (R$)", 0), ("Taxa de captação 2019-2022", "Taxa de captação (projetos de 2019 a 2022)", 0)]):
        p1.cartao(16 + i * 314, 88, 302, 110, medida, rotulo, unidades)
    p1.barras(16, 210, 820, 494, "clusteredColumnChart", "ano", ["Valor aprovado", "Valor captado"],
              "Valor aprovado e captado por ano (R$)", nota, ordenar="ano", crescente=True, rotulos=False)
    p1.barras(848, 210, 416, 494, "clusteredBarChart", "etapa", ["Projetos aprovados"],
              "Projetos aprovados por etapa", "Situação atual no SALIC, agrupada", ordenar="Projetos aprovados")

    p2 = Pagina("territorio", "Território")
    p2.texto(16, 12, 610, 64, [("Onde a captação acontece", 18, True), ("Projetos com captação encerrada, 2019 a 2022", 10, False)])
    filtros_topo(p2)
    p2.barras(16, 88, 600, 616, "clusteredBarChart", "uf", ["Valor captado 2019-2022"],
              "Valor captado por UF (R$ milhões)", "Projetos de 2019 a 2022", ordenar="Valor captado 2019-2022",
              unidades=1_000_000)
    p2.tabela(628, 88, 636, 300, [("regiao", "Região")],
              [("Projetos aprovados 2019-2022", "Projetos"), ("Valor captado 2019-2022", "Valor captado (R$)"),
               ("Taxa de captação 2019-2022", "Taxa de captação"), ("% que captaram 2019-2022", "% que captaram")],
              "Indicadores por região", "Valor captado 2019-2022", "Projetos de 2019 a 2022")
    p2.barras(628, 400, 636, 304, "clusteredBarChart", "regiao", ["Taxa de captação 2019-2022"],
              "Taxa de captação por região", "Parcela do valor aprovado que foi captada", ordenar="Taxa de captação 2019-2022")

    p3 = Pagina("areas", "Áreas e segmentos")
    p3.texto(16, 12, 610, 64, [("O que se capta, por área", 18, True), ("Projetos com captação encerrada, 2019 a 2022", 10, False)])
    filtros_topo(p3)
    p3.barras(16, 88, 560, 616, "clusteredBarChart", "area", ["Taxa de captação 2019-2022"],
              "Taxa de captação por área cultural", "Parcela do valor aprovado que foi captada", ordenar="Taxa de captação 2019-2022")
    p3.tabela(588, 88, 676, 616, [("segmento", "Segmento"), ("area", "Área")],
              [("Projetos aprovados 2019-2022", "Projetos"), ("Valor captado 2019-2022", "Captado (R$)"),
               ("Taxa de captação 2019-2022", "Taxa")],
              "Segmentos", "Valor captado 2019-2022", "Projetos de 2019 a 2022, do maior para o menor valor captado",
              larguras={"segmento": 250, "area": 130})

    p4 = Pagina("proponentes", "Proponentes")
    p4.texto(16, 12, 610, 64, [("Quem capta", 18, True), ("Concentração da captação entre proponentes", 10, False)])
    filtros_topo(p4)
    p4.barras(16, 88, 420, 300, "clusteredColumnChart", "tipo_proponente", ["Taxa de captação 2019-2022"],
              "Taxa de captação por tipo de proponente", "Projetos de 2019 a 2022", ordenar="Taxa de captação 2019-2022")
    p4.barras(16, 400, 420, 304, "clusteredColumnChart", "tipo_proponente", ["% que captaram 2019-2022"],
              "Projetos que captaram algum valor", "Projetos de 2019 a 2022", ordenar="% que captaram 2019-2022")
    p4.tabela(448, 88, 816, 616, [("proponente", "Proponente"), ("uf", "UF")],
              [("Projetos aprovados", "Projetos"), ("Valor captado", "Valor captado (R$)"),
               ("Participação no captado", "Parte do total captado")],
              "Maiores captadores", "Valor captado", "Todos os anos. O filtro de proponente separa pessoas físicas, MEI e empresas",
              larguras={"proponente": 400, "uf": 40})
    p5 = Pagina("desigualdade", "Desigualdade")
    p5.texto(16, 12, 610, 64, [("Quem fica com a captação", 18, True),
                               ("Indicadores comparados com a literatura sobre a lei", 10, False)])
    filtros_topo(p5)
    for i, (medida, rotulo, unidades) in enumerate([
            ("Parcela pelo Artigo 18", "Captado pelo Artigo 18 (dedução integral)", 0),
            ("Captado por habitante", "Valor captado por habitante (R$)", 1),
            ("Parcela dos 20 maiores", "Parte dos 20 maiores proponentes", 0),
            ("Proponentes", "Proponentes com projeto aprovado", 1)]):
        p5.cartao(16 + i * 314, 88, 302, 100, medida, rotulo, unidades)
    p5.barras(16, 200, 520, 504, "clusteredBarChart", "regiao",
              ["Participação no captado", "Parcela do PIB", "Parcela da população"],
              "Captação, PIB e população por região", "PIB de 2023 e população do Censo 2022 (IBGE)",
              ordenar="Participação no captado")
    p5.barras(548, 200, 340, 504, "clusteredBarChart", "uf", ["Captado por habitante"],
              "Valor captado por habitante (R$)", "Por UF do proponente", ordenar="Captado por habitante", unidades=1)
    p5.barras(900, 200, 364, 246, "clusteredColumnChart", "faixa_valor", ["% que captaram 2019-2022"],
              "Projetos que captaram, por valor aprovado", "Projetos de 2019 a 2022", ordenar="faixa_valor", crescente=True)
    p5.barras(900, 458, 364, 246, "lineChart", "ano", ["Parcela dos 82 maiores", "Parcela dos 20 maiores"],
              "Parte dos maiores proponentes no captado", "Por ano do projeto. Anos recentes ainda captando",
              ordenar="ano", crescente=True, rotulos=False)
    p5.visuais[-1]["filterConfig"] = filtro_ano_ate(2025)   # 2026 ainda está em curso
    return [p1, p2, p3, p4, p5]


def filtro_ano_ate(ano):
    """Filtro de visual que mantém só os projetos até o ano dado."""
    coluna = {"Column": {"Expression": {"SourceRef": {"Entity": TABELA}}, "Property": "ano"}}
    return {"filters": [{
        "name": tag("filtro_ano", str(ano))[:20].replace("-", ""),
        "field": coluna,
        "type": "Advanced",
        "filter": {
            "Version": 2,
            "From": [{"Name": "p", "Entity": TABELA, "Type": 0}],
            "Where": [{"Condition": {"Comparison": {
                "ComparisonKind": 4,  # menor ou igual
                "Left": {"Column": {"Expression": {"SourceRef": {"Source": "p"}}, "Property": "ano"}},
                "Right": {"Literal": {"Value": f"{ano}L"}},
            }}}],
        },
    }]}


def tema():
    return {
        "name": "Portfolio",
        "dataColors": [AZUL, LARANJA, "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
        "foreground": TINTA, "foregroundNeutralSecondary": TINTA_2, "foregroundNeutralTertiary": APAGADO,
        "background": SUPERFICIE, "backgroundLight": "#f9f9f7", "backgroundNeutral": GRADE,
        "tableAccent": AZUL,
        "textClasses": {
            "callout": {"fontFace": "Segoe UI", "color": TINTA},
            "title": {"fontFace": "Segoe UI Semibold", "color": TINTA},
            "header": {"fontFace": "Segoe UI Semibold", "color": TINTA},
            "label": {"fontFace": "Segoe UI", "color": TINTA_2},
        },
        "visualStyles": {"*": {"*": {
            "border": [{"show": False}],
            "dropShadow": [{"show": False}],
            "background": [{"show": True, "color": {"solid": {"color": "#ffffff"}}, "transparency": 0}],
        }}, "page": {"*": {"background": [{"color": {"solid": {"color": "#f4f3ef"}}, "transparency": 0}]}}},
    }


def gerar_relatorio(pagina_inicial=None):
    if RELATORIO.exists():
        shutil.rmtree(RELATORIO)
    origem = local_power_bi() / "bin" / "WebView2Resources" / "minerva" / "sharedresources" / "BaseThemes" / f"{TEMA_BASE}.json"
    destino = RELATORIO / "StaticResources" / "SharedResources" / "BaseThemes" / f"{TEMA_BASE}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origem, destino)
    escrever(RELATORIO / "StaticResources" / "RegisteredResources" / "Portfolio.json", tema())

    escrever(RELATORIO / "definition.pbir", {
        "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NOME}.SemanticModel"}},
    })
    d = RELATORIO / "definition"
    escrever(d / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
                                  "version": "2.0.0"})
    escrever(d / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/1.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": TEMA_BASE, "reportVersionAtImport": "5.59", "type": "SharedResources"},
            "customTheme": {"name": "Portfolio.json", "reportVersionAtImport": "5.59", "type": "RegisteredResources"},
        },
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": TEMA_BASE, "path": f"BaseThemes/{TEMA_BASE}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "Portfolio.json", "path": "Portfolio.json", "type": "CustomTheme"}]},
        ],
        "objects": {"outspacePane": [{"properties": {"expanded": lit(False)}}]},
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True},
    })
    lista = paginas()
    nomes = [p.nome for p in lista]
    escrever(d / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": nomes, "activePageName": pagina_inicial if pagina_inicial in nomes else nomes[0],
    })
    for p in lista:
        escrever(d / "pages" / p.nome / "page.json", {
            "$schema": f"{SCHEMA}/item/report/definition/page/1.0.0/schema.json",
            "name": p.nome, "displayName": p.exibicao, "displayOption": "FitToPage", "height": 720, "width": 1280,
        })
        for v in p.visuais:
            escrever(d / "pages" / p.nome / "visuals" / v["name"] / "visual.json", v)
    return sum(len(p.visuais) for p in lista), len(lista)


def gerar(pagina_inicial=None):
    pasta_dados = RAIZ / "dados" / "painel"
    gerar_modelo(pasta_dados)
    n_visuais, n_paginas = gerar_relatorio(pagina_inicial)
    escrever(AQUI / f"{NOME}.pbip", {
        "$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NOME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    print(f"{NOME}.pbip gerado: {n_paginas} páginas, {n_visuais} visuais, {len(MEDIDAS)} medidas")
    print(f"Dados lidos de {pasta_dados}")


if __name__ == "__main__":
    import sys
    gerar(sys.argv[1] if len(sys.argv) > 1 else None)  # opcional, página que abre primeiro

"""
Análise dos projetos da Lei Rouanet (2019 a 2026).

Lê dados/tratados/projetos.csv (gerado por limpar.py) e produz

    resultados/*.csv              tabelas da análise (pequenas, ficam no repositório)
    figuras/*.png                 gráficos usados no README
    dados/painel/projetos_powerbi.csv   base para o Power BI (separador ; e vírgula decimal)

Recorte de tempo
    Um projeto aprovado tem cerca de dois anos para captar, com prorrogações. Os projetos de 2023 em
    diante ainda estão captando (em 2026, 94% deles), então a taxa de captação desses anos ainda vai
    subir. Por isso as taxas por área, região e proponente usam a coorte 2019 a 2022, em que menos de
    1% dos projetos ainda está captando. Os totais por ano usam todos os anos, com esse aviso.

Uso
    python analisar.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ENTRADA = Path("dados/tratados/projetos.csv")
RESULTADOS = Path("resultados")
FIGURAS = Path("figuras")
PAINEL = Path("dados/painel")
AUX = Path("dados/auxiliares")

COORTE = (2019, 2022)          # anos com prazo de captação já encerrado
ANOS_COMPLETOS = (2019, 2025)  # 2026 ainda está em curso

UF_DO_CODIGO = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
                "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
                "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS",
                "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
REGIAO_DA_UF = {**dict.fromkeys(["RO", "AC", "AM", "RR", "PA", "AP", "TO"], "Norte"),
                **dict.fromkeys(["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"], "Nordeste"),
                **dict.fromkeys(["MG", "ES", "RJ", "SP"], "Sudeste"),
                **dict.fromkeys(["PR", "SC", "RS"], "Sul"),
                **dict.fromkeys(["MS", "MT", "GO", "DF"], "Centro-Oeste")}

# Paleta e tinta (referência de visualização, modo claro)
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
APAGADO = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
AZUL = "#2a78d6"               # série 1
LARANJA = "#eb6834"            # série 2
VERDE = "#1baf7a"              # série 3

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 10,
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": EIXO,
    "axes.labelcolor": TINTA_2,
    "xtick.color": APAGADO,
    "ytick.color": APAGADO,
    "text.color": TINTA,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlelocation": "left",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlepad": 30,
})


# ---------- formatação em português ----------

def reais(v, casas=1):
    if abs(v) >= 1e9:
        return f"R$ {v / 1e9:.{casas}f} bi".replace(".", ",")
    if abs(v) >= 1e6:
        return f"R$ {v / 1e6:.{casas}f} mi".replace(".", ",")
    return f"R$ {v:,.0f}".replace(",", ".")


def pct(v, casas=0):
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def inteiro(v):
    return f"{v:,.0f}".replace(",", ".")


def subtitulo(ax, texto):
    ax.annotate(texto, (0, 1), xycoords="axes fraction", xytext=(0, 7), textcoords="offset points",
                color=TINTA_2, fontsize=9.5, va="bottom")


def rodape(fig, texto="Fonte: SALIC, Ministério da Cultura (API de dados abertos). Elaboração própria."):
    fig.text(0.01, 0.01, texto, color=APAGADO, fontsize=8, ha="left", va="bottom")


def grade(ax, eixo="y"):
    ax.grid(axis=eixo, color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


# ---------- dados do IBGE ----------

def sidra(url, destino, montar):
    """Baixa uma tabela do SIDRA uma vez e guarda em dados/auxiliares."""
    if not destino.exists():
        import requests
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        AUX.mkdir(parents=True, exist_ok=True)
        montar(r.json()[1:]).to_csv(destino, index=False)
    return pd.read_csv(destino)


def populacao_e_pib():
    """População do Censo 2022 (tabela 4709) e PIB de 2023 (tabela 5938) por UF."""
    pop = sidra("https://apisidra.ibge.gov.br/values/t/4709/n3/all/v/93/p/2022", AUX / "populacao_uf.csv",
                lambda l: pd.DataFrame({"uf": [x["D1C"] for x in l], "populacao": [int(x["V"]) for x in l]})
                .assign(uf=lambda d: d["uf"].map(UF_DO_CODIGO)))
    pib = sidra("https://apisidra.ibge.gov.br/values/t/5938/n3/all/v/37/p/2023", AUX / "pib_uf_2023.csv",
                lambda l: pd.DataFrame({"uf": [x["D1C"] for x in l], "pib": [float(x["V"]) * 1000 for x in l]})
                .assign(uf=lambda d: d["uf"].map(UF_DO_CODIGO)))
    return pop.merge(pib, on="uf").set_index("uf")


# ---------- tabelas ----------

def agregar(df, chave):
    g = df.groupby(chave, observed=True).agg(
        projetos=("pronac", "size"),
        valor_aprovado=("valor_aprovado", "sum"),
        valor_captado=("valor_captado", "sum"),
        projetos_que_captaram=("captou", "sum"),
    )
    g["taxa_captacao"] = g["valor_captado"] / g["valor_aprovado"]
    g["pct_projetos_que_captaram"] = g["projetos_que_captaram"] / g["projetos"]
    g["participacao_no_captado"] = g["valor_captado"] / g["valor_captado"].sum()
    g["participacao_nos_projetos"] = g["projetos"] / g["projetos"].sum()
    return g


def concentracao(df):
    """Curva de concentração da captação entre proponentes (todos os anos)."""
    chave = df["cpf_cnpj"].astype(str) + "|" + df["proponente"].astype(str)
    por_prop = df.assign(chave=chave).groupby("chave")["valor_captado"].sum().sort_values(ascending=False)
    acumulado = por_prop.cumsum() / por_prop.sum()
    x = np.arange(1, len(por_prop) + 1) / len(por_prop)
    def fatia(p):
        return por_prop.iloc[: max(1, int(round(len(por_prop) * p)))].sum() / por_prop.sum()
    return por_prop, x, acumulado.to_numpy(), {p: fatia(p) for p in (0.01, 0.05, 0.10, 0.50)}


# ---------- gráficos ----------

def grafico_serie(por_ano):
    anos = por_ano.index.to_numpy()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    largura = 0.38
    ax.bar(anos - largura / 2 - 0.01, por_ano["valor_aprovado"] / 1e9, largura, color=AZUL,
           label="Valor aprovado", edgecolor=SUPERFICIE, linewidth=1)
    ax.bar(anos + largura / 2 + 0.01, por_ano["valor_captado"] / 1e9, largura, color=LARANJA,
           label="Valor captado", edgecolor=SUPERFICIE, linewidth=1)
    for a in anos:
        r = por_ano.loc[a]
        ax.text(a + largura / 2, r["valor_captado"] / 1e9 + 0.25, pct(r["taxa_captacao"]),
                ha="center", va="bottom", fontsize=8.5, color=TINTA_2)
    ax.axvspan(2022.5, anos.max() + 0.6, color="#f0efec", zorder=0)
    ax.text(2022.6, ax.get_ylim()[1] * 0.97, "Projetos ainda captando,\ntaxas vão subir", va="top",
            fontsize=8.5, color=TINTA_2)
    ax.set_xticks(anos)
    ax.set_xlim(anos.min() - 0.6, anos.max() + 0.6)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"R$ {v:.0f} bi"))
    grade(ax)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.set_title("A partir de 2023, o valor aprovado se multiplica")
    subtitulo(ax, "Valor aprovado e captado por ano do projeto, em R$ bilhões. Acima das barras, % do aprovado que foi captado")
    rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / "01_serie_anual.png", dpi=160)
    plt.close(fig)


def grafico_barras_h(serie, rotulos, titulo, sub, arquivo, formato=pct, media=None):
    serie = serie.sort_values()
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(serie) + 1.6))
    y = np.arange(len(serie))
    ax.barh(y, serie.to_numpy(), height=0.62, color=AZUL, edgecolor=SUPERFICIE, linewidth=1)
    for i, (k, v) in enumerate(serie.items()):
        ax.text(v + serie.max() * 0.01, i, f"{formato(v)}  {rotulos.get(k, '')}", va="center", fontsize=9, color=TINTA_2,
                bbox=dict(facecolor=SUPERFICIE, edgecolor="none", pad=1.5), zorder=3)
    if media is not None:
        ax.axvline(media, color=TINTA_2, linewidth=1, linestyle=(0, (3, 3)))
        ax.text(media, len(serie) - 0.4, f" média {formato(media)}", color=TINTA_2, fontsize=8.5, va="bottom")
    ax.set_yticks(y, serie.index, color=TINTA)
    ax.set_xlim(0, serie.max() * 1.35)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: formato(v)))
    grade(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.set_title(titulo)
    subtitulo(ax, sub)
    rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / arquivo, dpi=160)
    plt.close(fig)


def grafico_concentracao(x, acumulado, fatias, n):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(x * 100, acumulado * 100, color=AZUL, linewidth=2)
    ax.plot([0, 100], [0, 100], color=EIXO, linewidth=1, linestyle=(0, (3, 3)))
    ax.text(62, 55, "Distribuição igual", color=APAGADO, fontsize=8.5, rotation=0)
    for p, pos in ((0.01, (3.5, 50)), (0.10, (12.5, 86))):
        yv = fatias[p] * 100
        ax.plot(p * 100, yv, "o", color=AZUL, markersize=7, markeredgecolor=SUPERFICIE, markeredgewidth=2)
        ax.annotate(f"{pct(p)} dos proponentes\ncaptaram {pct(fatias[p])} do total",
                    (p * 100, yv), xytext=pos, fontsize=9, color=TINTA, va="center" if p == 0.01 else "top")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlabel("Proponentes, do que mais captou para o que menos captou")
    ax.set_ylabel("Parcela acumulada do valor captado")
    grade(ax, "both")
    ax.set_title("A captação é muito concentrada")
    subtitulo(ax, f"Curva de concentração do valor captado entre {inteiro(n)} proponentes com projeto aprovado, 2019 a 2026")
    rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / "03_concentracao.png", dpi=160)
    plt.close(fig)


def grafico_regiao(por_regiao):
    r = por_regiao.sort_values("participacao_no_captado")
    y = np.arange(len(r))
    fig, ax = plt.subplots(figsize=(9, 4.4))
    h = 0.36
    ax.barh(y + h / 2 + 0.01, r["participacao_nos_projetos"], h, color=AZUL, label="Parcela dos projetos aprovados",
            edgecolor=SUPERFICIE, linewidth=1)
    ax.barh(y - h / 2 - 0.01, r["participacao_no_captado"], h, color=LARANJA, label="Parcela do valor captado",
            edgecolor=SUPERFICIE, linewidth=1)
    for i, (_, linha) in enumerate(r.iterrows()):
        ax.text(linha["participacao_nos_projetos"] + 0.006, i + h / 2, pct(linha["participacao_nos_projetos"]),
                va="center", fontsize=8.5, color=TINTA_2)
        ax.text(linha["participacao_no_captado"] + 0.006, i - h / 2, pct(linha["participacao_no_captado"]),
                va="center", fontsize=8.5, color=TINTA_2)
    ax.set_yticks(y, r.index, color=TINTA)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: pct(v)))
    ax.set_xlim(0, max(r["participacao_no_captado"].max(), r["participacao_nos_projetos"].max()) * 1.15)
    grade(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title("O Sudeste capta mais do que sua parcela de projetos")
    subtitulo(ax, f"Projetos aprovados de {COORTE[0]} a {COORTE[1]}, por região do proponente")
    rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / "04_regiao.png", dpi=160)
    plt.close(fig)


def grafico_regiao_pop_pib(r):
    r = r.sort_values("captado")
    y = np.arange(len(r))
    fig, ax = plt.subplots(figsize=(9, 5.2))
    h = 0.26
    series = [("captado", LARANJA, "Parcela do valor captado"), ("pib", VERDE, "Parcela do PIB (2023)"),
              ("populacao", AZUL, "Parcela da população (2022)")]
    for k, (col, cor, rotulo) in enumerate(series):
        pos = y + (1 - k) * (h + 0.02)
        ax.barh(pos, r[col], h, color=cor, label=rotulo, edgecolor=SUPERFICIE, linewidth=1)
        for p, v in zip(pos, r[col]):
            ax.text(v + 0.006, p, pct(v), va="center", fontsize=8.5, color=TINTA_2)
    ax.set_yticks(y, r.index, color=TINTA)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: pct(v)))
    ax.set_xlim(0, r[["captado", "pib", "populacao"]].max().max() * 1.12)
    grade(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title("A captação vai além do peso econômico do Sudeste")
    subtitulo(ax, f"Parcela de cada região no valor captado ({ANOS_COMPLETOS[0]} a {ANOS_COMPLETOS[1]}), no PIB e na população")
    rodape(fig, "Fonte: SALIC (Ministério da Cultura), IBGE (Censo 2022 e Contas Regionais). Elaboração própria.")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / "06_regiao_pop_pib.png", dpi=160)
    plt.close(fig)


def grafico_faixas(f):
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(f))
    ax.bar(x, f["pct_projetos_que_captaram"], 0.6, color=AZUL, edgecolor=SUPERFICIE, linewidth=1)
    for i, (_, l) in enumerate(f.iterrows()):
        ax.text(i, l["pct_projetos_que_captaram"] + 0.015, pct(l["pct_projetos_que_captaram"]), ha="center",
                fontsize=9.5, color=TINTA)
        ax.text(i, 0.02, f"{inteiro(l['projetos'])}\nprojetos", ha="center", va="bottom", fontsize=8,
                color=SUPERFICIE)
    ax.set_xticks(x, f.index, color=TINTA)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: pct(v)))
    grade(ax)
    ax.set_title("Projetos grandes conseguem patrocínio com mais frequência")
    subtitulo(ax, f"Parcela dos projetos que captaram algum valor, por faixa de valor aprovado. Projetos de {COORTE[0]} a {COORTE[1]}")
    rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / "08_faixa_de_valor.png", dpi=160)
    plt.close(fig)


def grafico_concentracao_ano(c):
    fig, ax = plt.subplots(figsize=(9, 5))
    anos = c.index.to_numpy()
    for col, cor, rotulo in (("top82", LARANJA, "82 maiores proponentes"), ("top20", AZUL, "20 maiores proponentes")):
        ax.plot(anos, c[col], color=cor, linewidth=2, marker="o", markersize=7, markeredgecolor=SUPERFICIE,
                markeredgewidth=2, label=rotulo)
        ax.text(anos[0] - 0.15, c[col].iloc[0], pct(c[col].iloc[0]), ha="right", va="center", fontsize=9, color=TINTA_2)
        ax.text(anos[-1] + 0.15, c[col].iloc[-1], pct(c[col].iloc[-1]), ha="left", va="center", fontsize=9, color=TINTA_2)
    ax.axvspan(2022.5, anos.max() + 0.6, color="#f0efec", zorder=0)
    ax.text(2022.6, 0.68, "Projetos ainda captando", fontsize=8.5, color=TINTA_2, va="top")
    ax.set_xticks(anos)
    ax.set_xlim(anos.min() - 0.6, anos.max() + 0.6)
    ax.set_ylim(0, 0.7)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: pct(v)))
    grade(ax)
    ax.legend(frameon=False, loc="upper right", fontsize=9, bbox_to_anchor=(1, 1.0))
    ax.set_title("A fatia dos maiores caiu quando a base de proponentes cresceu")
    subtitulo(ax, "Parcela do valor captado pelos maiores proponentes, por ano do projeto")
    rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / "10_concentracao_por_ano.png", dpi=160)
    plt.close(fig)


def literatura(t, aprovados, coorte):
    """Indicadores que dialogam com os estudos sobre a Lei Rouanet (ver README)."""
    completos = aprovados[aprovados["ano"].between(*ANOS_COMPLETOS)]
    total = completos["valor_captado"].sum()
    ibge = populacao_e_pib()

    # Região contra população e PIB
    ibge_reg = ibge.groupby(ibge.index.map(REGIAO_DA_UF)).sum()
    reg = pd.DataFrame({"captado": completos.groupby("regiao")["valor_captado"].sum() / total,
                        "populacao": ibge_reg["populacao"] / ibge_reg["populacao"].sum(),
                        "pib": ibge_reg["pib"] / ibge_reg["pib"].sum()})
    reg.to_csv(RESULTADOS / "regiao_populacao_pib.csv", encoding="utf-8-sig")
    grafico_regiao_pop_pib(reg)

    # Captado por habitante e em relação ao PIB, por UF
    uf = completos.groupby("uf")["valor_captado"].sum().to_frame("valor_captado").join(ibge)
    uf["por_habitante"] = uf["valor_captado"] / uf["populacao"]
    uf["por_mil_reais_de_pib"] = uf["valor_captado"] / uf["pib"] * 1000
    uf.sort_values("por_habitante", ascending=False).to_csv(RESULTADOS / "uf_por_habitante.csv", encoding="utf-8-sig")
    media = total / ibge["populacao"].sum()
    grafico_barras_h(uf["por_habitante"], {}, "Rio de Janeiro e São Paulo lideram a captação por habitante",
                     f"Valor captado por habitante, projetos de {ANOS_COMPLETOS[0]} a {ANOS_COMPLETOS[1]}, em R$",
                     "07_por_habitante_uf.png", formato=lambda v: f"R$ {v:.0f}", media=media)

    # Faixa de valor aprovado (coorte encerrada)
    faixas = pd.cut(coorte["valor_aprovado"], [0, 1e5, 3e5, 1e6, 3e6, np.inf],
                    labels=["até 100 mil", "100 a 300 mil", "300 mil a 1 mi", "1 a 3 mi", "acima de 3 mi"])
    por_faixa = agregar(coorte.assign(faixa=faixas), "faixa")
    por_faixa.to_csv(RESULTADOS / "por_faixa_de_valor.csv", encoding="utf-8-sig")
    grafico_faixas(por_faixa)

    # Proponentes por região, primeiro e último ano completos
    prop = aprovados.groupby(["regiao", "ano"])["cpf_cnpj"].nunique().unstack()
    ini, fim = ANOS_COMPLETOS
    cresc = (prop[fim] / prop[ini] - 1).rename("crescimento")
    pd.concat([prop[[ini, fim]], cresc], axis=1).to_csv(RESULTADOS / "proponentes_por_regiao.csv", encoding="utf-8-sig")
    grafico_barras_h(cresc, {k: f"({inteiro(prop.loc[k, ini])} para {inteiro(prop.loc[k, fim])})" for k in cresc.index},
                     "O número de proponentes cresceu mais no Nordeste e no Norte",
                     f"Crescimento dos proponentes com projeto aprovado, de {ini} para {fim}",
                     "09_proponentes_por_regiao.png", formato=lambda v: pct(v))

    # Concentração ano a ano (20 e 82 maiores, os recortes usados por Teixeira, Xavier e Faria)
    linhas = {}
    for ano, g in completos.groupby("ano"):
        p = g.groupby("cpf_cnpj")["valor_captado"].sum().sort_values(ascending=False)
        linhas[ano] = {"proponentes": len(p), "proponentes_que_captaram": int((p > 0).sum()),
                       "top20": p.head(20).sum() / p.sum(), "top82": p.head(82).sum() / p.sum()}
    conc = pd.DataFrame(linhas).T
    conc.to_csv(RESULTADOS / "concentracao_por_ano.csv", encoding="utf-8-sig")
    grafico_concentracao_ano(conc)

    # Números citados no README
    capitais = (((completos["municipio"] == "São Paulo") & (completos["uf"] == "SP"))
                | ((completos["municipio"] == "Rio de Janeiro") & (completos["uf"] == "RJ")))
    mun = completos.groupby(["municipio", "uf"])["valor_captado"].sum()
    return {
        f"parcela do Sudeste no captado ({ini} a {fim})": pct(reg.loc["Sudeste", "captado"], 1),
        "parcela do Sudeste no PIB (2023)": pct(reg.loc["Sudeste", "pib"], 1),
        "parcela do Sudeste na população (2022)": pct(reg.loc["Sudeste", "populacao"], 1),
        "parcela do Norte e Nordeste no captado": pct(reg.loc[["Norte", "Nordeste"], "captado"].sum(), 1),
        "parcela do Norte e Nordeste na população": pct(reg.loc[["Norte", "Nordeste"], "populacao"].sum(), 1),
        "parcela das capitais SP e RJ no captado": pct(completos.loc[capitais, "valor_captado"].sum() / total),
        "municípios de proponentes que captaram algo": inteiro((mun > 0).sum()),
        "parcela do captado pelo Artigo 18 (dedução integral)":
            pct(completos.loc[completos["enquadramento"] == "Artigo 18", "valor_captado"].sum() / total, 1),
        "parcela do captado por planos anuais":
            pct(completos.loc[completos["tipicidade"] == "Planos Anuais", "valor_captado"].sum() / total),
        "captado por habitante, média do Brasil": f"R$ {media:.0f}",
        "captado por habitante, SP": f"R$ {uf.loc['SP', 'por_habitante']:.0f}",
        "captado por habitante, RJ": f"R$ {uf.loc['RJ', 'por_habitante']:.0f}",
        "UFs abaixo de R$ 15 por habitante": inteiro((uf["por_habitante"] < 15).sum()),
    }


# ---------- principal ----------

def analisar():
    for p in (RESULTADOS, FIGURAS, PAINEL):
        p.mkdir(parents=True, exist_ok=True)

    t = pd.read_csv(ENTRADA, encoding="utf-8-sig", dtype={"pronac": str, "cpf_cnpj": str},
                    parse_dates=["data_inicio", "data_termino"], low_memory=False)
    t = t[t["ano"] >= 2019]                                  # 2016 e 2018 têm um projeto cada
    aprovados = t[t["aprovado"]]
    coorte = aprovados[aprovados["ano"].between(*COORTE)]

    # Série anual
    por_ano = agregar(aprovados, "ano")
    por_ano.to_csv(RESULTADOS / "por_ano.csv", encoding="utf-8-sig")
    grafico_serie(por_ano)

    # Área cultural
    por_area = agregar(coorte, "area").sort_values("taxa_captacao", ascending=False)
    por_area.to_csv(RESULTADOS / "por_area.csv", encoding="utf-8-sig")
    taxa_media = coorte["valor_captado"].sum() / coorte["valor_aprovado"].sum()
    grafico_barras_h(
        por_area["taxa_captacao"],
        {k: f"({inteiro(v)} projetos)" for k, v in por_area["projetos"].items()},
        "Museus captam mais, festas e cultura popular bem menos",
        f"Parcela do valor aprovado que foi captada, por área cultural. Projetos de {COORTE[0]} a {COORTE[1]}, média geral {pct(taxa_media)}",
        "02_taxa_por_area.png")

    # Região e UF
    por_regiao = agregar(coorte, "regiao")
    por_regiao.to_csv(RESULTADOS / "por_regiao.csv", encoding="utf-8-sig")
    grafico_regiao(por_regiao)
    agregar(coorte, "uf").sort_values("valor_captado", ascending=False).to_csv(RESULTADOS / "por_uf.csv", encoding="utf-8-sig")

    # Tipo de proponente
    por_tipo = agregar(coorte, "tipo_proponente")
    por_tipo.to_csv(RESULTADOS / "por_tipo_proponente.csv", encoding="utf-8-sig")

    # Concentração (todos os anos, só projetos aprovados)
    por_prop, x, acumulado, fatias = concentracao(aprovados)
    grafico_concentracao(x, acumulado, fatias, len(por_prop))

    # Maiores captadores, só pessoas jurídicas (nomes de pessoas físicas ficam de fora)
    pj = aprovados[aprovados["tipo_proponente"] == "Pessoa jurídica"]
    top = (pj.groupby(["proponente", "uf"])
             .agg(projetos=("pronac", "size"), valor_captado=("valor_captado", "sum"))
             .sort_values("valor_captado", ascending=False).head(20))
    top["participacao_no_total_captado"] = top["valor_captado"] / aprovados["valor_captado"].sum()
    top.to_csv(RESULTADOS / "top20_proponentes_pj.csv", encoding="utf-8-sig")

    # Números de destaque
    resumo = {
        "projetos na base (2019 a 2026)": inteiro(len(t)),
        "projetos aprovados": inteiro(len(aprovados)),
        "valor aprovado total": reais(aprovados["valor_aprovado"].sum()),
        "valor captado total": reais(aprovados["valor_captado"].sum()),
        f"coorte {COORTE[0]} a {COORTE[1]}, projetos aprovados": inteiro(len(coorte)),
        f"coorte {COORTE[0]} a {COORTE[1]}, % do valor aprovado captado": pct(taxa_media),
        f"coorte {COORTE[0]} a {COORTE[1]}, % dos projetos que captaram algo": pct(coorte["captou"].mean()),
        "proponentes com projeto aprovado": inteiro(len(por_prop)),
        "parcela do captado com o 1% maior": pct(fatias[0.01]),
        "parcela do captado com os 10% maiores": pct(fatias[0.10]),
        "proponentes que não captaram nada": pct((por_prop == 0).mean()),
    }
    resumo.update(literatura(t, aprovados, coorte))
    pd.Series(resumo, name="valor").rename_axis("indicador").to_csv(RESULTADOS / "resumo.csv", encoding="utf-8-sig")

    # Base para o Power BI (pt-BR)
    t.to_csv(PAINEL / "projetos_powerbi.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig",
             date_format="%Y-%m-%d")

    print("Resumo")
    for k, v in resumo.items():
        print(f"  {k}: {v}")
    print("\nPor área (coorte)")
    print(por_area[["projetos", "taxa_captacao", "pct_projetos_que_captaram"]].round(3).to_string())
    print("\nPor região (coorte)")
    print(por_regiao[["projetos", "participacao_nos_projetos", "participacao_no_captado", "taxa_captacao"]].round(3).to_string())
    print("\nPor tipo de proponente (coorte)")
    print(por_tipo[["projetos", "taxa_captacao", "pct_projetos_que_captaram"]].round(3).to_string())
    print("\nTop 5 PJ")
    print(top.head(5).to_string())


if __name__ == "__main__":
    analisar()

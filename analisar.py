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

COORTE = (2019, 2022)          # anos com prazo de captação já encerrado

# Paleta e tinta (referência de visualização, modo claro)
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
APAGADO = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
AZUL = "#2a78d6"               # série 1
LARANJA = "#eb6834"            # série 2

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
    ax.text(0, 1.025, texto, transform=ax.transAxes, color=TINTA_2, fontsize=9.5, va="bottom")


def rodape(fig, texto="Fonte: SALIC, Ministério da Cultura (API de dados abertos). Elaboração própria."):
    fig.text(0.01, 0.01, texto, color=APAGADO, fontsize=8, ha="left", va="bottom")


def grade(ax, eixo="y"):
    ax.grid(axis=eixo, color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


# ---------- tabelas ----------

def agregar(df, chave):
    g = df.groupby(chave).agg(
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

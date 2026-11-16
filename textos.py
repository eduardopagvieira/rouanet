"""
Análise do texto dos projetos da Lei Rouanet.

Pergunta. O jeito como o proponente descreve o projeto diz algo sobre a chance de conseguir patrocínio?

Lê o resumo e os objetivos de cada projeto (dados/projetos_salic.csv.gz, gerado por coletar_salic.py) e
usa só os projetos aprovados da coorte 2019 a 2022, cujo prazo de captação já terminou. Faz duas coisas.

1. Palavras que separam quem captou de quem não captou. Usa o log da razão de chances com prior de
   Dirichlet informativo (Monroe, Colaresi e Quinn, 2008, "Fightin' Words"), um método comum na ciência
   política para comparar o vocabulário de dois grupos sem dar peso demais a palavras raras. Cada
   palavra conta uma vez por projeto. A comparação é feita dentro de cada área cultural e depois
   somada, para que uma palavra de música não pareça boa só porque música capta mais.

2. Temas. Um modelo de tópicos (NMF sobre TF-IDF) agrupa os resumos em temas. Para cada tema calcula a
   taxa de captação e a compara com a de projetos da mesma área, região e faixa de valor, com uma
   regressão logística.

Gera
    resultados/texto_palavras.csv   palavras com z de cada lado
    resultados/texto_temas.csv      temas com palavras, projetos, taxa bruta e efeito ajustado
    figuras/12_palavras.png
    figuras/13_temas.png

Uso
    python textos.py
"""

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

import analisar as A

TEXTOS = Path("dados/projetos_salic.csv.gz")
N_TEMAS = 14
SEMENTE = 7

PARADAS = set("""
a à ao aos as às até com como da das de dela dele deles do dos e é ela elas ele eles em entre era essa
esse esta está estão este eu foi foram há isso isto já la lhe mais mas me mesmo meu minha muito na nas
nem no nos nós num numa o os ou para pela pelas pelo pelos por qual quando que quem se sem ser seu seus
sua suas só também te tem têm ter um uma umas uns vai você será serão sendo sobre cada todo toda todos
todas outro outra outros outras onde assim bem através além durante após partir forma meio
projeto projetos proposta presente objetivo objetivos objetivo_geral geral especifico especificos
realizar realização realizacao promover visa visando busca buscando pretende consiste ser sera serao
cultura cultural culturais atividades atividade ações acao acoes ano anos meses dias edição edicao
lei rouanet incentivo artigo
""".split())


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


PARADAS = {sem_acento(p) for p in PARADAS}


def preparar(texto):
    texto = sem_acento(str(texto).lower())
    texto = re.sub(r"[^a-z\s]", " ", texto)
    return " ".join(p for p in texto.split() if len(p) > 2 and p not in PARADAS)


def carregar():
    t = pd.read_csv(A.ENTRADA, encoding="utf-8-sig", low_memory=False,
                    usecols=["pronac", "ano", "regiao", "area", "aprovado", "captou", "valor_aprovado", "valor_captado"])
    t = t[t["aprovado"] & t["ano"].between(*A.COORTE)].copy()
    txt = pd.read_csv(TEXTOS, usecols=["PRONAC", "resumo", "objetivos"]).rename(columns={"PRONAC": "pronac"})
    t = t.merge(txt, on="pronac", how="left")
    t["texto"] = (t["resumo"].fillna("") + " " + t["objetivos"].fillna("")).map(preparar)
    t["faixa"] = pd.cut(t["valor_aprovado"], [0, 1e5, 3e5, 1e6, 3e6, np.inf],
                        labels=["até 100 mil", "100 a 300 mil", "300 mil a 1 mi", "1 a 3 mi", "mais de 3 mi"])
    return t[t["texto"].str.len() > 0].reset_index(drop=True)


def log_odds(X, grupo, vocab, prior=None):
    """z do log da razão de chances com prior de Dirichlet informativo. Positivo = mais comum no grupo."""
    y1 = np.asarray(X[grupo].sum(axis=0)).ravel()
    y2 = np.asarray(X[~grupo].sum(axis=0)).ravel()
    tot = y1 + y2
    a = prior if prior is not None else tot / tot.sum() * tot.sum() * 0.01
    a0 = a.sum()
    n1, n2 = y1.sum(), y2.sum()
    delta = np.log((y1 + a) / (n1 + a0 - y1 - a)) - np.log((y2 + a) / (n2 + a0 - y2 - a))
    var = 1 / (y1 + a) + 1 / (y2 + a)
    return pd.Series(delta / np.sqrt(var), index=vocab)


def acentos(t):
    """Forma acentuada mais comum de cada palavra, só para exibir."""
    from collections import Counter
    c = Counter(re.findall(r"[a-zà-ü]+", " ".join(t["resumo"].fillna("").str.lower().sample(4000, random_state=1))))
    forma = {}
    for w, _ in c.most_common():
        forma.setdefault(sem_acento(w), w)
    return lambda frase: " ".join(forma.get(w, w) for w in frase.split())


def palavras(t):
    vet = CountVectorizer(binary=True, min_df=40, ngram_range=(1, 2))
    X = vet.fit_transform(t["texto"])
    vocab = vet.get_feature_names_out()
    # prior vem do corpus inteiro, então palavras ausentes numa área não geram divisão por zero
    geral = np.asarray(X.sum(axis=0)).ravel() + 1.0
    zs, pesos = [], []
    for area, idx in t.groupby("area").groups.items():
        sub = t.loc[idx]
        if sub["captou"].nunique() < 2 or len(sub) < 300:
            continue
        prior = geral / geral.sum() * len(sub) * 2
        zs.append(log_odds(X[idx], sub["captou"].to_numpy(), vocab, prior))
        pesos.append(len(sub))
    # soma de Stouffer ponderada pelo tamanho da área
    w = np.sqrt(np.array(pesos, dtype=float))
    z = sum(zi * wi for zi, wi in zip(zs, w)) / np.sqrt((w ** 2).sum())
    docs = np.asarray(X.sum(axis=0)).ravel()
    out = pd.DataFrame({"palavra": vocab, "z": z.to_numpy(), "projetos": docs})
    out["palavra"] = out["palavra"].map(acentos(t))
    return out.sort_values("z", ascending=False).reset_index(drop=True)


def temas(t):
    vet = TfidfVectorizer(min_df=30, max_df=0.4, ngram_range=(1, 2), sublinear_tf=True)
    X = vet.fit_transform(t["texto"])
    nmf = NMF(n_components=N_TEMAS, random_state=SEMENTE, init="nndsvda", max_iter=400)
    W = nmf.fit_transform(X)
    vocab = vet.get_feature_names_out()
    topo = [", ".join(vocab[i] for i in comp.argsort()[::-1][:10]) for comp in nmf.components_]
    t = t.assign(tema=W.argmax(axis=1), peso=W.max(axis=1))
    return t, topo



# Nomes dados aos temas depois de ler as palavras e uma amostra de textos de cada um.
# A ordem segue o NMF com N_TEMAS = 14 e SEMENTE = 7. Se mudar um dos dois, revise os nomes.
NOMES = {
    0: "Música instrumental e concertos",
    1: "Objetivos da lei citados (formulário de 2022)",
    2: "Livros e publicações",
    3: "Objetivos copiados do artigo 1º da lei",
    4: "Gravação de disco com texto modelo",
    5: "Temporada de teatro em São Paulo e Rio",
    6: "Documentários e curtas",
    7: "Oficinas para crianças e jovens",
    8: "Exposições de artes visuais",
    9: "Espetáculos de dança, circo e teatro",
    10: "Festivais e mostras de cinema",
    11: "Carnaval e escolas de samba",
    12: "Ações com escolas públicas",
    13: "Museus, acervo e patrimônio",
}
GENERICOS = {3, 4}   # temas definidos por texto padronizado, não pelo conteúdo


def ajustar(t):
    """Taxa de captação de cada tema se todos os projetos tivessem esse tema, mantendo área, região,
    faixa de valor e ano como estão (padronização pela regressão logística)."""
    d = t.assign(tema=t["tema"].astype(str), captou=t["captou"].astype(int), ano=t["ano"].astype(str),
                 faixa=t["faixa"].astype(str))
    m = smf.logit("captou ~ C(tema) + C(area) + C(regiao) + C(faixa) + C(ano)", d).fit(disp=0)
    return {int(k): float(m.predict(d.assign(tema=k)).mean()) for k in sorted(d["tema"].unique(), key=int)}


def grafico_palavras(p):
    uni = p[~p["palavra"].str.contains(" ")]
    pos, neg = uni.head(12), uni.tail(12).iloc[::-1]
    fig, axs = A.plt.subplots(1, 2, figsize=(10, 5.2))
    for ax, d, cor, titulo in [(axs[0], neg, A.LARANJA, "Mais comuns entre os que não captaram"),
                               (axs[1], pos, A.AZUL, "Mais comuns entre os que captaram")]:
        y = np.arange(len(d))[::-1]
        ax.barh(y, d["z"].abs(), color=cor, height=0.62)
        ax.set_yticks(y, d["palavra"])
        ax.set_title(titulo, fontsize=10.5, pad=8)
        A.grade(ax, "x")
        ax.set_xlabel("z do log da razão de chances (dentro da área)")
    fig.suptitle("As palavras que separam quem conseguiu patrocínio", x=0.01, ha="left", fontweight="bold", fontsize=13)
    fig.text(0.01, 0.92, "Resumo e objetivos de projetos aprovados de 2019 a 2022, cada palavra conta uma vez por projeto",
             color=A.TINTA_2, fontsize=9.5)
    A.rodape(fig)
    fig.tight_layout(rect=(0, 0.04, 1, 0.9))
    fig.savefig(A.FIGURAS / "12_palavras.png", dpi=160)
    A.plt.close(fig)


def grafico_temas(r, media):
    r = r.sort_values("ajustada")
    fig, ax = A.plt.subplots(figsize=(9, 6))
    y = np.arange(len(r))
    cores = [A.LARANJA if g else A.AZUL for g in r["generico"]]
    ax.hlines(y, r[["bruta", "ajustada"]].min(axis=1), r[["bruta", "ajustada"]].max(axis=1), color=A.GRADE, lw=2)
    ax.scatter(r["bruta"], y, s=34, facecolor=A.SUPERFICIE, edgecolor=cores, lw=1.6, zorder=3, label="Taxa observada")
    ax.scatter(r["ajustada"], y, s=44, color=cores, zorder=4, label="Ajustada por área, região, valor e ano")
    ax.axvline(media, color=A.EIXO, lw=1, ls="--")
    ax.set_yticks(y, r["nome"])
    ax.xaxis.set_major_formatter(A.mticker.FuncFormatter(lambda v, _: A.pct(v)))
    ax.set_xlim(0, 0.85)
    A.grade(ax, "x")
    ax.set_title("Texto genérico, menos patrocínio")
    A.subtitulo(ax, "Parcela dos projetos que captaram, por tema do resumo. Laranja são temas de texto padronizado")
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="o", ls="", mfc=A.SUPERFICIE, mec=A.TINTA_2, mew=1.6, label="Taxa observada"),
                       Line2D([], [], marker="o", ls="", color=A.TINTA_2, label="Ajustada por área, região, valor e ano")],
              loc="lower right", frameon=False, fontsize=9)
    A.rodape(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(A.FIGURAS / "13_temas.png", dpi=160)
    A.plt.close(fig)


def main():
    t = carregar()
    p = palavras(t)
    p.to_csv(A.RESULTADOS / "texto_palavras.csv", index=False, encoding="utf-8-sig", float_format="%.3f")
    t, topo = temas(t)
    adj = ajustar(t)
    r = (t.groupby("tema").agg(projetos=("tema", "size"), bruta=("captou", "mean"),
                               captado=("valor_captado", "sum"), aprovado=("valor_aprovado", "sum"))
           .reset_index())
    r["nome"] = r["tema"].map(NOMES)
    r["palavras"] = r["tema"].map(dict(enumerate(topo)))
    r["ajustada"] = r["tema"].map(adj)
    r["generico"] = r["tema"].isin(GENERICOS)
    r["area_principal"] = r["tema"].map(t.groupby("tema")["area"].agg(lambda s: s.value_counts().index[0]))
    r.sort_values("ajustada", ascending=False).to_csv(A.RESULTADOS / "texto_temas.csv", index=False,
                                                        encoding="utf-8-sig", float_format="%.4f")
    media = t["captou"].mean()
    grafico_palavras(p)
    grafico_temas(r, media)
    print(f"{len(t)} projetos, {media:.1%} captaram")
    print(r.sort_values("ajustada", ascending=False)[["nome", "projetos", "bruta", "ajustada"]].to_string())
    print("palavras +", ", ".join(p[~p.palavra.str.contains(" ")].head(15).palavra))
    print("palavras -", ", ".join(p[~p.palavra.str.contains(" ")].tail(15).palavra))


if __name__ == "__main__":
    main()

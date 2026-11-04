"""
Limpeza dos projetos da Lei Rouanet coletados do SALIC.

Lê dados/projetos_salic.csv.gz (gerado por coletar_salic.py) e grava dados/tratados/projetos.csv,
uma linha por projeto, só com os campos estruturados e as colunas novas abaixo.

Os campos de texto longo (resumo, objetivos, justificativa etc.) ficam de fora porque ocupam
quase 1 GB. Para analisá-los, leia direto do arquivo de entrada com usecols, por exemplo
pd.read_csv("dados/projetos_salic.csv.gz", usecols=["PRONAC", "resumo", "objetivos"]).

Colunas criadas
    ano               ano do projeto com 4 dígitos (a API manda 2 dígitos)
    regiao            região do Brasil a partir da UF
    area              agrupamento dos 123 segmentos em áreas culturais
    etapa             agrupamento das 71 situações em etapas do ciclo do projeto
    tipo_proponente   Pessoa física, MEI ou Pessoa jurídica
    aprovado          projeto que chegou a ter valor aprovado para captar
    captou            captou algum valor
    taxa_captacao     valor captado dividido pelo aprovado
    alerta_valor      marca valores que não fecham (aprovado negativo, captado acima do aprovado)

Uso
    python limpar.py
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

ENTRADA = Path("dados/projetos_salic.csv.gz")
SAIDA = Path("dados/tratados")

TEXTOS = ["resumo", "objetivos", "justificativa", "sinopse", "democratizacao", "acessibilidade",
          "etapa", "ficha_tecnica", "impacto_ambiental", "especificacao_tecnica",
          "estrategia_execucao", "providencia"]

RENOMEAR = {
    "PRONAC": "pronac", "UF": "uf", "cgccpf": "cpf_cnpj",
    "enquadradmento": "enquadramento", "mecanisnmo": "mecanismo",   # erros de digitação da própria API
    "situacao": "situacao_salic",
}

REGIOES = {
    "Norte": "AC AM AP PA RO RR TO", "Nordeste": "AL BA CE MA PB PE PI RN SE",
    "Centro-Oeste": "DF GO MS MT", "Sudeste": "ES MG RJ SP", "Sul": "PR RS SC",
}
UF_REGIAO = {uf: regiao for regiao, ufs in REGIOES.items() for uf in ufs.split()}

# A ordem importa. Vale a primeira regra que casar.
AREAS = [
    ("Equipamentos culturais", r"Constru|Constr/|Implant|Implan\.|equipamentos culturais|EquipamCult|equip cult|"
                               r"Territórios Criativos|Arquitetura|centro comunitário|Cons/Man de salas|edificações"),
    ("Festas e cultura popular", r"Desfile|samba|Cultura Popular|Capoeira|Artesanato|Gastronomia"),
    ("Música", r"Música|Musica|Canto Coral|Ópera"),
    ("Artes cênicas", r"Teatro|Dança|Circo|Formas Animadas|formas animadas|bonecos|mamulengos?"),
    ("Audiovisual", r"\bAV\b|\bAv\b|AV\.|Audiovisual|audiovisua|Games|Jogos eletrônicos|websérie|Websérie|Radio|"
                    r"Radiofônica|radiofônicas|Televisiva|VOD|cinema|Rádios e TVs|Audiovisuais"),
    ("Museus e memória", r"Museu|Museológ|museais|museografia|[Mm]emória"),
    ("Artes visuais", r"Artes Visuais|Exposição Cultural|Artes Plásticas|Fotografia|arte visual|A\.visu"),
    ("Livro e leitura", r"Livro|Literá|Leitu|leitura|literário|publicações|Obras de Referência|Bibli|bibliot|Humanidades"),
    ("Patrimônio", r"[Pp]atrimô|tombad|Restaura|Preserva|[Aa]cervo|arqueológico|bens culturais|bens móveis|Arquiv|registro"),
    ("Formação e economia criativa", r"Educ|[Ee]ducativo|Capacit|[Cc]apacitação|Treinament|Empreend|Pesquisa|Sistem|seminár"),
]

# Etapas do ciclo de um projeto. Também vale a primeira regra que casar.
ETAPAS = [
    ("Indeferido", r"^Indeferido"),
    ("Arquivado ou desistência", r"^Arquiv|arquivamento"),
    ("Irregular", r"Inadimplente|desaprovada|Débito|Tomada de Contas|Prescrição"),
    ("Encerrado sem captar", r"sem captação|Expirado o prazo de captação|insuficiência de captação"),
    ("Prestação de contas", r"[Pp]restação de [Cc]ontas|Análise Financeira|análise financeira|avaliação de resultados|"
                            r"cumprimento de objeto|preditiva|revisão de resultados|Consultoria|^Recurso"),
    ("Em execução", r"em execução|Diligenciado - (Readequação|Monitoramento|movimentação)|"
                    r"Análise de resposta de diligência|suspenso|Análise de Recurso"),
    ("Captando", r"Autorizada a captação|Prorrogação|adequação à realidade|adequado à realidade|"
                 r"portaria de (redução|complementação)|ação continuada"),
    ("Em análise", r"análise técnica|[Ee]dital|avaliação documental|CNIC|Parecer técnico|enquadr|"
                   r"Aguarda publicação de portaria$|portaria de autorização|complementação de documentos"),
]
ETAPAS_NAO_APROVADAS = {"Em análise", "Indeferido"}


def classificar(serie, regras, padrao):
    valores = serie.dropna().unique()
    mapa = {}
    for v in valores:
        mapa[v] = next((nome for nome, regex in regras if re.search(regex, v)), padrao)
    return serie.map(mapa).fillna(padrao), [v for v, k in mapa.items() if k == padrao]


def tipo_proponente(linha):
    doc = re.sub(r"\D", "", str(linha.cpf_cnpj))
    if len(doc) != 14:
        return "Pessoa física"                     # a API mascara o CPF (***123456**)
    if re.match(r"^\d{2}\.\d{3}\.\d{3} ", str(linha.proponente)):
        return "MEI"                               # MEIs aparecem com o CNPJ antes do nome
    return "Pessoa jurídica"


def limpar():
    SAIDA.mkdir(parents=True, exist_ok=True)
    colunas = pd.read_csv(ENTRADA, encoding="utf-8-sig", nrows=0).columns
    estruturadas = [c for c in colunas if c not in TEXTOS]

    t = pd.read_csv(ENTRADA, encoding="utf-8-sig", usecols=estruturadas,
                    dtype={"cgccpf": str, "PRONAC": str})
    t = t.rename(columns=RENOMEAR)
    print(f"{len(t)} projetos lidos")

    for c in ["nome", "proponente", "municipio", "segmento", "situacao_salic", "tipologia", "tipicidade"]:
        t[c] = t[c].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)

    t["ano"] = 2000 + t["ano_projeto"]
    t = t.drop(columns="ano_projeto")
    for c in ["data_inicio", "data_termino"]:
        t[c] = pd.to_datetime(t[c], errors="coerce")

    t["regiao"] = t["uf"].map(UF_REGIAO)
    t["area"], sem_area = classificar(t["segmento"], AREAS, "Outros")
    t["etapa"], sem_etapa = classificar(t["situacao_salic"], ETAPAS, "Outra")
    if sem_area:
        print("Segmentos sem área:", sem_area)
    if sem_etapa:
        print("Situações sem etapa:", sem_etapa)

    t["tipo_proponente"] = t.apply(tipo_proponente, axis=1)

    # Valores
    alerta = pd.Series("", index=t.index)
    negativo = t["valor_aprovado"] < 0
    alerta[negativo] = "aprovado negativo"
    t.loc[negativo, ["valor_aprovado", "valor_projeto"]] = np.nan
    acima = t["valor_captado"] > t["valor_aprovado"] * 1.01
    alerta[acima & ~negativo] = "captado acima do aprovado"
    t["alerta_valor"] = alerta.replace("", pd.NA)

    t["aprovado"] = (t["valor_aprovado"] > 0) & ~t["etapa"].isin(ETAPAS_NAO_APROVADAS)
    t["captou"] = t["valor_captado"] > 0
    t["taxa_captacao"] = np.where(t["aprovado"], t["valor_captado"] / t["valor_aprovado"], np.nan)

    ordem = ["pronac", "nome", "ano", "data_inicio", "data_termino", "uf", "regiao", "municipio",
             "area", "segmento", "tipologia", "tipicidade", "enquadramento", "mecanismo",
             "etapa", "situacao_salic", "proponente", "cpf_cnpj", "tipo_proponente",
             "valor_proposta", "valor_solicitado", "valor_aprovado", "valor_projeto", "valor_captado",
             "outras_fontes", "aprovado", "captou", "taxa_captacao", "alerta_valor", "local_realizacao"]
    t = t[ordem]
    t.to_csv(SAIDA / "projetos.csv", index=False, encoding="utf-8-sig")
    print(f"projetos.csv salvo ({len(t)} linhas, {t.shape[1]} colunas)")
    print("  alertas de valor:", t["alerta_valor"].value_counts().to_dict())
    print("  aprovados:", int(t["aprovado"].sum()), "| captaram algo:", int(t["captou"].sum()))


if __name__ == "__main__":
    limpar()

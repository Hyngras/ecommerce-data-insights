import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import scipy.stats as st
from statsmodels.stats.proportion import proportion_confint
import os

from abt import load_data

'''
Estatísticas descritivas:
- Informações da base
- Gráficos essenciais (salvos em /images)
- Séries temporais
- Logística (atraso, prazo, serviços)
- Pagamentos e conversão
- Elasticidade preço x quantidade
- Outliers (ticket e entrega)
- Intervalos de confiança (IC 95%)
- Exportação opcional para CSV
'''

# ===============================================================
# Preparação
# ===============================================================

# Carregar ABT
df, items = load_data()

# Criar pastas de saída
os.makedirs("images", exist_ok=True)
os.makedirs("output", exist_ok=True)

# Filtros úteis
df_confirmed = df[df["is_confirmed"] == 1].copy()
df_delivered = df[(df["Delivery_Status"].str.lower().isin(["entregue", "atrasado"]))
                  & df["D_Date"].notna()].copy()


# ===============================================================
# KPIs numéricos principais
# ===============================================================

kpis = {
    "ticket_medio": df_confirmed["Total"].mean(),
    "receita_total": df_confirmed["Total"].sum(),
    "subtotal_total": df_confirmed["Subtotal"].sum(),
    "desconto_medio_perc": df_confirmed["Discount"].sum() / df_confirmed["Subtotal"].sum(),
    "take_rate_frete": df_confirmed["freight_share"].mean(),
    "prazo_medio_entrega": df_delivered["delivery_lead_time"].mean(),
    "taxa_atraso": df_delivered["is_late"].mean(),
    "taxa_cancelamento": df["is_canceled"].mean()
}

pd.DataFrame([kpis]).to_csv("output/kpis_gerais.csv", index=False)


# ===============================================================
# Funções de Inferência Estatística
# ===============================================================

def ic_media(data, confidence=0.95):
    if len(data) < 2:
        return (np.nan, np.nan)
    mean = data.mean()
    sem = st.sem(data)
    n = len(data)
    ic = st.t.interval(confidence=confidence, df=n-1, loc=mean, scale=sem)
    return ic


def ic_proporcao(data, confidence=0.95):
    total = len(data)
    if total == 0:
        return (np.nan, np.nan)
    sucessos = data.sum()
    ic = proportion_confint(sucessos, total, alpha=(1 - confidence), method="wilson")
    return ic


inferencias = {
    "ticket_medio": {
        "media": df_confirmed["Total"].mean(),
        "IC95": ic_media(df_confirmed["Total"])
    },
    "prazo_medio_entrega": {
        "media": df_delivered["delivery_lead_time"].mean(),
        "IC95": ic_media(df_delivered["delivery_lead_time"])
    },
    "taxa_atraso": {
        "proporcao": df_delivered["is_late"].mean(),
        "IC95": ic_proporcao(df_delivered["is_late"])
    },
    "taxa_cancelamento": {
        "proporcao": df["is_canceled"].mean(),
        "IC95": ic_proporcao(df["is_canceled"])
    }
}

pd.DataFrame(inferencias).to_csv("output/inferencias.csv")


# ===============================================================
# EDA: Histogramas e Boxplots
# ===============================================================

sns.set_style("whitegrid")

def salvar_fig(nome):
    plt.savefig(f"images/{nome}.png", dpi=150, bbox_inches="tight")
    plt.close()


# Histograma Ticket
plt.figure(figsize=(10, 5))
sns.histplot(df_confirmed["Total"], bins=50, kde=True)
plt.title("Distribuição do Ticket (Pedidos Confirmados)")
plt.xlabel("Valor Total (R$)")
plt.ylabel("Contagem")
salvar_fig("hist_ticket")


# Boxplot Ticket
plt.figure(figsize=(8, 4))
sns.boxplot(x=df_confirmed["Total"])
plt.title("Boxplot do Ticket (Pedidos Confirmados)")
salvar_fig("box_ticket")


# Histograma Desconto
plt.figure(figsize=(10, 5))
sns.histplot(df_confirmed["Discount"], bins=40, kde=True)
plt.title("Distribuição do Desconto")
salvar_fig("hist_discount")


# Histograma Lead Time
if not df_delivered.empty:
    plt.figure(figsize=(10, 5))
    sns.histplot(df_delivered["delivery_lead_time"], bins=40, kde=True)
    plt.title("Distribuição do Prazo de Entrega")
    plt.xlabel("Dias")
    plt.ylabel("Contagem")
    salvar_fig("hist_prazo_entrega")


# ===============================================================
# Sazonalidade
# ===============================================================

df_confirmed["mes"] = df_confirmed["Order_Date"].dt.to_period("M").astype(str)

receita_mensal = df_confirmed.groupby("mes")["Total"].sum().reset_index()

plt.figure(figsize=(12, 5))
sns.lineplot(data=receita_mensal, x="mes", y="Total", marker="o")
plt.title("Receita Mensal")
plt.xticks(rotation=45)
salvar_fig("receita_mensal")


# ===============================================================
# Performance Logística
# ===============================================================

# Atraso por Serviço
if not df_delivered.empty:
    atraso_serv = df_delivered.groupby("Service")["is_late"].mean().reset_index()

    plt.figure(figsize=(8, 4))
    ax = sns.barplot(data=atraso_serv, x="Service", y="is_late")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    plt.title("Taxa de Atraso por Serviço")
    salvar_fig("atraso_por_service")


# Atraso por Região
if not df_delivered.empty:
    atraso_reg = df_delivered.groupby("Region")["is_late"].mean().reset_index()

    plt.figure(figsize=(8, 4))
    ax = sns.barplot(data=atraso_reg, x="Region", y="is_late")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    plt.title("Taxa de Atraso por Região")
    salvar_fig("atraso_por_regiao")


# ===============================================================
# Elasticidade (Desconto vs Quantidade)
# ===============================================================

items_confirmed = items.merge(
    df_confirmed[["order_id", "Discount", "Subtotal"]],
    left_on="Id",
    right_on="order_id",
    how="inner"
)

items_confirmed["discount_perc"] = items_confirmed["Discount"] / items_confirmed["Subtotal"]

# bins usados pelo notebook original
bins = [-0.01, 0, 0.05, 0.10, 0.15, 0.20, 1]
labels = ["0%", "0-5%", "5-10%", "10-15%", "15-20%", ">20%"]

items_confirmed["faixa"] = pd.cut(items_confirmed["discount_perc"], bins=bins, labels=labels)

elastic = items_confirmed.groupby("faixa")["Quantity"].mean().reset_index()

plt.figure(figsize=(10, 4))
sns.barplot(data=elastic, x="faixa", y="Quantity")
plt.title("Elasticidade: Quantidade Média por Faixa de Desconto")
salvar_fig("elasticidade")


# ===============================================================
# Final
# ===============================================================

print("EDA concluído com sucesso.")
print("Gráficos salvos na pasta /images")
print("KPIs salvos em output/kpis_gerais.csv")
print("Inferências salvas em output/inferencias.csv")

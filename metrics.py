import numpy as np
import pandas as pd
import scipy.stats as st
from statsmodels.stats.proportion import proportion_confint

'''
Aqui fazKPI financeiros
- KPI logísticos
- KPI de conversão
- Elasticidade preço × quantidade
- Outliers (ticket e lead-time)
- Intervalos de confiança (média e proporção)
- Retorna tudo de forma organizada em dicionários (ideal para Streamlit depois)
'''

# ================================
# INTERVALOS DE CONFIANÇA
# ================================

def ic_media(data, confidence=0.95):
    data = pd.Series(data).dropna()
    if len(data) < 2:
        return (np.nan, np.nan)
    n = len(data)
    mean = data.mean()
    sem = st.sem(data)
    ic = st.t.interval(confidence, n - 1, loc=mean, scale=sem)
    return ic


def ic_proporcao(data, confidence=0.95):
    data = pd.Series(data).dropna()
    total = len(data)
    if total == 0:
        return (np.nan, np.nan)
    sucessos = data.sum()
    ic = proportion_confint(
        count=sucessos,
        nobs=total,
        alpha=(1 - confidence),
        method="wilson"
    )
    return ic


# ================================
# KPIs NUMÉRICOS
# ================================

def compute_kpis(df):
    df_confirmed = df[df["is_confirmed"] == 1]
    df_delivered = df[(df["D_Date"].notna()) & df["delivery_lead_time"].notna()]

    return {
        "receita_total": df_confirmed["Total"].sum(),
        "ticket_medio": df_confirmed["Total"].mean(),
        "subtotal_total": df_confirmed["Subtotal"].sum(),
        "desconto_medio": df_confirmed["Discount"].sum() / df_confirmed["Subtotal"].sum(),
        "take_rate_frete": df_confirmed["freight_share"].mean(),
        "prazo_medio_entrega": df_delivered["delivery_lead_time"].mean(),
        "taxa_atraso": df_delivered["is_late"].mean(),
        "taxa_cancelamento": df["is_canceled"].mean(),
        "qtd_pedidos": len(df)
    }


# ================================
# ELASTICIDADE
# ================================

def elasticidade(items, df_confirmed):
    df = items.merge(
        df_confirmed[["order_id", "Discount", "Subtotal"]],
        left_on="Id",
        right_on="order_id",
        how="inner"
    )
    df["discount_perc"] = df["Discount"] / df["Subtotal"]

    bins = [-0.01, 0, 0.05, 0.10, 0.15, 0.20, 1]
    labels = ["0%", "0-5%", "5-10%", "10-15%", "15-20%", ">20%"]

    df["faixa"] = pd.cut(df["discount_perc"], bins=bins, labels=labels)

    return df.groupby("faixa")["Quantity"].mean().reset_index()

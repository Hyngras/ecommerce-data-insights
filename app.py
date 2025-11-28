import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

from abt import load_data
from metrics import compute_kpis, ic_media, ic_proporcao, elasticidade


# ===============================================================
# CONFIGURAÇÃO DA PÁGINA
# ===============================================================

st.set_page_config(
    page_title="E-commerce Analytics",
    layout="wide"
)

st.title("E-commerce Data Insights")


# ===============================================================
# CARREGAR DADOS
# ===============================================================
df, items = load_data()
df_confirmed = df[df["is_confirmed"] == 1]


# ===============================================================
# KPIs GERAIS
# ===============================================================
st.header("Indicadores Principais")

kpis = compute_kpis(df)

col1, col2, col3 = st.columns(3)
col1.metric("Ticket Médio", f"R$ {kpis['ticket_medio']:.2f}")
col2.metric("Receita Total", f"R$ {kpis['receita_total']:.2f}")
col3.metric("Desconto Médio (%)", f"{kpis['desconto_medio']*100:.1f}%")

col4, col5, col6 = st.columns(3)
col4.metric("Take-Rate de Frete", f"{kpis['take_rate_frete']*100:.1f}%")
col5.metric("Prazo Médio de Entrega", f"{kpis['prazo_medio_entrega']:.1f} dias")
col6.metric("Taxa de Atraso", f"{kpis['taxa_atraso']*100:.1f}%")


# ===============================================================
# SEÇÃO DE GRÁFICOS
# ===============================================================
st.header("Visualizações")

img_dir = "images"

def mostrar_imagem(nome, titulo):
    path = os.path.join(img_dir, nome)
    if os.path.exists(path):
        st.subheader(titulo)
        st.image(path, use_column_width=True)
    else:
        st.warning(f"Imagem não encontrada: {path}")


tabs = st.tabs([
    "Ticket",
    "Descontos",
    "Entrega",
    "Sazonalidade",
    "Atrasos",
    "Elasticidade"
])

with tabs[0]:
    mostrar_imagem("hist_ticket.png", "Histograma do Ticket")
    mostrar_imagem("box_ticket.png", "Boxplot do Ticket")

with tabs[1]:
    mostrar_imagem("hist_discount.png", "Distribuição do Desconto")

with tabs[2]:
    mostrar_imagem("hist_prazo_entrega.png", "Prazos de Entrega")

with tabs[3]:
    mostrar_imagem("receita_mensal.png", "Sazonalidade da Receita")

with tabs[4]:
    mostrar_imagem("atraso_por_service.png", "Atraso por Serviço")
    mostrar_imagem("atraso_por_regiao.png", "Atraso por Região")

with tabs[5]:
    mostrar_imagem("elasticidade.png", "Elasticidade (Desconto vs Quantidade)")


# ===============================================================
# INFERÊNCIA ESTATÍSTICA
# ===============================================================

st.header("Intervalos de Confiança (95%)")

ic1 = ic_media(df_confirmed["Total"])
ic2 = ic_media(df[df["delivery_lead_time"].notna()]["delivery_lead_time"])
ic3 = ic_proporcao(df[df["delivery_lead_time"].notna()]["is_late"])
ic4 = ic_proporcao(df["is_canceled"])

ic_df = pd.DataFrame({
    "KPI": ["Ticket Médio", "Prazo de Entrega", "Taxa de Atraso", "Taxa de Cancelamento"],
    "IC Inferior": [ic1[0], ic2[0], ic3[0], ic4[0]],
    "IC Superior": [ic1[1], ic2[1], ic3[1], ic4[1]]
})

st.dataframe(ic_df)


# ===============================================================
# TABELAS DE DADOS BRUTOS 
# ===============================================================
st.header("Dados Brutos")
if st.checkbox("Mostrar tabelas completas"):
    st.subheader("Pedidos")
    st.dataframe(df)

    st.subheader("Itens")
    st.dataframe(items)

import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# ANALISES ADICIONAIS 
# =========================================================

st.markdown("---")
st.header("Análises Avançadas")

# ---------------------------------------------------------
# 1. Taxa de confirmação por método de pagamento
# ---------------------------------------------------------
st.subheader("Taxa de Confirmação por Método de Pagamento")

conv = df.groupby("Payment_Method")["is_confirmed"].mean().reset_index()
conv["is_confirmed"] = conv["is_confirmed"] * 100

fig_conv = px.bar(
    conv,
    x="Payment_Method",
    y="is_confirmed",
    text="is_confirmed",
    labels={"is_confirmed": "Taxa de Confirmação (%)"},
    title="Taxa de Confirmação por Método de Pagamento"
)
fig_conv.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
st.plotly_chart(fig_conv, use_container_width=True)

# ---------------------------------------------------------
# 2. Performance logística por tipo de serviço
# ---------------------------------------------------------
st.subheader("Performance Logística por Serviço de Entrega")

temp = df[df["delivery_lead_time"].notna()]
lead = temp.groupby("Service")["delivery_lead_time"].mean().reset_index()

fig_lead = px.bar(
    lead,
    x="Service",
    y="delivery_lead_time",
    title="Tempo Médio de Entrega por Serviço",
    labels={"delivery_lead_time": "Dias"}
)
st.plotly_chart(fig_lead, use_container_width=True)

# ---------------------------------------------------------
# 3. Boxplot do prazo por tipo de entrega
# ---------------------------------------------------------
st.subheader("Distribuição do Prazo por Serviço")

fig_box = px.box(
    temp,
    x="Service",
    y="delivery_lead_time",
    title="Boxplot do Prazo de Entrega por Serviço",
    labels={"delivery_lead_time": "Dias"}
)
st.plotly_chart(fig_box, use_container_width=True)

# ---------------------------------------------------------
# 4. Receita por Categoria e Subcategoria
# ---------------------------------------------------------
st.subheader("Receita por Categoria e Subcategoria")

items["Total_Item"] = items["Quantity"] * items["Price"]

cat = items.groupby("Category")["Total_Item"].sum().reset_index()
subcat = items.groupby("Subcategory")["Total_Item"].sum().reset_index()

fig_cat = px.bar(
    cat,
    x="Category",
    y="Total_Item",
    title="Receita por Categoria",
    labels={"Total_Item": "Receita (R$)"}
)
st.plotly_chart(fig_cat, use_container_width=True)

fig_subcat = px.bar(
    subcat,
    x="Subcategory",
    y="Total_Item",
    title="Receita por Subcategoria",
    labels={"Total_Item": "Receita (R$)"}
)
st.plotly_chart(fig_subcat, use_container_width=True)

# ---------------------------------------------------------
# 5. Receita por UF e Região
# ---------------------------------------------------------
st.subheader("Receita por Estado e Região")

merge_geo = df.merge(items[["order_id", "Total_Item"]], on="order_id", how="left")

geo_uf = merge_geo.groupby("UF")["Total_Item"].sum().reset_index()
geo_reg = merge_geo.groupby("Region")["Total_Item"].sum().reset_index()

fig_uf = px.bar(
    geo_uf,
    x="UF",
    y="Total_Item",
    title="Receita por Estado",
)
st.plotly_chart(fig_uf, use_container_width=True)

fig_reg = px.bar(
    geo_reg,
    x="Region",
    y="Total_Item",
    title="Receita por Região",
)
st.plotly_chart(fig_reg, use_container_width=True)

# ---------------------------------------------------------
# 6. Sazonalidade avançada (UF e Região)
# ---------------------------------------------------------
st.subheader("Sazonalidade Geográfica")

df["month"] = df["Order_Date"].dt.to_period("M").astype(str)

sas_uf = df.groupby(["UF", "month"])["Total"].sum().reset_index()

fig_sas_uf = px.line(
    sas_uf,
    x="month",
    y="Total",
    color="UF",
    title="Sazonalidade de Receita por UF"
)
st.plotly_chart(fig_sas_uf, use_container_width=True)

sas_reg = df.groupby(["Region", "month"])["Total"].sum().reset_index()

fig_sas_reg = px.line(
    sas_reg,
    x="month",
    y="Total",
    color="Region",
    title="Sazonalidade de Receita por Região"
)
st.plotly_chart(fig_sas_reg, use_container_width=True)


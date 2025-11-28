import pandas as pd
import numpy as np
'''
Usa TODAS as 5 bases:
- Agrega FACT_Orders corretamente
- Junta FACT + Delivery + Customer
- Junta Shopping + Products

Gera df_abt com:
- logística (lead time, atraso)
- financeiro (subtotal, total, desconto)
- conversão (confirmado/cancelado)
- frete
- sazonalidade (Order_Date)
'''

# ==========================================================
#               FUNÇÃO PRINCIPAL: LOAD_DATA()
# ==========================================================

def load_data():
    # --------------------------------------------
    # 1. CARREGAMENTO DOS DADOS
    # --------------------------------------------
    fact = pd.read_csv("ecommerce_data/FACT_Orders.csv")
    cust = pd.read_csv("ecommerce_data/DIM_Customer.csv")
    prod = pd.read_csv("ecommerce_data/DIM_Products.csv")
    shop = pd.read_csv("ecommerce_data/DIM_Shopping.csv")
    deli = pd.read_csv("ecommerce_data/DIM_Delivery.csv")

    # --------------------------------------------
    # 2. PREPARAR FACT (PEDIDOS)
    # --------------------------------------------
    fact = fact.rename(columns={
        "Id": "order_id",
        "payment": "Payment_Method",
        "Purchase_Status": "Purchase_Status"
    })

    fact["Order_Date"] = pd.to_datetime(fact["Order_Date"], errors="coerce")

    # Agregar pedidos (já vêm agregados, mas garantimos)
    fact_agg = fact.groupby("order_id").agg(
        Order_Date=("Order_Date", "first"),
        Payment_Method=("Payment_Method", "first"),
        Purchase_Status=("Purchase_Status", "first"),
        Subtotal=("Subtotal", "sum"),
        Discount=("Discount", "sum"),
        Total=("Total", "sum")
    ).reset_index()

    # --------------------------------------------
    # 3. PREPARAR DIM DELIVERY
    # --------------------------------------------
    deli = deli.rename(columns={
        "Id": "order_id",
        "Services": "Service",
        "P_Sevice": "P_Service",
        "D_Forecast": "D_Forecast",
        "D_Date": "D_Date",
        "Status": "Delivery_Status"
    })

    deli["D_Forecast"] = pd.to_datetime(deli["D_Forecast"], errors="coerce")
    deli["D_Date"] = pd.to_datetime(deli["D_Date"], errors="coerce")

    # --------------------------------------------
    # 4. PREPARAR DIM CUSTOMER
    # --------------------------------------------
    cust = cust.rename(columns={
        "Id": "order_id",
        "State": "UF",
        "Region": "Region"
    })

    # --------------------------------------------
    # 5. MERGE PRINCIPAL (MODELO ESTRELA)
    # --------------------------------------------
    df = (
        fact_agg
        .merge(deli, on="order_id", how="left")
        .merge(cust[["order_id", "UF", "Region"]], on="order_id", how="left")
    )

    # --------------------------------------------
    # 6. FEATURE ENGINEERING
    # --------------------------------------------
    # prazo do pedido até entrega
    df["delivery_lead_time"] = (df["D_Date"] - df["Order_Date"]).dt.days

    # atraso vs previsão
    df["delivery_delay_days"] = (df["D_Date"] - df["D_Forecast"]).dt.days

    df["is_late"] = (df["delivery_delay_days"] > 0).astype(int)

    df["is_confirmed"] = (df["Purchase_Status"].str.lower() == "confirmado").astype(int)
    df["is_canceled"] = (df["Purchase_Status"].str.lower() == "cancelado").astype(int)

    df["freight_share"] = np.where(df["Total"] > 0, df["P_Service"] / df["Total"], 0)

    # --------------------------------------------
    # 7. REMOVER DATAS IMPOSSÍVEIS
    # --------------------------------------------
    idx_ruins = df[df["D_Date"] < df["Order_Date"]].index
    df = df.drop(idx_ruins)

    # --------------------------------------------
    # 8. PREPARAÇÃO DOS ITENS DO PEDIDO
    # --------------------------------------------

    # SHOPPING
    items = shop.copy()

    # extrair Product_Key
    items["Product_Key"] = items["Item_ID"].str.split(",").str[1]

    # PRODUCTS
    prod["Product_Key"] = prod["Product_Id"].str.split(",").str[1]

    items = items.merge(
        prod[["Product_Key", "Product_Name", "Category", "Subcategory"]],
        on="Product_Key",
        how="left"
    )

    # merge das datas dos pedidos
    items = items.merge(
        fact_agg[["order_id", "Order_Date"]],
        left_on="Id",
        right_on="order_id",
        how="left"
    )

    items["Order_Date"] = pd.to_datetime(items["Order_Date"], errors="coerce")

    # segurança extra
    if "Id" not in items.columns:
        raise Exception("Erro: coluna 'Id' desapareceu em items!")

    return df, items



# ==========================================================
#               EXECUÇÃO DIRETA (DEBUG)
# ==========================================================
if __name__ == "__main__":
    df, items = load_data()

    print("\nTABELA PRINCIPAL (df):")
    print(df.head())

    print("\nITENS (items):")
    print(items.head())

    print("\nLinhas totais:")
    print("df:", len(df))
    print("items:", len(items))

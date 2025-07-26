import streamlit as st
import pandas as pd
import plotly.express as px
from mongo_conn import carregar_dados_em_dataframe

# ───────────────────────────────
# 🎨  Paleta de cores (Excel Eficiente)
# ───────────────────────────────
GREEN_DARK  = "#4C9A2A"
GREEN_LIGHT = "#A8C66C"
ORANGE      = "#F39200"
EXTRA1      = "#6A994E"
EXTRA2      = "#386641"
COLOR_SEQ   = [GREEN_DARK, GREEN_LIGHT, ORANGE, EXTRA1, EXTRA2]

st.set_page_config(page_title="Distribuição de Cargas Brasil", layout="wide", initial_sidebar_state="collapsed")

# CSS quick tuning
st.markdown("""<style>
    #MainMenu, footer {visibility: hidden;}
    .card{background:#1e1e1e;padding:1rem;border-radius:.75rem;text-align:center;color:#fff;box-shadow:0 4px 8px rgba(0,0,0,.15)}
    .title{font-size:1.6rem;font-weight:700;text-align:center;margin:.5rem 0 1rem}
</style>""", unsafe_allow_html=True)

# ───────────────────────────────
# 📊  Mock data
# ───────────────────────────────
REGIOES = ["Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]

df_region = pd.DataFrame({
    "Região": REGIOES,
    "Entregue":  [140, 327, 253, 144, 108],
    "Pendente":  [8,   9,   6,   5,   4],
})

df_region["Total"] = df_region["Entregue"] + df_region["Pendente"]

# df_veic = pd.DataFrame({"Tipo": ["Van", "Fiorino", "Caminhão"], "Quantidade": [15, 8, 12]})

map_data = pd.DataFrame({
    "Região": REGIOES,
    "Lat":  [-15.6, -9.7,  0.5, -22.0, -28.0],
    "Lon":  [-56.1, -39.3, -60.0, -47.0, -51.0],
    "Total": df_region["Total"],
})

# total_pedidos = int(df_region["Total"].sum())

# # Dados de carga por motorista

# df_motorista = pd.DataFrame({
#     "Motorista": ["Carlos Silva", "João Martins"],
#     "Peso (kg)": [950, 580],
#     "Volume (m³)": [4.5, 2.9],
#     "Pedidos": [12, 7]
# })


def carregar_interface():
    # Carregar dados do MongoDB
    df = carregar_dados_em_dataframe("output_llm")

    # Garantir tipos corretos
    df["capacidade_total_unidades"] = pd.to_numeric(df["capacidade_total_unidades"], errors="coerce")
    df["quantidade_atual"] = pd.to_numeric(df["quantidade_atual"], errors="coerce")

    # 1. DataFrame de regiões (agregação por estado)
    df["roteirizado"] = df["motorista_id"].apply(lambda x: "Entregue" if x else "Pendente")
    df_region = df.groupby(["estado", "roteirizado"]).size().unstack(fill_value=0).reset_index()
    df_region["Total"] = df_region["Entregue"] + df_region["Pendente"]
    df_region.rename(columns={"estado": "Região"}, inplace=True)

    # 2. DataFrame de veículos (quantidade por tipo de veículo)
    df_veic = df[df["tipo_veiculo"] != ""].groupby("tipo_veiculo").size().reset_index(name="Quantidade")
    df_veic.rename(columns={"tipo_veiculo": "Tipo"}, inplace=True)

    # 3. DataFrame de motoristas (carga por motorista)
    df_motorista = df[df["motorista_id"] != ""].copy()
    df_motorista = (
        df_motorista.groupby("motorista_nome")
        .agg({
            "capacidade_total_unidades": "first",
            "quantidade_atual": "sum",
            "pedido_id": "count"
        })
        .reset_index()
    )
    df_motorista.columns = ["Motorista", "Peso (kg)", "Volume (m³)", "Pedidos"]
    df_motorista.fillna(0, inplace=True)

    # 4. DataFrame para mapa (com coordenadas aproximadas por estado)
    estados_latlon = {
        "SP": [-23.5, -46.6], "RJ": [-22.9, -43.2], "MG": [-19.9, -43.9],
        "RS": [-30.0, -51.2], "PR": [-25.4, -49.3], "SC": [-27.6, -48.6],
        "BA": [-12.9, -38.5], "PE": [-8.0, -34.9], "CE": [-3.7, -38.5],
        "DF": [-15.8, -47.9], "GO": [-16.6, -49.3], "MT": [-12.6, -55.7],
        "PA": [-1.4, -48.5], "AM": [-3.1, -60.0], "MA": [-2.5, -44.3],
        "PB": [-7.1, -34.8], "RN": [-5.8, -36.6], "AL": [-9.6, -35.7],
        "PI": [-5.0, -42.8], "RO": [-11.5, -63.6], "RR": [2.8, -60.7],
        "SE": [-10.9, -37.1], "AC": [-9.9, -67.8], "TO": [-10.2, -48.3],
        "AP": [0.0, -51.0]
    }
    df_region[["Lat", "Lon"]] = df_region["Região"].apply(lambda uf: pd.Series(estados_latlon.get(uf, [0, 0])))

    # 5. Total de pedidos
    total_pedidos = int(df.shape[0])

    total_pedidos = df.shape[0]
    motoristas_ativos = df[df["motorista_id"] != ""]["motorista_id"].nunique()
    pedidos_roteirizados = df[df["motorista_id"] != ""].shape[0]
    percentual_roteirizado = (pedidos_roteirizados / total_pedidos) * 100 if total_pedidos > 0 else 0


    # Carrega todos os dados da coleção
    df = carregar_dados_em_dataframe("output_llm")

    # ───────────────────────────────
    # 📰  Header + KPIs
    # ───────────────────────────────
    st.image("logo.png", width=200)
    st.markdown("<div class='title'>Dashboard - Distribuição de Cargas Brasil</div>", unsafe_allow_html=True)

    k1,k2,k3 = st.columns(3)

    with k1:
        st.markdown(f"<div class='card'><h4>📦 Total de pedidos</h4><h2>{total_pedidos}</h2></div>", unsafe_allow_html=True)

    with k2:
        st.markdown(f"<div class='card'><h4>🚚 Motoristas ativos</h4><h2>{motoristas_ativos}</h2></div>", unsafe_allow_html=True)

    with k3:
        st.markdown(f"<div class='card'><h4>🎯 Pedidos roteirizados (%)</h4><h2>{percentual_roteirizado:.1f}%</h2></div>", unsafe_allow_html=True)


    st.markdown("\n")

    # ───────────────────────────────
    # 🗺️ + 📊  Primeira linha (lado a lado)
    # ───────────────────────────────
    left, right = st.columns([7,5])

    with left:
        st.markdown("#### 🗺️ Mapa de Pedidos por Região")
        fig_map = px.scatter_mapbox(
            map_data, lat="Lat", lon="Lon", size="Total", color="Região",
            size_max=55, zoom=3.5, mapbox_style="carto-positron",
            color_discrete_sequence=COLOR_SEQ, hover_name="Região")
        fig_map.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=420)
        st.plotly_chart(fig_map, use_container_width=True)

    with right:
        st.markdown("#### 📊 Pedidos por Região (Total)")
        fig_tot = px.bar(df_region, x="Região", y="Total", color="Região", text="Total",
                        color_discrete_sequence=COLOR_SEQ)
        fig_tot.update_layout(height=420, showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
        fig_tot.update_traces(textposition='outside')
        st.plotly_chart(fig_tot, use_container_width=True)

    # ───────────────────────────────
    # 🛻 + 🚚  Segunda linha (lado a lado)
    # ───────────────────────────────
    left2, right2 = st.columns([7,5])

    # Pie de veículos
    with left2:
        st.markdown("#### 🛻 Veículos por Tipo")
        fig_pie = px.pie(
            df_veic,
            names='Tipo',
            values='Quantidade',
            hole=.35,
            color_discrete_sequence=[GREEN_DARK, GREEN_LIGHT, ORANGE]
        )
        # Mostrar valores absolutos em vez de %
        fig_pie.update_traces(textinfo='label+value', texttemplate='%{label}<br>%{value}')
        fig_pie.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # Novo gráfico: Carga por Motorista
    with right2:
        st.markdown("#### 🚚 Carga por Motorista")
        df_melt_m = df_motorista.melt(id_vars="Motorista", value_vars=["Peso (kg)", "Volume (m³)", "Pedidos"],
                                    var_name="Indicador", value_name="Valor")
        fig_driver = px.bar(df_melt_m, x="Motorista", y="Valor", color="Indicador", barmode="group",
                            height=380, color_discrete_sequence=[GREEN_DARK, GREEN_LIGHT, ORANGE])
        fig_driver.update_layout(margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_driver, use_container_width=True)




    # Seleciona os campos mais relevantes
    colunas = [
        "pedido_id",
        "motorista_id",
        "motorista_nome",
        "estado",
        "local_previsto_nova_entrega",
        "motivo_escolha"
    ]

    # Filtra e ordena
    relatorio = df[colunas].copy()
    relatorio.sort_values(by="estado", inplace=True)

    # Exibe os primeiros resultados
    print(relatorio.head(10))

    # Salva em CSV para análise externa (opcional)
    relatorio.to_csv("relatorio_motivos_llm.csv", index=False, encoding="utf-8-sig")


    st.markdown("### 📄 Relatório: Motivos de Escolha do LLM")
    st.dataframe(relatorio, use_container_width=True)

    # Para exportação
    st.download_button(
        label="📥 Baixar CSV",
        data=relatorio.to_csv(index=False, encoding="utf-8-sig"),
        file_name="relatorio_motivos_llm.csv",
        mime="text/csv"
    )

carregar_interface()

from pathlib import Path

import pandas as pd
import streamlit as st

from src.ui.streamlit_upload_page import render_upload_page

# Page configuration
st.set_page_config(
    layout="wide",
    page_title="CRM Destro",
    page_icon="📦"
)

# Custom CSS for modern look
st.markdown("""
    <style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Product cards */
    .product-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .product-code {
        font-size: 0.8em;
        color: #666;
    }
    .product-ean {
        font-size: 0.8em;
        color: #666;
    }
    .product-description {
        font-size: 1.1em;
        font-weight: bold;
        margin: 10px 0;
        color: #333;
    }
    .stock-tag {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        text-transform: uppercase;
    }
    .stock-in {
        background-color: #d4edda;
        color: #155724;
    }
    .stock-out {
        background-color: #f8d7da;
        color: #721c24;
    }
    .price-unit {
        font-size: 1.8em;
        font-weight: bold;
        color: #28a745;
        margin: 10px 0;
    }
    .price-box {
        font-size: 1em;
        color: #666;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("📦 Portal do RCA - Destro")

page = st.sidebar.radio("Navegação", ["Catálogo", "Carga"], index=0)

# Sidebar controls
st.sidebar.header("⚙️ Controle de Precificação")
acm_percent = st.sidebar.number_input(
    "ACM (Flex) %", min_value=0.0, value=0.0, step=0.1)
commission_percent = st.sidebar.number_input(
    "Comissão %", min_value=0.0, value=2.0, step=0.1)
search_term = st.sidebar.text_input("🔍 Buscar por nome ou código", placeholder="Digite para filtrar...")

# Load data with caching


@st.cache_data
def load_data():
    try:
        curated_path = Path("data/curated/curated_app_ready.parquet")
        if not curated_path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(curated_path)
        df["estoque_atual"] = pd.to_numeric(df.get("estoque_atual", 0), errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {str(e)}")
        return pd.DataFrame()


if page == "Carga":
    render_upload_page()
else:
    df = load_data()

    if df.empty:
        st.warning("⚠️ Nenhum dado curated encontrado em data/curated/curated_app_ready.parquet.")
    else:
        if search_term:
            mask = (
                df["codigo_destro"].astype(str).str.contains(search_term, case=False, na=False)
                | df["descricao_produto"].astype(str).str.contains(search_term, case=False, na=False)
                | df.get("ean", pd.Series(dtype=str)).astype(str).str.contains(search_term, case=False, na=False)
            )
            filtered_df = df[mask]
        else:
            filtered_df = df.head(30)

        st.markdown("### 🛒 Catálogo de Produtos")
        cols = st.columns(4)

        for idx, (_, product) in enumerate(filtered_df.iterrows()):
            col = cols[idx % 4]
            acm_factor = 1 + (acm_percent / 100)
            commission_factor = 1 + (commission_percent / 100)
            preco_caixa = float(product.get("preco_base", 0) or 0) * acm_factor * commission_factor

            qtd_caixa = 1
            preco_unitario = preco_caixa / qtd_caixa

            estoque_atual = float(product.get("estoque_atual", 0) or 0)
            classe_estoque = "stock-in" if estoque_atual > 0 else "stock-out"
            texto_estoque = f"{int(estoque_atual)} Cx em Estoque" if estoque_atual > 0 else "Sem Estoque"

            with col:
                st.markdown(
                    f"""
                    <div class="product-card">
                        <div class="product-code">Cód: {product.get('codigo_destro', '')} | EAN: {product.get('ean', '')}</div>
                        <div class="product-description">{product.get('descricao_produto', '')}</div>
                        <div>
                            <span class="stock-tag {classe_estoque}">{texto_estoque}</span>
                        </div>
                        <div class="price-unit">R$ {preco_unitario:.2f} <span style="font-size: 0.4em; color: #666;">/ un</span></div>
                        <div class="price-box">Caixa Fechada: R$ {preco_caixa:.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.button("Adicionar", key=f"btn_{product.get('codigo_destro', idx)}")

# Footer fixo
st.markdown("""
    <div style='position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; background: #f1f1f1; font-size: 12px;'>
        © 2026 Carlos Gonçalves - CRM Destro Abril. Todos os direitos reservados.
    </div>
""", unsafe_allow_html=True)

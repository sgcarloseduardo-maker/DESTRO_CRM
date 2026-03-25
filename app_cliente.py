import streamlit as st
import pandas as pd
import numpy as np
import re
import os
import base64
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(
    page_title="Catálogo de Pedidos - Cliente",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS premium para refinamento visual do CRM cliente
st.markdown("""
<style>
    :root {
        --destro-red: #d72638;
        --destro-red-dark: #b81f30;
        --destro-red-soft: #fdecee;
        --destro-navy: #0f172a;
        --destro-slate: #334155;
        --destro-muted: #64748b;
        --destro-border: #e2e8f0;
        --destro-panel: #ffffff;
        --destro-bg: #f6f8fc;
        --destro-blue-soft: #eef4ff;
        --destro-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        --destro-radius: 18px;
    }

    .stApp {
        background:
            radial-gradient(circle at top right, rgba(215, 38, 56, 0.06), transparent 22%),
            linear-gradient(180deg, #fbfcff 0%, #f6f8fc 100%);
    }

    .main .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1380px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #172033 100%);
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.2rem;
    }

    section[data-testid="stSidebar"] * {
        color: #e5edf8;
    }

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .stText,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #d9e3f0 !important;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stMultiSelect > div > div {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 14px !important;
        color: white !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.09) !important;
    }

    .destro-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        padding: 14px 20px;
        margin-bottom: 18px;
        border: 1px solid rgba(15, 23, 42, 0.07);
        background: rgba(255,255,255,0.85);
        backdrop-filter: blur(10px);
        border-radius: 18px;
        box-shadow: var(--destro-shadow);
    }

    .destro-topbar-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .destro-topbar-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: var(--destro-red-soft);
        color: var(--destro-red-dark);
        border: 1px solid #f8c9cf;
        border-radius: 999px;
        padding: 7px 12px;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .destro-hero {
        position: relative;
        overflow: hidden;
        padding: 28px 30px;
        margin-bottom: 22px;
        border-radius: 26px;
        background: linear-gradient(135deg, #0f172a 0%, #172554 48%, #d72638 140%);
        color: white;
        box-shadow: 0 22px 45px rgba(15, 23, 42, 0.18);
        border: 1px solid rgba(255,255,255,0.08);
    }

    .destro-hero::before,
    .destro-hero::after {
        content: "";
        position: absolute;
        border-radius: 999px;
        background: rgba(255,255,255,0.08);
        filter: blur(1px);
    }

    .destro-hero::before {
        width: 220px;
        height: 220px;
        top: -70px;
        right: -40px;
    }

    .destro-hero::after {
        width: 160px;
        height: 160px;
        bottom: -60px;
        right: 140px;
    }

    .destro-hero-grid {
        position: relative;
        z-index: 2;
        display: grid;
        grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.7fr);
        gap: 24px;
        align-items: center;
    }

    .destro-kicker {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-weight: 800;
        opacity: 0.86;
        margin-bottom: 12px;
    }

    .destro-title {
        font-size: 2.3rem;
        line-height: 1.05;
        font-weight: 900;
        margin: 0 0 12px 0;
        color: white !important;
    }

    .destro-subtitle {
        font-size: 1rem;
        line-height: 1.6;
        color: rgba(255,255,255,0.86);
        max-width: 760px;
        margin: 0;
    }

    .destro-info-card {
        position: relative;
        z-index: 2;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 20px;
        padding: 18px 18px 16px 18px;
        backdrop-filter: blur(10px);
    }

    .destro-info-card-title {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
        color: rgba(255,255,255,0.78);
        margin-bottom: 10px;
    }

    .destro-info-card strong {
        display: block;
        font-size: 1.35rem;
        margin-bottom: 6px;
    }

    .destro-mini-note {
        font-size: 0.92rem;
        color: rgba(255,255,255,0.8);
        line-height: 1.5;
    }

    .destro-section-title {
        font-size: 1.18rem;
        font-weight: 800;
        color: var(--destro-navy);
        margin: 0.2rem 0 0.8rem 0;
    }

    .destro-soft-card {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(15, 23, 42, 0.06);
        border-radius: 18px;
        box-shadow: var(--destro-shadow);
        padding: 12px 14px;
    }

    .destro-footer-note {
        text-align: right;
        color: #7c8ba1;
        font-size: 12px;
        margin-top: -8px;
        margin-bottom: 16px;
        font-weight: 600;
    }

    h1, h2, h3 {
        color: var(--destro-navy);
        letter-spacing: -0.02em;
    }

    h1 {
        font-weight: 900 !important;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
        border: 1px solid rgba(15, 23, 42, 0.07);
        border-radius: 18px;
        padding: 12px 14px;
        box-shadow: var(--destro-shadow);
    }

    div[data-testid="stButton"] > button {
        border-radius: 14px !important;
        border: 1px solid #d9e2ef !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em;
        min-height: 2.9rem !important;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
        transition: all 0.18s ease;
    }

    div[data-testid="stButton"] > button:hover {
        transform: translateY(-1px);
        border-color: #c2cfdf !important;
    }

    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, var(--destro-red) 0%, #ef4444 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 14px 28px rgba(215, 38, 56, 0.24) !important;
    }

    div[data-testid="stDownloadButton"] > button {
        border-radius: 14px !important;
        min-height: 2.95rem !important;
        font-weight: 800 !important;
        border: none !important;
        color: white !important;
        background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%) !important;
        box-shadow: 0 14px 28px rgba(20, 184, 166, 0.24) !important;
    }

    [data-baseweb="select"] > div,
    .stTextInput > div > div,
    .stNumberInput > div > div,
    .stDateInput > div > div,
    .stTextArea textarea {
        border-radius: 14px !important;
        border: 1px solid #d9e2ef !important;
        background: rgba(255,255,255,0.96) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    }

    div[data-testid="stSelectbox"] label,
    div[data-testid="stMultiSelect"] label {
        font-weight: 700 !important;
        color: var(--destro-slate) !important;
    }

    div[data-testid="stVerticalBlock"] div.st-emotion-cache-1wivap2 {
        min-height: 410px !important;
        height: 410px !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
        border: 1px solid rgba(15, 23, 42, 0.06) !important;
        border-radius: 22px !important;
        box-shadow: var(--destro-shadow);
        padding: 8px 8px 10px 8px;
    }

    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 180px !important;
        width: 100% !important;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        overflow: hidden;
        border-radius: 18px;
        border: 1px solid #edf2f7;
    }

    div[data-testid="stImage"] img {
        object-fit: contain !important;
        max-height: 160px !important;
        max-width: 160px !important;
        margin: auto;
        filter: drop-shadow(0 6px 10px rgba(15, 23, 42, 0.08));
    }

    .stCaption {
        color: var(--destro-muted) !important;
        font-weight: 600;
    }

    .tabela-carrinho {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        overflow: hidden;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        box-shadow: var(--destro-shadow);
        background: white;
        font-family: Arial, sans-serif;
    }

    .tabela-carrinho th {
        text-align: center;
        padding: 10px 8px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-bottom: 1px solid #1e293b;
        font-size: 13px;
        font-weight: 800;
        color: #f8fafc;
    }

    .tabela-carrinho td {
        text-align: center;
        padding: 8px 10px !important;
        margin: 0px !important;
        border-bottom: 1px solid #e2e8f0;
        height: 52px !important;
        font-size: 12px !important;
        font-weight: 700;
        color: #1e293b;
        vertical-align: middle;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 320px;
        background: white;
    }

    .tabela-carrinho tr:nth-child(even) td {
        background: #fbfdff;
    }

    .tabela-carrinho img {
        height: 34px !important;
        width: 34px !important;
        object-fit: contain !important;
        vertical-align: middle;
        display: block;
        margin: 0 auto;
    }

    div[data-testid="column"] button {
        padding: 0 !important;
        margin: 0px 0px 4px 0px !important;
        min-height: 52px !important;
        height: 52px !important;
        font-size: 13px !important;
        line-height: 1 !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    div[data-testid="stHorizontalBlock"] {
        align-items: stretch;
    }

    [data-testid="stMarkdownContainer"] hr {
        margin-top: 1rem;
        margin-bottom: 1rem;
        border-color: #e9eef5;
    }

    @media (max-width: 900px) {
        .destro-hero-grid {
            grid-template-columns: 1fr;
        }
        .destro-title {
            font-size: 1.8rem;
        }
        .destro-topbar {
            flex-direction: column;
            align-items: flex-start;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# TOPO INSTITUCIONAL E LOGO
# ==========================================
def obter_logo_destro():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base_dir, "LOGO.png"),
        os.path.join(base_dir, "images.jpg"),
    ]
    for caminho in candidatos:
        if os.path.exists(caminho):
            return caminho
    return None


def renderizar_topo_destro():
    logo_path = obter_logo_destro()

    st.markdown("""
    <div class='destro-topbar'>
        <div class='destro-topbar-left'>
            <div class='destro-topbar-badge'>CRM Cliente • Destro</div>
        </div>
        <div class='destro-footer-note'>Sistema elaborado por EDG ENGENHARIA REPRESENTAÇÕES LTDA</div>
    </div>
    """, unsafe_allow_html=True)

    hero_col1, hero_col2 = st.columns([1.6, 1.0], vertical_alignment="center")

    with hero_col1:
        st.markdown("""
        <div class='destro-hero'>
            <div class='destro-hero-grid'>
                <div>
                    <div class='destro-kicker'>Plataforma Comercial</div>
                    <h1 class='destro-title'>Catálogo de Pedidos DESTRO</h1>
                    <p class='destro-subtitle'>Escolha seus produtos com facilidade, monte seu pedido em poucos cliques e baixe o PDF final para enviar com praticidade.</p>
                </div>
                <div class='destro-info-card'>
                    <div class='destro-info-card-title'>Atendimento rápido</div>
                    <strong>Pedido simples e organizado</strong>
                    <div class='destro-mini-note'>Navegue com facilidade, visualize melhor os produtos e finalize seu pedido de forma clara, rápida e segura.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with hero_col2:
        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown("""
            <div class='destro-soft-card' style='min-height: 210px; display:flex; align-items:center; justify-content:center; text-align:center;'>
                <div>
                    <div style='font-size:12px; font-weight:800; color:#d72638; text-transform:uppercase; letter-spacing:.08em; margin-bottom:8px;'>Marca</div>
                    <div style='font-size:2rem; font-weight:900; color:#0f172a; letter-spacing:-.03em;'>DESTRO</div>
                    <div style='font-size:.96rem; color:#64748b; margin-top:8px;'>Adicione LOGO.png ou images.jpg na pasta do app para exibição automática.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DE IMAGEM E DIRETÓRIOS
# ==========================================
def normalizar_codigo_imagem(codigo: str) -> str:
    if not codigo:
        return ""
    s = str(codigo).split("-")[0]
    return re.sub(r"\D", "", s)


@st.cache_data
def obter_indice_imagens():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pasta_imagens = os.path.join(base_dir, "Base de Imagens")
    idx = {}
    if not os.path.exists(pasta_imagens):
        return idx
    for root, _, files in os.walk(pasta_imagens):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                base = os.path.splitext(fn)[0]
                num = re.sub(r"\D", "", base)
                if num:
                    idx[num] = os.path.join(root, fn)
    return idx


def imagem_para_base64(img_path):
    if img_path and os.path.exists(img_path):
        with open(img_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    return None
# ==========================================
# CARREGAMENTO DOS DADOS E SINÔNIMOS
# ==========================================
def limpar_industria(val):
    val_str = str(val)
    match = re.search(r'\"(.*?)\"', val_str)
    if match:
        return match.group(1).strip()
    return val_str.replace("(", "").replace(")", "").replace("'", "").replace('"', "").split(",")[0].strip()


def manter_categoria_completa(txt):
    s = "" if txt is None else str(txt).strip()
    s = re.sub(r'\s+', ' ', s).strip()
    if s.lower() == "nan" or s == "":
        return ""
    return s


def mapear_sinonimos(desc):
    desc_up = desc.upper()
    sinonimos = []

    if 'P HIG' in desc_up or 'PAPEL HIG' in desc_up or 'P.HIG' in desc_up:
        sinonimos.append('PAPEL HIGIÊNICO')
    if 'LIMP VD' in desc_up or 'LIMP.VD' in desc_up:
        sinonimos.append('LIMPA VIDROS')
    if 'DET ' in desc_up or 'DETERG ' in desc_up:
        sinonimos.append('DETERGENTE')
    if 'ALC ' in desc_up or 'ALC.' in desc_up:
        sinonimos.append('ÁLCOOL')
    if 'DESINF ' in desc_up or 'DESINF.' in desc_up:
        sinonimos.append('DESINFETANTE')
    if 'SAB ' in desc_up or 'SAB.' in desc_up:
        sinonimos.append('SABÃO SABONETE')
    if 'COND ' in desc_up or 'COND.' in desc_up:
        sinonimos.append('CONDICIONADOR')
    if 'SHAMP ' in desc_up or 'SH ' in desc_up:
        sinonimos.append('SHAMPOO')
    if 'AMAC ' in desc_up or 'AMAC.' in desc_up:
        sinonimos.append('AMACIANTE')
    if 'PAP TOA' in desc_up:
        sinonimos.append('PAPEL TOALHA')
    if 'CR DENT' in desc_up or 'CREME DENT' in desc_up:
        sinonimos.append('CREME DENTAL PASTA DE DENTE')
    if 'ESCOVA DENT' in desc_up or 'ESC DENT' in desc_up:
        sinonimos.append('ESCOVA DE DENTE')
    if 'APAR BARBA' in desc_up or 'AP BARBA' in desc_up:
        sinonimos.append('APARELHO DE BARBEAR PRESTOBARBA GILETTE')
    if 'ABS ' in desc_up or 'ABSORV ' in desc_up:
        sinonimos.append('ABSORVENTE')
    if 'FRAL ' in desc_up or 'FRALD ' in desc_up:
        sinonimos.append('FRALDA')
    if 'DESOD ' in desc_up or 'DESODOR ' in desc_up:
        sinonimos.append('DESODORANTE')
    if 'LIMP MULT' in desc_up:
        sinonimos.append('LIMPADOR MULTIUSO')
    if 'AG SANIT' in desc_up or 'AG.SANIT' in desc_up:
        sinonimos.append('ÁGUA SANITÁRIA CÂNDIDA')

    if sinonimos:
        return desc + " [" + ", ".join(sinonimos) + "]"
    return desc


@st.cache_data
def carregar_dados():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_planilha = os.path.join(base_dir, "Programa_Destro-04-03.xlsx")

    if not os.path.exists(caminho_planilha):
        st.error(f"🚨 PLANILHA NÃO ENCONTRADA: '{caminho_planilha}'.")
        return pd.DataFrame()

    try:
        df_ind = pd.read_excel(caminho_planilha, sheet_name="Industrias",
                               skiprows=1, header=None, engine='openpyxl')
        lista_industrias = sorted([i for i in df_ind[0].apply(
            limpar_industria).dropna().unique() if i != ''])
    except Exception:
        lista_industrias = []

    try:
        df_marcas = pd.read_excel(
            caminho_planilha, sheet_name="Marcas", skiprows=1, header=None, engine='openpyxl')
        lista_marcas_reais = sorted([m.strip() for m in df_marcas[0].dropna().astype(
            str) if m.strip().lower() != 'nan' and m.strip() != ''])
    except Exception:
        lista_marcas_reais = []

    marcas_sorted = sorted(lista_marcas_reais, key=len, reverse=True)

    def achar_marca(desc):
        desc_up = str(desc).upper()
        for m in marcas_sorted:
            if re.search(r'\b' + re.escape(m.upper()) + r'\b', desc_up):
                return m
        return 'Outra Marca'

    try:
        df_bateu = pd.read_excel(
            caminho_planilha, sheet_name="BateuLevou", engine='openpyxl')
        df_bateu['Desc_Norm'] = df_bateu['DESCRICAO'].astype(
            str).apply(lambda x: re.sub(r'\s+', ' ', x.strip().upper()))
        dict_bateu_ind = df_bateu.set_index(
            'Desc_Norm')['INDUSTRIA'].to_dict() if 'INDUSTRIA' in df_bateu.columns else {}
        dict_bateu_mar = df_bateu.set_index(
            'Desc_Norm')['MARCA'].to_dict() if 'MARCA' in df_bateu.columns else {}
    except Exception:
        dict_bateu_ind, dict_bateu_mar = {}, {}

    try:
        df = pd.read_excel(caminho_planilha, sheet_name="Banco_Dados_Semanal",
                           skiprows=5, header=None, engine='openpyxl')
        cat_raw = df[1].astype(str)
        mask_categoria = cat_raw.str.match(r'^\s*\d{1,3}\s*-\s*.+')
        df['Categoria'] = cat_raw.where(
            mask_categoria, other=None).ffill().apply(manter_categoria_completa)
        df['Categoria'] = df['Categoria'].replace(
            '', 'Sem Categoria').fillna('Sem Categoria')

        df['Código'] = df[0].astype(str)
        df['Descrição'] = df[2].astype(str).str.strip("* ")

        df = df[(df['Descrição'].str.strip().str.lower() != 'nan')
                & (df['Descrição'].str.strip() != '')]

        df['Desc_Norm'] = df['Descrição'].apply(
            lambda x: re.sub(r'\s+', ' ', str(x).strip().upper()))
        df['Indústria'] = df['Desc_Norm'].map(
            dict_bateu_ind).fillna('Sem Indústria')
        df['Marca'] = df['Desc_Norm'].map(dict_bateu_mar)
        mask_missing = df['Marca'].isna() | (df['Marca'] == '')
        if mask_missing.any():
            df.loc[mask_missing, 'Marca'] = df.loc[mask_missing,
                                                   'Desc_Norm'].apply(achar_marca)

        return df[['Código', 'Descrição', 'Indústria', 'Marca', 'Categoria']].drop_duplicates()

    except Exception as e:
        st.error(f"Erro ao carregar Excel: {e}")
        return pd.DataFrame()


df_raw = carregar_dados()

# ==========================================
# VARIÁVEIS DE SESSÃO
# ==========================================
if 'carrinho' not in st.session_state:
    st.session_state['carrinho'] = {}

if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = 1

if 'busca_manual' not in st.session_state:
    st.session_state['busca_manual'] = None


def resetar_pagina():
    st.session_state['pagina_atual'] = 1


def proxima_pagina():
    st.session_state['pagina_atual'] += 1


def pagina_anterior():
    if st.session_state['pagina_atual'] > 1:
        st.session_state['pagina_atual'] -= 1

# ==========================================
# GERAÇÃO DO PDF
# ==========================================
def remover_fundo_branco(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    datas = img.getdata()
    newData = []
    for r, g, b, a in datas:
        if r > 240 and g > 240 and b > 240:
            newData.append((255, 255, 255, 0))
        else:
            newData.append((r, g, b, a))
    img.putdata(newData)
    return img


def rodape_pdf(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.gray)
    canvas.drawString(
        30, 20, "Sistema elaborado por EDG ENGENHARIA REPRESENTAÇÕES LTDA")
    canvas.restoreState()


def gerar_pdf_pedido(produtos_selecionados):
    img_idx = obter_indice_imagens()
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30,
                            leftMargin=30, topMargin=30, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph("<b>Meu Pedido de Produtos</b>", styles['Title'])
    elements.append(title)

    data_atual = datetime.now().strftime("%d/%m/%Y")
    elements.append(
        Paragraph(f"<b>Data do Pedido:</b> {data_atual}", styles['Normal']))
    elements.append(Spacer(1, 15))

    data = [["Foto", "Código", "Descrição"]]

    for prod in produtos_selecionados:
        codigo = normalizar_codigo_imagem(prod['Código'])
        desc = prod['Descrição']
        img_path = img_idx.get(codigo)

        img_pdf = ""
        if img_path and os.path.exists(img_path):
            try:
                img_pil = Image.open(img_path).convert("RGBA")
                img_pil = remover_fundo_branco(img_pil)
                bbox = img_pil.getbbox()
                if bbox:
                    img_pil = img_pil.crop(bbox)

                img_pil.thumbnail((200, 200), Image.Resampling.LANCZOS)

                bg = Image.new("RGB", img_pil.size, (255, 255, 255))
                bg.paste(img_pil, mask=img_pil.split()[3])

                temp_buffer = BytesIO()
                bg.save(temp_buffer, format="JPEG", quality=95)
                temp_buffer.seek(0)

                img_pdf = RLImage(temp_buffer, width=45,
                                  height=45, kind='proportional')
            except Exception:
                img_pdf = "Sem Foto"
        else:
            img_pdf = "Sem Foto"

        data.append([img_pdf, prod['Código'],
                    Paragraph(desc, styles['Normal'])])

    t = Table(data, colWidths=[70, 100, 360], rowHeights=[
              30] + [55] * len(produtos_selecionados))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#002D62")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LEFTPADDING', (0, 1), (0, -1), 5),
        ('RIGHTPADDING', (0, 1), (0, -1), 5),
        ('TOPPADDING', (0, 1), (0, -1), 5),
        ('BOTTOMPADDING', (0, 1), (0, -1), 5),
    ]))

    elements.append(t)

    doc.build(elements, onFirstPage=rodape_pdf, onLaterPages=rodape_pdf)

    buffer.seek(0)
    return buffer


# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
with st.sidebar:
    logo_sidebar = obter_logo_destro()
    if logo_sidebar:
        st.image(logo_sidebar, use_container_width=True)

    st.markdown("<div class='destro-section-title'>🛒 Resumo do Pedido</div>", unsafe_allow_html=True)

    carrinho_lista = list(st.session_state['carrinho'].values())
    st.write(f"**Itens selecionados:** {len(carrinho_lista)}")

    if len(carrinho_lista) > 0:
        if st.button("🗑️ Limpar Carrinho", use_container_width=True):
            st.session_state['carrinho'] = {}
            st.rerun()

        pdf_buffer = gerar_pdf_pedido(carrinho_lista)
        if pdf_buffer:
            st.download_button(
                label="📥 Baixar PDF",
                data=pdf_buffer,
                file_name="Meu_Pedido.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

    st.divider()
    st.markdown("<div class='destro-section-title'>🔍 Filtros de Busca</div>", unsafe_allow_html=True)

    df_filtrado = df_raw.copy()

    if not df_filtrado.empty:
        industrias_disp = sorted(
            [str(x) for x in df_filtrado['Indústria'].dropna().unique() if str(x).strip() != ''])
        industria_f = st.selectbox("1. Indústria", options=[
                                   'Todas'] + industrias_disp, on_change=resetar_pagina)
        if industria_f != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Indústria'] == industria_f]

        marcas_disp = sorted(
            [str(x) for x in df_filtrado['Marca'].dropna().unique() if str(x).strip() != ''])
        marca_f = st.selectbox("2. Marca", options=[
                               'Todas'] + marcas_disp, on_change=resetar_pagina)
        if marca_f != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Marca'] == marca_f]

        cats_disp = sorted([str(x) for x in df_filtrado['Categoria'].dropna(
        ).unique() if str(x).strip() not in ('', 'Sem Categoria')])
        categoria_f = st.selectbox("3. Categoria", options=[
                                   'Todas'] + cats_disp, on_change=resetar_pagina)
        if categoria_f != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_f]

img_idx_global = obter_indice_imagens()

renderizar_topo_destro()

st.markdown("<div class='destro-section-title'>Catálogo de Produtos</div>", unsafe_allow_html=True)

# ==========================================
# CAMPO DE BUSCA MANUAL
# ==========================================
st.markdown("<div class='destro-section-title'>Selecionar Produtos Manualmente</div>", unsafe_allow_html=True)
if not df_filtrado.empty:
    df_filtrado['Opcao_Busca'] = df_filtrado.apply(
        lambda x: f"{x['Código']} - {mapear_sinonimos(x['Descrição'])}", axis=1)

    def processar_busca_manual():
        val = st.session_state.busca_manual
        if val:
            cod = val.split(" - ")[0].strip()
            row = df_filtrado[df_filtrado['Código'] == cod].iloc[0]
            st.session_state['carrinho'][cod] = {
                'Código': cod,
                'Descrição': row['Descrição'],
                'ImgPath': img_idx_global.get(normalizar_codigo_imagem(cod))
            }
            st.session_state.busca_manual = None

    st.selectbox(
        "Selecionar Produtos pelo Nome ou Código",
        options=df_filtrado['Opcao_Busca'].tolist(),
        index=None,
        placeholder="Digite o nome do produto ou o código interno...",
        key="busca_manual",
        on_change=processar_busca_manual,
        label_visibility="collapsed"
    )

    st.divider()

    # Exibição do Catálogo (Grade)
    itens_por_pagina = 20
    total_paginas = max(1, len(df_filtrado) // itens_por_pagina +
                        (1 if len(df_filtrado) % itens_por_pagina > 0 else 0))

    if st.session_state['pagina_atual'] > total_paginas:
        st.session_state['pagina_atual'] = 1

    pagina_atual = st.session_state['pagina_atual']

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        st.button("⬅️ Página Anterior", on_click=pagina_anterior,
                  disabled=(pagina_atual == 1), use_container_width=True)
    with col_nav2:
        st.markdown(
            f"<h4 style='text-align: center;'>Página {pagina_atual} de {total_paginas}</h4>", unsafe_allow_html=True)
    with col_nav3:
        st.button("Próxima Página ➡️", on_click=proxima_pagina, disabled=(
            pagina_atual == total_paginas), use_container_width=True)
    st.divider()

    inicio = (pagina_atual - 1) * itens_por_pagina
    fim = inicio + itens_por_pagina
    df_exibir = df_filtrado.iloc[inicio:fim]

    for i in range(0, len(df_exibir), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(df_exibir):
                row = df_exibir.iloc[i + j]
                cod = row['Código']
                desc = row['Descrição']
                cod_img = normalizar_codigo_imagem(cod)
                img_path = img_idx_global.get(cod_img)

                with col:
                    with st.container(border=True):
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            st.markdown(
                                "<div style='height: 180px; display: flex; align-items: center; justify-content: center; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); color: #64748b; margin-bottom: 1rem; border-radius: 18px; border: 1px solid #edf2f7;'>Sem Imagem</div>",
                                unsafe_allow_html=True
                            )

                        st.markdown(f"**Cód: {cod}**")
                        desc_curta = desc if len(desc) <= 45 else desc[:42] + "..."
                        st.caption(desc_curta)

                        no_carrinho = cod in st.session_state['carrinho']
                        if no_carrinho:
                            if st.button("❌ Remover", key=f"btn_rem_{cod}", use_container_width=True):
                                del st.session_state['carrinho'][cod]
                                st.rerun()
                        else:
                            if st.button("➕ Adicionar", key=f"btn_add_{cod}", type="primary", use_container_width=True):
                                st.session_state['carrinho'][cod] = {
                                    'Código': cod,
                                    'Descrição': desc,
                                    'ImgPath': img_path
                                }
                                st.rerun()

    st.divider()
    col_nav1_bot, col_nav2_bot, col_nav3_bot = st.columns([1, 2, 1])
    with col_nav1_bot:
        st.button("⬅️ Página Anterior ", key="ant_bot", on_click=pagina_anterior, disabled=(
            pagina_atual == 1), use_container_width=True)
    with col_nav2_bot:
        st.markdown(
            f"<h4 style='text-align: center;'>Página {pagina_atual} de {total_paginas}</h4>", unsafe_allow_html=True)
    with col_nav3_bot:
        st.button("Próxima Página ➡️ ", key="prox_bot", on_click=proxima_pagina, disabled=(
            pagina_atual == total_paginas), use_container_width=True)

else:
    st.warning("Nenhum produto encontrado com os filtros selecionados.")

# ==========================================
# LISTA DE PRODUTOS SELECIONADOS
# ==========================================
st.divider()
st.markdown("<div class='destro-section-title'>📋 Produtos no seu Carrinho</div>", unsafe_allow_html=True)

if len(st.session_state['carrinho']) > 0:

    c_tab, c_btn = st.columns([9, 1])

    with c_tab:
        tabela_html = """<table class='tabela-carrinho'>
<tr>
<th style='width: 10%;'>Foto</th>
<th style='width: 25%;'>Código</th>
<th style='width: 65%;'>Descrição</th>
</tr>"""

        for cod, prod in list(st.session_state['carrinho'].items()):
            img_path = prod.get('ImgPath')
            base64_img = imagem_para_base64(img_path)

            img_tag = f"<img src='data:image/jpeg;base64,{base64_img}'>" if base64_img else "<span style='color: gray; font-size: 8px;'>S/F</span>"

            linha = f"""<tr>
<td>{img_tag}</td>
<td>{cod}</td>
<td>{prod['Descrição']}</td>
</tr>"""
            tabela_html += linha

        tabela_html += "</table>"
        st.html(tabela_html)

    with c_btn:
        st.markdown("<div style='height: 52px;'></div>", unsafe_allow_html=True)

        for cod in list(st.session_state['carrinho'].keys()):
            if st.button("🗑️", key=f"lista_rem_{cod}", help="Remover", use_container_width=True):
                del st.session_state['carrinho'][cod]
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    c_espaco1, btn_limpar, btn_baixar, c_espaco2 = st.columns([2, 2, 2, 2])

    with btn_limpar:
        if st.button("🗑️ Limpar Carrinho", key="botao_limpar_rodape", use_container_width=True):
            st.session_state['carrinho'] = {}
            st.rerun()

    with btn_baixar:
        pdf_buffer_fim = gerar_pdf_pedido(
            list(st.session_state['carrinho'].values()))
        st.download_button(
            label="📥 Baixar PDF",
            data=pdf_buffer_fim,
            file_name="Meu_Pedido.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="botao_baixar_rodape"
        )
else:
    st.info(
        "Nenhum produto adicionado ainda. Escolha produtos na vitrine ou na busca acima.")

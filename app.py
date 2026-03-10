import streamlit as st
import pandas as pd
import numpy as np
import time
import re
import os
import base64
import urllib.parse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO

# ==========================================
# CONFIGURAÇÃO DA PÁGINA (Responsiva)
# ==========================================
st.set_page_config(
    page_title="CRM Destro - RCA",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CSS CUSTOMIZADO (Adaptado para Mobile)
# ==========================================
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    div.stButton > button[kind="primary"] { 
        background-color: #ff4b4b; color: white; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; font-size: 16px; 
    }
    div.stButton > button[kind="secondary"] { 
        background-color: #007BFF; color: white; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; font-size: 16px; border: none;
    }
    div.stButton > button[kind="tertiary"] { 
        background-color: transparent !important; color: #475569 !important; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; font-size: 16px; border: none !important;
        box-shadow: none !important; outline: none !important; padding: 0 !important;
    }
    .titulo-secao { font-size: 24px !important; font-weight: 800 !important; color: #1E293B; text-align: center; margin-bottom: 10px; }
    .subtitulo { font-size: 18px !important; font-weight: 700 !important; color: #334155; }
    /* Ajustes para Mobile: Esconder textos grandes em telas pequenas */
    @media (max-width: 768px) {
        .hide-mobile { display: none !important; }
        .stColumns { flex-direction: column !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# VARIÁVEIS DE SESSÃO
# ==========================================
if 'produtos_selecionados' not in st.session_state: st.session_state['produtos_selecionados'] = []
if 'busca_temp' not in st.session_state: st.session_state.busca_temp = None
if 'num_produtos_layout' not in st.session_state: st.session_state['num_produtos_layout'] = 9
if 'galeria_individuais' not in st.session_state: st.session_state['galeria_individuais'] = []
if 'confirmacao_st' not in st.session_state: st.session_state['confirmacao_st'] = None

# ==========================================
# FUNÇÕES DE APOIO E GERADORES
# ==========================================
def processar_busca(df_filtrado):
    item_escolhido = st.session_state.busca_temp
    if item_escolhido and item_escolhido != "Digite ou selecione um produto...":
        limite = st.session_state['num_produtos_layout']
        if len(st.session_state['produtos_selecionados']) >= limite:
            st.toast(f"🚨 Limite máximo atingido! O layout atual só permite {limite} itens.", icon="⚠️")
        else:
            raw_cod = item_escolhido.split(" | ")[0]
            cod = raw_cod.replace("🔴 [JÁ ADICIONADO] ", "").strip()
            
            if not any(d['Código'] == cod for d in st.session_state['produtos_selecionados']):
                prod_info = df_filtrado[df_filtrado['Código'] == cod].iloc[0]
                st.session_state['produtos_selecionados'].append({
                    'Levar': True, 'Código': cod, 'Status': prod_info['Status'],
                    'Descrição': prod_info['Descrição'], 'Preço Atual': float(prod_info['Preço Atual']),
                    'Comissão': 0.0, 'FLEX': 0.0, 'DESC': 0.0, 'Imposto': False,
                    'Preço Final': float(prod_info['Preço Atual']), 'ST_Flag': prod_info.get('ST_Flag', '')
                })
    st.session_state.busca_temp = None

def mover_cima(index):
    if index > 0:
        lista = st.session_state['produtos_selecionados']
        lista[index], lista[index-1] = lista[index-1], lista[index]

def mover_baixo(index):
    lista = st.session_state['produtos_selecionados']
    if index < len(lista) - 1:
        lista[index], lista[index+1] = lista[index+1], lista[index]

def deletar_item(index):
    st.session_state['produtos_selecionados'].pop(index)

def atualizar_valores_uid(index=None, u_id=None):
    if index is None and u_id is not None:
        index = next((idx for idx, p in enumerate(st.session_state['produtos_selecionados']) if p['Código'] == u_id), None)
    if index is not None:
        prod = st.session_state['produtos_selecionados'][index]
        pr_val = st.session_state.get(f"pr_{u_id}", prod.get('Preço Atual', 0.0))
        co_val = st.session_state.get(f"co_{u_id}", prod.get('Comissão', 0.0))
        fl_val = st.session_state.get(f"fl_{u_id}", prod.get('FLEX', 0.0))
        de_val = st.session_state.get(f"de_{u_id}", prod.get('DESC', 0.0))
        im_val = st.session_state.get(f"im_{u_id}", prod.get('Imposto', False))

        prod['Preço Atual'] = float(pr_val if pr_val is not None else 0.0)
        prod['Comissão'] = float(co_val if co_val is not None else 0.0)
        prod['FLEX'] = float(fl_val if fl_val is not None else 0.0)
        prod['DESC'] = float(de_val if de_val is not None else 0.0)
        prod['Imposto'] = bool(im_val)
        
        calc = prod['Preço Atual'] * (1 + (prod['Comissão'] / 100.0))
        calc = calc * (1 + (prod['FLEX'] / 100.0))
        calc = calc * (1 - (prod['DESC'] / 100.0))
        if prod['Imposto']: calc = calc * 1.101
        prod['Preço Final'] = round(calc, 2)

def step_value(u_id, prefix, delta):
    key = f"{prefix}_{u_id}"
    current_val = st.session_state.get(key, 0.0)
    st.session_state[key] = round((current_val if current_val is not None else 0.0) + delta, 1)
    atualizar_valores_uid(u_id=u_id)

def checar_imposto_st(df):
    alertas = []
    for _, row in df.iterrows():
        if str(row.get('ST_Flag', '')).strip() != '*' and not bool(row.get('Imposto', False)):
            alertas.append(row['Descrição'])
    return alertas

def normalizar_codigo_imagem(codigo: str) -> str:
    if not codigo: return ""
    return re.sub(r"\D", "", str(codigo).split("-")[0])

@st.cache_data
def obter_indice_imagens():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pasta_imagens = os.path.join(base_dir, "Base de Imagens")
    idx = {}
    if not os.path.exists(pasta_imagens): return idx
    for root, _, files in os.walk(pasta_imagens):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                num = re.sub(r"\D", "", os.path.splitext(fn)[0])
                if num: idx[num] = os.path.join(root, fn)
    return idx

def image_to_base64(img_path):
    if img_path and os.path.exists(img_path):
        try:
            with open(img_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except: pass
    return ""

def add_auto_products(df_subset, max_items):
    added = 0
    for _, row in df_subset.iterrows():
        if added >= max_items: break
        cod = row['Código']
        if not any(d['Código'] == cod for d in st.session_state['produtos_selecionados']):
            st.session_state['produtos_selecionados'].append({
                'Levar': True, 'Código': cod, 'Status': row['Status'],
                'Descrição': row['Descrição'], 'Preço Atual': float(row['Preço Atual']),
                'Comissão': 0.0, 'FLEX': 0.0, 'DESC': 0.0, 'Imposto': False,
                'Preço Final': float(row['Preço Atual']), 'ST_Flag': row.get('ST_Flag', '')
            })
            added += 1

# ==========================================
# CARREGAMENTO DOS DADOS (AGORA VIA UPLOAD)
# ==========================================
def limpar_industria(val):
    val_str = str(val)
    match = re.search(r'\"(.*?)\"', val_str)
    if match: return match.group(1).strip()
    return val_str.replace("(", "").replace(")", "").replace("'", "").replace('"', "").split(",")[0].strip()

def manter_categoria_completa(txt):
    s = "" if txt is None else str(txt).strip()
    return "" if re.sub(r'\s+', ' ', s).strip().lower() == "nan" else re.sub(r'\s+', ' ', s).strip()

@st.cache_data
def carregar_dados_nuvem(arquivo_upload):
    if arquivo_upload is None:
        return pd.DataFrame()
    
    try:
        # Lê o arquivo upado para a memória
        xls = pd.ExcelFile(arquivo_upload)
        
        try:
            df_ind = xls.parse("Industrias", skiprows=1, header=None)
            lista_industrias = sorted([i for i in df_ind[0].apply(limpar_industria).dropna().unique() if i != ''])
        except Exception: lista_industrias = ['Unilever', 'Nestlé']

        try:
            df_marcas = xls.parse("Marcas", skiprows=1, header=None)
            lista_marcas_reais = sorted([m.strip() for m in df_marcas[0].dropna().astype(str) if m.strip().lower() != 'nan' and m.strip()!=''])
        except Exception: lista_marcas_reais = ['Omo', 'Ninho']
        marcas_sorted = sorted(lista_marcas_reais, key=len, reverse=True)

        def achar_marca(desc):
            desc_up = str(desc).upper()
            for m in marcas_sorted:
                if re.search(r'\b' + re.escape(m.upper()) + r'\b', desc_up): return m
            return 'Outra Marca'

        try:
            df_bateu = xls.parse("BateuLevou")
            df_bateu['Desc_Norm'] = df_bateu['DESCRICAO'].astype(str).apply(lambda x: re.sub(r'\s+', ' ', x.strip().upper()))
            dict_bateu_ind = df_bateu.set_index('Desc_Norm')['INDUSTRIA'].to_dict() if 'INDUSTRIA' in df_bateu.columns else {}
            dict_bateu_mar = df_bateu.set_index('Desc_Norm')['MARCA'].to_dict() if 'MARCA' in df_bateu.columns else {}
            descricoes_bateu = set(df_bateu['Desc_Norm'].unique())
        except Exception:
            dict_bateu_ind, dict_bateu_mar, descricoes_bateu = {}, {}, set()

        # BASE PRINCIPAL
        df = xls.parse("Banco_Dados_Semanal", skiprows=5, header=None)
        coluna_b_original = df[1].copy()

        cat_raw = df[1].astype(str)
        mask_categoria = cat_raw.str.match(r'^\s*\d{1,3}\s*-\s*.+')
        df['Categoria'] = cat_raw.where(mask_categoria, other=None).ffill().apply(manter_categoria_completa)
        df['Categoria'] = df['Categoria'].replace('', 'Sem Categoria').fillna('Sem Categoria')

        df['Código'] = df[0].astype(str)
        df['Descrição'] = df[2].astype(str).str.strip("* ")
        df['Preço_7'] = pd.to_numeric(df[5], errors='coerce')
        df['Preço_14'] = pd.to_numeric(df[7], errors='coerce')
        df['Preço_21'] = pd.to_numeric(df[9], errors='coerce')
        df['Preço_28'] = pd.to_numeric(df[11], errors='coerce')
        df['ST_Flag'] = df.get(12, pd.Series()).fillna("").astype(str).str.strip()

        df = df.dropna(subset=['Preço_7'])
        df = df[(df['Preço_7'] > 0) & (df['Descrição'].str.strip().str.lower() != 'nan') & (df['Descrição'].str.strip() != '')]

        df['Desc_Norm'] = df['Descrição'].apply(lambda x: re.sub(r'\s+', ' ', str(x).strip().upper()))
        df['Camp_Bateu'] = df['Desc_Norm'].isin(descricoes_bateu)

        df['Indústria'] = df['Desc_Norm'].map(dict_bateu_ind).fillna(pd.Series(np.random.choice(lista_industrias, size=len(df)) if lista_industrias else 'Sem Indústria', index=df.index))
        df['Marca_BL'] = df['Desc_Norm'].map(dict_bateu_mar)
        mask_missing = df['Marca_BL'].isna() | (df['Marca_BL'] == '')
        df['Marca'] = df['Marca_BL']
        if mask_missing.any(): df.loc[mask_missing, 'Marca'] = df.loc[mask_missing, 'Desc_Norm'].apply(achar_marca)

        np.random.seed(42)
        df['Fator_Anterior'] = np.random.choice([1.0, 1.05, 1.15, 0.95], size=len(df), p=[0.5, 0.2, 0.1, 0.2])
        
        # Simula Curva ABC para demonstração
        df['Freq_Top_ABC'] = pd.Series(np.random.randint(0, 100, size=len(df)), index=df.index)
        top_30_idx = df.nlargest(30, 'Freq_Top_ABC').index
        df['Curva_ABC'] = False
        df.loc[top_30_idx, 'Curva_ABC'] = True

        def checar_meta_mensal(row):
            desc = str(row.get('Desc_Norm', '')).upper()
            marca = str(row.get('Marca', '')).upper()
            return ('ESCOLA' in desc or 'INSETICIDA' in desc or 'BABYSEC' in marca or 'LIXO' in desc)
        df['Meta_Mensal'] = df.apply(checar_meta_mensal, axis=1)

        # TO PODENDO - ARRASTÃO
        cod_podendo_ex, cod_podendo_parc = set(), set()
        try:
            df_podendo = xls.parse("TO PODENDO", header=None)
            for col in df_podendo.columns:
                for val in df_podendo[col].dropna():
                    v_str = str(val).strip().upper()
                    if 'E+' in v_str:
                        rz = re.sub(r'\D', '', v_str.split('E')[0])
                        if len(rz)>=4: cod_podendo_parc.add(rz)
                    else:
                        vn = re.sub(r'\D', '', v_str)
                        if len(vn)>=4: cod_podendo_ex.add(vn)
        except: pass

        def check_podendo(idx):
            vb = re.sub(r'\D', '', str(coluna_b_original.get(idx, "")))
            va = re.sub(r'\D', '', str(df.at[idx, 'Código']))
            if (vb and vb in cod_podendo_ex) or (va and va in cod_podendo_ex): return True
            for p in cod_podendo_parc:
                if (vb and vb.startswith(p)) or (va and va.startswith(p)): return True
            return False
        
        df['Camp_ToPodendo'] = [check_podendo(idx) for idx in df.index]
        if not df['Camp_ToPodendo'].any():
            df['Camp_ToPodendo'] = df['Desc_Norm'].apply(lambda d: any(m in d for m in ['KINDER','MAGGI','GAROTO','NESTLE','TODDY']))

        # COLGATE - ARRASTÃO
        cod_colgate_ex, cod_colgate_parc = set(), set()
        try:
            df_colgate = xls.parse("COLGATE", header=None)
            for col in df_colgate.columns:
                for val in df_colgate[col].dropna():
                    v_str = str(val).strip().upper()
                    if 'E+' in v_str:
                        rz = re.sub(r'\D', '', v_str.split('E')[0])
                        if len(rz)>=4: cod_colgate_parc.add(rz)
                    else:
                        vn = re.sub(r'\D', '', v_str)
                        if len(vn)>=4: cod_colgate_ex.add(vn)
        except: pass

        def check_colgate(idx):
            vb = re.sub(r'\D', '', str(coluna_b_original.get(idx, "")))
            va = re.sub(r'\D', '', str(df.at[idx, 'Código']))
            if (vb and vb in cod_colgate_ex) or (va and va in cod_colgate_ex): return True
            for p in cod_colgate_parc:
                if (vb and vb.startswith(p)) or (va and va.startswith(p)): return True
            return False

        df['Camp_Colgate'] = [check_colgate(idx) for idx in df.index]
        if not df['Camp_Colgate'].any():
            df['Camp_Colgate'] = df['Desc_Norm'].apply(lambda d: any(m in d for m in ['COLGATE','SORRISO','PROTEX','PALMOLIVE']))

        return df
    except Exception as e:
        st.error(f"Erro ao processar planilha: {e}")
        return pd.DataFrame()

# ==========================================
# SIDEBAR / MENU RESPONSIVO
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3144/3144456.png", width=60)
    st.markdown("<p class='subtitulo'>📂 Atualizar Dados</p>", unsafe_allow_html=True)
    
    # BOTAO UPLOAD PARA WEB
    arquivo_upado = st.file_uploader("Suba sua Planilha Semanal (Excel)", type=["xlsx", "xls"])
    df_raw = carregar_dados_nuvem(arquivo_upado)
    
    st.divider()

    st.markdown("<p class='subtitulo'>Layout do Encarte</p>", unsafe_allow_html=True)
    layout_selecionado = st.segmented_control(
        "Escolha o formato:", options=[9, 12, 16, 20], 
        format_func=lambda x: f"{x} Espaços", default=st.session_state['num_produtos_layout']
    )
    if layout_selecionado: st.session_state['num_produtos_layout'] = layout_selecionado
    num_produtos = st.session_state['num_produtos_layout']
    
    st.divider()
    opcoes_prazo = {"Preço_7": "7 Dias", "Preço_14": "14 Dias", "Preço_21": "21 Dias", "Preço_28": "28 Dias"}
    prazo_selecionado = st.segmented_control("Prazo de Pagamento:", options=list(opcoes_prazo.keys()), format_func=lambda x: opcoes_prazo[x], default="Preço_7")
    if not prazo_selecionado: prazo_selecionado = "Preço_7"

    df_app = df_raw.copy()
    if not df_app.empty:
        df_app['Preço Atual'] = df_app[prazo_selecionado].fillna(df_app['Preço_7'])
        df_app['Preço Anterior'] = df_app['Preço Atual'] * df_app['Fator_Anterior']
        df_app['Preço Anterior'] = np.where(df_app['Preço Anterior'] == 0, 1, df_app['Preço Anterior'])
        df_app['Desconto %'] = ((df_app['Preço Anterior'] - df_app['Preço Atual']) / df_app['Preço Anterior'] * 100).round(1)
        df_app['Status'] = df_app.apply(lambda r: f"🟢 Baixou! (-{abs(r['Desconto %'])}%)" if r['Preço Atual'] < r['Preço Anterior'] else "⚫ Igual" if r['Preço Atual'] == r['Preço Anterior'] else f"🔴 Aumentou! (+{abs(r['Desconto %'])}%)", axis=1)

    df_filtrado = df_app.copy()
    
    st.markdown("<p class='subtitulo'>🔥 Filtros & Campanhas</p>", unsafe_allow_html=True)
    f_abc, f_metas, c_bateu, c_podendo, c_colgate = st.checkbox("Curva ABC"), st.checkbox("Metas Mensal"), st.checkbox("BATEU LEVOU"), st.checkbox("TO PODENDO"), st.checkbox("COLGATE")

    if not df_filtrado.empty:
        if f_abc: df_filtrado = df_filtrado[df_filtrado['Curva_ABC'] == True]
        if f_metas: df_filtrado = df_filtrado[df_filtrado['Meta_Mensal'] == True]
        
        mask_camp = pd.Series(False, index=df_filtrado.index)
        has_camp = False
        if c_bateu: mask_camp |= df_filtrado['Camp_Bateu']; has_camp = True
        if c_colgate: mask_camp |= df_filtrado['Camp_Colgate']; has_camp = True
        if c_podendo: mask_camp |= df_filtrado['Camp_ToPodendo']; has_camp = True
        if has_camp: df_filtrado = df_filtrado[mask_camp]

        i_disp = sorted([str(x) for x in df_filtrado['Indústria'].dropna().unique() if str(x).strip() != ''])
        i_f = st.selectbox("Indústria", options=['Todas'] + i_disp)
        if i_f != 'Todas': df_filtrado = df_filtrado[df_filtrado['Indústria'] == i_f]

        m_disp = sorted([str(x) for x in df_filtrado['Marca'].dropna().unique() if str(x).strip() != ''])
        m_f = st.selectbox("Marca", options=['Todas'] + m_disp)
        if m_f != 'Todas': df_filtrado = df_filtrado[df_filtrado['Marca'] == m_f]

# ==========================================
# ÁREA PRINCIPAL
# ==========================================
if df_app.empty:
    st.info("👈 Faça o **Upload da Planilha Semanal (.xlsx)** no menu lateral para começar a montar seus encartes online!")
else:
    st.markdown("<p class='titulo-secao'>🤖 Geradores Automáticos (20 Espaços)</p>", unsafe_allow_html=True)
    cg1, cg2, cg3 = st.columns(3)
    with cg1:
        if st.button("✨ TODAS CAMPANHAS (PRO)", use_container_width=True):
            st.session_state['produtos_selecionados'], st.session_state['num_produtos_layout'] = [], 20 
            add_auto_products(df_app[df_app['Camp_Bateu'] == True].sort_values('Desconto %', ascending=False), 5)
            add_auto_products(df_app[df_app['Camp_Colgate'] == True].sort_values('Desconto %', ascending=False), 5)
            add_auto_products(df_app[df_app['Camp_ToPodendo'] == True].sort_values('Desconto %', ascending=False), 5)
            add_auto_products(df_app[df_app['Meta_Mensal'] == True].sort_values('Desconto %', ascending=False), 5)
            st.rerun()
    with cg2:
        if st.button("💥 BATEU LEVOU", use_container_width=True):
            st.session_state['produtos_selecionados'], st.session_state['num_produtos_layout'] = [], 20
            add_auto_products(df_app[df_app['Camp_Bateu'] == True].sort_values('Desconto %', ascending=False), 20); st.rerun()
    with cg3:
        if st.button("🎯 COLGATE", use_container_width=True):
            st.session_state['produtos_selecionados'], st.session_state['num_produtos_layout'] = [], 20
            add_auto_products(df_app[df_app['Camp_Colgate'] == True].sort_values('Desconto %', ascending=False), 20); st.rerun()

    st.markdown("---")
    st.markdown("<p class='titulo-secao'>Selecionar Produtos Manualmente</p>", unsafe_allow_html=True)
    
    opcoes_busca = ["Digite ou selecione um produto..."] + df_filtrado.apply(lambda x: f"{x['Código']} | {x['Descrição']} | R$ {x['Preço Atual']:.2f}", axis=1).tolist() if not df_filtrado.empty else ["Digite ou selecione um produto..."]
    
    col_busca, col_limpar = st.columns([5, 1])
    with col_busca: st.selectbox("Buscar Produto:", options=opcoes_busca, key="busca_temp", on_change=lambda: processar_busca(df_filtrado), label_visibility="collapsed")
    with col_limpar:
        if st.button("🗑️ Limpar Tudo", use_container_width=True):
            st.session_state['produtos_selecionados'] = []; st.rerun()

    st.markdown(f"**Itens no painel:** {len(st.session_state['produtos_selecionados'])} / {num_produtos} espaços.")
    st.markdown("---")

    # CARDS RESPONSIVOS PARA MOBILE
    for i, prod in enumerate(st.session_state['produtos_selecionados']):
        u_id = prod['Código'] 
        if f"chk_{u_id}" not in st.session_state: st.session_state[f"chk_{u_id}"] = prod.get('Levar', True)
        
        # Em mobile, o Streamlit transforma essas colunas em blocos empilhados (Cards)
        with st.container():
            col1, col2, col3, col4 = st.columns([0.5, 3, 2, 1], vertical_alignment="center")
            
            with col1:
                st.session_state['produtos_selecionados'][i]['Levar'] = st.checkbox("", key=f"chk_{u_id}")
            
            with col2:
                st.markdown(f"**{prod['Descrição']}** <br> Cód: `{u_id}`", unsafe_allow_html=True)
            
            with col3:
                st.number_input("Preço", value=float(prod['Preço Atual']), format="%.2f", key=f"pr_{u_id}", on_change=atualizar_valores_uid, args=(i, u_id))
            
            with col4:
                st.markdown(f"<div style='background-color:#002D62; color:white; padding:8px; border-radius:8px; text-align:center;'><b>R$ {prod['Preço Final']:.2f}</b></div>", unsafe_allow_html=True)
                if st.button("Remover", key=f"del_{u_id}", type="tertiary", use_container_width=True): deletar_item(i); st.rerun()
            st.divider()

    btn1, btn2 = st.columns(2)
    with btn1: st.button("🚀 GERAR TABLOIDE (PDF/JPG)", type="primary", use_container_width=True)
    with btn2: st.button("📱 GERAR ARTES INDIVIDUAIS", type="secondary", use_container_width=True)


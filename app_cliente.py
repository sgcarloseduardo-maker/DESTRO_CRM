import streamlit as st
import pandas as pd
import numpy as np
import re
import os
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(
    page_title="Catálogo de Pedidos - Cliente",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para padronizar o tamanho das imagens na grade de produtos e centralização na lista
st.markdown("""
<style>
    /* CSS da grade de produtos (vitrine) */
    div[data-testid="stImage"] img {
        object-fit: contain;
        height: 180px;
        width: 100%;
        background-color: white;
    }
    
    /* CSS específico para as miniaturas do carrinho para forçar altura fixa e menor */
    .carrinho-img img {
        object-fit: contain !important;
        height: 50px !important;
        width: 50px !important;
    }
    
    /* Centralização vertical dos textos no carrinho */
    .carrinho-texto {
        display: flex;
        align-items: center;
        height: 50px;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# COPYRIGHT NO TOPO
st.markdown("<div style='text-align: right; color: gray; font-size: 12px; margin-top: -40px; margin-bottom: 20px;'>Sistema elaborado por EDG ENGENHARIA REPRESENTAÇÕES LTDA</div>", unsafe_allow_html=True)

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

# ==========================================
# CARREGAMENTO DOS DADOS
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
    st.toast("📄 Gerando PDF...", icon="⏳")
    img_idx = obter_indice_imagens()
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30,
                            leftMargin=30, topMargin=30, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph("<b>Meu Pedido de Produtos</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))

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
            except Exception as e:
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
    st.header("🛒 Resumo")

    carrinho_lista = list(st.session_state['carrinho'].values())
    st.write(f"**Itens selecionados:** {len(carrinho_lista)}")

    if len(carrinho_lista) > 0:
        if st.button("🗑️ Limpar Carrinho", use_container_width=True):
            st.session_state['carrinho'] = {}
            st.rerun()

        pdf_buffer = gerar_pdf_pedido(carrinho_lista)
        if pdf_buffer:
            st.download_button(
                label="📥 Baixar PDF do Pedido",
                data=pdf_buffer,
                file_name="Meu_Pedido.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

    st.divider()
    st.header("🔍 Filtros de Busca")

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

st.title("Catálogo de Produtos")

if not df_filtrado.empty:
    img_idx_global = obter_indice_imagens()

    itens_por_pagina = 20
    total_paginas = max(1, len(df_filtrado) // itens_por_pagina +
                        (1 if len(df_filtrado) % itens_por_pagina > 0 else 0))

    if st.session_state['pagina_atual'] > total_paginas:
        st.session_state['pagina_atual'] = 1

    pagina_atual = st.session_state['pagina_atual']

    st.divider()
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
                            st.info("📷 Sem Imagem")

                        st.markdown(f"**Cód: {cod}**")
                        desc_curta = desc if len(
                            desc) <= 45 else desc[:42] + "..."
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
# LISTA DE PRODUTOS SELECIONADOS (LINHAS COMPACTAS E ALINHADAS)
# ==========================================
st.divider()
st.header("📋 Produtos no seu Carrinho")

if len(st.session_state['carrinho']) > 0:

    # Cabeçalho
    c1, c2, c3, c4 = st.columns([1, 2, 6, 1])
    c1.markdown("**Foto**")
    c2.markdown("**Código**")
    c3.markdown("**Descrição**")
    c4.markdown("**Remover**")
    st.markdown("<hr style='margin: 5px 0px;'>", unsafe_allow_html=True)

    for cod, prod in list(st.session_state['carrinho'].items()):
        c1, c2, c3, c4 = st.columns([1, 2, 6, 1], gap="small")

        # Coluna de Imagem (com classe CSS para manter proporção e tamanho fixo)
        with c1:
            img_path = prod.get('ImgPath')
            if img_path and os.path.exists(img_path):
                st.markdown(f"<div class='carrinho-img'>",
                            unsafe_allow_html=True)
                st.image(img_path)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div class='carrinho-texto' style='color: gray; font-size: 11px;'>Sem foto</div>", unsafe_allow_html=True)

        # Coluna Código (Centralizado verticalmente)
        with c2:
            st.markdown(
                f"<div class='carrinho-texto'>{cod}</div>", unsafe_allow_html=True)

        # Coluna Descrição (Centralizado verticalmente)
        with c3:
            st.markdown(
                f"<div class='carrinho-texto'>{prod['Descrição']}</div>", unsafe_allow_html=True)

        # Botão de Remover
        with c4:
            st.markdown("<div style='margin-top: 5px;'>",
                        unsafe_allow_html=True)
            if st.button("❌", key=f"lista_rem_{cod}", help="Remover produto"):
                del st.session_state['carrinho'][cod]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Linha separadora bem justa e fina
        st.markdown(
            "<hr style='margin: 0px 0px 5px 0px; opacity: 0.2;'>", unsafe_allow_html=True)
else:
    st.info("Nenhum produto adicionado ainda. Escolha produtos na vitrine acima.")

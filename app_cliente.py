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

# CSS para layout do carrinho super compacto e centralizado
st.markdown("""
<style>
    div[data-testid="stImage"] img {
        object-fit: contain;
        height: 180px;
        width: 100%;
        background-color: white;
    }
    
    /* Remove padding interno das colunas do streamlit na parte do carrinho para colar os elementos */
    .compact-row div[data-testid="column"] {
        padding: 0px !important;
        margin: 0px !important;
    }
    
    /* Configuração da miniatura com altura mínima */
    .carrinho-img img {
        object-fit: contain !important;
        height: 25px !important;
        width: 25px !important;
    }
    
    /* Centralização horizontal e vertical de todos os textos com altura espremida */
    .carrinho-texto {
        display: flex;
        justify-content: center; /* Centraliza horizontalmente */
        align-items: center;     /* Centraliza verticalmente */
        height: 25px;            /* Altura mínima acompanhando a foto */
        font-size: 13px;
        font-weight: bold;       /* Coloca em negrito conforme solicitado */
        margin: 0;
        padding: 0;
    }
    
    /* Centraliza o botão dentro da sua div */
    .carrinho-btn {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 25px;
    }
    
    /* Espreme o botão padrão do streamlit no carrinho */
    .carrinho-btn button {
        min-height: 20px !important;
        height: 20px !important;
        padding: 0px 8px !important;
        line-height: 1 !important;
        font-size: 10px !important;
        margin: 0 !important;
    }

    /* Linha divisória bem grudada */
    .linha-separadora {
        margin: 2px 0px 2px 0px !important; 
        border: 0; 
        border-top: 2px solid #94a3b8;
    }
    
    /* Remove espaço extra do markdown vazio (botões) */
    p {
        margin-bottom: 0 !important;
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

    # DATA APENAS (Sem horário)
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
                label="📥 Baixar PDF",
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

img_idx_global = obter_indice_imagens()

st.title("Catálogo de Produtos")

# ==========================================
# CAMPO DE BUSCA MANUAL
# ==========================================
st.markdown("<h3>Selecionar Produtos Manualmente</h3>", unsafe_allow_html=True)

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

    # Exibição do Catálogo
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
# LISTA DE PRODUTOS SELECIONADOS - VISUAL LIMPO E COMPACTO
# ==========================================
st.divider()
st.header("📋 Produtos no seu Carrinho")

if len(st.session_state['carrinho']) > 0:

    # Cabeçalho Centralizado
    st.markdown("""
        <div style='display: flex; font-weight: bold; margin-bottom: 5px; font-size: 14px;'>
            <div style='width: 10%; text-align: center;'>Foto</div>
            <div style='width: 20%; text-align: center;'>Código</div>
            <div style='width: 60%; text-align: center;'>Descrição</div>
            <div style='width: 10%; text-align: center;'>Remover</div>
        </div>
        <hr class='linha-separadora'>
    """, unsafe_allow_html=True)

    # Criação de um container com uma classe especial para remover o padding das colunas nativas
    st.markdown('<div class="compact-row">', unsafe_allow_html=True)

    for cod, prod in list(st.session_state['carrinho'].items()):
        c1, c2, c3, c4 = st.columns([1, 2, 6, 1])

        with c1:
            img_path = prod.get('ImgPath')
            if img_path and os.path.exists(img_path):
                st.markdown(
                    f"<div class='carrinho-img' style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
                st.image(img_path)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    "<div class='carrinho-texto' style='color: gray; font-size: 11px; font-weight: normal;'>Sem foto</div>", unsafe_allow_html=True)

        with c2:
            st.markdown(
                f"<div class='carrinho-texto'>{cod}</div>", unsafe_allow_html=True)

        with c3:
            st.markdown(
                f"<div class='carrinho-texto'>{prod['Descrição']}</div>", unsafe_allow_html=True)

        with c4:
            st.markdown("<div class='carrinho-btn'>", unsafe_allow_html=True)
            if st.button("❌", key=f"lista_rem_{cod}", help="Remover produto"):
                del st.session_state['carrinho'][cod]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Linha separadora logo abaixo de cada item
        st.markdown("<hr class='linha-separadora'>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # BOTOES NO FINAL (Baixar PDF e Limpar Carrinho)
    st.markdown("<br>", unsafe_allow_html=True)

    # Organiza os botões lado a lado centralizados
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

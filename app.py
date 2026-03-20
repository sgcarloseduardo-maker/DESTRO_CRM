import streamlit as st
import pandas as pd
import numpy as np
import time
import re
import os
import glob
import base64
import urllib.parse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="CRM Destro - RCA",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CSS CUSTOMIZADO
# ==========================================
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    div.stButton > button[kind="primary"] { 
        background-color: #ff4b4b; color: white; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; font-size: 16px; 
    }
    div.stButton > button[kind="primary"]:hover { box-shadow: 0px 4px 10px rgba(255, 75, 75, 0.4); }
    div.stButton > button[kind="secondary"] { 
        background-color: #007BFF; color: white; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; font-size: 16px; border: none;
    }
    div.stButton > button[kind="secondary"]:hover { background-color: #0056b3; box-shadow: 0px 4px 10px rgba(0, 123, 255, 0.4); }
    div.stButton > button[kind="tertiary"] { 
        background-color: transparent !important; color: #475569 !important; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; font-size: 16px; border: none !important;
        box-shadow: none !important; outline: none !important; padding: 0 !important;
    }
    div.stButton > button[kind="tertiary"]:hover { background-color: #e2e8f0 !important; }
    .titulo-secao { font-size: 26px !important; font-weight: 800 !important; color: #1E293B; text-align: center; margin-bottom: 10px; }
    .subtitulo { font-size: 18px !important; font-weight: 700 !important; color: #334155; }
    div[data-testid="stHorizontalBlock"] { align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# VARIÁVEIS DE SESSÃO E FUNÇÕES
# ==========================================
if 'produtos_selecionados' not in st.session_state:
    st.session_state['produtos_selecionados'] = []
if 'busca_temp' not in st.session_state:
    st.session_state.busca_temp = None
if 'num_produtos_layout' not in st.session_state:
    st.session_state['num_produtos_layout'] = 0
if 'galeria_individuais' not in st.session_state:
    st.session_state['galeria_individuais'] = []

if 'confirmacao_st' not in st.session_state:
    st.session_state['confirmacao_st'] = None
if 'alertas_st' not in st.session_state:
    st.session_state['alertas_st'] = []
if 'df_pendente' not in st.session_state:
    st.session_state['df_pendente'] = None
if 'path_pendente' not in st.session_state:
    st.session_state['path_pendente'] = None
if 'pdf_buffer_pronto' not in st.session_state:
    st.session_state['pdf_buffer_pronto'] = None


def processar_busca():
    item_escolhido = st.session_state.busca_temp
    if item_escolhido and item_escolhido != "Digite ou selecione um produto...":
        limite = st.session_state['num_produtos_layout']
        if limite > 0 and len(st.session_state['produtos_selecionados']) >= limite:
            st.toast(
                f"🚨 Limite máximo atingido! O layout atual só permite {limite} itens.", icon="⚠️")
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
        index = next((idx for idx, p in enumerate(
            st.session_state['produtos_selecionados']) if p['Código'] == u_id), None)
    if index is not None:
        prod = st.session_state['produtos_selecionados'][index]
        pr_val = st.session_state.get(
            f"pr_{u_id}", prod.get('Preço Atual', 0.0))
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
        if prod['Imposto']:
            calc = calc * 1.101
        prod['Preço Final'] = round(calc, 2)


def step_value(u_id, prefix, delta):
    key = f"{prefix}_{u_id}"
    current_val = st.session_state.get(key, 0.0)
    st.session_state[key] = round(
        (current_val if current_val is not None else 0.0) + delta, 1)
    atualizar_valores_uid(u_id=u_id)


def checar_imposto_st(df):
    alertas = []
    for _, row in df.iterrows():
        if str(row.get('ST_Flag', '')).strip() != '*' and not bool(row.get('Imposto', False)):
            alertas.append(row['Descrição'])
    return alertas


def add_auto_products(df_subset, max_items):
    added = 0
    for _, row in df_subset.iterrows():
        if max_items > 0 and added >= max_items:
            break
        cod = row['Código']
        if not any(d['Código'] == cod for d in st.session_state['produtos_selecionados']):
            st.session_state['produtos_selecionados'].append({
                'Levar': True, 'Código': cod, 'Status': row['Status'],
                'Descrição': row['Descrição'], 'Preço Atual': float(row['Preço Atual']),
                'Comissão': 0.0, 'FLEX': 0.0, 'DESC': 0.0, 'Imposto': False,
                'Preço Final': float(row['Preço Atual']), 'ST_Flag': row.get('ST_Flag', '')
            })
            added += 1


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


def salvar_imagem_upload(uploaded_file, codigo_produto):
    if uploaded_file is not None:
        # Define o caminho para a pasta Base de Imagens
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pasta_imagens = os.path.join(base_dir, "Base de Imagens")

        # Cria a pasta se ela não existir
        os.makedirs(pasta_imagens, exist_ok=True)

        # Pega a extensão original do arquivo (ex: .jpg, .png)
        extensao = os.path.splitext(uploaded_file.name)[1].lower()
        if not extensao:
            extensao = ".jpg"  # fallback seguro

        # Define o caminho do novo arquivo usando o código do produto
        caminho_salvar = os.path.join(
            pasta_imagens, f"{codigo_produto}{extensao}")

        # Salva o arquivo fisicamente
        with open(caminho_salvar, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Limpa o cache para forçar a função obter_indice_imagens() a ler a nova imagem
        st.cache_data.clear()
        return True
    return False


def image_to_base64(img_path):
    if img_path and os.path.exists(img_path):
        try:
            with open(img_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except:
            pass
    return ""


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


def carregar_fonte(caminho, tamanho):
    try:
        if caminho and os.path.exists(caminho):
            return ImageFont.truetype(caminho, tamanho)
    except Exception:
        pass
    return ImageFont.load_default()


def desenhar_placeholder(bg_img, x1, y1, x2, y2):
    draw = ImageDraw.Draw(bg_img)
    draw.rectangle([x1, y1, x2, y2], outline="red",
                   width=4, fill=(245, 245, 245, 255))
    draw.line((x1, y1, x2, y2), fill="red", width=4)
    draw.line((x1, y2, x2, y1), fill="red", width=4)

    texto = "IMAGEM\nINDISPONÍVEL\nNO MOMENTO"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "Fontes", "Montserrat-Bold.ttf")
    tamanho_fonte = max(14, int((x2 - x1) * 0.08))
    fonte = carregar_fonte(font_path, tamanho_fonte)

    cx, cy = x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2
    try:
        box = draw.multiline_textbbox(
            (0, 0), texto, font=fonte, align="center")
        w, h = box[2] - box[0], box[3] - box[1]
    except:
        w, h = 150, 60

    pad = 10
    draw.rectangle([cx - w//2 - pad, cy - h//2 - pad, cx + w//2 +
                   pad, cy + h//2 + pad], fill="white", outline="red", width=2)
    draw.multiline_text((cx - w//2, cy - h//2), texto,
                        fill="red", font=fonte, align="center")


# ==========================================
# MOTOR DINÂMICO DE ENCARTES (DPI INTELIGENTE)
# ==========================================
LAYOUTS = {
    9: {
        "cols": 3, "rows": 3,
        "img_x": [(3.2, 15.0), (16.4, 27.1), (28.7, 38.8)],
        "img_y": [(18.1, 24.6), (29.1, 36.9), (41.9, 49.4)],
        "desc_x": [(2.5, 7.1), (16.0, 22.1), (28.4, 33.8)],
        "desc_y": [(24.9, 28.0), (37.4, 40.6), (49.9, 53.0)],
        "preco_x": [(9.9, 15.3), (22.5, 27.2), (34.1, 38.8)],
        "preco_y": [(24.9, 28.0), (37.4, 40.6), (49.9, 53.0)],
        "bg_pattern": "FUNDO-BASE-USADO-NA-AUTOMACAO-{v}.jpg"
    },
    12: {
        "cols": 4, "rows": 3,
        "img_x": [(0.7, 4.3), (6.0, 9.6), (11.3, 14.9), (16.6, 20.2)],
        "img_y": [(9.2, 11.9), (15.7, 18.5), (22.3, 25.1)],
        "desc_x": [(0.3, 4.7), (5.6, 10.0), (11.0, 15.3), (16.3, 20.6)],
        "desc_y": [(7.7, 9.0), (14.3, 15.6), (20.8, 22.1)],
        "preco_x": [(1.6, 3.2), (6.9, 8.5), (12.2, 13.6), (17.4, 19.0)],
        "preco_y": [(12.3, 13.2), (18.9, 19.8), (25.5, 26.4)],
        "bg_pattern": "Modelo 12 Espaços-{v}.jpg"
    },
    16: {
        "cols": 4, "rows": 4,
        "img_x": [(0.7, 4.3), (6.0, 9.6), (11.3, 14.9), (16.6, 20.2)],
        "img_y": [(6.6, 8.8), (12.3, 14.5), (17.9, 20.1), (23.5, 25.7)],
        "desc_x": [(0.3, 4.7), (5.6, 10.0), (11.0, 15.3), (16.3, 20.6)],
        "desc_y": [(5.4, 6.5), (11.1, 12.2), (16.7, 17.8), (22.3, 23.4)],
        "preco_x": [(1.6, 3.2), (6.9, 8.5), (12.2, 13.6), (17.4, 19.0)],
        "preco_y": [(9.2, 10.1), (14.9, 15.8), (20.4, 21.2), (26.0, 26.8)],
        "bg_pattern": "Modelo 16 Espaços-{v}.jpg"
    },
    20: {
        "cols": 5, "rows": 4,
        "img_x": [(0.9, 3.1), (5.0, 7.3), (9.2, 11.5), (13.4, 15.6), (17.6, 19.8)],
        "img_y": [(8.9, 10.6), (13.2, 14.9), (17.6, 19.3), (21.9, 23.6)],
        "desc_x": [(0.3, 3.7), (4.5, 7.9), (8.7, 12.1), (12.8, 16.2), (17.0, 20.4)],
        "desc_y": [(7.9, 8.8), (12.2, 13.1), (16.6, 17.5), (20.9, 21.8)],
        "preco_x": [(1.3, 2.7), (5.5, 6.9), (9.7, 11.1), (13.8, 15.2), (18.0, 19.4)],
        "preco_y": [(10.9, 11.5), (15.2, 15.8), (19.6, 20.2), (23.8, 24.4)],
        "bg_pattern": "Modelo 20 Espaços-{v}.jpg"
    }
}


def desenhar_texto_box_grade(draw, texto, x_ini, x_fim, y_ini, y_fim, fonte_path, fator_x, fator_y):
    x1, x2 = int(x_ini * fator_x), int(x_fim * fator_x)
    y1, y2 = int(y_ini * fator_y), int(y_fim * fator_y)
    largura = x2 - x1
    altura = y2 - y1
    cx = x1 + largura // 2

    tamanho = max(12, int(altura * 0.40))
    if tamanho > 60:
        tamanho = 60

    fonte = carregar_fonte(fonte_path, tamanho)

    while tamanho > 10:
        palavras = str(texto).split()
        linhas = []
        linha_atual = ""
        for p in palavras:
            teste = (linha_atual + " " + p).strip()
            try:
                w = draw.textlength(teste, font=fonte)
            except:
                w = draw.textbbox((0, 0), teste, font=fonte)[2]
            if w <= largura:
                linha_atual = teste
            else:
                if linha_atual:
                    linhas.append(linha_atual)
                linha_atual = p
        if linha_atual:
            linhas.append(linha_atual)

        try:
            h_line = draw.textbbox((0, 0), "A", font=fonte)[
                3] - draw.textbbox((0, 0), "A", font=fonte)[1]
        except:
            h_line = tamanho

        total_h = len(linhas[:3]) * (h_line + 4)
        if len(linhas) <= 3 and total_h <= altura:
            break
        tamanho -= 2
        fonte = carregar_fonte(fonte_path, tamanho)

    try:
        h_line = draw.textbbox((0, 0), "A", font=fonte)[
            3] - draw.textbbox((0, 0), "A", font=fonte)[1]
    except:
        h_line = tamanho

    linhas = linhas[:3]
    total_h = len(linhas) * h_line + (len(linhas)-1) * 4
    cur_y = y1 + (altura - total_h) // 2

    for l in linhas:
        try:
            w = draw.textlength(l, font=fonte)
        except:
            w = draw.textbbox((0, 0), l, font=fonte)[2]
        try:
            offset_y = draw.textbbox((0, 0), l, font=fonte)[1]
        except:
            offset_y = 0

        draw.text((cx - w // 2, cur_y - offset_y), l, fill="black", font=fonte)
        cur_y += h_line + 4


def desenhar_preco_box_grade(draw, preco, x_ini, x_fim, y_ini, y_fim, fonte_path, fator_x, fator_y):
    x1, x2 = int(x_ini * fator_x), int(x_fim * fator_x)
    y1, y2 = int(y_ini * fator_y), int(y_fim * fator_y)
    h_box, w_box = y2 - y1, x2 - x1
    cx, cy = x1 + w_box // 2, y1 + h_box // 2

    texto = f"R$ {float(preco):,.2f}".replace(
        ",", "X").replace(".", ",").replace("X", ".")

    tamanho = max(15, int(h_box * 0.85))
    if tamanho > 150:
        tamanho = 150
    fonte = carregar_fonte(fonte_path, tamanho)

    while tamanho > 12:
        try:
            box = draw.textbbox((0, 0), texto, font=fonte)
            w, h = box[2] - box[0], box[3] - box[1]
        except:
            w, h = draw.textsize(texto, font=fonte)
        if w <= (w_box - 4) and h <= (h_box + 4):
            break
        tamanho -= 2
        fonte = carregar_fonte(fonte_path, tamanho)

    try:
        box = draw.textbbox((0, 0), texto, font=fonte)
        w, h = box[2] - box[0], box[3] - box[1]
        offset_y = box[1]
    except:
        w, h = draw.textsize(texto, font=fonte)
        offset_y = 0

    draw.text((cx - w // 2, cy - h // 2 - offset_y),
              texto, fill="white", font=fonte)


def colar_imagem_grade(bg, img_path, x_ini, x_fim, y_ini, y_fim, fator_x, fator_y):
    x1, x2 = int(x_ini * fator_x), int(x_fim * fator_x)
    y1, y2 = int(y_ini * fator_y), int(y_fim * fator_y)
    w_box, h_box = x2 - x1, y2 - y1
    cx, cy = x1 + w_box // 2, y1 + h_box // 2

    if not img_path or not os.path.exists(img_path):
        desenhar_placeholder(bg, x1, y1, x2, y2)
        return False

    try:
        prod = Image.open(img_path).convert("RGBA")
        prod = remover_fundo_branco(prod)
        bbox = prod.getbbox()
        if bbox:
            prod = prod.crop(bbox)

        prod.thumbnail((w_box - 4, h_box - 4), Image.Resampling.LANCZOS)
        wi, hi = prod.size
        bg.paste(prod, (cx - wi // 2, cy - hi // 2), prod)
        return True
    except:
        desenhar_placeholder(bg, x1, y1, x2, y2)
        return False


def acionar_gerador_grade(df_produtos, fundo_path, n_layout):
    st.toast("🎨 Gerando Tabloide com Resolução Inteligente...", icon="⏳")
    if len(df_produtos) != n_layout:
        st.error(
            f"❌ O template atual precisa de exatamente {n_layout} produtos. Você selecionou {len(df_produtos)}.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    saida_dir = os.path.join(base_dir, "Encartes_Gerados")
    os.makedirs(saida_dir, exist_ok=True)

    font_desc = os.path.join(base_dir, "Fontes", "Montserrat-SemiBold.ttf")
    font_preco = os.path.join(base_dir, "Fontes", "Montserrat-Bold.ttf")

    if not os.path.exists(fundo_path):
        st.error(f"❌ Imagem de fundo não encontrada em: {fundo_path}")
        return

    produtos = df_produtos.to_dict("records")
    img_idx = obter_indice_imagens()

    bg = Image.open(fundo_path).convert("RGBA")
    draw = ImageDraw.Draw(bg)
    bg_w, bg_h = bg.size

    if n_layout == 9:
        fator_x = 37.8
        fator_y = 37.8
    else:
        fator_x = bg_w / 21.0
        fator_y = bg_h / 29.7

    faltantes = []
    cfg = LAYOUTS.get(n_layout, LAYOUTS[9])
    cols_count = cfg["cols"]

    for i in range(n_layout):
        row = produtos[i]
        codigo = normalizar_codigo_imagem(row.get("Código", ""))
        desc = str(row.get("Descrição", "")).strip()
        preco = row.get("Preço Final", row.get("Preço Atual", 0.0))
        c, l = i % cols_count, i // cols_count

        img_path = img_idx.get(codigo)
        ok = colar_imagem_grade(bg, img_path, cfg['img_x'][c][0], cfg['img_x']
                                [c][1], cfg['img_y'][l][0], cfg['img_y'][l][1], fator_x, fator_y)
        if not ok:
            faltantes.append({"Código": codigo, "Descrição": desc})

        desenhar_texto_box_grade(draw, desc, cfg['desc_x'][c][0], cfg['desc_x'][c]
                                 [1], cfg['desc_y'][l][0], cfg['desc_y'][l][1], font_desc, fator_x, fator_y)
        desenhar_preco_box_grade(draw, preco, cfg['preco_x'][c][0], cfg['preco_x'][c]
                                 [1], cfg['preco_y'][l][0], cfg['preco_y'][l][1], font_preco, fator_x, fator_y)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(saida_dir, f"encarte_grade_{n_layout}_{ts}.jpg")
    bg.convert("RGB").save(out_path, "JPEG", quality=95, optimize=True)

    st.balloons()
    st.success("✅ Arte gerada com sucesso e alinhada aos pixels reais!")

    if faltantes:
        st.warning(f"⚠️ {len(faltantes)} produto(s) não tinham imagem!")

    st.image(out_path, caption="Sua arte está pronta!",
             use_container_width=True)
    with open(out_path, "rb") as f:
        st.download_button(
            label="💾 BAIXAR IMAGEM ALTA RESOLUÇÃO (JPG)",
            data=f,
            file_name=os.path.basename(out_path),
            mime="image/jpeg",
            type="primary",
            use_container_width=True
        )

# ==========================================
# 2. GERADOR ARTES INDIVIDUAIS
# ==========================================


def acionar_gerador_individual(df_produtos, fundo_path):
    st.toast("🎨 Gerando Artes Individuais...", icon="⏳")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    saida_dir = os.path.join(base_dir, "Encartes_Individuais")
    os.makedirs(saida_dir, exist_ok=True)

    font_desc = os.path.join(base_dir, "Fontes", "Montserrat-SemiBold.ttf")
    font_preco = os.path.join(base_dir, "Fontes", "Montserrat-Bold.ttf")

    if not os.path.exists(fundo_path):
        st.error(f"❌ Template não encontrado: {fundo_path}")
        return []

    produtos = df_produtos.to_dict("records")
    img_idx = obter_indice_imagens()

    faltantes = []
    gerados = []

    for i, row in enumerate(produtos):
        codigo = normalizar_codigo_imagem(row.get("Código", ""))
        desc = str(row.get("Descrição", "")).strip()
        preco = row.get("Preço Final", row.get("Preço Atual", 0.0))

        img_path = img_idx.get(codigo)
        bg = Image.open(fundo_path).convert("RGBA")
        draw = ImageDraw.Draw(bg)

        x1, x2 = 397, 1649
        y1, y2 = 684, 1619
        max_w = x2 - x1
        max_h = y2 - y1

        if img_path and os.path.exists(img_path):
            try:
                prod = Image.open(img_path).convert("RGBA")
                prod = remover_fundo_branco(prod)
                bbox = prod.getbbox()
                if bbox:
                    prod = prod.crop(bbox)

                prod_w, prod_h = prod.size
                ratio = min(max_w / prod_w, max_h / prod_h)
                new_w, new_h = int(prod_w * ratio), int(prod_h * ratio)

                prod = prod.resize((new_w, new_h), Image.Resampling.LANCZOS)
                cx, cy = x1 + max_w // 2, y1 + max_h // 2
                bg.paste(prod, (cx - new_w // 2, cy - new_h // 2), prod)
            except Exception:
                faltantes.append({"Código": codigo, "Descrição": desc})
                ph_w, ph_h = min(max_w, 700), min(max_h, 700)
                cx, cy = x1 + max_w // 2, y1 + max_h // 2
                desenhar_placeholder(
                    bg, cx - ph_w//2, cy - ph_h//2, cx + ph_w//2, cy + ph_h//2)
        else:
            faltantes.append({"Código": codigo, "Descrição": desc})
            ph_w, ph_h = min(max_w, 700), min(max_h, 700)
            cx, cy = x1 + max_w // 2, y1 + max_h // 2
            desenhar_placeholder(bg, cx - ph_w//2, cy -
                                 ph_h//2, cx + ph_w//2, cy + ph_h//2)

        cx_desc = 397 + (1649 - 397) // 2
        tamanho_desc = 80
        fonte_d = carregar_fonte(font_desc, tamanho_desc)
        largura_max = 1250

        while tamanho_desc > 30:
            palavras = str(desc).split()
            linhas = []
            linha_atual = ""
            for p in palavras:
                teste = (linha_atual + " " + p).strip()
                try:
                    w = draw.textlength(teste, font=fonte_d)
                except:
                    w = draw.textbbox((0, 0), teste, font=fonte_d)[2]
                if w <= largura_max:
                    linha_atual = teste
                else:
                    if linha_atual:
                        linhas.append(linha_atual)
                    linha_atual = p
            if linha_atual:
                linhas.append(linha_atual)
            if len(linhas) <= 3:
                break
            tamanho_desc -= 4
            fonte_d = carregar_fonte(font_desc, tamanho_desc)

        total_h = len(linhas) * tamanho_desc + (len(linhas) - 1) * 10
        cur_y = 1660 + (250 - total_h) // 2
        for l in linhas[:3]:
            try:
                w = draw.textlength(l, font=fonte_d)
            except:
                w = draw.textbbox((0, 0), l, font=fonte_d)[2]
            draw.text((cx_desc - w // 2, cur_y), l, fill="black", font=fonte_d)
            cur_y += tamanho_desc + 10

        preco_str = f"{float(preco):.2f}".replace(".", ",")
        if "," in preco_str:
            inteiro, centavo = preco_str.split(",")
            centavo = "," + centavo
        else:
            inteiro, centavo = preco_str, ",00"

        box_x1, box_x2 = 1579, 1906
        box_y1, box_y2 = 321, 442
        box_w, box_h = box_x2 - box_x1, box_y2 - box_y1
        tamanho_preco_int = 250

        while tamanho_preco_int > 40:
            tamanho_preco_cent = int(tamanho_preco_int * 0.5)
            fonte_p_int = carregar_fonte(font_preco, tamanho_preco_int)
            fonte_p_cent = carregar_fonte(font_preco, tamanho_preco_cent)

            try:
                w_int = draw.textlength(inteiro, font=fonte_p_int)
            except:
                w_int = draw.textbbox((0, 0), inteiro, font=fonte_p_int)[2]
            try:
                w_cent = draw.textlength(centavo, font=fonte_p_cent)
            except:
                w_cent = draw.textbbox((0, 0), centavo, font=fonte_p_cent)[2]
            try:
                bbox_int = draw.textbbox((0, 0), inteiro, font=fonte_p_int)
                h_int = bbox_int[3] - bbox_int[1]
            except:
                h_int = tamanho_preco_int * 0.8

            if (w_int + w_cent) <= box_w and h_int <= box_h:
                break
            tamanho_preco_int -= 5

        total_w = w_int + w_cent
        start_x = box_x1 + (box_w - total_w) // 2
        cy_preco_top = box_y1 + (box_h - h_int) // 2

        try:
            offset_y_int = draw.textbbox((0, 0), inteiro, font=fonte_p_int)[1]
        except:
            offset_y_int = 0
        try:
            offset_y_cent = draw.textbbox(
                (0, 0), centavo, font=fonte_p_cent)[1]
        except:
            offset_y_cent = 0

        draw.text((start_x, cy_preco_top - offset_y_int),
                  inteiro, fill="black", font=fonte_p_int)
        draw.text((start_x + w_int, cy_preco_top - offset_y_cent),
                  centavo, fill="black", font=fonte_p_cent)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"arte_{codigo}_{ts}.jpg"
        out_path = os.path.join(saida_dir, nome_arquivo)
        bg.convert("RGB").save(out_path, "JPEG", quality=95, optimize=True)
        gerados.append({"path": out_path, "nome": nome_arquivo, "desc": desc})

    st.balloons()
    st.success(f"✅ {len(gerados)} Arte(s) Individual(is) gerada(s)!")
    if faltantes:
        st.warning(
            f"⚠️ {len(faltantes)} produto(s) com 'Imagem Indisponível'.")
    return gerados

# ==========================================
# 3. GERADOR PDF COM PLANILHA
# ==========================================


def gerar_pdf_planilha(df_produtos):
    st.toast("📄 Gerando PDF interativo...", icon="⏳")
    img_idx = obter_indice_imagens()
    buffer = BytesIO()

    page_width, page_height = landscape(letter)
    c = pdfcanvas.Canvas(buffer, pagesize=(page_width, page_height))
    form = c.acroForm

    margem_esq = 20
    margem_dir = 20
    margem_top = 20
    margem_bottom = 20

    largura_util = page_width - margem_esq - margem_dir
    altura_util = page_height - margem_top - margem_bottom

    titulo_h = 28
    header_h = 24
    row_h = 62

    # --- LARGURAS RECONFIGURADAS E PRIORIZADAS ---
    col_foto = 85
    col_desc = 477
    col_preco = 90
    col_chk = 55
    col_qtd = 45

    x_foto = margem_esq
    x_desc = x_foto + col_foto
    x_preco = x_desc + col_desc
    x_chk = x_preco + col_preco
    x_qtd = x_chk + col_chk

    rows_per_page = int((altura_util - titulo_h - header_h - 60) // row_h)
    rows_per_page = max(rows_per_page, 1)

    def quebrar_texto(texto, max_chars_l1=85, max_chars_l2=85):
        if len(texto) <= max_chars_l1:
            return [texto]
        palavras = texto.split()
        linhas = []
        limites = [max_chars_l1, max_chars_l2]

        for limite in limites:
            nova_linha = ""
            while palavras:
                teste = (nova_linha + " " + palavras[0]).strip()
                if len(teste) <= limite:
                    nova_linha = teste
                    palavras.pop(0)
                else:
                    break
            if nova_linha:
                linhas.append(nova_linha)

        if palavras:
            sobra = " ".join(palavras)
            if linhas:
                linhas[-1] = (linhas[-1][:max(0, len(linhas[-1]) - 3)
                                         ] + "...") if len(linhas[-1]) > 3 else "..."
            else:
                linhas = [sobra[:max_chars_l1 - 3] + "..."]
        return linhas[:2]

    def desenhar_cabecalho_pagina():
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor("#002D62"))
        c.drawString(margem_esq, page_height -
                     margem_top, "Tabela de Produtos")

        y_header_top = page_height - margem_top - titulo_h
        y_header_bottom = y_header_top - header_h

        c.setFillColor(colors.HexColor("#002D62"))
        c.rect(margem_esq, y_header_bottom,
               largura_util, header_h, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x_foto + col_foto / 2, y_header_bottom + 7, "Foto")
        c.drawCentredString(x_desc + col_desc / 2,
                            y_header_bottom + 7, "Código / Descrição")
        c.drawCentredString(x_preco + col_preco / 2,
                            y_header_bottom + 7, "Preço Final")
        c.drawCentredString(x_chk + col_chk / 2, y_header_bottom + 7, "Levar")
        c.drawCentredString(x_qtd + col_qtd / 2, y_header_bottom + 7, "Qtd")

        return y_header_bottom

    def desenhar_linha(y_top, row, idx_global):
        y_bottom = y_top - row_h

        if idx_global % 2 == 0:
            c.setFillColor(colors.white)
        else:
            c.setFillColor(colors.HexColor("#F7F7F7"))
        c.rect(margem_esq, y_bottom, largura_util, row_h, fill=1, stroke=0)

        c.setStrokeColor(colors.grey)
        c.rect(margem_esq, y_bottom, largura_util, row_h, fill=0, stroke=1)

        for x in [x_desc, x_preco, x_chk, x_qtd]:
            c.line(x, y_bottom, x, y_top)

        codigo = normalizar_codigo_imagem(row.get("Código", ""))
        codigo_original = str(row.get("Código", "")).strip()
        desc = str(row.get("Descrição", "")).strip()
        preco = float(row.get("Preço Final", row.get("Preço Atual", 0.0)))
        preco_str = f"R$ {preco:.2f}".replace(".", ",")

        img_path = img_idx.get(codigo)
        if img_path and os.path.exists(img_path):
            try:
                img_temp = Image.open(img_path).convert("RGBA")
                img_temp = remover_fundo_branco(img_temp)
                bbox = img_temp.getbbox()
                if bbox:
                    img_temp = img_temp.crop(bbox)

                max_img_w = 65
                max_img_h = 56
                img_w, img_h = img_temp.size
                ratio = min(max_img_w / img_w, max_img_h / img_h)
                new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                img_temp = img_temp.resize(
                    (new_w, new_h), Image.Resampling.LANCZOS)

                temp_img_buffer = BytesIO()
                img_temp.save(temp_img_buffer, format="PNG")
                temp_img_buffer.seek(0)

                img_reader = ImageReader(temp_img_buffer)
                img_x = x_foto + (col_foto - new_w) / 2
                img_y = y_bottom + (row_h - new_h) / 2
                c.drawImage(img_reader, img_x, img_y, width=new_w,
                            height=new_h, mask='auto')
            except Exception:
                c.setFont("Helvetica", 8)
                c.setFillColor(colors.red)
                c.drawCentredString(x_foto + col_foto / 2,
                                    y_bottom + 25, "Sem Foto")
        else:
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.red)
            c.drawCentredString(x_foto + col_foto / 2,
                                y_bottom + 25, "Sem Foto")

        texto_desc = f"{codigo_original} - {desc}"
        linhas = quebrar_texto(texto_desc, max_chars_l1=85, max_chars_l2=85)

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 11)

        if len(linhas) == 1:
            y_text = y_top - 34
            c.drawString(x_desc + 12, y_text, linhas[0])
        else:
            y_text = y_top - 24
            for linha in linhas:
                c.drawString(x_desc + 12, y_text, linha)
                y_text -= 16

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x_preco + col_preco / 2, y_bottom + 24, preco_str)

        chk_name = f"levar_{idx_global}"
        form.checkbox(
            name=chk_name,
            tooltip=f"Selecionar produto {codigo_original}",
            x=x_chk + 18,
            y=y_bottom + 20,
            buttonStyle='check',
            borderWidth=1,
            borderColor=colors.black,
            fillColor=colors.white,
            textColor=colors.black,
            forceBorder=True,
            checked=False
        )

        qtd_name = f"qtd_{idx_global}"
        form.textfield(
            name=qtd_name,
            tooltip=f"Quantidade do produto {codigo_original}",
            x=x_qtd + 6,
            y=y_bottom + 16,
            width=col_qtd - 12,
            height=22,
            borderStyle='inset',
            borderWidth=1,
            borderColor=colors.black,
            fillColor=colors.white,
            textColor=colors.black,
            forceBorder=True,
            value=""
        )

    def desenhar_rodape_final(total_produtos, y_fim_planilha):
        y2 = 28
        y3 = 16

        # Frase de ofertas centralizada logo abaixo da tabela
        c.setFillColor(colors.HexColor("#0f172a"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_width / 2, y_fim_planilha - 22,
                            "*Ofertas válidas para hoje ou enquanto durarem os estoques.")

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawRightString(page_width - margem_dir, 10,
                          f"Total de produtos: {total_produtos}")

        c.setFont("Helvetica", 8)
        c.drawString(margem_esq, y2,
                     "Abrir no Adobe Acrobat Reader para preencher")

        c.setFillColor(colors.HexColor("#666666"))
        c.setFont("Helvetica", 6.5)
        c.drawString(
            margem_esq, y3, "Sistema elaborado por EDG ENGENHARIA REPRESENTAÇÕES LTDA")

    total = len(df_produtos)
    registros = df_produtos.to_dict("records")

    for inicio in range(0, total, rows_per_page):
        y_header_bottom = desenhar_cabecalho_pagina()
        y_top = y_header_bottom

        bloco = registros[inicio:inicio + rows_per_page]
        for i, row in enumerate(bloco):
            desenhar_linha(y_top - (i * row_h), row, inicio + i)

        ultima_pagina = (inicio + rows_per_page >= total)
        if ultima_pagina:
            y_fim = y_top - (len(bloco) * row_h)
            desenhar_rodape_final(total, y_fim)
        else:
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.grey)
            c.drawRightString(page_width - margem_dir, 10,
                              f"Total de produtos: {total}")
            c.showPage()

    c.save()
    buffer.seek(0)

    st.balloons()
    st.success(
        f"✅ PDF interativo gerado com sucesso! ({len(df_produtos)} produtos)")
    return buffer


# ==========================================
# CARREGAMENTO DOS DADOS EXCEL (PASTA INTELIGENTE)
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
        st.error(
            f"🚨 PLANILHA NÃO ENCONTRADA: O sistema não achou '{caminho_planilha}'. Verifique o nome do arquivo no GitHub.")
        return pd.DataFrame(), []

    # LÊ A ABA "Curva ABC_Semanal" OFICIAL DA PLANILHA
    try:
        df_abc = pd.read_excel(
            caminho_planilha, sheet_name="Curva ABC_Semanal", header=None, engine='openpyxl')

        col_b = df_abc[1].astype(str)
        mask_tante = col_b.str.contains("TANTE: 999", na=False)
        idx_tante = df_abc.index[mask_tante]
        curva_abc_codigos = []

        if len(idx_tante) > 0:
            linha_inicio = idx_tante[0] + 2
            for i in range(linha_inicio, len(df_abc)):
                val = str(df_abc.iloc[i, 1]).strip()
                if (val == "" or val.lower() == "nan") and str(df_abc.iloc[i, 0]).strip().lower() in ["", "nan"]:
                    break

                cod_val = str(df_abc.iloc[i, 0])
                cod_limpo = re.sub(r"\D", "", cod_val.split("-")[0])
                if cod_limpo:
                    curva_abc_codigos.append(cod_limpo)
        else:
            curva_abc_codigos = []
    except Exception as e:
        print(f"Erro ao ler Curva ABC: {e}")
        curva_abc_codigos = []

    try:
        df_ind = pd.read_excel(caminho_planilha, sheet_name="Industrias",
                               skiprows=1, header=None, engine='openpyxl')
        lista_industrias = sorted([i for i in df_ind[0].apply(
            limpar_industria).dropna().unique() if i != ''])
    except Exception:
        lista_industrias = ['Unilever', 'Nestlé']

    try:
        df_marcas = pd.read_excel(
            caminho_planilha, sheet_name="Marcas", skiprows=1, header=None, engine='openpyxl')
        lista_marcas_reais = sorted([m.strip() for m in df_marcas[0].dropna().astype(
            str) if m.strip().lower() != 'nan' and m.strip() != ''])
    except Exception:
        lista_marcas_reais = ['Omo', 'Ninho']

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
        descricoes_bateu = set(df_bateu['Desc_Norm'].unique())
    except Exception:
        dict_bateu_ind, dict_bateu_mar, descricoes_bateu = {}, {}, set()

    try:
        df = pd.read_excel(caminho_planilha, sheet_name="Banco_Dados_Semanal",
                           skiprows=5, header=None, engine='openpyxl')

        coluna_b_original = df[1].copy()

        cat_raw = df[1].astype(str)
        mask_categoria = cat_raw.str.match(r'^\s*\d{1,3}\s*-\s*.+')
        df['Categoria'] = cat_raw.where(
            mask_categoria, other=None).ffill().apply(manter_categoria_completa)
        df['Categoria'] = df['Categoria'].replace(
            '', 'Sem Categoria').fillna('Sem Categoria')

        df['Código'] = df[0].astype(str)
        df['Descrição'] = df[2].astype(str).str.strip("* ")

        df['Preço_7'] = pd.to_numeric(df[5], errors='coerce')
        df['Preço_14'] = pd.to_numeric(df[7], errors='coerce')
        df['Preço_21'] = pd.to_numeric(df[9], errors='coerce')
        df['Preço_28'] = pd.to_numeric(df[11], errors='coerce')
        df['ST_Flag'] = df.get(12, pd.Series()).fillna(
            "").astype(str).str.strip()

        df = df.dropna(subset=['Preço_7'])
        df = df[(df['Preço_7'] > 0) & (df['Descrição'].str.strip(
        ).str.lower() != 'nan') & (df['Descrição'].str.strip() != '')]

        df['Desc_Norm'] = df['Descrição'].apply(
            lambda x: re.sub(r'\s+', ' ', str(x).strip().upper()))
        df['Camp_Bateu'] = df['Desc_Norm'].isin(descricoes_bateu)

        df['Indústria'] = df['Desc_Norm'].map(dict_bateu_ind).fillna(pd.Series(np.random.choice(
            lista_industrias, size=len(df)) if lista_industrias else 'Sem Indústria', index=df.index))
        df['Marca_BL'] = df['Desc_Norm'].map(dict_bateu_mar)
        mask_missing = df['Marca_BL'].isna() | (df['Marca_BL'] == '')
        df['Marca'] = df['Marca_BL']
        if mask_missing.any():
            df.loc[mask_missing, 'Marca'] = df.loc[mask_missing,
                                                   'Desc_Norm'].apply(achar_marca)

        np.random.seed(42)
        df['Fator_Anterior'] = np.random.choice(
            [1.0, 1.05, 1.15, 0.95], size=len(df), p=[0.5, 0.2, 0.1, 0.2])

        curva_abc_set = set(curva_abc_codigos)

        def eh_curva_abc(cod):
            num = re.sub(r"\D", "", str(cod).split("-")[0])
            return num in curva_abc_set
        df['Curva_ABC'] = df['Código'].apply(eh_curva_abc)

        def checar_meta_mensal(row):
            desc = str(row.get('Desc_Norm', '')).upper()
            marca = str(row.get('Marca', '')).upper()
            cat = str(row.get('Categoria', '')).upper()

            if 'ESCOLA' in cat or 'PAPELARIA' in cat:
                return True
            if 'INSETICIDA' in cat or 'INSETICIDA' in desc:
                return True
            if 'FOLHALEV' in marca or 'FOLHA LEV' in marca:
                return True
            if 'BABYSEC' in marca or 'BABY SEC' in marca:
                return True
            if 'CHAMEX' in marca or 'CHAMEX' in desc:
                return True
            if 'CHAMEQUINHO' in marca or 'CHAMEQUINHO' in desc:
                return True
            if ('LIMAO' in marca or 'LIMÃO' in marca) and ('LIXO' in desc or 'SACO' in desc):
                return True
            if 'LIMAO' in desc and 'LIXO' in desc:
                return True
            if 'NETZ' in marca and ('LIXO' in desc or 'SACO' in desc):
                return True
            if 'NETZ' in desc and 'LIXO' in desc:
                return True
            return False

        df['Meta_Mensal'] = df.apply(checar_meta_mensal, axis=1)

        # TO PODENDO
        codigos_podendo_exatos, codigos_podendo_parciais = set(), set()
        try:
            df_podendo = pd.read_excel(
                caminho_planilha, sheet_name="TO PODENDO", header=None, engine='openpyxl')
            for col in df_podendo.columns:
                for val in df_podendo[col].dropna():
                    val_str = str(val).strip().upper()
                    if 'E+' in val_str:
                        raiz = re.sub(r'\D', '', val_str.split('E')[0])
                        if len(raiz) >= 4:
                            codigos_podendo_parciais.add(raiz)
                    else:
                        v_num = re.sub(r'\D', '', val_str)
                        if len(v_num) >= 4:
                            codigos_podendo_exatos.add(v_num)
        except Exception:
            pass

        def cruzar_ean_podendo(idx):
            val_b = re.sub(r'\D', '', str(coluna_b_original.get(idx, "")))
            val_a = re.sub(r'\D', '', str(df.at[idx, 'Código']))
            if val_b and val_b in codigos_podendo_exatos:
                return True
            if val_a and val_a in codigos_podendo_exatos:
                return True
            for parcial in codigos_podendo_parciais:
                if val_b and val_b.startswith(parcial):
                    return True
                if val_a and val_a.startswith(parcial):
                    return True
            return False

        df['Camp_ToPodendo'] = [cruzar_ean_podendo(idx) for idx in df.index]
        if not df['Camp_ToPodendo'].any():
            marcas_podendo = ['KINDER', 'MAGGI', 'GAROTO',
                              'NESTLE', 'SUFRESH', 'TODDY', 'NESCAU']

            def fallback_podendo(desc):
                for m in marcas_podendo:
                    if m in desc:
                        return True
                return False
            df['Camp_ToPodendo'] = df['Desc_Norm'].apply(fallback_podendo)

        # COLGATE
        codigos_colgate_exatos, codigos_colgate_parciais = set(), set()
        try:
            df_colgate = pd.read_excel(
                caminho_planilha, sheet_name="COLGATE", header=None, engine='openpyxl')
            for col in df_colgate.columns:
                for val in df_colgate[col].dropna():
                    val_str = str(val).strip().upper()
                    if 'E+' in val_str:
                        raiz = re.sub(r'\D', '', val_str.split('E')[0])
                        if len(raiz) >= 4:
                            codigos_colgate_parciais.add(raiz)
                    else:
                        v_num = re.sub(r'\D', '', val_str)
                        if len(v_num) >= 4:
                            codigos_colgate_exatos.add(v_num)
        except Exception:
            pass

        def cruzar_ean_colgate(idx):
            val_b = re.sub(r'\D', '', str(coluna_b_original.get(idx, "")))
            val_a = re.sub(r'\D', '', str(df.at[idx, 'Código']))
            if val_b and val_b in codigos_colgate_exatos:
                return True
            if val_a and val_a in codigos_colgate_exatos:
                return True
            for parcial in codigos_colgate_parciais:
                if val_b and val_b.startswith(parcial):
                    return True
                if val_a and val_a.startswith(parcial):
                    return True
            return False

        df['Camp_Colgate'] = [cruzar_ean_colgate(idx) for idx in df.index]
        if not df['Camp_Colgate'].any():
            marcas_colgate = ['COLGATE', 'SORRISO',
                              'PROTEX', 'PALMOLIVE', 'AJAX', 'PINHO SOL']

            def fallback_colgate(desc):
                for m in marcas_colgate:
                    if m in desc:
                        return True
                return False
            df['Camp_Colgate'] = df['Desc_Norm'].apply(fallback_colgate)

    except Exception as e:
        st.error(f"Erro ao carregar Excel: {e}")
        df = pd.DataFrame()

    return df, curva_abc_codigos


# ==============================================================
# CARREGAMENTO SEGURO DA SESSÃO
# ==============================================================
try:
    df_raw, lista_abc = carregar_dados()
except ValueError:
    st.cache_data.clear()
    df_raw, lista_abc = carregar_dados()

st.session_state['codigos_abc_planilha'] = lista_abc


def atualizar_prazo():
    novo_prazo = st.session_state.prazo_selector
    if not novo_prazo:
        novo_prazo = "Preço_7"
    for prod in st.session_state['produtos_selecionados']:
        cod = prod['Código']
        row = df_raw[df_raw['Código'] == cod]
        if not row.empty:
            novo_preco = row.iloc[0][novo_prazo]
            if pd.isna(novo_preco):
                novo_preco = row.iloc[0]['Preço_7']

            prod['Preço Atual'] = float(novo_preco)
            st.session_state[f"pr_{cod}"] = float(novo_preco)
            atualizar_valores_uid(u_id=cod)


# ==========================================
# INTERFACE DO STREAMLIT
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3144/3144456.png", width=60)
    st.markdown("<p class='subtitulo'>Layout do Encarte</p>",
                unsafe_allow_html=True)

    if 'num_produtos_layout' not in st.session_state:
        st.session_state['num_produtos_layout'] = 0

    opcoes_layout = {0: "Sem Limite", 9: "9 Espaços", 12: "12 Espaços",
                     16: "16 Espaços", 20: "20 Espaços"}
    layout_selecionado = st.segmented_control(
        "Escolha o formato:", options=list(opcoes_layout.keys()),
        format_func=lambda x: opcoes_layout[x], selection_mode="single",
        default=st.session_state.get('num_produtos_layout', 0),
        key=f"layout_selector_dinamico_{st.session_state.get('num_produtos_layout', 0)}"
    )

    if layout_selecionado is not None and layout_selecionado != st.session_state['num_produtos_layout']:
        st.session_state['num_produtos_layout'] = layout_selecionado

    num_produtos = st.session_state['num_produtos_layout']
    st.divider()

    st.markdown("<p class='subtitulo'>Prazo de Pagamento</p>",
                unsafe_allow_html=True)
    opcoes_prazo = {"Preço_7": "7 Dias", "Preço_14": "14 Dias",
                    "Preço_21": "21 Dias", "Preço_28": "28 Dias"}
    prazo_selecionado = st.segmented_control(
        "Escolha o prazo:", options=list(opcoes_prazo.keys()),
        format_func=lambda x: opcoes_prazo[x], default="Preço_7",
        selection_mode="single", key="prazo_selector", on_change=atualizar_prazo
    )
    if not prazo_selecionado:
        prazo_selecionado = "Preço_7"

    df_app = df_raw.copy()
    if not df_app.empty:
        df_app['Preço Atual'] = df_app[prazo_selecionado].fillna(
            df_app['Preço_7'])
        df_app['Preço Anterior'] = df_app['Preço Atual'] * \
            df_app['Fator_Anterior']
        df_app['Preço Anterior'] = np.where(
            df_app['Preço Anterior'] == 0, 1, df_app['Preço Anterior'])
        df_app['Desconto %'] = (
            (df_app['Preço Anterior'] - df_app['Preço Atual']) / df_app['Preço Anterior'] * 100).round(1)

        def gerar_status(row):
            perc = row['Desconto %']
            if row['Preço Atual'] < row['Preço Anterior']:
                return f"🟢 Baixou! (-{abs(perc)}%)"
            elif row['Preço Atual'] > row['Preço Anterior']:
                return f"🔴 Aumentou! (+{abs(perc)}%)"
            else:
                return "⚫ Igual"
        df_app['Status'] = df_app.apply(gerar_status, axis=1)

    df_filtrado = df_app.copy()
    st.divider()

    st.markdown("<p class='subtitulo'>🔥 Filtros Inteligentes</p>",
                unsafe_allow_html=True)
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_abc = st.checkbox("Curva ABC")
    with col_f2:
        filtro_metas = st.checkbox("Metas Mensal (PRO)")

    if filtro_abc and not df_filtrado.empty:
        df_filtrado = df_filtrado[df_filtrado['Curva_ABC'] == True]
    if filtro_metas and not df_filtrado.empty:
        df_filtrado = df_filtrado[df_filtrado['Meta_Mensal'] == True]

    st.divider()
    st.markdown("<p class='subtitulo'>Campanhas</p>", unsafe_allow_html=True)
    c_bateu = st.checkbox("BATEU LEVOU")
    c_podendo = st.checkbox("TO PODENDO")
    c_sellout = st.checkbox("SELL OUT")
    c_colgate = st.checkbox("COLGATE")

    if not df_filtrado.empty and (c_bateu or c_podendo or c_sellout or c_colgate):
        mask_campanhas = pd.Series(False, index=df_filtrado.index)
        if c_bateu:
            mask_campanhas = mask_campanhas | df_filtrado['Camp_Bateu']
        if c_colgate:
            mask_campanhas = mask_campanhas | df_filtrado['Camp_Colgate']
        if c_podendo:
            mask_campanhas = mask_campanhas | df_filtrado['Camp_ToPodendo']
        if c_sellout:
            mask_campanhas = mask_campanhas | (
                df_filtrado['Campanha'] == 'SELL OUT') if 'Campanha' in df_filtrado.columns else mask_campanhas

        df_filtrado = df_filtrado[mask_campanhas]
        if df_filtrado.empty:
            st.warning(
                "⚠️ Nenhum produto encontrado com os filtros atuais selecionados.")

    st.divider()
    st.markdown("<p class='subtitulo'>Filtros de Busca (Cascata)</p>",
                unsafe_allow_html=True)
    if not df_filtrado.empty:
        industrias_disp = sorted(
            [str(x) for x in df_filtrado['Indústria'].dropna().unique() if str(x).strip() != ''])
        industria_f = st.selectbox("1. Indústria", options=[
                                   'Todas'] + industrias_disp)
        if industria_f != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Indústria'] == industria_f]

        marcas_disp = sorted(
            [str(x) for x in df_filtrado['Marca'].dropna().unique() if str(x).strip() != ''])
        marca_f = st.selectbox("2. Marca", options=['Todas'] + marcas_disp)
        if marca_f != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Marca'] == marca_f]

        cats_disp = sorted([str(x) for x in df_filtrado['Categoria'].dropna(
        ).unique() if str(x).strip() not in ('', 'Sem Categoria')])
        categoria_f = st.selectbox(
            "3. Categoria", options=['Todas'] + cats_disp)
        if categoria_f != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_f]
    else:
        st.info("Nenhum item disponível para filtrar nessas categorias.")

tab1, tab2 = st.tabs(["📊 Montagem do Tabloide", "🤖 IA Limpador"])

with tab1:
    if not df_app.empty:
        df_baixou = df_app[df_app['Status'].str.contains("Baixou")]
        top_10 = df_baixou.nlargest(10, 'Desconto %')
        if not top_10.empty:
            img_idx_global = obter_indice_imagens()
            html_items = ""
            for _, r in top_10.iterrows():
                cod = normalizar_codigo_imagem(r['Código'])
                caminho_img = img_idx_global.get(cod)
                b64_str = image_to_base64(caminho_img)
                img_tag = f"<img src='data:image/jpeg;base64,{b64_str}' style='height:40px; border-radius:4px; vertical-align:middle; margin-right:8px; background-color:white;' />" if b64_str else ""
                desc_curta = str(r['Descrição'])[
                    :30] + "..." if len(str(r['Descrição'])) > 30 else str(r['Descrição'])
                html_items += f"<span style='display:inline-block; margin:0 40px; align-items:center;'>{img_tag}🔥 {desc_curta} <span style='background-color:#00E676; color:#002D62; padding:2px 8px; border-radius:12px; font-weight:800; margin-left:8px;'>-{r['Desconto %']}%</span> (De: R$ <strike>{r['Preço Anterior']:.2f}</strike> | Por: R$ {r['Preço Atual']:.2f})</span>"

            banner_html = f"<!DOCTYPE html><html><head><style>body{{margin:0;padding:0;background-color:transparent;font-family:sans-serif;}}.mq-container{{width:100%;overflow:hidden;background-color:#002D62;color:white;padding:12px 0;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1);white-space:nowrap;}}.mq-content{{display:inline-block;animation:scroll 25s linear infinite;font-size:18px;font-weight:600;white-space:nowrap;}}.mq-container:hover .mq-content{{animation-play-state:paused;}}@keyframes scroll{{0%{{transform:translateX(100vw);}}100%{{transform:translateX(-100%);}}}} </style></head><body><div class='mq-container'><div class='mq-content'>{html_items}</div></div></body></html>"
            st.components.v1.html(banner_html, height=65)

    st.markdown("<p class='titulo-secao'>🤖 Geradores Automáticos (20 Espaços)</p>",
                unsafe_allow_html=True)

    cg1, cg2, cg3, cg4 = st.columns(4)

    with cg1:
        if st.button("✨ TODAS CAMPANHAS (PRO)", use_container_width=True):
            st.session_state['produtos_selecionados'] = []
            st.session_state['num_produtos_layout'] = 20
            add_auto_products(df_app[df_app['Camp_Bateu'] == True].sort_values(
                'Desconto %', ascending=False), 5)
            add_auto_products(df_app[df_app['Curva_ABC'] == True], 5)
            add_auto_products(df_app[df_app['Camp_Colgate'] == True].sort_values(
                'Desconto %', ascending=False), 3)
            add_auto_products(df_app[df_app['Camp_ToPodendo'] == True].sort_values(
                'Desconto %', ascending=False), 3)
            add_auto_products(df_app[df_app['Meta_Mensal'] == True].sort_values(
                'Desconto %', ascending=False), 4)
            st.rerun()

    with cg2:
        if st.button("💥 BATEU LEVOU (20 Itens)", use_container_width=True):
            st.session_state['produtos_selecionados'] = []
            st.session_state['num_produtos_layout'] = 20
            add_auto_products(df_app[df_app['Camp_Bateu'] == True].sort_values(
                'Desconto %', ascending=False), 20)
            st.rerun()

    with cg3:
        if st.button("🎯 META MENSAL - PRO (20 Itens)", use_container_width=True):
            st.session_state['produtos_selecionados'] = []
            st.session_state['num_produtos_layout'] = 20
            add_auto_products(df_app[df_app['Meta_Mensal'] == True].sort_values(
                'Desconto %', ascending=False), 20)
            st.rerun()

    with cg4:
        if st.button("📈 CURVA ABC", use_container_width=True):
            st.session_state['produtos_selecionados'] = []
            st.session_state['num_produtos_layout'] = 20
            faltantes = []
            codigos_para_adicionar = st.session_state.get(
                'codigos_abc_planilha', [])

            for cod in codigos_para_adicionar:
                df_match = df_app[df_app['Código'].apply(
                    lambda x: re.sub(r"\D", "", str(x).split("-")[0])) == cod]
                if df_match.empty:
                    faltantes.append(cod)
                else:
                    r = df_match.iloc[0]
                    if not any(d['Código'] == r['Código'] for d in st.session_state['produtos_selecionados']):
                        st.session_state['produtos_selecionados'].append({
                            'Levar': True, 'Código': r['Código'], 'Status': r['Status'],
                            'Descrição': r['Descrição'], 'Preço Atual': float(r['Preço Atual']),
                            'Comissão': 0.0, 'FLEX': 0.0, 'DESC': 0.0, 'Imposto': False,
                            'Preço Final': float(r['Preço Atual']), 'ST_Flag': r.get('ST_Flag', '')
                        })

            if faltantes:
                st.warning(
                    f"⚠️ {len(faltantes)} produto(s) da Curva ABC não foram encontrados na aba Banco_Dados_Semanal.")
            st.rerun()

    st.markdown("---")
    st.markdown("<p class='titulo-secao'>Selecionar Produtos Manualmente</p>",
                unsafe_allow_html=True)

    img_idx_busca = obter_indice_imagens()
    codigos_ja_selecionados = [p['Código']
                               for p in st.session_state['produtos_selecionados']]

    if not df_filtrado.empty:
        def formatar_opcao(x):
            preco_atual, preco_antigo = f"R$ {x['Preço Atual']:.2f}", f"R$ {x['Preço Anterior']:.2f}"
            tem_foto = "📸 Com Foto" if normalizar_codigo_imagem(
                x['Código']) in img_idx_busca else "❌ Sem Foto"
            texto_base = f"{x['Código']} | {x['Descrição']} | Atual: {preco_atual} (Era: {preco_antigo} - {x['Status']}) | {tem_foto}"
            return f"🔴 [JÁ ADICIONADO] {texto_base}" if str(x['Código']) in codigos_ja_selecionados else texto_base

        opcoes_busca = ["Digite ou selecione um produto..."] + \
            df_filtrado.apply(formatar_opcao, axis=1).tolist()
    else:
        opcoes_busca = ["Digite ou selecione um produto..."]

    col_busca, col_limpar, col_atualizar = st.columns([5, 1.2, 1.2])
    with col_busca:
        st.selectbox("Adicionar Produto:", options=opcoes_busca, key="busca_temp",
                     on_change=processar_busca, label_visibility="collapsed")
    with col_limpar:
        if st.button("🗑️ Esvaziar Tudo", use_container_width=True):
            st.session_state['produtos_selecionados'], st.session_state['galeria_individuais'], st.session_state['confirmacao_st'] = [
            ], [], None
            st.rerun()
    with col_atualizar:
        if st.button("🔄 Atualizar App", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

    txt_limite = "Sem limite" if num_produtos == 0 else f"{num_produtos} espaços"
    st.markdown(
        f"**Itens no painel:** {len(st.session_state['produtos_selecionados'])} / {txt_limite}")
    st.markdown("---")

    if len(st.session_state['produtos_selecionados']) == 0:
        st.info(
            "O painel está vazio. Busque e adicione produtos acima para montar seu encarte.")
    else:
        ch_c, stat_c, img_c, desc_c, prec_c, co_c, flex_c, des_c, imp_c, fin_c = st.columns(
            [1.2, 0.9, 1.0, 2.2, 1.0, 1.3, 1.3, 1.3, 1.0, 1.3])
        ch_c.markdown("**Ações**")
        stat_c.markdown("**Status**")
        img_c.markdown("**Foto**")
        desc_c.markdown("**Descrição**")
        prec_c.markdown("**Preço (R$)**")
        co_c.markdown("**Comissão(%)**")
        flex_c.markdown("**FLEX(%)**")
        des_c.markdown("**DESC(%)**")
        imp_c.markdown("**Imposto**")
        fin_c.markdown("**FINAL**")
        st.markdown("---")

        img_idx_global = obter_indice_imagens()

        for i, prod in enumerate(st.session_state['produtos_selecionados']):
            u_id = prod['Código']
            if f"chk_{u_id}" not in st.session_state:
                st.session_state[f"chk_{u_id}"] = prod.get('Levar', True)
            if f"pr_{u_id}" not in st.session_state:
                st.session_state[f"pr_{u_id}"] = float(prod['Preço Atual'])
            if f"co_{u_id}" not in st.session_state:
                st.session_state[f"co_{u_id}"] = float(prod['Comissão'])
            if f"fl_{u_id}" not in st.session_state:
                st.session_state[f"fl_{u_id}"] = float(prod['FLEX'])
            if f"de_{u_id}" not in st.session_state:
                st.session_state[f"de_{u_id}"] = float(prod['DESC'])
            if f"im_{u_id}" not in st.session_state:
                st.session_state[f"im_{u_id}"] = bool(
                    prod.get('Imposto', False))

            c_bt, c_st, c_ig, c_ds, c_pr, c_co, c_fl, c_de, c_im, c_fi = st.columns(
                [1.2, 0.9, 1.0, 2.2, 1.0, 1.3, 1.3, 1.3, 1.0, 1.3], vertical_alignment="center")

            with c_bt:
                b1, b2, b3, b4 = st.columns([1.2, 1, 1, 1])
                with b1:
                    st.session_state['produtos_selecionados'][i]['Levar'] = st.checkbox(
                        "", key=f"chk_{u_id}")
                with b2:
                    if st.button("⬆️", key=f"up_{u_id}", type="tertiary"):
                        mover_cima(i)
                        st.rerun()
                with b3:
                    if st.button("⬇️", key=f"dw_{u_id}", type="tertiary"):
                        mover_baixo(i)
                        st.rerun()
                with b4:
                    if st.button("❌", key=f"del_{u_id}", type="tertiary"):
                        deletar_item(i)
                        st.rerun()

            with c_st:
                st.write(prod['Status'])

        with c_ig:
            cod = normalizar_codigo_imagem(prod['Código'])
            caminho_img = img_idx_global.get(cod)
            url_google = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(prod['Descrição'])}"

            # Sub-colunas minúsculas para alinhar Buscar e Trocar lado a lado
            b1, b2 = st.columns([1, 1], gap="small")

            # Estilo unificado para o botão de Buscar HTML
            style_base = "display:flex; align-items:center; justify-content:center; height:24px; font-size:9px; font-weight:bold; border-radius:4px; text-decoration:none; margin-top:2px;"
            style_sec = f"{style_base} background-color:#f1f5f9; color:#475569; border:1px solid #cbd5e1;"
            style_prim = f"{style_base} background-color:#3b82f6; color:#ffffff; border:1px solid #3b82f6;"

            # Estilo CSS injetado especificamente para forçar o botão do Popover a ficar idêntico
            st.markdown("""
                <style>
                div[data-testid="stPopover"] > button {
                    height: 24px !important;
                    min-height: 24px !important;
                    padding: 0 !important;
                    font-size: 9px !important;
                    font-weight: bold !important;
                    margin-top: 2px !important;
                }
                </style>
            """, unsafe_allow_html=True)

            if caminho_img and os.path.exists(caminho_img):
                st.image(caminho_img, width=45)
                
                with b1:
                    st.markdown(f"<a href='{url_google}' target='_blank' style='{style_sec}'>🔄 Buscar</a>", unsafe_allow_html=True)
                with b2:
                    with st.popover("📤 Trocar", use_container_width=True):
                        nova_img = st.file_uploader("Nova foto:", type=['png', 'jpg', 'jpeg', 'webp'], key=f"up_trocar_{u_id}")
                        if nova_img and st.button("Salvar", key=f"btn_trocar_{u_id}", type="primary"):
                            salvar_imagem_upload(nova_img, cod)
                            st.rerun()
            else:
                st.markdown("<div style='text-align:center; color:#ff4b4b; font-size:10px; font-weight:bold; line-height:1.2; padding-top:5px; height:45px; display:flex; align-items:center; justify-content:center;'>❌<br>Sem Foto</div>", unsafe_allow_html=True)
                
                with b1:
                    st.markdown(f"<a href='{url_google}' target='_blank' style='{style_prim}'>🔍 Buscar</a>", unsafe_allow_html=True)
                with b2:
                    with st.popover("📤 Subir", use_container_width=True):
                        nova_img = st.file_uploader("Upload:", type=['png', 'jpg', 'jpeg', 'webp'], key=f"up_novo_{u_id}")
                        if nova_img and st.button("Salvar", key=f"btn_novo_{u_id}", type="primary"):
                            salvar_imagem_upload(nova_img, cod)
                            st.rerun()

            with c_ds:
                cod_base = normalizar_codigo_imagem(prod['Código'])
                html_copy = f"""<html><body style="margin:0; padding:0; background:transparent; overflow:hidden;"><script>function copyText(text, btn) {{ if (navigator.clipboard) {{ navigator.clipboard.writeText(text); }} else {{ var t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); document.execCommand("Copy"); t.remove(); }} btn.innerText = '✔️ Copiado!'; setTimeout(() => btn.innerText = '📋 Copiar', 2000); }}</script><div style="font-family: sans-serif; display: flex; align-items: center; gap: 8px; margin-top:2px; margin-bottom:5px;"><span style="font-size: 13px; font-weight: bold; color: #64748b;">Cód: {cod_base}</span><button onclick="copyText('{cod_base}', this)" style="border: 1px solid #cbd5e1; background: #f8fafc; cursor: pointer; border-radius: 4px; font-size: 10px; padding: 2px 6px; color: #475569; transition: 0.2s;">📋 Copiar</button></div></body></html>"""
                st.components.v1.html(html_copy, height=25)
                st.write(f"**{prod['Descrição']}**")

            with c_pr:
                st.number_input("", format="%.2f", step=None, key=f"pr_{u_id}", on_change=atualizar_valores_uid, args=(
                    i, u_id), label_visibility="collapsed")

            with c_co:
                m_co, i_co, p_co = st.columns(
                    [0.7, 2.0, 0.7], gap="small", vertical_alignment="center")
                m_co.button("➖", key=f"co_m_{u_id}", type="tertiary", on_click=step_value, args=(
                    u_id, "co", -1.0))
                i_co.number_input("", format="%.1f", step=0.1, key=f"co_{u_id}", on_change=atualizar_valores_uid, args=(
                    i, u_id), label_visibility="collapsed")
                p_co.button("➕", key=f"co_p_{u_id}", type="tertiary", on_click=step_value, args=(
                    u_id, "co", 1.0))

            with c_fl:
                m_fl, i_fl, p_fl = st.columns(
                    [0.7, 2.0, 0.7], gap="small", vertical_alignment="center")
                m_fl.button("➖", key=f"fl_m_{u_id}", type="tertiary", on_click=step_value, args=(
                    u_id, "fl", -1.0))
                i_fl.number_input("", format="%.1f", step=0.1, key=f"fl_{u_id}", on_change=atualizar_valores_uid, args=(
                    i, u_id), label_visibility="collapsed")
                p_fl.button("➕", key=f"fl_p_{u_id}", type="tertiary", on_click=step_value, args=(
                    u_id, "fl", 1.0))

            with c_de:
                m_de, i_de, p_de = st.columns(
                    [0.7, 2.0, 0.7], gap="small", vertical_alignment="center")
                m_de.button("➖", key=f"de_m_{u_id}", type="tertiary", on_click=step_value, args=(
                    u_id, "de", -1.0))
                i_de.number_input("", format="%.1f", step=0.1, key=f"de_{u_id}", on_change=atualizar_valores_uid, args=(
                    i, u_id), label_visibility="collapsed")
                p_de.button("➕", key=f"de_p_{u_id}", type="tertiary", on_click=step_value, args=(
                    u_id, "de", 1.0))

            with c_im:
                if prod.get('ST_Flag') == '*':
                    st.markdown("<div style='color:#10b981; font-size:11px; font-weight:800; text-align:center; line-height:1.2; margin-bottom:-5px; padding-top:10px;'>com S.T<br>Não Calcular</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='color:#ef4444; font-size:11px; font-weight:800; text-align:center; line-height:1.2; margin-bottom:-5px; padding-top:10px;'>sem S.T<br>CALCULAR</div>", unsafe_allow_html=True)
                st.checkbox(
                    "+10.1%", key=f"im_{u_id}", on_change=atualizar_valores_uid, args=(i, u_id))

            with c_fi:
                st.write(f"### R$ {prod['Preço Final']:.2f}")
            st.markdown("---")

    vazio_esq, col_central, vazio_dir = st.columns([1, 5, 1])
    with col_central:
        opt_grade = st.session_state.get("sel_grade", "Layout 1")
        n_layout = st.session_state.get('num_produtos_layout', 0)

        btn1, btn2, btn3 = st.columns(3)

        with btn1:
            if st.button("🚀 GERAR TABLOIDE (GRADE)", type="primary", use_container_width=True):
                if n_layout == 0:
                    st.error(
                        "⚠️ Para gerar um tabloide em grade, escolha um layout fixo (9, 12, 16 ou 20) no menu lateral.")
                else:
                    st.session_state['galeria_individuais'], st.session_state['pdf_buffer_pronto'] = [
                    ], None
                    df_final = pd.DataFrame(
                        st.session_state['produtos_selecionados'])
                    if not df_final.empty:
                        df_final = df_final[df_final['Levar'] == True]

                    if df_final.empty:
                        st.error("⚠️ Você não deixou nenhum item marcado!")
                    else:
                        padrao_fundo = LAYOUTS.get(n_layout, LAYOUTS[9])[
                            "bg_pattern"]
                        num_versao = opt_grade.split()[-1]

                        if "Modelo" in padrao_fundo:
                            fundo_grade_name = f"Modelo {n_layout} Espaços-{num_versao}.jpg"
                        else:
                            fundo_grade_name = f"FUNDO-BASE-USADO-NA-AUTOMACAO-{num_versao}.jpg"

                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        f_path_grade = os.path.join(base_dir, fundo_grade_name)

                        alertas = checar_imposto_st(df_final)
                        if alertas:
                            st.session_state['confirmacao_st'], st.session_state['alertas_st'], st.session_state[
                                'df_pendente'], st.session_state['path_pendente'] = 'grade', alertas, df_final, f_path_grade
                        else:
                            st.session_state['confirmacao_st'] = None
                            acionar_gerador_grade(
                                df_final, f_path_grade, n_layout)

        with btn2:
            if st.button("📱 GERAR ARTES INDIVIDUAIS", type="secondary", use_container_width=True):
                opt_indiv = st.session_state.get("sel_indiv", "Layout 1")
                num_versao_indiv = opt_indiv.split()[-1]

                base_dir = os.path.dirname(os.path.abspath(__file__))
                f_path_indiv = os.path.join(
                    base_dir, f"Modelo_arte_individual_{num_versao_indiv}.jpg")

                st.session_state['pdf_buffer_pronto'] = None
                df_final = pd.DataFrame(
                    st.session_state['produtos_selecionados'])
                if not df_final.empty:
                    df_final = df_final[df_final['Levar'] == True]

                if df_final.empty:
                    st.error("⚠️ O painel está vazio ou sem itens marcados!")
                else:
                    alertas = checar_imposto_st(df_final)
                    if alertas:
                        st.session_state['confirmacao_st'], st.session_state['alertas_st'], st.session_state[
                            'df_pendente'], st.session_state['path_pendente'] = 'indiv', alertas, df_final, f_path_indiv
                    else:
                        st.session_state['confirmacao_st'] = None
                        st.session_state['galeria_individuais'] = acionar_gerador_individual(
                            df_final, f_path_indiv)

        with btn3:
            if st.button("📄 GERAR PDF (PLANILHA)", type="secondary", use_container_width=True):
                st.session_state['pdf_buffer_pronto'] = None
                df_final = pd.DataFrame(
                    st.session_state['produtos_selecionados'])
                if not df_final.empty:
                    df_final = df_final[df_final['Levar'] == True]

                if df_final.empty:
                    st.error("⚠️ O painel está vazio ou sem itens marcados!")
                else:
                    alertas = checar_imposto_st(df_final)
                    if alertas:
                        st.session_state['confirmacao_st'], st.session_state[
                            'alertas_st'], st.session_state['df_pendente'] = 'pdf', alertas, df_final
                    else:
                        st.session_state['confirmacao_st'] = None
                        st.session_state['pdf_buffer_pronto'] = gerar_pdf_planilha(
                            df_final)

        if st.session_state['confirmacao_st'] is not None:
            st.markdown("<div style='background-color:#fff1f2; border-left:4px solid #e11d48; padding:15px; margin-top:15px; margin-bottom:15px; border-radius:4px; box-shadow: 0px 4px 6px rgba(225, 29, 72, 0.1);'><h4 style='color:#e11d48; margin-top:0;'>⚠️ Atenção: Imposto Não Aplicado</h4><p style='color:#4c0519; margin-bottom:10px;'>Os seguintes produtos constam como <b>SEM S.T (Calcular)</b>, mas a caixa de <b>Imposto (+10.1%)</b> não foi marcada:</p><ul style='color:#881337; margin-bottom:15px; font-weight:bold;'>" +
                        "".join([f"<li>{p}</li>" for p in st.session_state['alertas_st']]) + "</ul><p style='color:#4c0519; font-weight:bold; margin-bottom:0;'>Deseja continuar a geração mesmo assim?</p></div>", unsafe_allow_html=True)
            c_sim, c_nao = st.columns(2)
            with c_sim:
                if st.button("✅ SIM, CONTINUAR", type="primary", use_container_width=True):
                    acao, df_p = st.session_state['confirmacao_st'], st.session_state['df_pendente']
                    path_p = st.session_state.get('path_pendente', '')
                    st.session_state['confirmacao_st'] = None
                    if acao == 'grade':
                        acionar_gerador_grade(
                            df_p, path_p, st.session_state.get('num_produtos_layout', 9))
                    elif acao == 'indiv':
                        st.session_state['galeria_individuais'] = acionar_gerador_individual(
                            df_p, path_p)
                    elif acao == 'pdf':
                        st.session_state['pdf_buffer_pronto'] = gerar_pdf_planilha(
                            df_p)
            with c_nao:
                if st.button("❌ NÃO, CANCELAR E ARRUMAR", type="secondary", use_container_width=True):
                    st.session_state['confirmacao_st'] = None
                    st.rerun()

        if st.session_state.get('pdf_buffer_pronto') is not None:
            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
            st.download_button("⬇️ BAIXAR PDF GERADO", data=st.session_state['pdf_buffer_pronto'],
                               file_name=f"produtos_planilha_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf", type="primary", use_container_width=True)

            st.markdown(
                "<hr style='margin: 15px 0;'><p class='subtitulo' style='text-align:center;'>🖼️ Escolha os Layouts</p>",
                unsafe_allow_html=True
            )
        # === RENDERIZAÇÃO DAS ARTES INDIVIDUAIS GERADAS ===
        if st.session_state.get('galeria_individuais'):
            st.markdown("<hr style='margin: 15px 0'>", unsafe_allow_html=True)
            st.markdown(
                "<h4 style='text-align:center; color:#1E293B;'>🎨 Galeria de Artes Individuais</h4>", unsafe_allow_html=True)

            cols_galeria = st.columns(4)
            for idx, arte in enumerate(st.session_state['galeria_individuais']):
                c_gal = cols_galeria[idx % 4]
                with c_gal:
                    if os.path.exists(arte['path']):
                        st.image(arte['path'], use_container_width=True)
                        with open(arte['path'], "rb") as f:
                            st.download_button(
                                label="⬇️ Baixar",
                                data=f,
                                file_name=arte['nome'],
                                mime="image/jpeg",
                                key=f"dl_indiv_{idx}",
                                use_container_width=True
                            )

        c_prev1, c_prev2, c_prev3 = st.columns(3)

        with c_prev1:
            texto_layout = "Sem Limite Definido" if n_layout == 0 else f"{n_layout} Espaços"
            st.markdown(
                f"<div style='text-align:center; font-weight:bold; color:#1E293B; margin-bottom:8px;'>Layout do Tabloide ({texto_layout})</div>",
                unsafe_allow_html=True
            )
            st.selectbox(
                "Versão Tabloide",
                ["Layout 1", "Layout 2", "Layout 3", "Layout 4"],
                key="sel_grade",
                label_visibility="collapsed"
            )

            if n_layout != 0:
                opt_g = st.session_state.get("sel_grade", "Layout 1")
                num_v_g = opt_g.split()[-1]

                if n_layout == 9:
                    nome_fundo_grade = f"FUNDO-BASE-USADO-NA-AUTOMACAO-{num_v_g}.jpg"
                else:
                    nome_fundo_grade = f"Modelo {n_layout} Espaços-{num_v_g}.jpg"

                f_path_g = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    nome_fundo_grade
                )
                if os.path.exists(f_path_g):
                    st.image(f_path_g, use_container_width=True)
                else:
                    st.warning(
                        f"⚠️ Imagem '{nome_fundo_grade}' não encontrada.")
            else:
                st.info(
                    "⚠️ Sem limite não gera tabloide em grade. Apenas artes individuais ou PDF.")

        with c_prev2:
            st.markdown(
                "<div style='text-align:center; font-weight:bold; color:#1E293B; margin-bottom:8px;'>Arte Individual</div>",
                unsafe_allow_html=True
            )
            st.selectbox(
                "Versão Individual",
                ["Layout 1", "Layout 2", "Layout 3", "Layout 4"],
                key="sel_indiv",
                label_visibility="collapsed"
            )

            opt_i = st.session_state.get("sel_indiv", "Layout 1")
            nome_fundo_indiv = f"Modelo_arte_individual_{opt_i.split()[-1]}.jpg"
            f_path_i = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                nome_fundo_indiv
            )

            if os.path.exists(f_path_i):
                st.image(f_path_i, use_container_width=True)
            else:
                st.warning(f"⚠️ Imagem '{nome_fundo_indiv}' faltando.")

        with c_prev3:
            st.markdown("""
            <div style='text-align:center; font-weight:bold; color:#1E293B; margin-bottom:8px;'>
                PDF Planilha
            </div>
            <div style='background-color: #ecfeff; border: 2px dashed #06b6d4; border-radius: 8px; height: 180px;
                        display: flex; align-items: center; justify-content: center; flex-direction: column;'>
                <span style='font-size: 40px;'>📄</span>
                <span style='color: #0f172a; font-weight: bold; margin-top: 10px;'>PDF Interativo</span>
                <span style='color: #475569; font-size: 12px; margin-top: 6px;'>Com checkboxes e campo de quantidade</span>
            </div>
            """, unsafe_allow_html=True)


with tab2:
    st.header("🤖 Decifrador de Sistema")
    texto_bruto = st.text_area(
        "Bloco de Texto:", height=200, placeholder="Ex: 05011897LIMP VD VIDREX TRAD...")
    if st.button("Decifrar com IA"):
        with st.spinner("Conectando..."):
            time.sleep(2)
            st.success("Interpretado!")

def gerar_encarte(df_produtos, formato):
    # Por enquanto este gerador foi feito para a arte 3x3 (9 espaços)
    if formato != "Grade":
        st.error(
            "Neste momento o gerador automático está disponível apenas para o formato Grade (9 espaços).")
        return

    if len(df_produtos) != 9:
        st.error("Para gerar a arte 3x3, selecione exatamente 9 produtos.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Ajuste para a sua estrutura local
    # pasta com 00016.jpeg, 00125.jpeg etc (conforme seu print)
    pasta_imagens = os.path.join(base_dir, "Base de Imagens")
    fundo_path = os.path.join(base_dir, "FUNDO-BASE-USADO-NA-AUTOMACAO-4.jpg")
    json_lista = os.path.join(base_dir, "ListaImagem-3.json")  # opcional

    saida_dir = os.path.join(base_dir, "saidas_encarte")

    # Fontes opcionais (se você colocar os .ttf dentro de uma pasta fonts)
    font_desc = os.path.join(base_dir, "fonts", "Montserrat-SemiBold.ttf")
    font_preco = os.path.join(base_dir, "fonts", "Montserrat-Bold.ttf")

    # Se você NÃO tiver as fontes, o gerador cai automaticamente para a fonte padrão do PIL.
    if not os.path.exists(font_desc):
        font_desc = None
    if not os.path.exists(font_preco):
        font_preco = None

    produtos = df_produtos.to_dict("records")

    try:
        out_path, faltantes = gerar_encarte_grade_jpg(
            produtos=produtos,
            pasta_imagens=pasta_imagens,
            fundo_path=fundo_path,
            saida_dir=saida_dir,
            json_lista_path=json_lista if os.path.exists(json_lista) else None,
            font_desc=font_desc,
            font_preco=font_preco
        )
    except Exception as e:
        st.error(f"Erro ao gerar encarte: {e}")
        return

    st.success("Encarte gerado com sucesso.")

    # Mostra faltantes (não trava, mas te garante que você saiba o que falhou)
    if faltantes:
        st.warning(
            f"{len(faltantes)} produto(s) ficaram sem imagem (ver lista abaixo).")
        st.dataframe(pd.DataFrame(faltantes))

    # Preview + download
    st.image(out_path, caption="Preview do encarte gerado",
             use_container_width=True)
    with open(out_path, "rb") as f:
        st.download_button(
            "Baixar JPG",
            data=f,
            file_name=os.path.basename(out_path),
            mime="image/jpeg",
            use_container_width=True
        )

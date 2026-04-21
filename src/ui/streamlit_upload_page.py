from pathlib import Path

import streamlit as st

from src.services.upload_service import process_upload


def render_upload_page() -> None:
    st.title("Carga de Arquivos")
    st.caption("Classificação por conteúdo, confirmação para banda intermediária e execução com dry-run.")

    uploaded = st.file_uploader("Envie planilha (.xls/.xlsx)", type=["xls", "xlsx"])
    user_name = st.text_input("Usuário operacional", value="operador")
    dry_run = st.checkbox("Executar em dry-run (sem efeitos colaterais)", value=True)

    if "pending_confirmation" not in st.session_state:
        st.session_state.pending_confirmation = None
    if "last_upload_report" not in st.session_state:
        st.session_state.last_upload_report = None

    if st.button("Processar upload", type="primary"):
        if not uploaded:
            st.error("Selecione um arquivo para continuar.")
            return

        temp_path = Path(".streamlit_upload_temp") / uploaded.name
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(uploaded.getbuffer())

        report = process_upload(
            str(temp_path),
            user=user_name,
            dry_run=dry_run,
            confirm_intermediate=False,
        )

        if report.get("decision") == "needs_confirmation":
            st.session_state.pending_confirmation = {
                "temp_path": str(temp_path),
                "user": user_name,
                "dry_run": dry_run,
                "preview_report": report,
            }
            st.warning("Arquivo caiu na banda intermediária. Escolha Confirmar ou Cancelar abaixo.")
        else:
            st.session_state.pending_confirmation = None
            st.session_state.last_upload_report = report

    pending = st.session_state.pending_confirmation
    if pending:
        st.subheader("Confirmação Obrigatória")
        st.json(pending["preview_report"])
        col_confirm, col_cancel = st.columns(2)

        if col_confirm.button("Confirmar carga", type="primary"):
            final_report = process_upload(
                pending["temp_path"],
                user=pending["user"],
                dry_run=pending["dry_run"],
                confirm_intermediate=True,
            )
            st.session_state.last_upload_report = final_report
            st.session_state.pending_confirmation = None
            st.success("Carga confirmada e processada.")

        if col_cancel.button("Cancelar carga"):
            st.session_state.last_upload_report = {
                "decision": "cancelled_by_operator",
                "reason": "intermediate_band_cancelled",
                "file": pending["preview_report"].get("file", ""),
            }
            st.session_state.pending_confirmation = None
            st.info("Carga cancelada pelo operador.")

    if st.session_state.last_upload_report is not None:
        st.subheader("Resultado")
        st.json(st.session_state.last_upload_report)

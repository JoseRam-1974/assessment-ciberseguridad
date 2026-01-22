import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuración inicial
st.set_page_config(page_title="Assessment Madurez CS", layout="wide")

if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'datos_contacto': {},
        'datos_enviados': False
    })

# --- ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Diagnóstico de Madurez CS")
    with st.form("registro"):
        nombre = st.text_input("Nombre*")
        empresa = st.text_input("Empresa*")
        email = st.text_input("Email*")
        if st.form_submit_button("Siguiente"):
            if nombre and empresa and email:
                st.session_state.datos_contacto = {"Nombre": nombre, "Empresa": empresa, "Email": email}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Campos obligatorios faltantes.")

# --- ETAPA 2: PREGUNTAS (SIMULADAS) ---
elif st.session_state.etapa == 'preguntas':
    st.title("Preguntas de Evaluación")
    st.write("Responda las preguntas...")
    if st.button("Finalizar y Guardar"):
        st.session_state.etapa = 'finalizado'
        st.rerun()


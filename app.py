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

# --- ETAPA 3: FINALIZADO Y GUARDADO ---
elif st.session_state.etapa == 'finalizado':
    st.success("✅ Assessment completado.")
    
   # --- BLOQUE DE GUARDADO SEGURO ---
if not st.session_state.datos_enviados:
    try:
        # Indicamos explícitamente la URL desde los secrets
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Recuperamos datos de forma segura
        info = st.session_state.get('datos_contacto', {})
        
        nueva_fila = pd.DataFrame([{
            "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Nombre": info.get("Nombre", "N/A"),
            "Empresa": info.get("Empresa", "N/A"),
            "Email": info.get("Email", "N/A"),
            "Madurez": nivel # Asegúrate de que esta variable esté definida arriba
        }])
        
        # IMPORTANTE: Cambia "Sheet1" por el nombre exacto de la pestaña de tu Excel (ej: "Hoja 1")
        actualizado = conn.create(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=nueva_fila)
        
        st.session_state.datos_enviados = True
        st.toast("✅ Lead registrado en Google Sheets")
    except Exception as e:
        st.error(f"Error al conectar con Sheets: {e}")

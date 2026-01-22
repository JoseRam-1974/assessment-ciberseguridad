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
    
    if not st.session_state.datos_enviados:
        try:
            # 1. Establecer conexión
            conn = st.connection("gsheets", type=GSheetsConnection)
            
            # 2. Preparar los datos de contacto de forma segura
            info = st.session_state.get('datos_contacto', {})
            
            # 3. Crear el DataFrame con la nueva fila
            nueva_fila = pd.DataFrame([{
                "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": info.get("Nombre", "N/A"),
                "Empresa": info.get("Empresa", "N/A"),
                "Email": info.get("Email", "N/A"),
                "Madurez": "Evaluado" # Puedes cambiarlo por tu variable de nivel
            }])
            
            # 4. Leer datos actuales para concatenar
            # Usamos el nombre de la hoja (Sheet1) o la URL de los secrets
            df_actual = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"])
            
            # 5. Concatenar y actualizar la hoja completa
            df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
            
            st.session_state.datos_enviados = True
            st.balloons()
            st.toast("🚀 Datos sincronizados con el Backoffice")
            
        except Exception as e:
            st.error(f"Error al sincronizar: {e}")

    if st.button("Realizar nuevo test"):
        st.session_state.clear()
        st.rerun()

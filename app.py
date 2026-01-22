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
    
    # 1. Definimos el nivel (asegúrate de que este cálculo ocurra aquí)
    # Si ya tienes una lógica de puntuación, aplícala antes de esta línea
    nivel_detectado = "Completado" 
    
    st.metric("Nivel de Madurez", nivel_detectado)
    
    # 2. BLOQUE DE GUARDADO SEGURO
    if not st.session_state.datos_enviados:
        try:
            # Conexión con la librería st-gsheets-connection
            conn = st.connection("gsheets", type=GSheetsConnection)
            
            # Recuperamos datos de contacto de la sesión
            info = st.session_state.get('datos_contacto', {})
            
            # Creamos la nueva fila con los datos capturados
            nueva_fila = pd.DataFrame([{
                "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": info.get("Nombre", "N/A"),
                "Empresa": info.get("Empresa", "N/A"),
                "Email": info.get("Email", "N/A"),
                "Madurez": nivel_detectado
            }])
            
            # Leemos la hoja actual usando la URL de tus Secrets
            # IMPORTANTE: La pestaña en tu Excel debe llamarse "Sheet1"
            df_actual = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="Sheet1")
            
            # Concatenamos los datos nuevos
            df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
            
            # Actualizamos la hoja de Google
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="Sheet1", data=df_final)
            
            st.session_state.datos_enviados = True
            st.balloons()
            st.toast("🚀 Datos sincronizados correctamente.")
            
        except Exception as e:
            st.error(f"Error al conectar con Sheets: {e}")

    if st.button("Realizar nuevo test"):
        st.session_state.clear()
        st.rerun()

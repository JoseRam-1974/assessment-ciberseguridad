import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re
import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# Inicializar todas las variables de sesión para evitar KeyErrors
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_usuario': [],
        'datos_contacto': {}, # Aquí se guardarán Nombre, Empresa, etc.
        'datos_enviados': False
    })

st.title("🛡️ Assessment Digital de Ciberseguridad")

# --- ETAPA 1: REGISTRO (Captura de Datos) ---
if st.session_state.etapa == 'registro':
    st.info("Por favor, ingrese sus datos corporativos para comenzar.")
    with st.form("registro_inicial"):
        c1, c2, c3 = st.columns(3)
        with c1: nombre = st.text_input("Nombre Completo*")
        with c2: cargo = st.text_input("Cargo*")
        with c3: empresa = st.text_input("Empresa*")
        
        c4, c5 = st.columns(2)
        with c4: mail = st.text_input("Email Corporativo*")
        with c5: tel = st.text_input("Teléfono")
        
        enviar_reg = st.form_submit_button("Comenzar Assessment")
        
        if enviar_reg:
            if nombre and empresa and mail:
                # GUARDAR EN SESSION STATE
                st.session_state.datos_contacto = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, "Email": mail, "Tel": tel
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Faltan campos obligatorios.")

# --- ETAPA 2: ASSESSMENT (Preguntas) ---
elif st.session_state.etapa == 'preguntas':
    # Aquí va tu lógica de lectura de 01. Preguntas.docx y el ciclo de preguntas
    # Al finalizar la última pregunta, cambia st.session_state.etapa = 'finalizado'
    st.write("Cargando preguntas...")
    # (Asumimos que el flujo llega al final)
    if st.button("Simular Finalización"): # Solo para probar el flujo
        st.session_state.etapa = 'finalizado'
        st.rerun()

# --- ETAPA 3: RESULTADOS Y BACKOFFICE ---
elif st.session_state.etapa == 'finalizado':
    st.success("✅ Evaluación Terminada")
    
    # Cálculos de madurez...
    nivel_final = "Intermedio" # Valor de ejemplo
    
    # --- BLOQUE SEGURO DE GOOGLE SHEETS ---
    if not st.session_state.datos_enviados:
        try:
            # Conexión
            conn = st.connection("gsheets", type=GSheetsConnection)
            
            # Recuperar datos usando .get() para evitar KeyErrors
            contacto = st.session_state.get('datos_contacto', {})
            
            # Crear el registro para la fila
            df_nuevo = pd.DataFrame([{
                "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": contacto.get("Nombre", "No proporcionado"),
                "Empresa": contacto.get("Empresa", "No proporcionado"),
                "Email": contacto.get("Email", "No proporcionado"),
                "Madurez": nivel_final
            }])
            
            # Actualizar Hoja
            df_actual = conn.read(worksheet="Sheet1")
            df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
            conn.update(worksheet="Sheet1", data=df_final)
            
            st.session_state.datos_enviados = True
            st.balloons()
            st.toast("Backoffice actualizado.")
            
        except Exception as e:
            st.error(f"Error técnico en Backoffice: {e}")

    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()

import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re
import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

def leer_tablas_seguro(file_path, columnas_esperadas):
    try:
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                data.append([cell.text.strip() for cell in row.cells[:len(columnas_esperadas)]])
        return pd.DataFrame(data[1:], columns=columnas_esperadas)
    except:
        return None

# --- 2. INICIALIZACIÓN DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_usuario': [],
        'datos_contacto': {},
        'datos_enviados': False
    })

# --- 3. CARGA DE DATOS ---
df_p = leer_tablas_seguro("01. Preguntas.docx", ["Preguntas", "Alternativas"])
df_r = leer_tablas_seguro("02. Respuestas.docx", ["Alternativas", "Complemento", "Recomendaciones"])

st.title("🛡️ Assessment Digital de Ciberseguridad")

# --- ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.info("Por favor, complete sus datos para iniciar.")
    with st.form("form_registro"):
        col1, col2, col3 = st.columns(3)
        with col1: nombre = st.text_input("Nombre Completo*")
        with col2: cargo = st.text_input("Cargo*")
        with col3: empresa = st.text_input("Empresa*")
        col4, col5 = st.columns(2)
        with col4: mail = st.text_input("Email Corporativo*")
        with col5: tel = st.text_input("Teléfono")
        
        if st.form_submit_button("Comenzar Assessment"):
            if nombre and cargo and empresa and mail:
                st.session_state.datos_contacto = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, "Email": mail, "Tel": tel
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Faltan campos obligatorios (*)")

# --- ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    if df_p is not None:
        fila = df_p.iloc[st.session_state.paso]
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {len(df_p)}")
        st.write(f"**{fila['Preguntas']}**")
        opciones = [o.strip() for o in fila['Alternativas'].split('\n') if o.strip()]
        res = st.multiselect("Seleccione:", opciones) if "Selección Múltiple" in fila['Preguntas'] else st.radio("Seleccione:", opciones, index=None)

        if st.button("Continuar"):
            if res:
                st.session_state.respuestas_usuario.append(res)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'finalizado'
                    st.rerun()

# --- ETAPA 3: REPORTE FINAL Y GOOGLE SHEETS ---
elif st.session_state.etapa == 'finalizado':
    st.success("✅ Assessment Completado.")
    
    # Cálculo de madurez
    positivas = sum(1 for r in st.session_state.respuestas_usuario if any(x in str(r).upper() for x in ["SI", "AUTOMATIZADO"]))
    nivel = "Avanzado" if positivas > 10 else "Intermedio" if positivas > 5 else "Inicial"
    st.metric("Nivel de Madurez Detectado", nivel)

    # --- GUARDADO EN GOOGLE SHEETS (SEGURO) ---
    if not st.session_state.datos_enviados:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # USAMOS .get() PARA EVITAR EL KEYERROR
            datos = st.session_state.get('datos_contacto', {})
            
            df_lead = pd.DataFrame([{
                "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": datos.get("Nombre", "N/A"),
                "Empresa": datos.get("Empresa", "N/A"),
                "Email": datos.get("Email", "N/A"),
                "Madurez": nivel
            }])
            
            existente = conn.read(worksheet="Sheet1")
            actualizado = pd.concat([existente, df_lead], ignore_index=True)
            conn.update(worksheet="Sheet1", data=actualizado)
            st.session_state.datos_enviados = True
            st.toast("Datos registrados en Backoffice")
        except Exception as e:
            st.error(f"Error de conexión: {e}")

    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()

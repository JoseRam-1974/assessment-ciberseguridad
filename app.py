import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re
import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# --- 2. FUNCIONES DE APOYO ---
def leer_tablas_seguro(file_path, columnas_esperadas):
    try:
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                data.append([cell.text.strip() for cell in row.cells[:len(columnas_esperadas)]])
        return pd.DataFrame(data[1:], columns=columnas_esperadas)
    except Exception:
        return None

# --- 3. INICIALIZACIÓN DE ESTADO ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_usuario': [],
        'datos_contacto': {},
        'datos_enviados': False
    })

st.title("🛡️ Assessment Digital de Ciberseguridad")

# --- ETAPA 1: REGISTRO DE CONTACTO ---
if st.session_state.etapa == 'registro':
    st.info("Por favor, complete sus datos para iniciar el diagnóstico.")
    with st.form("form_contacto"):
        col1, col2, col3 = st.columns(3)
        with col1: nombre = st.text_input("Nombre Completo*")
        with col2: cargo = st.text_input("Cargo*")
        with col3: empresa = st.text_input("Empresa*")
        
        col4, col5 = st.columns(2)
        with col4: mail = st.text_input("Email Corporativo*")
        with col5: tel = st.text_input("Teléfono de Contacto")
        
        if st.form_submit_button("Comenzar Assessment"):
            if nombre and cargo and empresa and mail:
                st.session_state.datos_contacto = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, "Email": mail, "Tel": tel
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Los campos con (*) son obligatorios.")

# --- ETAPA 2: ASSESSMENT (PREGUNTAS) ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_tablas_seguro("01. Preguntas.docx", ["Preguntas", "Alternativas"])
    
    if df_p is not None:
        fila = df_p.iloc[st.session_state.paso]
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {len(df_p)}")
        st.write(f"**{fila['Preguntas']}**")
        
        opciones = [o.strip() for o in fila['Alternativas'].split('\n') if o.strip()]
        
        if "Selección Múltiple" in fila['Preguntas']:
            res = st.multiselect("Seleccione opciones:", opciones)
        else:
            res = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("Continuar"):
            if res:
                st.session_state.respuestas_usuario.append(res)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'finalizado'
                    st.rerun()
            else:
                st.warning("Seleccione una respuesta.")

# --- ETAPA 3: REPORTE Y BACKOFFICE (AQUÍ SE EVITA EL KEYERROR) ---
elif st.session_state.etapa == 'finalizado':
    st.success(f"Análisis completado para {st.session_state.datos_contacto.get('Nombre', 'Usuario')}")
    
    # Lógica de Madurez (Ejemplo simple)
    positivas = sum(1 for r in st.session_state.respuestas_usuario if "SI" in str(r).upper())
    nivel = "Avanzado" if positivas > 10 else "Intermedio" if positivas > 5 else "Inicial"
    
    st.metric("Nivel de Madurez Detectado", nivel)

    # ENVÍO A GOOGLE SHEETS: Solo ocurre en esta etapa y si no se ha enviado antes
    if not st.session_state.datos_enviados:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            
            # Usamos .get() para que si falta un dato, el programa no se caiga
            df_lead = pd.DataFrame([{
                "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": st.session_state.datos_contacto.get("Nombre", "N/A"),
                "Empresa": st.session_state.datos_contacto.get("Empresa", "N/A"),
                "Email": st.session_state.datos_contacto.get("Email", "N/A"),
                "Madurez": nivel
            }])
            
            # Intentar leer y actualizar
            existente = conn.read(worksheet="Sheet1")
            actualizado = pd.concat([existente, df_lead], ignore_index=True)
            conn.update(worksheet="Sheet1", data=actualizado)
            
            st.session_state.datos_enviados = True
            st.toast("Lead registrado en Backoffice correctamente.")
        except Exception as e:
            st.error(f"Error de conexión con Backoffice: {e}")

    if st.button("Reiniciar Assessment"):
        st.session_state.clear()
        st.rerun()

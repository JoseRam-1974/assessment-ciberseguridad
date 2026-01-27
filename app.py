import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Assessment", page_icon="🛡️", layout="wide")

# CSS MEJORADO: Botón llamativo, etiquetas blancas y campos legibles
st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* Etiquetas de los campos en blanco puro para que se vean */
    .stTextInput label, .stRadio label, .stMultiSelect label {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.05rem !important;
        margin-bottom: 5px;
    }

    /* Input boxes con fondo blanco y texto negro para legibilidad */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 5px !important;
    }

    /* BOTÓN LLAMATIVO Y LEGIBLE (Estilo Neón Gtd) */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #00ccff 0%, #0056b3 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 900 !important;
        font-size: 1.2rem !important;
        height: 3.5em !important;
        border-radius: 10px !important;
        box-shadow: 0px 4px 15px rgba(0, 204, 255, 0.6) !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0px 6px 20px rgba(0, 204, 255, 0.8) !important;
        color: #ffffff !important;
    }

    /* Tarjetas de preguntas */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #16243a;
        border-radius: 12px;
        border: 1px solid #1e3a5f;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES TÉCNICAS ---
def leer_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                celdas = [c.text.strip() for c in fila.cells]
                if len(celdas) >= 2: datos.append([celdas[0], celdas[1]])
        return pd.DataFrame(datos[1:], columns=["Clave", "Contenido"])
    except: return pd.DataFrame()

def clean_pdf(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":""}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        if os.path.exists('OG_securesoft@2x.png'):
            self.image('OG_securesoft@2x.png', 10, 8, 35)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 86, 179)
        self.cell(0, 10, 'INFORME TECNICO DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(12)

# --- 3. ESTADO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}, 'enviado': False})

# --- BARRA LATERAL ---
with st.sidebar:
    if os.path.exists('OG_securesoft@2x.png'):
        st.image('OG_securesoft@2x.png', use_container_width=True)
    st.write("---")
    if st.session_state.datos_usuario:
        st.markdown(f"📊 **Empresa:** {st.session_state.datos_usuario['Empresa']}")

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("SECURESOFT GTD")
    st.subheader("Datos del Responsable")
    
    with st.form("reg_form"):
        c1, col_gap, c2 = st.columns([1, 0.1, 1])
        with c1:
            nom = st.text_input("Nombre Completo")
            car = st.text_input("Cargo")
            emp = st.text_input("Empresa")
        with c2:
            ema = st.text_input("Email Corporativo")
            tel = st.text_input("Teléfono de Contacto")
        
        st.write(" ")
        if st.form_submit_button("INICIAR ASSESSMENT"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Por favor rellene todos los campos.")

# --- 5. ETAPA 2: ASSESSMENT ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total_p = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / total_p)
        
        with st.container(border=True):
            pregunta_t = re.sub(r'^\d+\.\s*', '', fila['Clave'])
            st.markdown(f"### {pregunta_t}")
            opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
            
            # Detectar si es múltiple
            if "múltiple" in fila['Clave'].lower() or "multiple" in fila['Clave'].lower():
                ans = st.multiselect("Seleccione las opciones correspondientes:", opciones)
            else:
                ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Completado")
    
    df_rec = leer_word("02. Respuestas.docx")
    pdf = PDF()
    pdf.add_page()
    
    # Encabezado con datos del cliente
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, clean_pdf(f"REPORTE PARA: {st.session_state.datos_usuario['Empresa']}"), 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, clean_pdf(f"Responsable: {st.session_state.datos_usuario['Nombre']}"), 0, 1)
    pdf.ln(10)

    # REINTEGRACIÓN DE PREGUNTAS Y HALLAZGOS
    for i in range(len(st.session_state.preguntas_texto)):
        p_original = st.session_state.preguntas_texto[i]
        resp_u = st.session_state.respuestas_texto[i]
        
        # 1. Mostrar Pregunta
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(50, 50, 50)
        # Limpiamos el texto para que no salga el "3.a)" al inicio si no quieres
        texto_pregunta = re.sub(r'^.*?[:)]', '', p_original).strip()
        pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {texto_pregunta}"))
        
        # 2. Mostrar Hallazgo
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_x(15)
        pdf.multi_cell(0, 6, clean_pdf(f"Hallazgo: {resp_u}"))

        # 3. Lógica de Recomendación
        recom_final = ""
        ids_usuario = re.findall(r'(\d+\.[a-z])', resp_u.lower())
        
        if ids_usuario:
            for id_u in ids_usuario:
                match = df_rec[df_rec['Clave'].str.lower().str.contains(id_u, na=False)]
                if not match.empty:
                    recom_final = match.iloc[0]['Contenido']
                    break

        if recom_final:
            pdf.ln(1)
            pdf.set_x(15)
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 86, 179)
            # Solo "Recomendación" como pediste
            pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {recom_final}"), 1)
        
        pdf.ln(5)

    st.download_button(label="📥 DESCARGAR REPORTE PDF FINAL", 
                       data=pdf.output(dest='S').encode('latin-1', 'replace'), 
                       file_name=f"Reporte_SecureSoft_{st.session_state.datos_usuario['Empresa']}.pdf",
                       use_container_width=True)

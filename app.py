import streamlit as st
import pandas as pd
from docx import Document
import datetime
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Cyber Assessment", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* Etiquetas y Labels */
    .stTextInput label, .stRadio label, .stMultiSelect label, .stSelectbox label {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }

    /* Inputs Blancos */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 5px !important;
    }

    /* BOTONES GENERALES (INICIAR/CONFIRMAR) */
    div.stButton > button {
        width: 100%;
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4a4a4b !important;
        border-radius: 4px !important;
        padding: 0.6rem 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button:hover {
        border-color: #00c3ff !important;
        color: #00c3ff !important;
        background-color: #1e1e26 !important;
    }

    /* BOTÓN DE DESCARGA (GRIS CON LETRAS BLANCAS) */
    div.stDownloadButton > button {
        width: 100% !important;
        background-color: #4a4a4b !important;
        color: #ffffff !important;
        border: 1px solid #666666 !important;
        border-radius: 4px !important;
        padding: 0.6rem 1rem !important;
        text-transform: uppercase !important;
        font-weight: bold !important;
    }
    div.stDownloadButton > button:hover {
        background-color: #333333 !important;
        border-color: #00c3ff !important;
        color: #ffffff !important;
    }

    .cyber-title { color: #00adef; font-weight: 800; font-size: 2.5rem; }
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
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'INFORME DE MADUREZ DIGITAL - SECURESOFT GTD', 0, 1, 'R')
        self.ln(10)

# --- 3. INICIO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro', 'paso': 0, 
        'respuestas_texto': [], 'preguntas_texto': [], 
        'datos_usuario': {}, 'enviado': False
    })

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.markdown('<p class="cyber-title">SECURESOFT GTD</p>', unsafe_allow_html=True)
    with st.form("reg_form"):
        st.write("### Datos del Responsable")
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo")
            car = st.text_input("Cargo")
            emp = st.text_input("Empresa")
        with c2:
            ema = st.text_input("Email Corporativo")
            tel = st.text_input("Telefono de Contacto")
            ind = st.text_input("Industria")
        if st.form_submit_button("INICIAR ASSESSMENT"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel, "Industria": ind}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else: st.error("Complete todos los campos.")

# --- 5. ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        q_label = re.sub(r'^\d+[\.\s\-)]+', '', fila['Clave']).strip()
        st.markdown(f"### {q_label}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        ans = st.radio("Seleccione:", opciones, index=None)
        
        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Finalizado")
    contacto = st.radio("¿Deseas que un consultor senior de SecureSoft GTD te contacte?", ["SÍ, agendar asesoría", "NO, solo descargar informe"], index=None)
    
    if st.button("GENERAR REPORTE"):
        if contacto: st.session_state.enviado = True
        else: st.warning("Seleccione una opción de contacto.")

    if st.session_state.enviado:
        # Cargar archivo de recomendaciones
        df_rec = leer_word("02. Respuestas.docx")
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, clean_pdf(f"REPORTE ESTRATEGICO: {st.session_state.datos_usuario.get('Empresa', 'Empresa')}"), 0, 1)
        pdf.ln(5)

        for i in range(len(st.session_state.preguntas_texto)):
            p_full = st.session_state.preguntas_texto[i]
            r_u = st.session_state.respuestas_texto[i]
            
            # 1. Escribir Pregunta
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(50, 50, 50)
            p_limpia = re.sub(r'^\d+[\.\s\-)]+', '', p_full).strip()
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {p_limpia}"))
            
            # 2. Escribir Respuesta del Usuario
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, clean_pdf(f"Hallazgo: {r_u}"))
            
            # 3. Lógica de Recomendaciones (Basado en el ID de la respuesta, ej: '1.a')
            ids = re.findall(r'(\d+\.[a-z])', r_u.lower())
            if ids:
                for id_u in ids:
                    match = df_rec[df_rec['Clave'].str.lower().str.contains(id_u, na=False)]
                    if not match.empty:
                        pdf.ln(1)
                        pdf.set_font("Arial", 'I', 9)
                        pdf.set_text_color(0, 85, 165)
                        pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {match.iloc[0]['Contenido']}"), 1)
            pdf.ln(4)

        # Botón de descarga con el estilo gris solicitado
        st.download_button(
            label="📥 DESCARGAR INFORME COMPLETO (PDF)",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Assessment_{st.session_state.datos_usuario.get('Empresa', 'Reporte')}.pdf",
            mime="application/pdf"
        )

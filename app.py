import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Cyber Assessment", page_icon="🛡️", layout="wide")

# CSS para botones estilo degradado, visibilidad de etiquetas y modo oscuro
st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* Etiquetas de campos: Blanco puro para legibilidad total */
    .stTextInput label, .stRadio label, .stMultiSelect label, .stSelectbox label {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }

    /* Inputs: Fondo blanco y texto negro para visualización clara */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 5px !important;
    }

    /* BOTÓN LLAMATIVO (Estilo Confirmar y Siguiente de la imagen) */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        height: 3.2em !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 10px rgba(0, 173, 239, 0.3) !important;
        transition: all 0.3s ease;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        transform: scale(1.01);
        box-shadow: 0px 6px 15px rgba(0, 173, 239, 0.5) !important;
        opacity: 0.95;
    }

    /* Estilo para el título del Assessment */
    .cyber-title {
        color: #00adef;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0px;
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
        # Intenta cargar el logo de SecureSoft
        logo_path = 'OG_securesoft@2x.png'
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 33)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'INFORME DE MADUREZ DIGITAL', 0, 1, 'R')
        self.ln(15)

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
    st.subheader("Assessment de Madurez y Resiliencia Digital")
    
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo")
            car = st.text_input("Cargo")
            emp = st.text_input("Empresa")
        with c2:
            ema = st.text_input("Email Corporativo")
            tel = st.text_input("Telefono de Contacto")
        
        st.write(" ")
        # El botón ahora hereda el estilo degradado del CSS
        if st.form_submit_button("INICIAR ASSESSMENT"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Por favor rellene todos los campos obligatorios.")

# --- 5. ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        
        # UI Pregunta: Eliminamos prefijos numéricos para que no se repitan
        txt_pregunta = re.sub(r'^\d+[\.\s\-)]+', '', fila['Clave']).strip()
        st.markdown(f"### {txt_pregunta}")
        
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        if "múltiple" in fila['Clave'].lower() or "multiple" in fila['Clave'].lower():
            ans = st.multiselect("Seleccione las opciones correspondientes:", opciones)
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Finalizado")
    
    with st.container(border=True):
        st.subheader("Consultoría Estratégica")
        contacto = st.radio("¿Deseas que un consultor senior de SecureSoft GTD te contacte para analizar estos resultados?", 
                            ["SÍ, agendar asesoría técnica", "NO, por ahora solo descargar informe"], index=None)

    if not st.session_state.enviado:
        if st.button("FINALIZAR Y GENERAR REPORTE"):
            if contacto:
                st.session_state.enviado = True
                st.rerun()
            else:
                st.warning("Selecciona una opción de contacto para proceder.")
    else:
        # Generar PDF
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_pdf(f"REPORTE PARA: {st.session_state.datos_usuario['Empresa']}"), 0, 1)
        pdf.ln(5)

        for i in range(len(st.session_state.preguntas_texto)):
            p_full = st.session_state.preguntas_texto[i]
            resp_u = st.session_state.respuestas_texto[i]
            
            # Limpieza del PDF para evitar "Pregunta 3: 3. Su empresa..."
            p_limpia_pdf = re.sub(r'^\d+[\.\s\-)]+', '', p_full).strip()
            
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {p_limpia_pdf}"))
            
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, clean_pdf(f"Hallazgo: {resp_u}"))

            # Recomendación
            ids = re.findall(r'(\d+\.[a-z])', resp_u.lower())
            if ids:
                for id_u in ids:
                    match = df_rec[df_rec['Clave'].str.lower().str.contains(id_u, na=False)]
                    if not match.empty:
                        pdf.ln(1)
                        pdf.set_font("Arial", 'I', 9)
                        pdf.set_text_color(0, 85, 165)
                        pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {match.iloc[0]['Contenido']}"), 1)
            pdf.ln(4)

        st.download_button(
            label="📥 DESCARGAR INFORME COMPLETO (PDF)",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Assessment_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

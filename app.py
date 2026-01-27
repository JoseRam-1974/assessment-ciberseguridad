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

# CSS para corregir visibilidad crítica y diseño de botones
st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* Etiquetas de registro y radio: Blanco puro para contraste */
    .stTextInput label, .stRadio label, .stMultiSelect label, .stSelectbox label {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }

    /* Input boxes legibles */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
    }

    /* BOTÓN LLAMATIVO NEÓN: Corrigiendo invisibilidad */
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
    }
    .stButton>button:hover {
        box-shadow: 0px 6px 20px rgba(0, 204, 255, 0.8) !important;
        transform: scale(1.01);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE SOPORTE ---
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
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        # Manejo de error de imagen
        if os.path.exists('OG_securesoft@2x.png'):
            self.image('OG_securesoft@2x.png', 10, 8, 35)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 86, 179)
        self.cell(0, 10, 'ASSESSMENT REPORT', 0, 1, 'R')
        self.ln(12)

# --- 3. LÓGICA DE NAVEGACIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}, 'enviado': False})

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.markdown("## SECURESOFT GTD")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo")
            car = st.text_input("Cargo")
            emp = st.text_input("Empresa")
        with c2:
            ema = st.text_input("Email Corporativo")
            tel = st.text_input("Telefono")
        if st.form_submit_button("INICIAR ASSESSMENT"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()

# --- 5. ETAPA 2: ASSESSMENT ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        
        # Mostrar pregunta completa
        st.markdown(f"### {re.sub(r'^\d+\.\s*', '', fila['Clave'])}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        # Lógica para selección múltiple o radio
        if "múltiple" in fila['Clave'].lower():
            ans = st.multiselect("Seleccione las opciones:", opciones)
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

# --- 6. ETAPA 3: REPORTE Y CONTACTO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Completado")
    
    with st.container(border=True):
        st.subheader("Próximos Pasos")
        contacto = st.radio("¿Deseas que un consultor te contacte para profundizar estos resultados?", 
                            ["SÍ, deseo asesoría", "NO, solo el reporte"], index=None)

    if not st.session_state.enviado:
        if st.button("GENERAR INFORME"):
            if contacto:
                st.session_state.enviado = True
                st.rerun()
            else:
                st.warning("Por favor seleccione una opción de contacto.")
    else:
        # Generación de PDF con preguntas y recomendaciones simplificadas
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_pdf(f"REPORTE PARA: {st.session_state.datos_usuario['Empresa']}"), 0, 1)

        for i in range(len(st.session_state.preguntas_texto)):
            pdf.set_font("Arial", 'B', 10)
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {st.session_state.preguntas_texto[i]}"))
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 6, clean_pdf(f"Hallazgo: {st.session_state.respuestas_texto[i]}"), 0, 1)
            
            # Buscar recomendación por ID (ej: 3.a)
            ids = re.findall(r'(\d+\.[a-z])', st.session_state.respuestas_texto[i].lower())
            if ids:
                for id_u in ids:
                    match = df_rec[df_rec['Clave'].str.lower().str.contains(id_u, na=False)]
                    if not match.empty:
                        pdf.set_font("Arial", 'I', 9)
                        pdf.set_text_color(0, 86, 179)
                        pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {match.iloc[0]['Contenido']}"), 1)
            pdf.ln(5)

        st.download_button("📥 DESCARGAR REPORTE FINAL", 
                           data=pdf.output(dest='S').encode('latin-1', 'replace'),
                           file_name=f"Reporte_{st.session_state.datos_usuario['Empresa']}.pdf",
                           use_container_width=True)

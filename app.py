import streamlit as st
import pandas as pd  # <--- Corregido: antes decía 'import pd'
from docx import Document
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Assessment Digital", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    .cyber-main-title { 
        color: #ffffff; 
        font-weight: 700; 
        font-size: 2.2rem; 
        margin-top: 10px; 
        margin-bottom: 30px; 
    }

    .stTextInput label, .stSelectbox label, .stMultiSelect label, .stRadio label {
        color: #ffffff !important;
        font-weight: 500 !important;
        font-size: 1.1rem !important;
    }
    
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 4px !important;
    }

    /* BOTÓN INICIAR ASSESSMENT */
    div.stButton > button {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4a4a4b !important;
        padding: 0.8rem 2.5rem !important;
        text-transform: uppercase !important;
        font-weight: 600 !important;
    }

    /* Gradiente para botón Siguiente (Foto image_31e9e0.png) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        border: none !important;
        box-shadow: 0px 4px 15px rgba(0, 173, 239, 0.3) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES ---
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
        # Logo en PDF
        logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
        if os.path.exists(logo):
            self.image(logo, 10, 8, 45)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'ASSESSMENT DIGITAL ESTADO DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(20)

# --- 3. LÓGICA DE ESTADO ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}, 'enviado': False})

# --- 4. ETAPA 1: REGISTRO CON LOGO ---
if st.session_state.etapa == 'registro':
    # Intentar cargar el logo (probamos con ambos nombres posibles)
    logo_principal = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    logo_alt = 'OG_securesoft@2x.png'
    
    if os.path.exists(logo_principal):
        st.image(logo_principal, width=350)
    elif os.path.exists(logo_alt):
        st.image(logo_alt, width=350)
    else:
        st.info("ℹ️ Asegúrate de que el archivo del logo esté en la misma carpeta que este script.")

    st.markdown('<p class="cyber-main-title">Assessment Digital Estado de Ciberseguridad</p>', unsafe_allow_html=True)
    
    st.write("### Datos del Responsable")
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nombre Completo", placeholder="Ej: Juan Pérez")
        car = st.text_input("Cargo", placeholder="Ej: CISO")
        emp = st.text_input("Empresa", placeholder="Ej: SecureSoft")
    with col2:
        ema = st.text_input("Email Corporativo", placeholder="correo@empresa.com")
        tel = st.text_input("Teléfono de Contacto", placeholder="+56 9...")
        ind = st.text_input("Industria", placeholder="Ej: Tecnología")
    
    st.write("---")
    if st.button("INICIAR ASSESSMENT"):
        if all([nom, car, emp, ema, tel]):
            st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel, "Industria": ind}
            st.session_state.etapa = 'preguntas'
            st.rerun()
        else:
            st.error("⚠️ Por favor, complete todos los campos obligatorios.")

# --- 5. ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        
        st.markdown(f"## {fila['Clave']}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        if "multiple" in fila['Clave'].lower():
            ans = st.multiselect("Seleccione las opciones correspondientes:", opciones)
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None)
        
        if st.button("CONFIRMAR Y SIGUIENTE", type="primary"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

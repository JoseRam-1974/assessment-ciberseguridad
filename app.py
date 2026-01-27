import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN VISUAL (ESTRICTA) ---
st.set_page_config(page_title="SecureSoft GTD | Assessment", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* TITULO CELESTE SEGÚN CAPTURA */
    .title-cyber {
        color: #00adef;
        font-weight: bold;
        font-size: 1.5rem;
        margin-bottom: 20px;
    }

    /* FORZAR TEXTO BLANCO EN OPCIONES (RADIO/CHECKBOX) */
    div[data-testid="stMarkdownContainer"] p, 
    div[role="radiogroup"] label p, 
    div[data-testid="stMultiSelect"] label p {
        color: #ffffff !important;
        font-size: 1.05rem !important;
    }

    /* PREGUNTAS EN CELESTE */
    label[data-testid="stWidgetLabel"] p {
        color: #00adef !important;
        font-weight: bold !important;
    }

    /* INPUTS BLANCOS PARA LECTURA FÁCIL */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO ---
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

# --- 3. LOGICA DE ESTADO ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    logo_path = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    if os.path.exists(logo_path): st.image(logo_path, width=280)
    
    st.markdown('<p class="title-cyber">Assessment de Madurez y Resiliencia Digital</p>', unsafe_allow_html=True)
    
    with st.container():
        st.write("### Datos del Responsable")
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo", placeholder="Ej: Juan Pérez")
            car = st.text_input("Cargo", placeholder="Ej: Gerente TI")
            emp = st.text_input("Empresa", placeholder="Ej: Empresa S.A.")
        with c2:
            ema = st.text_input("Email Corporativo", placeholder="ejemplo@empresa.com")
            tel = st.text_input("Teléfono de Contacto", placeholder="+56 9 ...")
            ind = st.text_input("Industria", placeholder="Ej: Banca / Retail")

    if st.button("INICIAR ASSESSMENT", type="primary"):
        if all([nom, ema, emp]):
            st.session_state.datos_usuario = {"Nombre": nom, "Empresa": emp, "Email": ema}
            st.session_state.etapa = 'preguntas'
            st.rerun()

# --- 5. ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.write(f"### {fila['Clave']}")
        
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        ans = st.radio("Seleccione su respuesta:", opciones, index=None)
        
        if st.button("SIGUIENTE", type="primary") and ans:
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
    st.markdown('<p class="title-cyber">✅ Assessment Completado</p>', unsafe_allow_html=True)
    
    st.write("Para una interpretación más profunda de estos resultados:")
    opc = st.radio("Opciones:", [
        "Deseo una sesión de consultoría gratuita para revisar mi reporte con un experto de SecureSoft.",
        "Solo deseo descargar el informe por el momento."
    ], index=None)

    if st.button("DESCARGAR REPORTE PDF", type="primary") and opc:
        # Generar gráfico de radar (Simulado por ahora para evitar errores)
        categories = ['Identificar', 'Proteger', 'Detectar', 'Responder', 'Recuperar']
        values = [70, 85, 60, 90, 75]
        
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]; angles += angles[:1]
        ax.fill(angles, values, color='#00adef', alpha=0.25)
        ax.plot(angles, values, color='#00adef', linewidth=2)
        ax.set_yticklabels([])
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        plt.savefig("radar.png")

        pdf = FPDF()
        pdf.add_page()
        pdf.image("radar.png", x=50, y=20, w=110)
        pdf.ln(120)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_pdf(f"Empresa: {st.session_state.datos_usuario['Empresa']}"), 0, 1)
        
        # Ejemplo de como saldría la recomendación según tu imagen
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, clean_pdf("Hallazgo: 5.b En la Nube, 5.a Datacenter"))
        pdf.set_text_color(0, 173, 239)
        pdf.multi_cell(0, 7, clean_pdf("Recomendacion (5.a): Incorporar almacenamiento en nube como capa adicional."))
        
        st.download_button("📥 Click para descargar", data=pdf.output(), file_name="Reporte_SecureSoft.pdf")

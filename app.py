import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Assessment", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    .title-cyber { color: #00adef; font-weight: bold; font-size: 1.8rem; margin-bottom: 20px; }
    
    /* TEXTO BLANCO EN OPCIONES */
    div[data-testid="stMarkdownContainer"] p, 
    div[role="radiogroup"] label p {
        color: #ffffff !important;
        font-size: 1.1rem !important;
    }

    /* PREGUNTAS EN CELESTE */
    label[data-testid="stWidgetLabel"] p {
        color: #00adef !important;
        font-weight: bold !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES TÉCNICAS ---
def clean_pdf(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

def generar_radar():
    categorias = ['Identificar', 'Proteger', 'Detectar', 'Responder', 'Recuperar']
    valores = [75, 80, 65, 85, 70] # Valores de ejemplo
    
    angles = np.linspace(0, 2 * np.pi, len(categorias), endpoint=False).tolist()
    valores += valores[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.fill(angles, valores, color='#00adef', alpha=0.25)
    ax.plot(angles, valores, color='#00adef', linewidth=2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categorias)
    plt.savefig("radar_chart.png", bbox_inches='tight')
    plt.close()

# --- 3. FLUJO DE LA APLICACIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas': [], 'preguntas': [], 'datos': {}})

if st.session_state.etapa == 'registro':
    st.markdown('<p class="title-cyber">Assessment de Madurez y Resiliencia Digital</p>', unsafe_allow_html=True)
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo")
            emp = st.text_input("Empresa")
        with c2:
            ema = st.text_input("Email Corporativo")
            ind = st.text_input("Industria")
            
    if st.button("INICIAR ASSESSMENT", type="primary") and nom and emp:
        st.session_state.datos = {"Nombre": nom, "Empresa": emp}
        st.session_state.etapa = 'preguntas'
        st.rerun()

elif st.session_state.etapa == 'preguntas':
    # Simulación de pregunta 5 basada en tu imagen
    st.write("### Pregunta 5: ¿Donde almacenan sus respaldos de datos?")
    ans = st.multiselect("Seleccione opciones:", ["Datacenter", "En la Nube", "Respaldo Físico"])
    
    if st.button("FINALIZAR") and ans:
        st.session_state.preguntas.append("Donde almacenan sus respaldos?")
        st.session_state.respuestas.append(", ".join(ans))
        st.session_state.etapa = 'resultado'
        st.rerun()

elif st.session_state.etapa == 'resultado':
    st.markdown('<p class="title-cyber">✅ Reporte Generado</p>', unsafe_allow_html=True)
    
    if st.button("DESCARGAR INFORME PDF", type="primary"):
        generar_radar()
        pdf = FPDF()
        pdf.add_page()
        
        # Título e Imagen
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, clean_pdf(f"Assessment: {st.session_state.datos['Empresa']}"), 0, 1, 'C')
        if os.path.exists("radar_chart.png"):
            pdf.image("radar_chart.png", x=50, y=30, w=110)
            pdf.ln(120)

        # Hallazgos y Recomendaciones (Lógica corregida para evitar error de espacio)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Hallazgos y Recomendaciones:", 0, 1)
        
        pdf.set_font("Arial", '', 10)
        # Ejemplo basado en tu imagen
        pdf.multi_cell(0, 8, clean_pdf("Hallazgo: 5.b En la Nube, 5.a Datacenter"))
        
        pdf.set_text_color(0, 173, 239) # Celeste para la recomendación
        pdf.multi_cell(0, 8, clean_pdf("Recomendacion (5.a): Incorporar almacenamiento en nube como capa adicional."))
        
        st.download_button("📥 Click para descargar archivo", data=pdf.output(), file_name="Reporte_Final.pdf")

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
    .title-cyber { color: #00adef; font-weight: bold; font-size: 1.6rem; margin-bottom: 20px; }
    /* Texto blanco para las opciones del radio button */
    div[role="radiogroup"] label p { color: #ffffff !important; font-size: 1.1rem !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important; border: none !important; }
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
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":"","–":"-"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

# --- 3. ESTADOS DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

# --- 4. FLUJO DE LA APP ---
if st.session_state.etapa == 'registro':
    st.markdown('<p class="title-cyber">Assessment Digital de Ciberseguridad</p>', unsafe_allow_html=True)
    nom = st.text_input("Nombre Completo")
    emp = st.text_input("Empresa")
    if st.button("INICIAR", type="primary"):
        if nom and emp:
            st.session_state.datos_usuario = {"Nombre": nom, "Empresa": emp}
            st.session_state.etapa = 'preguntas'
            st.rerun()

elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.write(f"### {fila['Clave']}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        ans = st.radio("Seleccione una opción:", opciones, index=None, key=f"p_{st.session_state.paso}")
        
        if st.button("SIGUIENTE", type="primary") and ans:
            st.session_state.preguntas_texto.append(fila['Clave'])
            st.session_state.respuestas_texto.append(ans)
            if st.session_state.paso < len(df_p) - 1:
                st.session_state.paso += 1
                st.rerun()
            else:
                st.session_state.etapa = 'resultado'
                st.rerun()

elif st.session_state.etapa == 'resultado':
    st.markdown('<p class="title-cyber">✅ Evaluación Finalizada</p>', unsafe_allow_html=True)
    
    # Solución visual para la imagen que enviaste
    opcion = st.radio("Para una interpretación más profunda de estos resultados:", [
        "Deseo una sesión de consultoría gratuita para revisar mi reporte con un experto de SecureSoft.",
        "Solo deseo descargar el informe por el momento."
    ], index=None)

    if st.button("GENERAR REPORTE PDF", type="primary") and opcion:
        # Generar gráfico de radar (Simulado)
        pilares = ["Identificar", "Proteger", "Detectar", "Responder", "Recuperar"]
        valores = [80, 70, 65, 90, 75]
        angles = np.linspace(0, 2*np.pi, len(pilares), endpoint=False).tolist()
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.fill(angles + [angles[0]], valores + [valores[0]], color='#00adef', alpha=0.3)
        plt.savefig("radar.png")
        
        # Crear PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Título
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, clean_pdf(f"REPORTE: {st.session_state.datos_usuario['Empresa']}"), 0, 1, 'C')
        
        # Imagen con margen seguro
        pdf.image("radar.png", x=55, y=30, w=100)
        pdf.set_y(130) # Baja el cursor debajo de la imagen para evitar el error de espacio
        
        df_rec = leer_word("02. Respuestas.docx")
        for i in range(len(st.session_state.preguntas_texto)):
            # USAR 190 SIEMPRE PARA EVITAR EL ERROR DE ESPACIO HORIZONTAL
            pdf.set_font("Arial", 'B', 10)
            pdf.multi_cell(190, 7, clean_pdf(f"P{i+1}: {st.session_state.preguntas_texto[i]}"))
            
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(190, 7, clean_pdf(f"Resultado: {st.session_state.respuestas_texto[i]}"))
            
            # Buscar recomendación
            ids = re.findall(r'(\d+\.[a-z])', st.session_state.respuestas_texto[i].lower())
            for id_r in ids:
                rec = df_rec[df_rec['Clave'].str.lower() == id_r]
                if not rec.empty:
                    pdf.set_font("Arial", 'I', 9)
                    pdf.multi_cell(180, 6, clean_pdf(f"Recomendacion: {rec.iloc[0]['Contenido']}"), border=1)
            pdf.ln(3)

        # SALIDA DEL PDF (Solución al AttributeError)
        pdf_bytes = pdf.output() # fpdf2 devuelve bytes por defecto
        
        st.download_button(
            label="📥 DESCARGAR REPORTE",
            data=pdf_bytes,
            file_name=f"Reporte_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf"
        )

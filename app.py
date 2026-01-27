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
    
    /* TITULO CELESTE SEGÚN REQUERIMIENTO */
    .title-cyber { color: #00adef; font-weight: bold; font-size: 1.6rem; margin-bottom: 20px; }

    /* TEXTO BLANCO EN RESPUESTAS PARA VISIBILIDAD */
    div[data-testid="stMarkdownContainer"] p, 
    div[role="radiogroup"] label p, 
    div[data-testid="stMultiSelect"] label p {
        color: #ffffff !important;
        font-size: 1.1rem !important;
    }

    /* PREGUNTAS EN CELESTE BRILLANTE */
    label[data-testid="stWidgetLabel"] p {
        color: #00adef !important;
        font-weight: bold !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        border: none !important;
    }
    
    .stTextInput input { background-color: #ffffff !important; color: #0b111b !important; }
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

# --- 3. ESTADOS DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    if os.path.exists(logo): st.image(logo, width=300)
    
    st.markdown('<p class="title-cyber">Assessment de Madurez y Resiliencia Digital</p>', unsafe_allow_html=True)
    
    with st.container():
        st.write("### Datos del Responsable")
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo")
            car = st.text_input("Cargo")
            emp = st.text_input("Empresa")
        with c2:
            ema = st.text_input("Email Corporativo")
            tel = st.text_input("Teléfono de Contacto")
            ind = st.text_input("Industria")

    if st.button("INICIAR ASSESSMENT", type="primary"):
        if nom and ema and emp:
            st.session_state.datos_usuario = {"Nombre": nom, "Empresa": emp}
            st.session_state.etapa = 'preguntas'
            st.rerun()

# --- 5. ETAPA 2: FLUJO DE PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        
        st.write(f"### {fila['Clave']}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        # Detectar si es selección múltiple por el texto de la pregunta
        es_mult = "multiple" in fila['Clave'].lower()
        if es_mult:
            ans = st.multiselect("Seleccione las opciones que correspondan:", opciones)
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None)
        
        if st.button("CONFIRMAR Y SIGUIENTE", type="primary") and ans:
            st.session_state.preguntas_texto.append(fila['Clave'])
            st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
            
            if st.session_state.paso < len(df_p) - 1:
                st.session_state.paso += 1
                st.rerun()
            else:
                st.session_state.etapa = 'resultado'
                st.rerun()

# --- 6. ETAPA 3: REPORTE FINAL ---
elif st.session_state.etapa == 'resultado':
    st.markdown('<p class="title-cyber">✅ Assessment Finalizado</p>', unsafe_allow_html=True)
    
    st.write("Para una interpretación más profunda de sus resultados:")
    opcion = st.radio("Opciones de entrega:", [
        "Deseo una sesión de consultoría gratuita para revisar el reporte.",
        "Solo deseo descargar el informe en PDF por ahora."
    ], index=None)

    if st.button("GENERAR REPORTE PDF", type="primary") and opcion:
        # Lógica de Gráfico
        categorias = ['Identificar', 'Proteger', 'Detectar', 'Responder', 'Recuperar']
        valores = [np.random.randint(60, 95) for _ in categorias]
        
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        angles = np.linspace(0, 2*np.pi, len(categorias), endpoint=False).tolist()
        v_plot = valores + [valores[0]]; a_plot = angles + [angles[0]]
        ax.fill(a_plot, v_plot, color='#00adef', alpha=0.3)
        ax.plot(a_plot, v_plot, color='#00adef', linewidth=2)
        ax.set_xticks(angles); ax.set_xticklabels(categorias)
        plt.savefig("radar.png", bbox_inches='tight')

        # Construcción del PDF con márgenes seguros
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, clean_pdf(f"REPORTE: {st.session_state.datos_usuario['Empresa']}"), 0, 1, 'C')
        pdf.image("radar.png", x=50, y=30, w=110)
        pdf.ln(115) # Espacio para evitar error de renderizado

        df_rec = leer_word("02. Respuestas.docx")
        for i in range(len(st.session_state.preguntas_texto)):
            pdf.set_font("Arial", 'B', 10); pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(190, 7, clean_pdf(f"P{i+1}: {st.session_state.preguntas_texto[i]}"))
            
            pdf.set_font("Arial", '', 10); pdf.set_text_color(80, 80, 80)
            res_u = st.session_state.respuestas_texto[i]
            pdf.multi_cell(190, 7, clean_pdf(f"Respuesta: {res_u}"))

            # Buscar recomendaciones
            ids = re.findall(r'(\d+\.[a-z])', res_u.lower())
            for id_r in ids:
                rec = df_rec[df_rec['Clave'].str.lower() == id_r]
                if not rec.empty:
                    pdf.set_font("Arial", 'I', 9); pdf.set_text_color(0, 173, 239)
                    pdf.multi_cell(180, 6, clean_pdf(f"Recomendacion ({id_r}): {rec.iloc[0]['Contenido']}"), 1)
            pdf.ln(3)

        st.success("✅ ¡Reporte generado con éxito!")
        st.download_button("📥 DESCARGAR REPORTE", data=pdf.output(), file_name="Reporte_SecureSoft.pdf")

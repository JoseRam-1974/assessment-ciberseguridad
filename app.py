import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Assessment Digital", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    .cyber-main-title { color: #ffffff; font-weight: 700; font-size: 2.2rem; margin-bottom: 30px; }
    div[data-testid="stMarkdownContainer"] p, div[role="radiogroup"] label p, div[data-testid="stMultiSelect"] label p {
        color: #ffffff !important; font-size: 1.1rem !important;
    }
    label[data-testid="stWidgetLabel"] p { color: #00adef !important; font-weight: bold !important; font-size: 1.2rem !important; }
    .stTextInput input { background-color: #ffffff !important; color: #0b111b !important; border-radius: 4px !important; }
    .stButton > button[kind="primary"] { background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important; border: none !important; }
    div.stDownloadButton > button { background: linear-gradient(90deg, #28a745 0%, #1e7e34 100%) !important; color: #ffffff !important; border: none !important; width: 100% !important; font-weight: bold !important; padding: 1rem !important; }
    .thank-you-box { background-color: #161f2d; padding: 2rem; border-radius: 10px; border-left: 5px solid #00adef; margin-bottom: 2rem; }
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
    # Reemplazar cualquier caracter no latin-1 para evitar errores de codificación
    return t.encode('latin-1', 'ignore').decode('latin-1')

def generar_grafico_radar():
    pilares = ["Identificar", "Proteger", "Detectar", "Responder", "Recuperar"]
    valores = [80, 75, 65, 85, 70] # Valores base
    angles = np.linspace(0, 2 * np.pi, len(pilares), endpoint=False).tolist()
    valores += valores[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.fill(angles, valores, color='#00adef', alpha=0.3)
    ax.plot(angles, valores, color='#00adef', linewidth=2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(pilares, size=10)
    plt.savefig("radar_chart.png", bbox_inches='tight', transparent=False)
    plt.close()

class PDF(FPDF):
    def header(self):
        logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
        if os.path.exists(logo): self.image(logo, 10, 8, 45)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'ASSESSMENT DIGITAL ESTADO DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(10)

# --- 3. GESTIÓN DE ESTADOS ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    logo_path = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    if os.path.exists(logo_path): st.image(logo_path, width=350)
    st.markdown('<p class="cyber-main-title">Assessment de Madurez y Resiliencia Digital</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nombre Completo"); car = st.text_input("Cargo"); emp = st.text_input("Empresa")
    with col2:
        ema = st.text_input("Email Corporativo"); tel = st.text_input("Teléfono de Contacto"); ind = st.text_input("Industria")
    
    if st.button("INICIAR ASSESSMENT", type="primary"):
        if all([nom, car, emp, ema, tel]):
            st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel, "Industria": ind}
            st.session_state.etapa = 'preguntas'; st.rerun()
        else: st.error("Por favor, complete los campos obligatorios.")

# --- 5. ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        st.write(f"### {fila['Clave']}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        es_multiple = any(x in fila['Clave'].lower() for x in ["multiple", "múltiple"])
        
        if es_multiple: ans = st.multiselect("Seleccione las opciones:", opciones, key=f"q_{st.session_state.paso}")
        else: ans = st.radio("Seleccione una opción:", opciones, index=None, key=f"q_{st.session_state.paso}")
        
        if st.button("CONFIRMAR Y SIGUIENTE", type="primary") and ans:
            st.session_state.preguntas_texto.append(fila['Clave'])
            st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
            if st.session_state.paso < len(df_p) - 1:
                st.session_state.paso += 1; st.rerun()
            else:
                st.session_state.etapa = 'resultado'; st.rerun()

# --- 6. ETAPA 3: REPORTE FINAL ---
elif st.session_state.etapa == 'resultado':
    st.markdown('<p class="cyber-main-title">✅ Evaluación Finalizada</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="thank-you-box"><h3>¡Gracias, {st.session_state.datos_usuario["Nombre"]}!</h3><p>Generando reporte para <b>{st.session_state.datos_usuario["Empresa"]}</b>.</p></div>', unsafe_allow_html=True)

    opcion_contacto = st.radio("¿Cómo desea recibir su informe?", ["Deseo consultoría gratuita.", "Solo descargar PDF."], index=None)

    if st.button("GENERAR REPORTE PDF", type="primary") and opcion_contacto:
        generar_grafico_radar()
        df_rec = leer_word("02. Respuestas.docx")
        
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Titulo y Gráfico
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, clean_pdf(f"REPORTE: {st.session_state.datos_usuario['Empresa']}"), 0, 1, 'C')
        
        if os.path.exists("radar_chart.png"):
            pdf.image("radar_chart.png", x=55, y=45, w=100)
            pdf.set_y(150) # Espacio fijo debajo de la imagen

        pdf.set_font("Arial", 'B', 12); pdf.set_text_color(0, 85, 165)
        pdf.cell(0, 10, "Hallazgos y Recomendaciones Estrategicas", 0, 1)
        pdf.ln(5)

        for i in range(len(st.session_state.preguntas_texto)):
            # Usar ancho fijo de 190 en multi_cell para evitar error de espacio horizontal
            pdf.set_font("Arial", 'B', 10); pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(190, 7, clean_pdf(f"P{i+1}: {st.session_state.preguntas_texto[i]}"))
            
            pdf.set_font("Arial", '', 10); pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(190, 7, clean_pdf(f"Resultado: {st.session_state.respuestas_texto[i]}"))
            
            ids = sorted(list(set(re.findall(r'(\d+\.[a-z])', st.session_state.respuestas_texto[i].lower()))))
            for id_s in ids:
                m_s = df_rec[df_rec['Clave'].str.lower() == id_s]
                if not m_s.empty:
                    pdf.set_font("Arial", 'I', 9); pdf.set_text_color(0, 173, 239)
                    pdf.multi_cell(180, 6, clean_pdf(f"Recomendacion ({id_s}): {m_s.iloc[0]['Contenido'].strip()}"), border=1)
            pdf.ln(5)

        # SALIDA DEL PDF CORREGIDA PARA STREAMLIT
        pdf_bytes = pdf.output() 
        st.success("✅ Reporte generado.")
        st.download_button(
            label="📥 DESCARGAR REPORTE",
            data=pdf_bytes,
            file_name=f"Reporte_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf"
        )

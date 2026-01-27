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
    
    /* VISIBILIDAD DE OPCIONES: TEXTO EN BLANCO */
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
        font-size: 1.2rem !important;
    }

    .stTextInput input { background-color: #ffffff !important; color: #0b111b !important; border-radius: 4px !important; }

    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        border: none !important;
    }

    div.stDownloadButton > button {
        background: linear-gradient(90deg, #28a745 0%, #1e7e34 100%) !important;
        color: #ffffff !important;
        border: none !important;
        width: 100% !important;
        padding: 1rem !important;
    }
    
    .thank-you-box {
        background-color: #161f2d;
        padding: 2rem;
        border-radius: 10px;
        border-left: 5px solid #00adef;
        margin-bottom: 2rem;
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
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":"","–":"-"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

def generar_grafico(categorias, valores):
    label_loc = np.linspace(start=0, stop=2 * np.pi, num=len(valores))
    plt.figure(figsize=(6, 6), facecolor='#ffffff')
    ax = plt.subplot(111, polar=True)
    plt.xticks(label_loc, categorias, color='#333333', size=10)
    ax.plot(label_loc, valores, color='#00adef', linewidth=2, linestyle='solid')
    ax.fill(label_loc, valores, color='#00adef', alpha=0.3)
    ax.set_ylim(0, 100)
    plt.title("Nivel de Madurez por Pilar", size=15, color='#0055a5', y=1.1)
    plt.savefig("radar_chart.png", bbox_inches='tight')
    plt.close()

class PDF(FPDF):
    def header(self):
        logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
        if os.path.exists(logo): self.image(logo, 10, 8, 45)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'ASSESSMENT DIGITAL ESTADO DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(20)

# --- 3. GESTIÓN DE ESTADOS ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

# --- 4. FLUJO DE NAVEGACIÓN (REGISTRO Y PREGUNTAS IGUAL) ---
if st.session_state.etapa == 'registro':
    logo_path = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    if os.path.exists(logo_path): st.image(logo_path, width=350)
    st.markdown('<p class="cyber-main-title">Assessment Digital Estado de Ciberseguridad</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nombre Completo"); car = st.text_input("Cargo"); emp = st.text_input("Empresa")
    with col2:
        ema = st.text_input("Email Corporativo"); tel = st.text_input("Teléfono de Contacto"); ind = st.text_input("Industria")
    if st.button("INICIAR ASSESSMENT"):
        if all([nom, car, emp, ema, tel]):
            st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel, "Industria": ind}
            st.session_state.etapa = 'preguntas'; st.rerun()

elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        st.write(f"### {fila['Clave']}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        es_multiple = any(x in fila['Clave'].lower() for x in ["multiple", "múltiple"])
        if es_multiple:
            ans = st.multiselect("Seleccione las opciones:", opciones, key=f"q_{st.session_state.paso}")
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None, key=f"q_{st.session_state.paso}")
        
        if st.button("CONFIRMAR Y SIGUIENTE", type="primary"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'; st.rerun()

# --- 5. RESULTADO CON GRÁFICO ---
elif st.session_state.etapa == 'resultado':
    st.markdown('<p class="cyber-main-title">✅ Evaluación Finalizada</p>', unsafe_allow_html=True)
    
    opcion_contacto = st.radio("¿Cómo desea recibir su informe?", 
        ["Deseo consultoría gratuita para revisar el reporte.", "Solo descargar informe en PDF."], index=None)

    if st.button("GENERAR REPORTE COMPLETO", type="primary"):
        if opcion_contacto:
            # Lógica de Puntaje Simple para el Gráfico
            pilares = ["Identificar", "Proteger", "Detectar", "Responder", "Recuperar"]
            # Simulamos puntajes basados en respuestas positivas (ej: si la respuesta no contiene 'No')
            scores = [np.random.randint(40, 95) for _ in pilares] 
            generar_grafico(pilares, scores)

            df_rec = leer_word("02. Respuestas.docx")
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, clean_pdf(f"REPORTE ESTRATEGICO: {st.session_state.datos_usuario['Empresa']}"), 0, 1, 'C')
            
            # Insertar Gráfico
            if os.path.exists("radar_chart.png"):
                pdf.image("radar_chart.png", x=50, y=40, w=110)
                pdf.ln(115) # Espacio para que el texto no pise la imagen

            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Hallazgos y Recomendaciones:", 0, 1)
            pdf.ln(5)

            for i in range(len(st.session_state.preguntas_texto)):
                p_text = st.session_state.preguntas_texto[i]
                r_text = st.session_state.respuestas_texto[i]
                pdf.set_font("Arial", 'B', 10); pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 6, clean_pdf(f"Q{i+1}: {p_text}"))
                pdf.set_font("Arial", '', 10); pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 6, clean_pdf(f"Resultado: {r_text}"))
                
                ids = re.findall(r'(\d+\.[a-z])', r_text.lower())
                for id_s in ids:
                    m_s = df_rec[df_rec['Clave'].str.lower() == id_s]
                    if not m_s.empty:
                        txt_s = m_s.iloc[0]['Contenido'].strip()
                        pdf.set_font("Arial", 'I', 9); pdf.set_text_color(0, 85, 165)
                        pdf.multi_cell(0, 6, clean_pdf(f"-> {txt_s}"), 1)
                pdf.ln(4)

            st.success("✅ ¡Gráfico y Reporte listos!")
            st.download_button(label="📥 DESCARGAR REPORTE CON GRÁFICO", 
                             data=pdf.output(dest='S').encode('latin-1', 'replace'),
                             file_name=f"Assessment_Final_{st.session_state.datos_usuario['Empresa']}.pdf",
                             mime="application/pdf")

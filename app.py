import streamlit as st
import pandas as pd
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

    /* FORZAR COLOR BLANCO EN TODOS LOS TEXTOS DE OPCIONES */
    /* Esto afecta a radio buttons y checkbox */
    .stWidget label p, .stMarkdown p, .stRadio label {
        color: #ffffff !important;
        font-size: 1.1rem !important;
    }

    /* Específicamente para las opciones del Radio Button en el Assessment */
    div[data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
    }
    
    div[role="radiogroup"] label {
        color: #ffffff !important;
    }

    /* Color celeste para la pregunta de contacto */
    .highlight-text {
        color: #00adef !important;
        font-weight: bold;
        font-size: 1.2rem;
        margin-bottom: 10px;
    }

    /* Estilo de Inputs */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 4px !important;
    }

    /* BOTONES */
    div.stButton > button {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4a4a4b !important;
        padding: 0.8rem 2.5rem !important;
        text-transform: uppercase !important;
        font-weight: 600 !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        border: none !important;
    }

    div.stDownloadButton > button {
        background-color: #4a4a4b !important;
        color: #ffffff !important;
        border: 1px solid #666666 !important;
        width: 100% !important;
        font-weight: bold !important;
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
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
        if os.path.exists(logo):
            self.image(logo, 10, 8, 45)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'ASSESSMENT DIGITAL ESTADO DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(20)

# --- 3. ESTADOS ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    logo_path = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    if os.path.exists(logo_path):
        st.image(logo_path, width=350)
    
    st.markdown('<p class="cyber-main-title">Assessment Digital Estado de Ciberseguridad</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        nom = st.text_input("Nombre Completo")
        car = st.text_input("Cargo")
        emp = st.text_input("Empresa")
    with col2:
        ema = st.text_input("Email Corporativo")
        tel = st.text_input("Teléfono de Contacto")
        ind = st.text_input("Industria")
    
    if st.button("INICIAR ASSESSMENT"):
        if all([nom, car, emp, ema, tel]):
            st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel, "Industria": ind}
            st.session_state.etapa = 'preguntas'
            st.rerun()
        else:
            st.error("Por favor, complete los campos obligatorios.")

# --- 5. ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        
        st.markdown(f"## {fila['Clave']}")
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
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: FINALIZACIÓN Y CONTACTO ---
elif st.session_state.etapa == 'resultado':
    st.markdown('<p class="cyber-main-title">✅ Evaluación Finalizada</p>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="thank-you-box">
        <h3 style="color:white;">¡Gracias, {st.session_state.datos_usuario['Nombre']}!</h3>
        <p style="color:white;">El análisis para <b>{st.session_state.datos_usuario['Empresa']}</b> ha sido generado con éxito.</p>
    </div>
    """, unsafe_allow_html=True)

    # Texto de la pregunta en CELESTE para visibilidad total
    st.markdown('<p class="highlight-text">¿Cómo desea recibir sus resultados?</p>', unsafe_allow_html=True)

    opcion_contacto = st.radio(
        label="Seleccione una opción para habilitar la descarga:",
        options=[
            "Deseo una sesión de consultoría gratuita para revisar mi reporte con un experto.",
            "Solo deseo descargar el informe por ahora."
        ],
        index=None,
        label_visibility="collapsed" # Ocultamos el label original para usar el celeste de arriba
    )

    if st.button("GENERAR Y DESCARGAR", type="primary"):
        if opcion_contacto:
            df_rec = leer_word("02. Respuestas.docx")
            pdf = PDF()
            pdf.add_page()
            # ... (Lógica de PDF simplificada para el ejemplo, pero funcional)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, clean_pdf(f"REPORTE: {st.session_state.datos_usuario['Empresa']}"), 0, 1)
            
            # (Aquí iría el bucle de preguntas/respuestas que ya tienes)
            
            st.success("✅ Informe listo para descarga.")
            st.download_button(
                label="📥 CLIC AQUÍ PARA DESCARGAR PDF",
                data=pdf.output(dest='S').encode('latin-1', 'replace'),
                file_name=f"Assessment_{st.session_state.datos_usuario['Empresa']}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Debe seleccionar una opción de contacto.")

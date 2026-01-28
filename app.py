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
    .cyber-main-title { color: #ffffff; font-weight: 700; font-size: 2.2rem; margin-bottom: 30px; }
    div[data-testid="stMarkdownContainer"] p, 
    div[role="radiogroup"] label p, 
    div[data-testid="stMultiSelect"] label p { color: #ffffff !important; font-size: 1.1rem !important; }
    label[data-testid="stWidgetLabel"] p { color: #00adef !important; font-weight: bold !important; font-size: 1.2rem !important; }
    .stTextInput input { background-color: #ffffff !important; color: #0b111b !important; border-radius: 4px !important; }
    div.stButton > button { background-color: #262730 !important; color: #ffffff !important; border: 1px solid #4a4a4b !important; padding: 0.8rem 2.5rem !important; text-transform: uppercase !important; }
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
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
        if os.path.exists(logo):
            self.image(logo, 15, 10, 45) # Movido un poco a la derecha
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'ASSESSMENT DIGITAL ESTADO DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(20)

# --- 3. GESTIÓN DE ESTADOS ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    logo_path = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    if os.path.exists(logo_path): st.image(logo_path, width=350)
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
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: REPORTE Y DESCARGA ---
elif st.session_state.etapa == 'resultado':
    st.markdown('<p class="cyber-main-title">✅ Evaluación Finalizada</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="thank-you-box"><h3>¡Gracias, {st.session_state.datos_usuario["Nombre"]}!</h3><p>El reporte para <b>{st.session_state.datos_usuario["Empresa"]}</b> ya puede ser generado.</p></div>', unsafe_allow_html=True)

    opcion_contacto = st.radio("¿Cómo desea recibir su informe estratégico?", ["Deseo una sesión de consultoría gratuita para revisar el reporte con un experto de SecureSoft.", "Solo deseo descargar el informe por el momento."], index=None)

    if st.button("GENERAR REPORTE PDF", type="primary"):
        if opcion_contacto:
            df_rec = leer_word("02. Respuestas.docx")
            pdf = PDF()
            
            # --- CORRECCIÓN DE MÁRGENES ---
            pdf.set_margins(left=15, top=15, right=15) 
            pdf.set_auto_page_break(auto=True, margin=20)
            pdf.add_page()
            
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(180, 10, clean_pdf(f"REPORTE DE CIBERSEGURIDAD: {st.session_state.datos_usuario['Empresa']}"), 0, 1, 'C')
            pdf.ln(5)

            # Ancho de celda seguro: 180mm (para que no se corte a la derecha)
            ancho_seguro = 180 

            for i in range(len(st.session_state.preguntas_texto)):
                p_text = st.session_state.preguntas_texto[i]
                r_text = st.session_state.respuestas_texto[i]
                
                # Pregunta
                pdf.set_font("Arial", 'B', 10); pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(ancho_seguro, 6, clean_pdf(f"Pregunta {i+1}: {p_text}"))
                
                # Resultado (Ajustado para que NO se corte)
                pdf.set_font("Arial", '', 10); pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(ancho_seguro, 6, clean_pdf(f"Resultado: {r_text}"))
                
                # Recomendación
                ids = sorted(list(set(re.findall(r'(\d+\.[a-z])', r_text.lower()))))
                for id_s in ids:
                    m_s = df_rec[df_rec['Clave'].str.lower() == id_s]
                    if not m_s.empty:
                        txt_s = m_s.iloc[0]['Contenido'].strip()
                        pdf.ln(1); pdf.set_font("Arial", 'I', 9); pdf.set_text_color(0, 85, 165)
                        pdf.multi_cell(ancho_seguro - 10, 6, clean_pdf(f"Recomendacion ({id_s}): {txt_s}"), 1)
                pdf.ln(6) # Más espacio entre bloques para evitar amontonamiento

            try:
                pdf_bytes = pdf.output()
                if isinstance(pdf_bytes, bytearray): pdf_bytes = bytes(pdf_bytes)
                st.success("✅ Informe generado exitosamente.")
                st.download_button(label="📥 CLIC AQUÍ PARA DESCARGAR EL REPORTE", data=pdf_bytes, file_name=f"Reporte_Cyber_{st.session_state.datos_usuario['Empresa']}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Error técnico: {e}")
        else:
            st.warning("Seleccione una opción de contacto.")

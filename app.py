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

    /* BOTONES GENERALES */
    div.stButton > button {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4a4a4b !important;
        padding: 0.8rem 2.5rem !important;
        text-transform: uppercase !important;
        font-weight: 600 !important;
    }

    /* Gradiente para botón Siguiente (Como en la foto) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important;
        border: none !important;
        box-shadow: 0px 4px 15px rgba(0, 173, 239, 0.3) !important;
    }

    /* BOTÓN DE DESCARGA (GRIS) */
    div.stDownloadButton > button {
        background-color: #4a4a4b !important;
        color: #ffffff !important;
        border: 1px solid #666666 !important;
        width: 100% !important;
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
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":""}
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

# --- 3. GESTIÓN DE ESTADOS ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro', 
        'paso': 0, 
        'respuestas_texto': [], 
        'preguntas_texto': [], 
        'datos_usuario': {}, 
        'enviado': False
    })

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    logo_principal = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
    if os.path.exists(logo_principal):
        st.image(logo_principal, width=350)
    
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
            st.error("Complete todos los campos obligatorios.")

# --- 5. ETAPA 2: PREGUNTAS (LÓGICA MÚLTIPLE REFORZADA) ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        
        clave_full = fila['Clave']
        # Limpiar número de la pregunta para el título
        q_titulo = re.sub(r'^\d+[\.\s\-)]+', '', clave_full).strip()
        st.markdown(f"## {q_titulo}")
        
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        # Detección estricta de opción múltiple
        es_multiple = any(x in clave_full.lower() for x in ["multiple", "múltiple"])
        
        if es_multiple:
            ans = st.multiselect("Seleccione todas las opciones que correspondan:", opciones, key=f"q_{st.session_state.paso}")
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None, key=f"q_{st.session_state.paso}")
        
        if st.button("CONFIRMAR Y SIGUIENTE", type="primary"):
            if ans:
                # Guardamos la clave completa y la respuesta (como string)
                st.session_state.preguntas_texto.append(clave_full)
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()
            else:
                st.warning("Debe seleccionar al menos una respuesta.")

# --- 6. ETAPA 3: REPORTE FINAL ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Finalizado")
    if st.button("GENERAR REPORTE ESTRATÉGICO"):
        st.session_state.enviado = True

    if st.session_state.enviado:
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, clean_pdf(f"REPORTE PARA: {st.session_state.datos_usuario.get('Empresa', '')}"), 0, 1)
        pdf.ln(5)

        for i in range(len(st.session_state.preguntas_texto)):
            p_text = st.session_state.preguntas_texto[i]
            r_text = st.session_state.respuestas_texto[i]
            
            pdf.set_font("Arial", 'B', 10); pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {p_text}"))
            
            pdf.set_font("Arial", '', 10); pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, clean_pdf(f"Hallazgo: {r_text}"))
            
            # Búsqueda de recomendaciones por ID (ej: 1.a) sin repetir contenido
            ids = sorted(list(set(re.findall(r'(\d+\.[a-z])', r_text.lower()))))
            mostrados = set()

            if ids:
                # Intentar combinación primero
                comb = " y ".join(ids)
                m_comb = df_rec[df_rec['Clave'].str.lower().str.contains(comb, na=False)]
                if not m_comb.empty:
                    txt = m_comb.iloc[0]['Contenido'].strip()
                    pdf.ln(1); pdf.set_font("Arial", 'I', 9); pdf.set_text_color(0, 85, 165)
                    pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {txt}"), 1)
                    mostrados.add(txt)
                else:
                    # Individuales si no hay combinación o contenido diferente
                    for id_s in ids:
                        m_s = df_rec[df_rec['Clave'].str.lower() == id_s]
                        if not m_s.empty:
                            txt_s = m_s.iloc[0]['Contenido'].strip()
                            if txt_s not in mostrados:
                                pdf.ln(1); pdf.set_font("Arial", 'I', 9); pdf.set_text_color(0, 85, 165)
                                pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion ({id_s}): {txt_s}"), 1)
                                mostrados.add(txt_s)
            pdf.ln(4)

        st.download_button(
            label="📥 DESCARGAR REPORTE EN PDF",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Assessment_{st.session_state.datos_usuario.get('Empresa', 'Cyber')}.pdf",
            mime="application/pdf"
        )

import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Cyber Assessment", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* Contenedor del Logo y Títulos */
    .header-container {
        margin-bottom: 20px;
    }

    .cyber-subtitle { 
        color: #ffffff; 
        font-weight: 700; 
        font-size: 1.8rem; 
        margin-top: 10px; 
        margin-bottom: 30px; 
    }

    /* Estilo de etiquetas y campos de entrada */
    .stTextInput label, .stSelectbox label, .stMultiSelect label, .stRadio label {
        color: #ffffff !important;
        font-weight: 500 !important;
        font-size: 1rem !important;
    }
    
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 4px !important;
        border: none !important;
        height: 45px !important;
    }

    /* BOTÓN INICIAR ASSESSMENT (Gris Oscuro profesional) */
    div.stButton > button {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4a4a4b !important;
        border-radius: 4px !important;
        padding: 0.75rem 2rem !important;
        text-transform: uppercase !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        width: auto !important;
        min-width: 200px;
    }
    div.stButton > button:hover {
        border-color: #00c3ff !important;
        color: #00c3ff !important;
    }

    /* BOTÓN DE DESCARGA (GRIS CON LETRAS BLANCAS) */
    div.stDownloadButton > button {
        background-color: #4a4a4b !important;
        color: #ffffff !important;
        border: 1px solid #666666 !important;
        border-radius: 4px !important;
        padding: 0.75rem 2rem !important;
        text-transform: uppercase !important;
        font-weight: bold !important;
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
        if os.path.exists('OG_securesoft@2x.png'):
            self.image('OG_securesoft@2x.png', 10, 8, 33)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'INFORME DE MADUREZ DIGITAL', 0, 1, 'R')
        self.ln(15)

# --- 3. GESTIÓN DE ESTADOS ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}, 'enviado': False})

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    # Logo reemplaza la leyenda de texto
    if os.path.exists('OG_securesoft@2x.png'):
        st.image('OG_securesoft@2x.png', width=280)
    
    st.markdown('<p class="cyber-subtitle">Assessment de Madurez y Resiliencia Digital</p>', unsafe_allow_html=True)
    
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
    
    st.write("---")
    # Botón Iniciar Assessment visible y alineado
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
        
        clave_q = fila['Clave']
        q_label = re.sub(r'^\d+[\.\s\-)]+', '', clave_q).strip()
        st.markdown(f"## {q_label}")
        
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        es_multiple = "multiple" in clave_q.lower() or "múltiple" in clave_q.lower()
        
        if es_multiple:
            ans = st.multiselect("Seleccione las opciones correspondientes:", opciones)
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None)
        
        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(clave_q)
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Evaluación Finalizada")
    if st.button("GENERAR REPORTE FINAL"):
        st.session_state.enviado = True

    if st.session_state.enviado:
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, clean_pdf(f"REPORTE ESTRATÉGICO: {st.session_state.datos_usuario['Empresa']}"), 0, 1)
        pdf.ln(5)

        for i in range(len(st.session_state.preguntas_texto)):
            p_full = st.session_state.preguntas_texto[i]
            r_u = st.session_state.respuestas_texto[i]
            
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {p_full}"))
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, clean_pdf(f"Hallazgo: {r_u}"))
            
            # Lógica de Recomendaciones (Prioriza combinadas y elimina duplicados textuales)
            ids = sorted(list(set(re.findall(r'(\d+\.[a-z])', r_u.lower()))))
            mostrados = set()

            if ids:
                combinacion = " y ".join(ids)
                m_comb = df_rec[df_rec['Clave'].str.lower().str.contains(combinacion, na=False)]
                if not m_comb.empty:
                    txt = m_comb.iloc[0]['Contenido'].strip()
                    pdf.ln(1); pdf.set_font("Arial", 'I', 9); pdf.set_text_color(0, 85, 165)
                    pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {txt}"), 1)
                    mostrados.add(txt)
                else:
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
            label="📥 DESCARGAR INFORME EN PDF",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Assessment_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf"
        )

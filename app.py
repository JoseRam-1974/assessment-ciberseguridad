import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Assessment", page_icon="🛡️", layout="wide")

# CSS para diseño neón, visibilidad de etiquetas y botones llamativos
st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* Etiquetas de campos: Blanco puro para máximo contraste */
    .stTextInput label, .stRadio label, .stMultiSelect label, .stSelectbox label {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }

    /* Inputs: Fondo blanco y texto negro para legibilidad al escribir */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 5px !important;
    }

    /* BOTÓN ESTILO NEÓN (Gtd Branded) */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #00ccff 0%, #0056b3 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 900 !important;
        font-size: 1.2rem !important;
        height: 3.5em !important;
        border-radius: 10px !important;
        box-shadow: 0px 4px 15px rgba(0, 204, 255, 0.6) !important;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        box-shadow: 0px 6px 20px rgba(0, 204, 255, 0.8) !important;
        transform: scale(1.01);
    }

    /* Tarjetas de preguntas */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #121d2f;
        border-radius: 12px;
        border: 1px solid #1e3a5f;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE PROCESAMIENTO ---
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
        # Manejo de logo dinámico
        for logo in ['OG_securesoft@2x.png', 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png']:
            if os.path.exists(logo):
                self.image(logo, 10, 8, 35)
                break
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 86, 179)
        self.cell(0, 10, 'CYBER RESILIENCE ASSESSMENT', 0, 1, 'R')
        self.ln(12)

# --- 3. ESTADO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro', 'paso': 0, 
        'respuestas_texto': [], 'preguntas_texto': [], 
        'datos_usuario': {}, 'enviado': False
    })

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("SECURESOFT GTD")
    st.subheader("Assessment de Madurez y Resiliencia Digital")
    
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo")
            car = st.text_input("Cargo")
            emp = st.text_input("Empresa")
        with c2:
            ema = st.text_input("Email Corporativo")
            tel = st.text_input("Telefono de Contacto")
        
        if st.form_submit_button("INICIAR ASSESSMENT"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Por favor rellene todos los campos.")

# --- 5. ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / len(df_p))
        
        # UI Pregunta
        preg_limpia = re.sub(r'^\d+\.\s*', '', fila['Clave'])
        st.markdown(f"### {preg_limpia}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        if "múltiple" in fila['Clave'].lower() or "multiple" in fila['Clave'].lower():
            ans = st.multiselect("Seleccione las opciones correspondientes:", opciones)
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: REPORTE Y CONTACTO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Completado")
    
    with st.container(border=True):
        st.subheader("Próximos Pasos")
        contacto = st.radio("¿Deseas que un ejecutivo senior te contacte para analizar estos resultados?", 
                            ["SÍ, deseo asesoría técnica", "NO, por ahora solo el informe"], index=None)

    if not st.session_state.enviado:
        if st.button("GENERAR INFORME FINAL"):
            if contacto:
                # Registro en GSheets si se requiere
                st.session_state.enviado = True
                st.rerun()
            else:
                st.warning("Por favor, selecciona una opción de contacto.")
    else:
        # Generación de PDF
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_pdf(f"REPORTE DE CIBERSEGURIDAD: {st.session_state.datos_usuario['Empresa']}"), 0, 1)
        pdf.ln(5)

        for i in range(len(st.session_state.preguntas_texto)):
            p_full = st.session_state.preguntas_texto[i]
            resp_u = st.session_state.respuestas_texto[i]
            
            # --- CORRECCIÓN: Evitar repetición de número ---
            # Removemos cualquier prefijo numérico (ej: "3. ") del contenido original del Word
            p_sin_numero = re.sub(r'^\d+[\.\s\-)]+', '', p_full).strip()
            
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {p_sin_numero}"))
            
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 6, clean_pdf(f"Hallazgo: {resp_u}"), 0, 1)

            # Lógica de Recomendación por ID
            ids = re.findall(r'(\d+\.[a-z])', resp_u.lower())
            if ids:
                for id_u in ids:
                    match = df_rec[df_rec['Clave'].str.lower().str.contains(id_u, na=False)]
                    if not match.empty:
                        pdf.set_font("Arial", 'I', 9)
                        pdf.set_text_color(0, 86, 179)
                        pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {match.iloc[0]['Contenido']}"), 1)
            pdf.ln(4)

        st.download_button(
            label="📥 DESCARGAR INFORME TÉCNICO (PDF)",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Reporte_SecureSoft_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

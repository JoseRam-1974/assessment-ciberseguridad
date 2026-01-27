import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL SECURESOFT (DARK MODE) ---
st.set_page_config(page_title="SecureSoft GTD | Cyber Assessment", page_icon="🛡️", layout="wide")

# CSS Avanzado para replicar el diseño y mejorar legibilidad
st.markdown("""
    <style>
    /* Fondo oscuro profundo */
    .stApp { 
        background-color: #0b111b; 
        color: #ffffff;
    }
    
    /* Banner Principal con imagen de diseño */
    .cyber-banner {
        background: linear-gradient(90deg, rgba(11,17,27,1) 0%, rgba(22,42,77,0.8) 100%), 
                    url('https://raw.githubusercontent.com/tu-usuario/tu-repo/main/diseño.jpg');
        background-size: cover;
        padding: 50px;
        border-radius: 15px;
        border-bottom: 4px solid #00ccff;
        margin-bottom: 30px;
        text-align: left;
    }

    /* Títulos en Celeste SecureSoft */
    h1, h2, h3 { color: #00ccff !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Forzar visibilidad de opciones (Radio y Checkbox) en Blanco */
    .stRadio [data-testid="stWidgetLabel"] p, 
    .stRadio label, 
    .stMultiSelect label,
    .stSelectbox label {
        color: #ffffff !important;
        font-size: 1.1rem !important;
    }

    /* Botones SecureSoft */
    .stButton>button {
        width: 100%;
        border-radius: 4px;
        height: 3.5em;
        background-color: #0056b3;
        color: white;
        border: 1px solid #00ccff;
        font-weight: bold;
        text-transform: uppercase;
    }
    .stButton>button:hover { 
        background-color: #00ccff; 
        color: #0b111b;
    }

    /* Tarjetas de preguntas */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #121d2f;
        border-radius: 12px;
        padding: 35px;
        border: 1px solid #1e3a5f;
    }

    /* Barra de progreso */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #0056b3, #00ccff);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO ---
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
    for a, b in rep.items(): txt = str(txt).replace(a, b)
    return txt.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        # Logo en el Informe
        if os.path.exists('OG_securesoft@2x.png'):
            self.image('OG_securesoft@2x.png', 10, 8, 40)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 86, 179)
        self.cell(0, 10, 'CONFIDENTIAL CYBER ASSESSMENT', 0, 1, 'R')
        self.ln(15)

# --- 3. LOGICA DE NAVEGACIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro', 'paso': 0, 
        'respuestas_texto': [], 'preguntas_texto': [], 
        'datos_usuario': {}, 'enviado': False
    })

# --- SIDEBAR CON LOGO ADJUNTO ---
with st.sidebar:
    if os.path.exists('OG_securesoft@2x.png'):
        st.image('OG_securesoft@2x.png', use_container_width=True)
    st.write("---")
    if st.session_state.datos_usuario:
        st.markdown(f"**Cliente:** {st.session_state.datos_usuario['Empresa']}")
        st.markdown(f"**Analista:** {st.session_state.datos_usuario['Nombre']}")

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.markdown('<div class="cyber-banner"><h1>SECURESOFT GTD</h1><p>Assessment de Madurez y Resiliencia Digital</p></div>', unsafe_allow_html=True)
    
    with st.form("reg_form"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Completo")
            car = st.text_input("Cargo")
            emp = st.text_input("Empresa")
        with col2:
            ema = st.text_input("Email Corporativo")
            tel = st.text_input("Teléfono")
        
        if st.form_submit_button("INICIAR ASSESSMENT"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()

# --- 5. ETAPA 2: PREGUNTAS (CON MEJORA DE VISIBILIDAD) ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total_p = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        
        st.progress((st.session_state.paso + 1) / total_p)
        
        with st.container(border=True):
            # Título de pregunta en Celeste
            titulo_q = re.sub(r'^\d+\.\s*', '', fila['Clave'])
            st.markdown(f"### {titulo_q}")
            
            opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
            
            # El CSS arriba asegura que estas opciones se vean blancas
            ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(ans)
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: RESULTADOS Y REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis de Brechas Finalizado")
    
    si_count = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    st.metric("Resultado Nivel de Madurez", nivel)
    
    with st.container(border=True):
        st.subheader("📍 Recomendación de Consultoría")
        st.write("Dada su infraestructura, recomendamos una sesión de validación técnica con SecureSoft.")
        opcion_contacto = st.radio("¿Deseas que un consultor te contacte?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("GENERAR INFORME TÉCNICO"):
            # Lógica de registro en GSheets (Usar el código que ya tienes configurado)
            st.session_state.enviado = True
            st.rerun()
    else:
        # Generación de PDF con Logo Blanco
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_pdf(f"REPORTE PARA: {st.session_state.datos_usuario['Empresa']}"), 1, 1, 'C')
        pdf.ln(10)

        for i in range(len(st.session_state.preguntas_texto)):
            preg = re.sub(r'^\d+\.\s*', '', st.session_state.preguntas_texto[i])
            resp = st.session_state.respuestas_texto[i]
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, clean_pdf(f"P{i+1}: {preg}"))
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            pdf.set_x(15)
            pdf.multi_cell(0, 5, clean_pdf(f"Hallazgo: {resp}"))

            # Búsqueda de recomendación (Match de IDs como reparamos antes)
            # ... (Lógica de match aquí) ...

            pdf.ln(4)

        st.download_button(
            label="📥 DESCARGAR PDF SECURESOFT",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Informe_Cyber_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("REINICIAR"):
        st.session_state.clear()
        st.rerun()

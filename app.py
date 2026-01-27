import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="SecureSoft GTD | Cyber Assessment", page_icon="🛡️", layout="wide")

# CSS para corregir visibilidad, botones llamativos y legibilidad en Dark Mode
st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    
    /* Títulos en Celeste SecureSoft */
    h1, h2, h3 { color: #00ccff !important; font-family: 'Segoe UI', sans-serif; }

    /* Etiquetas de campos: Blanco puro para legibilidad */
    .stTextInput label, .stRadio label, .stMultiSelect label, .stSelectbox label {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        margin-bottom: 8px;
    }

    /* Cajas de texto: Fondo blanco, texto negro para escribir cómodo */
    .stTextInput input {
        background-color: #ffffff !important;
        color: #0b111b !important;
        border-radius: 5px !important;
    }

    /* BOTÓN LLAMATIVO NEÓN (Iniciar Assessment y Siguiente) */
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #00ccff 0%, #0056b3 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 900 !important;
        font-size: 1.2rem !important;
        height: 3.8em !important;
        border-radius: 10px !important;
        box-shadow: 0px 0px 20px rgba(0, 204, 255, 0.5) !important;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0px 0px 30px rgba(0, 204, 255, 0.8) !important;
        color: #ffffff !important;
    }

    /* Tarjetas de preguntas */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #121d2f;
        border-radius: 15px;
        border: 1px solid #1e3a5f;
        padding: 25px;
    }

    /* Barra de progreso */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #0056b3, #00ccff);
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
            self.image('OG_securesoft@2x.png', 10, 8, 35)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 86, 179)
        self.cell(0, 10, 'INFORME TECNICO DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(12)

# --- 3. ESTADO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro', 'paso': 0, 
        'respuestas_texto': [], 'preguntas_texto': [], 
        'datos_usuario': {}, 'enviado': False,
        'opcion_contacto': None
    })

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.image('OG_securesoft@2x.png', width=200)
    st.title("SECURESOFT GTD")
    st.subheader("Datos del Responsable de TI / Seguridad")
    
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo*")
            car = st.text_input("Cargo*")
            emp = st.text_input("Empresa*")
        with c2:
            ema = st.text_input("Email Corporativo*")
            tel = st.text_input("Telefono de Contacto*")
        
        if st.form_submit_button("INICIAR ASSESSMENT"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Por favor complete todos los campos obligatorios.")

# --- 5. ETAPA 2: ASSESSMENT ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total_p = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        st.progress((st.session_state.paso + 1) / total_p)
        
        with st.container(border=True):
            # Limpiar número duplicado de la pregunta para la UI
            preg_display = re.sub(r'^\d+\.\s*', '', fila['Clave'])
            st.markdown(f"### {preg_display}")
            
            opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
            
            # Detectar Selección Múltiple
            if any(x in fila['Clave'].lower() for x in ["multiple", "múltiple", "varias"]):
                ans = st.multiselect("Seleccione una o más opciones:", opciones)
            else:
                ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: REPORTE Y CONTACTO ---
elif st.session_state.etapa == 'resultado':
    st.title("🛡️ Diagnóstico Finalizado")
    
    # Contenedor para la opción de contacto
    with st.container(border=True):
        st.subheader("🚀 Próximos Pasos")
        st.write("¿Deseas que un consultor senior de SecureSoft GTD te contacte para analizar estos resultados?")
        contacto = st.radio("Selecciona una opción:", ["SÍ, deseo asesoría técnica", "NO, solo descargar el informe"], index=None)
        st.session_state.opcion_contacto = contacto

    if not st.session_state.enviado:
        if st.button("GENERAR REPORTE Y FINALIZAR"):
            if st.session_state.opcion_contacto:
                # INTEGRACIÓN GSHEETS (Si ya tienes tus secrets configurados)
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    u = st.session_state.datos_usuario
                    df_nuevo = pd.DataFrame([{
                        "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Empresa": u["Empresa"], "Nombre": u["Nombre"], "Cargo": u["Cargo"],
                        "Email": u["Email"], "Telefono": u["Telefono"], "Contacto": st.session_state.opcion_contacto
                    }])
                    hist = conn.read(spreadsheet=url, ttl=0)
                    conn.update(spreadsheet=url, data=pd.concat([hist, df_nuevo], ignore_index=True))
                except: pass
                
                st.session_state.enviado = True
                st.rerun()
            else:
                st.warning("Por favor elige una opción de contacto antes de finalizar.")
    
    else:
        st.success("✅ Datos registrados correctamente.")
        
        # --- Lógica de Generación de PDF ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_pdf(f"REPORTE PARA: {st.session_state.datos_usuario['Empresa']}"), 0, 1)
        pdf.ln(5)

        for i in range(len(st.session_state.preguntas_texto)):
            p_orig = st.session_state.preguntas_texto[i]
            resp_u = st.session_state.respuestas_texto[i]
            
            # Pregunta limpia en el PDF
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(50, 50, 50)
            preg_pdf = re.sub(r'^\d+\.\s*', '', p_orig) # Quita el "3." inicial
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {preg_pdf}"))
            
            # Hallazgo
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.set_x(15)
            pdf.multi_cell(0, 6, clean_pdf(f"Hallazgo: {resp_u}"))

            # Recomendación (Basada en el ID de la respuesta)
            recom_final = ""
            ids_u = re.findall(r'(\d+\.[a-z])', resp_u.lower())
            
            if ids_u:
                for id_u in ids_u:
                    # Busca el ID (ej: 3.a) en la columna Clave del Word de respuestas
                    match = df_rec[df_rec['Clave'].str.lower().str.contains(id_u, na=False)]
                    if not match.empty:
                        recom_final = match.iloc[0]['Contenido']
                        break

            if recom_final:
                pdf.ln(1)
                pdf.set_x(15)
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(0, 86, 179)
                pdf.multi_cell(0, 6, clean_pdf(f"Recomendacion: {recom_final}"), 1)
            
            pdf.ln(5)

        # BOTÓN DE DESCARGA LLAMATIVO
        st.download_button(
            label="📥 DESCARGAR INFORME TÉCNICO PDF",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Assessment_SecureSoft_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        if st.button("Realizar nueva evaluación"):
            st.session_state.clear()
            st.rerun()

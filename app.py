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

# Estilos CSS para asegurar que el texto sea visible (blanco) en fondo oscuro
st.markdown("""
    <style>
    .stApp { background-color: #0b111b; color: #ffffff; }
    div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
    div[role="radiogroup"] label p { color: #ffffff !important; }
    label[data-testid="stWidgetLabel"] p { color: #00adef !important; font-weight: bold !important; }
    .stButton > button { background: linear-gradient(90deg, #00adef 0%, #0055a5 100%) !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES TÉCNICAS CORREGIDAS ---
def leer_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                celdas = [c.text.strip() for c in fila.cells]
                if len(celdas) >= 2: datos.append([celdas[0], celdas[1]])
        return pd.DataFrame(datos[1:], columns=["Clave", "Contenido"])
    except Exception: return pd.DataFrame()

def clean_pdf(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":"","–":"-"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

# --- 3. CLASE PDF OPTIMIZADA ---
class PDF(FPDF):
    def header(self):
        logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
        if os.path.exists(logo):
            self.image(logo, 10, 8, 40)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'ASSESSMENT DIGITAL DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(10)

# --- 4. GESTIÓN DE FLUJO ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa': 'registro', 'paso': 0, 'respuestas_texto': [], 'preguntas_texto': [], 'datos_usuario': {}})

if st.session_state.etapa == 'registro':
    st.title("Registro de Evaluación")
    nom = st.text_input("Nombre Completo")
    emp = st.text_input("Empresa")
    if st.button("INICIAR ASSESSMENT"):
        if nom and emp:
            st.session_state.datos_usuario = {"Nombre": nom, "Empresa": emp}
            st.session_state.etapa = 'preguntas'
            st.rerun()

elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.write(f"### {fila['Clave']}")
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        ans = st.radio("Seleccione una opción:", opciones, index=None, key=f"q_{st.session_state.paso}")
        
        if st.button("SIGUIENTE") and ans:
            st.session_state.preguntas_texto.append(fila['Clave'])
            st.session_state.respuestas_texto.append(ans)
            if st.session_state.paso < len(df_p) - 1:
                st.session_state.paso += 1
                st.rerun()
            else:
                st.session_state.etapa = 'resultado'
                st.rerun()

elif st.session_state.etapa == 'resultado':
    st.success(f"Evaluación completada para {st.session_state.datos_usuario['Empresa']}")
    
    # Opción de contacto (según tu imagen)
    opcion = st.radio("Para una interpretación más profunda de estos resultados:", 
                      ["Deseo una sesión de consultoría gratuita.", "Solo deseo descargar el informe por el momento."], index=None)

    if st.button("GENERAR REPORTE PDF") and opcion:
        # Generar gráfico radar base
        pilares = ["Identificar", "Proteger", "Detectar", "Responder", "Recuperar"]
        valores = [70, 85, 60, 75, 80]
        angles = np.linspace(0, 2*np.pi, len(pilares), endpoint=False).tolist()
        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
        ax.fill(angles + [angles[0]], valores + [valores[0]], color='#00adef', alpha=0.3)
        plt.savefig("radar.png", bbox_inches='tight')
        plt.close()

        # Crear PDF
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        
        # Título y Gráfico
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, clean_pdf(f"REPORTE: {st.session_state.datos_usuario['Empresa']}"), 0, 1, 'C')
        
        if os.path.exists("radar.png"):
            pdf.image("radar.png", x=55, y=45, w=100)
            pdf.set_y(150) # Espacio de seguridad debajo de la imagen

        pdf.set_font("Arial", 'B', 12); pdf.set_text_color(0, 85, 165)
        pdf.cell(190, 10, "Resultados por Puntos de Control:", 0, 1); pdf.ln(5)

        # Iteración de respuestas (Ancho fijo de 190 para evitar errores de espacio)
        for i in range(len(st.session_state.preguntas_texto)):
            pdf.set_font("Arial", 'B', 10); pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(190, 7, clean_pdf(f"P{i+1}: {st.session_state.preguntas_texto[i]}"))
            
            pdf.set_font("Arial", '', 10); pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(190, 7, clean_pdf(f"Resultado: {st.session_state.respuestas_texto[i]}"))
            pdf.ln(3)

        # Generar descarga (Método compatible con Streamlit)
        pdf_output = pdf.output() 
        st.download_button(
            label="📥 DESCARGAR REPORTE FINAL",
            data=bytes(pdf_output),
            file_name=f"Reporte_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf"
        )

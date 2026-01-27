import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from fpdf import FPDF
import re
import os

# --- FUNCIONES DE SOPORTE ---
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

# --- CLASE PDF CORREGIDA ---
class PDF(FPDF):
    def header(self):
        # Ajusta el nombre de tu logo aquí
        logo = 'Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'
        if os.path.exists(logo):
            self.image(logo, 10, 8, 40)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 85, 165)
        self.cell(0, 10, 'ASSESSMENT DIGITAL DE CIBERSEGURIDAD', 0, 1, 'R')
        self.ln(10)

# --- LÓGICA DE GENERACIÓN ---
# (Asumiendo que ya tienes los datos en st.session_state)

if st.button("GENERAR REPORTE PDF", type="primary"):
    # 1. Generar Gráfico (Soluciona ModuleNotFoundError)
    pilares = ["Identificar", "Proteger", "Detectar", "Responder", "Recuperar"]
    valores = [75, 80, 60, 85, 70] # Valores de ejemplo
    angles = np.linspace(0, 2*np.pi, len(pilares), endpoint=False).tolist()
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.fill(angles + [angles[0]], valores + [valores[0]], color='#00adef', alpha=0.3)
    plt.savefig("radar.png")
    plt.close()

    # 2. Crear PDF (Soluciona FPDFException)
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # Imagen y posicionamiento seguro
    if os.path.exists("radar.png"):
        pdf.image("radar.png", x=55, y=40, w=100)
        pdf.set_y(150) # Baja el cursor para evitar el error de "Not enough space"

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, clean_pdf("RESULTADOS ESTRATEGICOS"), 0, 1, 'C')
    pdf.ln(5)

    # 3. Contenido con ancho fijo de 190 (Crucial para evitar errores)
    for i in range(len(st.session_state.get('preguntas_texto', []))):
        pdf.set_font("Arial", 'B', 10)
        pdf.multi_cell(190, 7, clean_pdf(f"P{i+1}: {st.session_state.preguntas_texto[i]}"))
        
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(190, 7, clean_pdf(f"Respuesta: {st.session_state.respuestas_texto[i]}"))
        pdf.ln(2)

    # 4. Descarga compatible (Soluciona AttributeError)
    try:
        pdf_bytes = pdf.output() # fpdf2 genera bytes directamente
        st.success("✅ Reporte listo.")
        st.download_button(
            label="📥 DESCARGAR INFORME",
            data=pdf_bytes,
            file_name="Reporte_Ciberseguridad.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Error al exportar: {e}")

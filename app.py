import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Assessment Estratégico CS", layout="wide")

def leer_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                datos.append([celda.text.strip() for celda in fila.cells[:2]])
        return pd.DataFrame(datos[1:], columns=["Clave", "Contenido"])
    except:
        return pd.DataFrame()

def clean_pdf_text(texto):
    if not texto: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":"","º":".","ª":"."}
    t = str(texto)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class InformePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, 'PLAN DE RECOMENDACIONES ESTRATEGICAS', 0, 1, 'C')
        self.ln(5)

# --- INICIO DE LÓGICA ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa':'registro','paso':0,'respuestas':[],'datos_usuario':{},'enviado':False})

# (Etapa 1: Registro y Etapa 2: Preguntas se mantienen igual que tu versión funcional)
# ... [Omitido por brevedad para centrarse en el PDF, pero mantén tu lógica de preguntas] ...

# --- ETAPA 3: RESULTADOS Y RECOMENDACIONES ---
elif st.session_state.etapa == 'resultado':
    st.title("🎯 Resultado del Diagnóstico Estratégico")
    
    # 1. Cargar base de recomendaciones
    df_recomendaciones = leer_word("02. Respuestas.docx")
    
    conteo_si = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    nivel = "Avanzado" if conteo_si > 12 else "Intermedio" if conteo_si > 6 else "Inicial"
    
    st.metric("Nivel de Madurez Detectado", nivel)

    if st.button("Finalizar y Generar Reporte de Consultoría"):
        # Lógica de guardado en GSheets (Mantén tu lógica actual aquí)
        # ...
        
        st.session_state.enviado = True
        st.success("Análisis completado. Descargue su hoja de ruta a continuación:")

    if st.session_state.enviado:
        # --- GENERACIÓN DEL PDF DE CONSULTORÍA ---
        pdf = InformePDF()
        pdf.add_page()
        
        # Resumen Ejecutivo
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, " 1. RESUMEN EJECUTIVO", 0, 1, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        
        user = st.session_state.datos_usuario
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 7, clean_pdf_text(f"Preparado para: {user['Nombre']} - {user['Empresa']}"))
        pdf.multi_cell(0, 7, clean_pdf_text(f"Nivel Actual: {nivel}"))
        pdf.ln(5)

        # SECCIÓN CRÍTICA: RECOMENDACIONES PERSONALIZADAS
        pdf.set_fill_color(231, 76, 60) # Rojo corporativo para importancia
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, " 2. HOJA DE RUTA Y RECOMENDACIONES", 0, 1, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

        for r_usuario in st.session_state.respuestas:
            # Buscamos si existe recomendación para esta respuesta
            # Soporta múltiples opciones separadas por coma
            sub_respuestas = [sr.strip() for sr in r_usuario.split(",")]
            
            for sr in sub_respuestas:
                match = df_recomendaciones[df_recomendaciones['Clave'].str.contains(sr, na=False, case=False)]
                
                if not match.empty:
                    rec_texto = match.iloc[0]['Contenido']
                    pdf.set_font("Arial", 'B', 10)
                    pdf.multi_cell(0, 6, clean_pdf_text(f"> Sobre su seleccion: {sr}"))
                    pdf.set_font("Arial", '', 10)
                    pdf.multi_cell(0, 6, clean_pdf_text(f"RECOMENDACION: {rec_texto}"))
                    pdf.ln(3)

        st.download_button(
            label="📥 DESCARGAR INFORME DE CONSULTORÍA (PDF)",
            data=pdf.output(dest='S').encode('latin-1'),
            file_name=f"Plan_Ciberseguridad_{user['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

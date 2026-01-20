import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️")

def leer_tablas_seguro(file_path, columnas_esperadas):
    try:
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                # Tomamos solo las celdas necesarias para evitar el error de "4 columnas"
                data.append([cell.text.strip() for cell in row.cells[:len(columnas_esperadas)]])
        return pd.DataFrame(data[1:], columns=columnas_esperadas)
    except Exception as e:
        st.error(f"Error al cargar {file_path}: {e}")
        return None


# --- CARGA DE DATOS ---
df_preguntas = leer_tablas_seguro("01. Preguntas.docx", ["Preguntas", "Alternativas"])
df_respuestas = leer_tablas_seguro("02. Respuestas.docx", ["Alternativas", "Complemento", "Recomendaciones"])

if 'paso' not in st.session_state:
    st.session_state.update({'paso': 0, 'respuestas_usuario': [], 'finalizado': False})

# --- INTERFAZ ---
st.title("🛡️ Diagnóstico de Madurez CS")

if not st.session_state.finalizado:
    fila = df_preguntas.iloc[st.session_state.paso]
    st.subheader(f"Pregunta {st.session_state.paso + 1} de {len(df_preguntas)}")
    st.write(f"**{fila['Preguntas']}**")
    
    opciones = [opt.strip() for opt in fila['Alternativas'].split('\n') if opt.strip()]
    
    if "Selección Múltiple" in fila['Preguntas']:
        seleccion = st.multiselect("Seleccione una o más opciones:", opciones)
    else:
        seleccion = st.radio("Seleccione una opción:", opciones, index=None)

    if st.button("Continuar"):
        if seleccion:
            st.session_state.respuestas_usuario.append(seleccion)
            if st.session_state.paso < len(df_preguntas) - 1:
                st.session_state.paso += 1
                st.rerun()
            else:
                st.session_state.finalizado = True
                st.rerun()
        else:
            st.warning("Seleccione una respuesta para avanzar.")

# --- GENERACIÓN DEL INFORME FINAL ---
else:
    st.success("✅ Assessment completado. Analizando resultados...")
    
    # 1. Procesar recomendaciones basadas en Fuente 2
    informe_data = []
    respuestas_positivas = 0
    
    for r_usuario in st.session_state.respuestas_usuario:
        lista_r = r_usuario if isinstance(r_usuario, list) else [r_usuario]
        for r in lista_r:
            # Extraer código como '2.a' o '16.c'
            codigo = re.search(r'(\d+\.[a-z])', r)
            if codigo:
                cod = codigo.group(1)
                match = df_respuestas[df_respuestas['Alternativas'].str.contains(cod, na=False)]
                if not match.empty:
                    res = match.iloc[0]
                    informe_data.append(res)
                    # Contar como positivo si no es una opción de "NO" o "Lo desconozco"
                    if "SI" in r.upper() or "Automatizado" in r:
                        respuestas_positivas += 1

    # 2. Calcular Nivel de Madurez
    nivel = "Inicial"
    if respuestas_positivas > 10: nivel = "Avanzado"
    elif respuestas_positivas > 5: nivel = "Intermedio"

    # 3. Mostrar Informe en Pantalla
    st.header("📋 Informe Estratégico Final")
    st.metric("Nivel de Madurez Detectado", nivel)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💡 Recomendaciones")
        for i, item in enumerate(informe_data[:6]): # Mostrar las más relevantes
            st.write(f"**{i+1}. {item['Recomendaciones']}**")
    
    with col2:
        st.subheader("📝 Análisis Técnico")
        for item in informe_data[:3]:
            with st.expander(f"Detalle: {item['Recomendaciones']}"):
                st.write(item['Complemento'])

    # 4. Generación de PDF profesional
    def exportar_pdf():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "Reporte Ejecutivo de Ciberseguridad", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, f"Nivel de Madurez: {nivel}", ln=True)
        pdf.ln(5)
        
        for item in informe_data:
            pdf.set_font("Arial", 'B', 11)
            pdf.multi_cell(0, 10, f"Recomendación: {item['Recomendaciones']}")
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 8, item['Complemento'].encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(4)
        return pdf.output(dest='S').encode('latin-1')

    pdf_output = exportar_pdf()
    st.download_button("📥 Descargar Informe Completo (PDF)", pdf_output, "Reporte_CS.pdf", "application/pdf")



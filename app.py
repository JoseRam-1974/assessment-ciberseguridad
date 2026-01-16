import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="centered")

# --- FUNCIONES DE APOYO ---
def leer_tablas_docx(file_path):
    try:
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                data.append([cell.text.strip() for cell in row.cells])
        df = pd.DataFrame(data[1:], columns=data[0])
        return df
    except Exception as e:
        st.error(f"Error al leer {file_path}: {e}")
        return None

def generar_pdf(recs_usuario):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Resultado del Assessment de Ciberseguridad", ln=True, align='C')
    pdf.ln(10)
    
    for item in recs_usuario:
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 10, txt=f"Recomendación: {item['Recomendaciones']}")
        pdf.set_font("Arial", '', 11)
        # Limpieza de texto para evitar errores de caracteres en PDF
        texto_limpio = item['Complemento'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=texto_limpio)
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- CARGA DE DATOS ---
df_preguntas = leer_tablas_docx("01. Preguntas.docx")
df_respuestas = leer_tablas_docx("02. Respuestas.docx")

# --- ESTADO DE LA SESIÓN ---
if 'paso' not in st.session_state:
    st.session_state.update({'paso': 0, 'respuestas': [], 'finalizado': False})

# --- INTERFAZ DE USUARIO ---
st.title("🛡️ Diagnóstico de Madurez CS")
st.info("Responda las siguientes preguntas para obtener su informe técnico.")

if not st.session_state.finalizado:
    # Obtener pregunta actual
    fila = df_preguntas.iloc[st.session_state.paso]
    pregunta_texto = fila['Preguntas']
    opciones = [opt.strip() for opt in fila['Alternativas'].split('\n') if opt.strip()]
    
    st.subheader(f"Pregunta {st.session_state.paso + 1} de {len(df_preguntas)}")
    st.write(f"**{pregunta_texto}**")
    
    # Lógica de Selección Múltiple vs Única
    es_multiple = "Selección Múltiple" in pregunta_texto
    
    if es_multiple:
        seleccion = st.multiselect("Puede marcar varias opciones:", opciones)
    else:
        seleccion = st.radio("Seleccione una opción:", opciones, index=None)

    if st.button("Continuar"):
        if seleccion:
            st.session_state.respuestas.append(seleccion)
            if st.session_state.paso < len(df_preguntas) - 1:
                st.session_state.paso += 1
                st.rerun()
            else:
                st.session_state.finalizado = True
                st.rerun()
        else:
            st.warning("Por favor, elija una respuesta.")

else:
    st.success("✅ Assessment completado con éxito.")
    
    # --- PROCESAMIENTO DE RESULTADOS ---
    recs_para_pdf = []
    
    for respuesta_u in st.session_state.respuestas:
        # Si es múltiple, iteramos cada selección; si es única, la tratamos como lista de 1
        lista_resp = respuesta_u if isinstance(respuesta_u, list) else [respuesta_u]
        
        for r in lista_resp:
            # Extraer el código (ej: de '2.a) VPN' extraemos '2.a')
            match_codigo = re.search(r'(\d+\.[a-z])', r)
            if match_codigo:
                codigo = match_codigo.group(1)
                # Buscar en Fuente 2
                match_resp = df_respuestas[df_respuestas['Alternativas'].str.contains(codigo, na=False)]
                if not match_resp.empty:
                    recs_para_pdf.append(match_resp.iloc[0].to_dict())

    # --- MOSTRAR RECOMENDACIONES EN PANTALLA ---
    st.header("📋 Resumen de Recomendaciones")
    for item in recs_para_pdf:
        with st.expander(f"📌 {item['Recomendaciones']}"):
            st.write(item['Complemento'])

    # --- BOTÓN DE DESCARGA PDF ---
    pdf_bytes = generar_pdf(recs_para_pdf)
    st.download_button(
        label="📥 Descargar Reporte PDF",
        data=pdf_bytes,
        file_name="Diagnostico_Ciberseguridad.pdf",
        mime="application/pdf"
    )

    if st.button("Realizar nuevo test"):
        st.session_state.update({'paso': 0, 'respuestas': [], 'finalizado': False})
        st.rerun()

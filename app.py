import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

def leer_tablas_seguro(file_path, columnas_esperadas):
    try:
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                data.append([cell.text.strip() for cell in row.cells[:len(columnas_esperadas)]])
        return pd.DataFrame(data[1:], columns=columnas_esperadas)
    except Exception as e:
        st.error(f"Error al cargar {file_path}: {e}")
        return None

# --- CARGA DE DATOS ---
df_preguntas = leer_tablas_seguro("01. Preguntas.docx", ["Preguntas", "Alternativas"])
df_respuestas = leer_tablas_seguro("02. Respuestas.docx", ["Alternativas", "Complemento", "Recomendaciones"])

# --- ESTADO DE LA SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_usuario': [],
        'datos_contacto': {}
    })

st.title("🛡️ Assessment Digital de Ciberseguridad")

# --- ETAPA 1: REGISTRO DE DATOS (ORDEN HORIZONTAL) ---
if st.session_state.etapa == 'registro':
    st.info("Por favor, complete sus datos corporativos para iniciar el diagnóstico.")
    
    with st.form("form_contacto"):
        # Primera fila de campos
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre = st.text_input("Nombre Completo*")
        with col2:
            cargo = st.text_input("Cargo*")
        with col3:
            empresa = st.text_input("Empresa*")
            
        # Segunda fila de campos
        col4, col5 = st.columns(2)
        with col4:
            mail = st.text_input("Email Corporativo*")
        with col5:
            tel = st.text_input("Teléfono de Contacto")
            
        submit = st.form_submit_button("Comenzar Assessment")
        
        if submit:
            if nombre and cargo and empresa and mail:
                st.session_state.datos_contacto = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, "Email": mail, "Tel": tel
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Los campos con (*) son obligatorios.")

# --- ETAPA 2: ASSESSMENT ---
elif st.session_state.etapa == 'preguntas':
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
                st.session_state.etapa = 'finalizado'
                st.rerun()
        else:
            st.warning("Seleccione una respuesta.")

# --- ETAPA 3: REPORTE ---
elif st.session_state.etapa == 'finalizado':
    st.success(f"✅ Evaluación finalizada para {st.session_state.datos_contacto['Nombre']} de {st.session_state.datos_contacto['Empresa']}.")
    
    informe_data = []
    respuestas_positivas = 0
    
    for r_usuario in st.session_state.respuestas_usuario:
        lista_r = r_usuario if isinstance(r_usuario, list) else [r_usuario]
        for r in lista_r:
            codigo = re.search(r'(\d+\.[a-z])', r)
            if codigo:
                cod = codigo.group(1)
                match = df_respuestas[df_respuestas['Alternativas'].str.contains(cod, na=False)]
                if not match.empty:
                    res = match.iloc[0]
                    informe_data.append(res)
                    if "SI" in r.upper() or "Automatizado" in r:
                        respuestas_positivas += 1

    nivel = "Inicial"
    if respuestas_positivas > 10: nivel = "Avanzado"
    elif respuestas_positivas > 5: nivel = "Intermedio"

    st.metric("Nivel de Madurez Detectado", nivel)

# NUEVA SECCIÓN: Resumen de Calificación
    st.subheader("📝 ¿Por qué esta calificación?")
    
    # Contamos tipos de respuestas para el argumento
    con_control = respuestas_positivas
    sin_control = len(st.session_state.respuestas_usuario) - respuestas_positivas
    
    if nivel == "Avanzado":
        st.write(f"Su organización muestra una postura sólida con **{con_control} controles maduros** detectados. La calificación refleja el uso de tecnologías como MFA o EDR y procesos automatizados que reducen drásticamente la superficie de ataque.")
    elif nivel == "Intermedio":
        st.write(f"Se detectaron **{con_control} controles activos**, pero existen **{sin_control} áreas con gestión manual o inexistente**. Este nivel indica que, aunque hay conciencia de seguridad, la falta de integración técnica permite brechas que los atacantes podrían explotar.")
    else:
        st.write(f"La calificación **{nivel}** se debe a que la mayoría de los controles ({sin_control}) son manuales o no están implementados. Según la lógica de evaluación, su infraestructura actual depende de acciones humanas reactivas en lugar de protecciones proactivas.")

    st.divider()
    # ... (continúa con las recomendaciones)
    
    def exportar_pdf():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "Reporte Ejecutivo de Ciberseguridad", ln=True, align='C')
        pdf.set_font("Arial", '', 11)
        pdf.cell(200, 10, f"Cliente: {st.session_state.datos_contacto['Nombre']} - {st.session_state.datos_contacto['Empresa']}", ln=True, align='C')
        pdf.ln(10)
        
        for item in informe_data:
            pdf.set_font("Arial", 'B', 11)
            pdf.multi_cell(0, 10, f"Recomendación: {item['Recomendaciones']}")
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 8, item['Complemento'].encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(4)
        return pdf.output(dest='S').encode('latin-1')

    pdf_output = exportar_pdf()
    st.download_button("📥 Descargar Informe Completo (PDF)", pdf_output, "Reporte_CS.pdf", "application/pdf")

from streamlit_gsheets import GSheetsConnection
import datetime

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Preparar la fila de datos
nueva_fila = pd.DataFrame([{
    "Fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    "Nombre": st.session_state.datos_contacto['Nombre'],
    "Cargo": st.session_state.datos_contacto['Cargo'],
    "Empresa": st.session_state.datos_contacto['Empresa'],
    "Email": st.session_state.datos_contacto['Email'],
    "Tel": st.session_state.datos_contacto['Tel'],
    "Madurez": nivel,
    "Presupuesto": st.session_state.respuestas_usuario[-1] # Asumiendo que la P.16 es la última
}])

# Enviar datos (Solo una vez al finalizar)
if 'datos_enviados' not in st.session_state:
    try:
        # Leer datos actuales
        existente = conn.read(worksheet="Sheet1", usecols=list(range(8)))
        # Concatenar y actualizar
        actualizado = pd.concat([existente, nueva_fila], ignore_index=True)
        conn.update(worksheet="Sheet1", data=actualizado)
        st.session_state.datos_enviados = True
        st.toast("Datos registrados en el Backoffice")
    except Exception as e:
        st.error(f"Error al registrar en Backoffice: {e}")



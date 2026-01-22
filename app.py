import streamlit as st
import pandas as pd
from docx import Document
from fpdf import FPDF
import re
import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# --- 2. FUNCIONES DE APOYO ---
def leer_tablas_seguro(file_path, columnas_esperadas):
    try:
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                # Limpiamos y tomamos solo las columnas necesarias
                data.append([cell.text.strip() for cell in row.cells[:len(columnas_esperadas)]])
        return pd.DataFrame(data[1:], columns=columnas_esperadas)
    except:
        return None

def generar_pdf(datos_contacto, nivel, informe_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Reporte Ejecutivo de Ciberseguridad", ln=True, align='C')
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 10, f"Cliente: {datos_contacto.get('Nombre')} - {datos_contacto.get('Empresa')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"Nivel de Madurez Detectado: {nivel}", ln=True)
    pdf.ln(5)
    
    for item in informe_data:
        pdf.set_font("Arial", 'B', 11)
        pdf.multi_cell(0, 10, f"Recomendacion: {item['Recomendaciones']}")
        pdf.set_font("Arial", '', 10)
        # Limpieza de caracteres especiales para PDF
        texto = item['Complemento'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, texto)
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INICIALIZACIÓN DE ESTADO ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_usuario': [],
        'datos_contacto': {},
        'datos_enviados': False
    })

# --- 4. CARGA DE ARCHIVOS ---
df_p = leer_tablas_seguro("01. Preguntas.docx", ["Preguntas", "Alternativas"])
df_r = leer_tablas_seguro("02. Respuestas.docx", ["Alternativas", "Complemento", "Recomendaciones"])

st.title("🛡️ Assessment Digital de Ciberseguridad")

# --- ETAPA 1: REGISTRO INICIAL ---
if st.session_state.etapa == 'registro':
    st.info("Por favor, complete sus datos para iniciar el diagnóstico profesional.")
    with st.form("registro"):
        c1, c2, c3 = st.columns(3)
        with c1: nombre = st.text_input("Nombre Completo*")
        with c2: cargo = st.text_input("Cargo*")
        with c3: empresa = st.text_input("Empresa*")
        
        c4, c5 = st.columns(2)
        with c4: mail = st.text_input("Email Corporativo*")
        with c5: tel = st.text_input("Teléfono / WhatsApp")
        
        if st.form_submit_button("Comenzar Evaluación"):
            if nombre and cargo and empresa and mail:
                st.session_state.datos_contacto = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, "Email": mail, "Tel": tel
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Los campos con (*) son obligatorios.")

# --- ETAPA 2: ASSESSMENT (PREGUNTAS) ---
elif st.session_state.etapa == 'preguntas':
    fila = df_p.iloc[st.session_state.paso]
    st.subheader(f"Pregunta {st.session_state.paso + 1} de {len(df_p)}")
    st.write(f"**{fila['Preguntas']}**")
    
    opciones = [o.strip() for o in fila['Alternativas'].split('\n') if o.strip()]
    
    if "Selección Múltiple" in fila['Preguntas']:
        res = st.multiselect("Seleccione opciones:", opciones)
    else:
        res = st.radio("Seleccione una opción:", opciones, index=None)

    if st.button("Continuar"):
        if res:
            st.session_state.respuestas_usuario.append(res)
            if st.session_state.paso < len(df_p) - 1:
                st.session_state.paso += 1
                st.rerun()
            else:
                st.session_state.etapa = 'finalizado'
                st.rerun()
        else:
            st.warning("Debe elegir una respuesta.")

# --- ETAPA 3: RESULTADOS Y BACKOFFICE ---
elif st.session_state.etapa == 'finalizado':
    st.success(f"Análisis completado para {st.session_state.datos_contacto.get('Nombre')}")
    
    # Procesamiento de Recomendaciones
    informe_data = []
    positivas = 0
    for r_u in st.session_state.respuestas_usuario:
        lista = r_u if isinstance(r_u, list) else [r_u]
        for r in lista:
            cod = re.search(r'(\d+\.[a-z])', r)
            if cod:
                match = df_r[df_r['Alternativas'].str.contains(cod.group(1), na=False)]
                if not match.empty:
                    informe_data.append(match.iloc[0])
                    if any(x in r.upper() for x in ["SI", "AUTOMATIZADO"]): positivas += 1

    nivel = "Avanzado" if positivas > 10 else "Intermedio" if positivas > 5 else "Inicial"
    
    # Mostrar métricas
    st.metric("Nivel de Madurez", nivel)
    
    # --- ENVÍO A GOOGLE SHEETS (Backoffice) ---
    if not st.session_state.datos_enviados:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_lead = pd.DataFrame([{
                "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": st.session_state.datos_contacto.get("Nombre"),
                "Empresa": st.session_state.datos_contacto.get("Empresa"),
                "Email": st.session_state.datos_contacto.get("Email"),
                "Madurez": nivel,
                "Presupuesto": str(st.session_state.respuestas_usuario[-1])
            }])
            existente = conn.read(worksheet="Sheet1")
            actualizado = pd.concat([existente, df_lead], ignore_index=True)
            conn.update(worksheet="Sheet1", data=actualizado)
            st.session_state.datos_enviados = True
            st.toast("Lead registrado en Backoffice")
        except Exception as e:
            st.error(f"Error registrando datos: {e}")

    # Visualización y Descarga
    col_pdf, col_reset = st.columns(2)
    with col_pdf:
        pdf_bytes = generar_pdf(st.session_state.datos_contacto, nivel, informe_data)
        st.download_button("📥 Descargar Reporte PDF", pdf_bytes, "Reporte_CS.pdf", "application/pdf")
    
    with col_reset:
        if st.button("Reiniciar Assessment"):
            st.session_state.clear()
            st.rerun()

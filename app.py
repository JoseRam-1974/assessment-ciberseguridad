import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

def leer_preguntas_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                datos.append([celda.text.strip() for celda in fila.cells[:2]])
        return pd.DataFrame(datos[1:], columns=["Pregunta", "Opciones"])
    except:
        return pd.DataFrame()

# Funcion para limpiar texto para el PDF (Crucial para evitar UnicodeEncodeError)
def clean_pdf_text(texto):
    if not texto: return ""
    # Mapeo manual de caracteres conflictivos
    rep = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "¿": "", "¡": "", "º": ".", "ª": "."
    }
    t = str(texto)
    for a, b in rep.items():
        t = t.replace(a, b)
    # Forzar codificacion latin-1 ignorando lo que no se pudo convertir
    return t.encode('latin-1', 'ignore').decode('latin-1')

class InformePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'INFORME DE MADUREZ EN CIBERSEGURIDAD', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

# --- ESTADO DE SESION ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa':'registro','paso':0,'respuestas':[],'datos_usuario':{},'enviado':False})

# --- ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Diagnóstico de Ciberseguridad")
    with st.form("registro_inicial"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo*")
            car = st.text_input("Cargo*")
            emp = st.text_input("Empresa*")
        with c2:
            ema = st.text_input("Email*")
            tel = st.text_input("Teléfono*")
        if st.form_submit_button("Iniciar Evaluación"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre":nom,"Cargo":car,"Empresa":emp,"Email":ema,"Telefono":tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Complete los campos obligatorios")

# --- ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_preguntas = leer_preguntas_word("01. Preguntas.docx")
    if not df_preguntas.empty:
        total_p = len(df_preguntas)
        fila_q = df_preguntas.iloc[st.session_state.paso]
        
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {total_p}")
        st.write(f"### {fila_q['Pregunta']}")
        
        opciones = [o.strip() for o in fila_q['Opciones'].split('\n') if o.strip()]
        
        # DETECCION POR PALABRA "MULTIPLE"
        es_multiple = "múltiple" in fila_q['Pregunta'].lower() or "multiple" in fila_q['Pregunta'].lower()
        
        if es_multiple:
            st.info("💡 Selección Múltiple habilitada")
            respuesta = st.multiselect("Seleccione una o más opciones:", opciones, key=f"p_{st.session_state.paso}")
        else:
            respuesta = st.radio("Seleccione una opción:", opciones, index=None, key=f"p_{st.session_state.paso}")

        if st.button("Siguiente Pregunta"):
            if respuesta:
                dato = ", ".join(respuesta) if isinstance(respuesta, list) else respuesta
                st.session_state.respuestas.append(dato)
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()
            else:
                st.error("Debe responder para continuar.")

# --- ETAPA 3: RESULTADOS Y GUARDADO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Assessment Completado")
    
    # Cálculo de nivel (Lógica SI/NO)
    conteo_si = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    nivel_final = "Avanzado" if conteo_si > 12 else "Intermedio" if conteo_si > 6 else "Inicial"
    
    try: presu_valor = st.session_state.respuestas[15]
    except: presu_valor = "N/A"

    st.metric("Nivel de Madurez Detectado", nivel_final)
    st.divider()
    
    quiero_asesoria = st.radio("¿Quieres contactar a un ejecutivo para asesoría personalizada?", ["SÍ", "NO"], index=1, horizontal=True)

    if not st.session_state.enviado:
        if st.button("Finalizar y Guardar en Sistema"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url_sheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u_info = st.session_state.datos_usuario
                
                header_cols = ["Fecha","Nombre","Cargo","Empresa","Email","Telefono","Resultado","Presupuesto","Contacto"]
                
                registro_nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": u_info["Nombre"], "Cargo": u_info["Cargo"], "Empresa": u_info["Empresa"],
                    "Email": u_info["Email"], "Telefono": u_info["Telefono"],
                    "Resultado": nivel_final, "Presupuesto": presu_valor, "Contacto": quiero_asesoria
                }])

                try:
                    df_historico = conn.read(spreadsheet=url_sheet, ttl=0).reindex(columns=header_cols)
                    df_final = pd.concat([df_historico.dropna(how='all'), registro_nuevo], ignore_index=True)
                except:
                    df_final = registro_nuevo

                conn.update(spreadsheet=url_sheet, data=df_final)
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error de conexión: {e}")
    else:
        st.success("Tus datos han sido registrados exitosamente.")
        
        # Generación de PDF sin caracteres especiales
        pdf_doc = InformePDF()
        pdf_doc.add_page()
        pdf_doc.set_font("Arial", 'B', 12)
        pdf_doc.cell(0, 10, clean_pdf_text("DATOS DEL CLIENTE"), 1, 1, 'C')
        pdf_doc.set_font("Arial", '', 10)
        
        for k, v in st.session_state.datos_usuario.items():
            pdf_doc.cell(40, 8, f"{clean_pdf_text(k)}:", 0, 0)
            pdf_doc.cell(0, 8, f"{clean_pdf_text(v)}", 0, 1)
        
        pdf_doc.ln(5)
        pdf_doc.cell(0, 10, f"Nivel: {nivel_final}", 0, 1)
        pdf_doc.cell(0, 10, f"Presupuesto: {clean_pdf_text(presu_valor)}", 0, 1)
        
        pdf_doc.ln(5)
        pdf_doc.set_font("Arial", 'B', 10)
        pdf_doc.cell(0, 10, "RESPUESTAS DETALLADAS:", 0, 1)
        pdf_doc.set_font("Arial", '', 8)
        
        for idx, res_texto in enumerate(st.session_state.respuestas):
            pdf_doc.multi_cell(0, 5, f"P{idx+1}: {clean_pdf_text(res_texto)}")
            pdf_doc.ln(1)

        # Descarga de PDF
        st.download_button(
            label="📥 Descargar Reporte PDF",
            data=pdf_doc.output(dest='S').encode('latin-1'),
            file_name="Assessment_Ciberseguridad.pdf",
            mime="application/pdf"
        )

    if st.button("Realizar nueva evaluación"):
        st.session_state.clear()
        st.rerun()

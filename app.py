import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# Función para leer preguntas desde Word
def leer_preguntas_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                datos.append([celda.text.strip() for celda in fila.cells[:2]])
        return pd.DataFrame(datos[1:], columns=["Pregunta", "Opciones"])
    except Exception as e:
        st.error(f"Error cargando '01. Preguntas.docx': {e}")
        return pd.DataFrame()

# Clase para el Reporte PDF
class InformePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 15, 'Reporte de Madurez en Ciberseguridad', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# --- 2. INICIALIZACIÓN DEL ESTADO ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas': [],
        'datos_usuario': {},
        'enviado': False
    })

# --- ETAPA 1: REGISTRO DE DATOS ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    st.info("Complete sus datos para iniciar el diagnóstico profesional.")
    
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo*")
            cargo = st.text_input("Cargo*")
            empresa = st.text_input("Empresa*")
        with col2:
            email = st.text_input("Email Corporativo*")
            telefono = st.text_input("Teléfono / WhatsApp*")
        
        if st.form_submit_button("Comenzar Assessment"):
            if all([nombre, cargo, empresa, email, telefono]):
                st.session_state.datos_usuario = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, 
                    "Email": email, "Telefono": telefono
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Por favor, complete todos los campos obligatorios.")

# --- ETAPA 2: CUESTIONARIO DINÁMICO ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_preguntas_word("01. Preguntas.docx")
    
    if not df_p.empty:
        total = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        texto_q = fila['Pregunta']
        
        st.progress((st.session_state.paso + 1) / total)
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {total}")
        st.markdown(f"### {texto_q}")
        
        opciones = [o.strip() for o in fila['Opciones'].split('\n') if o.strip()]
        
        # Detección de Selección Múltiple
        keys_mult = ["seleccione las", "cuáles", "cuales", "indique las", "múltiple"]
        es_mult = any(k in texto_q.lower() for k in keys_mult)

        if es_mult:
            res = st.multiselect("Seleccione una o más opciones:", opciones, key=f"q_{st.session_state.paso}")
        else:
            res = st.radio("Seleccione una opción:", opciones, index=None, key=f"q_{st.session_state.paso}")

        if st.button("Siguiente"):
            if res:
                valor_final = ", ".join(res) if isinstance(res, list) else res
                st.session_state.respuestas.append(valor_final)
                
                if st.session_state.paso < total - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()
            else:
                st.warning("Seleccione una respuesta.")

# --- ETAPA 3: RESULTADOS, GOOGLE SHEETS Y PDF ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Evaluación Finalizada")
    
    # Cálculos
    si_count = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    try:
        presupuesto = st.session_state.respuestas[15] # Ajustar índice si la pregunta 16 varía
    except:
        presupuesto = "No especificado"

    st.metric("Nivel de Madurez", nivel)
    
    st.divider()
    st.subheader("¿Desea una asesoría personalizada?")
    quiere_contacto = st.radio("¿Quieres contactar a un ejecutivo?", ["SÍ", "NO"], index=1, horizontal=True)

    if not st.session_state.enviado:
        if st.button("Finalizar y Guardar Resultados"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                user = st.session_state.datos_usuario
                
                cols = ["Fecha", "Nombre", "Cargo", "Empresa", "Email", "Telefono", "Resultado", "Presupuesto", "Contacto_Ejecutivo"]
                
                nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": user["Nombre"], "Cargo": user["Cargo"], "Empresa": user["Empresa"],
                    "Email": user["Email"], "Telefono": user["Telefono"],
                    "Resultado": nivel, "Presupuesto": presupuesto, "Contacto_Ejecutivo": quiere_contacto
                }])

                # Lectura limpia (Antipisado)
                try:
                    historial = conn.read(spreadsheet=url, ttl=0).reindex(columns=cols)
                    final_df = pd.concat([historial.dropna(how='all'), nuevo], ignore_index=True)
                except:
                    final_df = nuevo

                conn.update(spreadsheet=url, data=final_df)
                st.session_state.enviado = True
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    
    else:
        st.success("Resultados registrados en el sistema.")
        
        # Generación de PDF
        pdf = InformePDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Datos del Cliente", 1, 1, 'C')
        pdf.set_font("Arial", '', 10)
        for k, v in st.session_state.datos_usuario.items():
            pdf.cell(40, 8, f"{k}:", 0, 0); pdf.cell(0, 8, f"{v}", 0, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Resultado: {nivel}", 0, 1)
        pdf.cell(0, 10, f"Presupuesto: {presupuesto}", 0, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, "Detalle de Respuestas:", 0, 1)
        pdf.set_font("Arial", '', 8)
        for i, r in enumerate(st.session_state.respuestas):
            pdf.multi_cell(0, 5, f"P{i+1}: {r}")
            pdf.ln(1)

        st.download_button(
            label="📥 Descargar Reporte PDF",
            data=bytes(pdf.output()),
            file_name=f"Reporte_{st.session_state.datos_usuario['Empresa']}.pdf",
            mime="application/pdf"
        )

    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()

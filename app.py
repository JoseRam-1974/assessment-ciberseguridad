import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# Función para leer el Word de preguntas
def leer_preguntas(file_path):
    try:
        doc = Document(file_path)
        data = []
        for table in doc.tables:
            for row in table.rows:
                data.append([cell.text.strip() for cell in row.cells[:2]])
        return pd.DataFrame(data[1:], columns=["Preguntas", "Alternativas"])
    except:
        return None

# 2. INICIALIZACIÓN DE ESTADO
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_usuario': [],
        'datos_contacto': {},
        'datos_enviados': False
    })

# 3. ETAPA 1: REGISTRO COMPLETO
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    st.info("Por favor, complete sus datos corporativos.")
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo*")
            cargo = st.text_input("Cargo*")
            empresa = st.text_input("Empresa*")
        with col2:
            email = st.text_input("Email Corporativo*")
            telefono = st.text_input("Teléfono / WhatsApp*")
        
        if st.form_submit_button("Comenzar Diagnóstico"):
            if nombre and cargo and empresa and email and telefono:
                st.session_state.datos_contacto = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, 
                    "Email": email, "Tel": telefono
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.error("Todos los campos marcados con * son obligatorios.")

# 4. ETAPA 2: PREGUNTAS DESDE EL WORD
elif st.session_state.etapa == 'preguntas':
    st.title("📝 Cuestionario de Madurez")
    df_p = leer_preguntas("01. Preguntas.docx")
    
    if df_p is not None and not df_p.empty:
        total_preguntas = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {total_preguntas}")
        st.write(f"### {fila['Preguntas']}")
        
        opciones = [o.strip() for o in fila['Alternativas'].split('\n') if o.strip()]
        res = st.radio("Seleccione una respuesta:", opciones, index=None)

        if st.button("Siguiente Pregunta"):
            if res:
                st.session_state.respuestas_usuario.append(res)
                if st.session_state.paso < total_preguntas - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'finalizado'
                    st.rerun()
            else:
                st.warning("Por favor, seleccione una opción.")
    else:
        st.error("No se pudo cargar el archivo '01. Preguntas.docx'. Verifique que el archivo esté en la carpeta del proyecto.")

# 5. ETAPA 3: RESULTADOS Y GUARDADO
elif st.session_state.etapa == 'finalizado':
    st.title("✅ Evaluación Finalizada")
    
    # Cálculo simple de madurez para el ejemplo
    positivas = sum(1 for r in st.session_state.respuestas_usuario if "SÍ" in r.upper() or "SI" in r.upper())
    nivel = "Avanzado" if positivas > 10 else "Intermedio" if positivas > 5 else "Inicial"
    
    st.metric("Su Nivel de Madurez es:", nivel)

    if not st.session_state.datos_enviados:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            info = st.session_state.datos_contacto
            
            # Preparamos la fila para Google Sheets
            nueva_fila = pd.DataFrame([{
                "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Nombre": info.get("Nombre"),
                "Cargo": info.get("Cargo"),
                "Empresa": info.get("Empresa"),
                "Email": info.get("Email"),
                "Telefono": info.get("Tel"),
                "Resultado": nivel
            }])
            
            # LEER Y ACTUALIZAR (Ajuste para evitar el error de "Sheet1 not found")
            # Esto leerá la primera pestaña disponible sin importar el nombre
            df_actual = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"])
            df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
            conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=df_final)
            
            st.session_state.datos_enviados = True
            st.balloons()
            st.success("Sus resultados han sido enviados al equipo de consultoría.")
        except Exception as e:
            st.error(f"Error de conexión: {e}")

    if st.button("Reiniciar Test"):
        st.session_state.clear()
        st.rerun()

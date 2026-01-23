import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Assessment Ciberseguridad", layout="wide")

def leer_preguntas_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                # Capturamos Pregunta y Alternativas
                datos.append([celda.text.strip() for celda in fila.cells[:2]])
        return pd.DataFrame(datos[1:], columns=["Pregunta", "Opciones"])
    except Exception as e:
        st.error(f"Error cargando el archivo de preguntas: {e}")
        return pd.DataFrame()

# --- 2. ESTADO DE LA SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas': [],
        'datos_usuario': {},
        'enviado': False
    })

st.title("🛡️ Assessment Digital de Ciberseguridad")

# --- ETAPA 1: REGISTRO COMPLETO ---
if st.session_state.etapa == 'registro':
    st.subheader("Información de Contacto")
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo*")
            cargo = st.text_input("Cargo*")
            empresa = st.text_input("Empresa*")
        with c2:
            email = st.text_input("Email Corporativo*")
            telefono = st.text_input("Teléfono / WhatsApp*")
        
        if st.form_submit_button("Siguiente"):
            if nombre and cargo and empresa and email and telefono:
                st.session_state.datos_usuario = {
                    "Nombre": nombre, "Cargo": cargo, "Empresa": empresa, 
                    "Email": email, "Telefono": telefono
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Por favor, complete todos los campos obligatorios (*).")

# --- ETAPA 2: CUESTIONARIO DINÁMICO ---
elif st.session_state.etapa == 'preguntas':
    df_preguntas = leer_preguntas_word("01. Preguntas.docx")
    
    if not df_preguntas.empty:
        total = len(df_preguntas)
        pregunta_actual = df_preguntas.iloc[st.session_state.paso]
        
        st.write(f"**Pregunta {st.session_state.paso + 1} de {total}**")
        st.markdown(f"### {pregunta_actual['Pregunta']}")
        
        opciones = [opt.strip() for opt in pregunta_actual['Opciones'].split('\n') if opt.strip()]
        seleccion = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("Continuar"):
            if seleccion:
                st.session_state.respuestas.append(seleccion)
                if st.session_state.paso < total - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()
            else:
                st.warning("Debe seleccionar una respuesta para continuar.")
    else:
        st.error("No se encontraron preguntas en el archivo '01. Preguntas.docx'.")

# --- ETAPA 3: FINALIZADO Y GUARDADO ---
elif st.session_state.etapa == 'resultado':
    st.success("✅ Evaluación finalizada correctamente.")
    
    # 1. Lógica de madurez y presupuesto
    si_count = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    try:
        dato_presupuesto = st.session_state.respuestas[15]
    except:
        dato_presupuesto = "No respondido"

    st.metric("Nivel de Madurez Detectado", nivel)
    st.divider()

    # 2. NUEVA CASILLA DE CONTACTO
    st.subheader("¿Deseas profundizar en tus resultados?")
    quiere_contacto = st.radio(
        "¿Quieres contactar a uno de nuestros ejecutivos para recibir una asesoría personalizada?",
        ["SÍ", "NO"],
        index=1, # Por defecto en "NO"
        horizontal=True
    )

    # 3. BOTÓN PARA PROCESAR ENVÍO
    if not st.session_state.enviado:
        if st.button("Finalizar y Registrar Resultados"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                usuario = st.session_state.datos_usuario
                url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
                
                # Crear el registro con TODA la información
                nuevo_registro = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": usuario.get("Nombre", "N/A"),
                    "Cargo": usuario.get("Cargo", "N/A"),
                    "Empresa": usuario.get("Empresa", "N/A"),
                    "Email": usuario.get("Email", "N/A"),
                    "Telefono": usuario.get("Telefono", "N/A"),
                    "Resultado": nivel,
                    "Presupuesto": dato_presupuesto,
                    "Contacto_Ejecutivo": quiere_contacto # <-- Nueva columna
                }])
                
                # Leer historial para hacer el Append (no pisar datos)
                try:
                    df_existente = conn.read(spreadsheet=url_hoja)
                    df_existente = df_existente.dropna(how='all')
                except:
                    df_existente = pd.DataFrame(columns=nuevo_registro.columns)
                
                # Concatenar y subir
                df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                conn.update(spreadsheet=url_hoja, data=df_final)
                
                st.session_state.enviado = True
                st.balloons()
                st.success("¡Datos guardados! Si seleccionaste 'SÍ', un ejecutivo te contactará pronto.")
                
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    else:
        st.info("Tus resultados ya han sido registrados en nuestro sistema.")

    if st.button("Reiniciar Test"):
        st.session_state.clear()
        st.rerun()

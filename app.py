import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# --- 1. CONFIGURACIÓN ESTRUCTURAL ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

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

def clean_t(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":"","ü":"u"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'INFORME ESTRATEGICO DE CIBERSEGURIDAD', 0, 1, 'C')
        self.ln(5)

# --- 2. ESTADO DE LA SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas': [],
        'datos_usuario': {},
        'enviado': False
    })

# --- ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    with st.form("form_reg"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Completo*")
            car = st.text_input("Cargo*")
            emp = st.text_input("Empresa*")
        with col2:
            ema = st.text_input("Email*")
            tel = st.text_input("Telefono*")
        
        if st.form_submit_button("Iniciar Assessment"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre":nom,"Cargo":car,"Empresa":emp,"Email":ema,"Telefono":tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Por favor rellene todos los campos.")

# --- ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        pregunta_texto = fila['Clave']
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {total}")
        st.write(f"### {pregunta_texto}")
        
        # Filtro sugerido: Palabra "Múltiple"
        es_m = "múltiple" in pregunta_texto.lower() or "multiple" in pregunta_texto.lower()
        
        if es_m:
            ans = st.multiselect("Seleccione las opciones que correspondan:", opciones)
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("Continuar"):
            if ans:
                st.session_state.respuestas.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < total - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()
            else:
                st.error("Debe responder para avanzar.")

# --- ETAPA 3: RESULTADOS Y CONSULTORÍA ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Analisis de Resultados")
    
    # Calculo de madurez
    si_count = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    try: presupuesto = st.session_state.respuestas[15]
    except: presupuesto = "N/A"

    st.metric("Nivel de Madurez Detectado", nivel)
    cont = st.radio("¿Desea que un consultor lo contacte?", ["SÍ", "NO"], index=1, horizontal=True)

    if not st.session_state.enviado:
        if st.button("Guardar y Generar Plan de Accion"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                cols = ["Fecha","Nombre","Cargo","Empresa","Email","Telefono","Resultado","Presupuesto","Contacto"]
                
                nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre":u["Nombre"],"Cargo":u["Cargo"],"Empresa":u["Empresa"],"Email":u["Email"],
                    "Telefono":u["Telefono"],"Resultado":nivel,"Presupuesto":presupuesto,"Contacto":cont
                }])

                try:
                    hist = conn.read(spreadsheet=url, ttl=0).reindex(columns=cols)
                    final = pd.concat([hist.dropna(how='all'), nuevo], ignore_index=True)
                except:
                    final = nuevo

                conn.update(spreadsheet=url, data=final)
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error de conexion: {e}")
    else:
        st.success("Analisis registrado. Descargue sus recomendaciones personalizadas.")
        
        # --- GENERACION PDF DE RECOMENDACIONES ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        # Seccion Cliente
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN DE SITUACION", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        pdf.ln(2)
        u = st.session_state.datos_usuario
        pdf.cell(0, 7, clean_t(f"Empresa: {u['Empresa']} | Responsable: {u['Nombre']}"), 0, 1)
        pdf.cell(0, 7, f"Nivel de Madurez Detectado: {nivel}", 0, 1)
        pdf.ln(5)

        # Seccion Recomendaciones
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. RECOMENDACIONES TECNICAS", 1, 1, 'L')
        pdf.ln(4)
        pdf.set_font("Arial", '', 9)

        for resp_usuario in st.session_state.respuestas:
            individuales = [s.strip() for s in resp_usuario.split(",")]
            for s in individuales:
                # Buscamos la recomendacion en el archivo 02. Respuestas
                match = df_rec[df_rec['Clave'].str.contains(s, na=False, case=False)]
                if not match.empty:
                    pdf.set_font("Arial", 'B', 9)
                    pdf.multi_cell(0, 6, clean_t(f"Situacion detectada: {s}"))
                    pdf.set_font("Arial", '', 9)
                    pdf.multi_cell(0, 6, clean_t(f"ACCION SUGERIDA: {match.iloc[0]['Contenido']}"))
                    pdf.ln(3)

        st.download_button(
            label="📥 Descargar Plan de Accion (PDF)",
            data=pdf.output(dest='S').encode('latin-1'),
            file_name=f"Plan_CS_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()

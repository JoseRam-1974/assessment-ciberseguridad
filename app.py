import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# --- CONFIGURACIÓN ---
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
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":"","ü":"u","(":"[",")":"]"}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'INFORME DE RECOMENDACIONES ESTRATEGICAS', 0, 1, 'C')
        self.ln(5)

# --- ESTADO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({'etapa':'registro','paso':0,'respuestas':[],'datos_usuario':{},'enviado':False})

# --- ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    with st.form("form_reg"):
        c1, c2 = st.columns(2)
        with c1:
            nom, car, emp = st.text_input("Nombre*"), st.text_input("Cargo*"), st.text_input("Empresa*")
        with c2:
            ema, tel = st.text_input("Email*"), st.text_input("Telefono*")
        if st.form_submit_button("Iniciar Assessment"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre":nom,"Cargo":car,"Empresa":emp,"Email":ema,"Telefono":tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()

# --- ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        fila = df_p.iloc[st.session_state.paso]
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {len(df_p)}")
        st.write(f"### {fila['Clave']}")
        opts = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        
        es_m = "múltiple" in fila['Clave'].lower() or "multiple" in fila['Clave'].lower()
        ans = st.multiselect("Seleccione:", opts) if es_m else st.radio("Opcion:", opts, index=None)

        if st.button("Continuar"):
            if ans:
                st.session_state.respuestas.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- ETAPA 3: RESULTADOS ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Finalizado")
    si_c = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    nivel = "Avanzado" if si_c > 12 else "Intermedio" if si_c > 6 else "Inicial"
    st.metric("Nivel de Madurez", nivel)
    
    cont = st.radio("¿Desea asesoría personalizada?", ["SÍ", "NO"], index=1, horizontal=True)

    if not st.session_state.enviado:
        if st.button("Guardar y Generar Informe"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                cols = ["Fecha","Nombre","Cargo","Empresa","Email","Telefono","Resultado","Presupuesto","Contacto"]
                nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre":u["Nombre"],"Cargo":u["Cargo"],"Empresa":u["Empresa"],"Email":u["Email"],
                    "Telefono":u["Telefono"],"Resultado":nivel,"Presupuesto":"Ver PDF","Contacto":cont
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
                st.error(f"Error de conexión: {e}")
    else:
        st.success("Resultados registrados. Generando reporte...")
        
        # CARGAR RECOMENDACIONES
        df_rec = leer_word("02. Respuestas.docx")
        
        pdf = PDF()
        pdf.add_page()
        
        # Sección 1
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. SITUACION ACTUAL", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_t(f"Empresa: {u['Empresa']} | Nivel detectado: {nivel}"), 0, 1)
        pdf.ln(5)

        # Sección 2
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. PLAN DE ACCION Y RECOMENDACIONES", 1, 1, 'L')
        pdf.ln(4)

        encontrados = 0
        for r_u in st.session_state.respuestas:
            indiv = [s.strip() for s in r_u.split(",")]
            for s in indiv:
                # BÚSQUEDA FLEXIBLE: Quitamos espacios y pasamos a minúsculas para comparar
                s_clean = s.strip().lower()
                # Buscamos en el dataframe de recomendaciones
                match = df_rec[df_rec['Clave'].str.strip().str.lower() == s_clean]
                
                if not match.empty:
                    encontrados += 1
                    pdf.set_font("Arial", 'B', 9)
                    pdf.multi_cell(0, 6, clean_t(f"Punto detectado: {s}"))
                    pdf.set_font("Arial", '', 9)
                    pdf.multi_cell(0, 6, clean_t(f"RECOMENDACION: {match.iloc[0]['Contenido']}"))
                    pdf.ln(3)
        
        # Si no encontró nada, ponemos un aviso para que no salga en blanco
        if encontrados == 0:
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 10, "No se encontraron recomendaciones especificas para las respuestas seleccionadas. Por favor, verifique que los textos en '01. Preguntas' y '02. Respuestas' coincidan exactamente.")

        st.download_button(
            label="📥 Descargar Reporte de Recomendaciones",
            data=pdf.output(dest='S').encode('latin-1'),
            file_name=f"Recomendaciones_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()

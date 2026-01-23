import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# --- CONFIGURACION ---
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

# Funcion para limpiar texto para el PDF (Elimina tildes y caracteres especiales)
def clean_t(txt):
    r = (("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n"),("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U"),("Ñ","N"),("¿",""),("¡",""))
    t = str(txt)
    for a, b in r:
        t = t.replace(a, b)
    return t

class InformePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'REPORTE DE MADUREZ DIGITAL CS', 0, 1, 'C')
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
    st.title("🛡️ Diagnostico de Madurez CS")
    with st.form("reg"):
        c1, c2 = st.columns(2)
        with c1:
            n = st.text_input("Nombre*")
            c = st.text_input("Cargo*")
            e = st.text_input("Empresa*")
        with c2:
            em = st.text_input("Email*")
            t = st.text_input("Telefono*")
        if st.form_submit_button("Siguiente"):
            if all([n, c, e, em, t]):
                st.session_state.datos_usuario = {"Nombre":n,"Cargo":c,"Empresa":e,"Email":em,"Telefono":t}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Complete los campos")

# --- ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df = leer_preguntas_word("01. Preguntas.docx")
    if not df.empty:
        f = df.iloc[st.session_state.paso]
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {len(df)}")
        st.write(f"### {f['Pregunta']}")
        opts = [o.strip() for o in f['Opciones'].split('\n') if o.strip()]
        
        # Seleccion multiple o simple
        es_m = any(k in f['Pregunta'].lower() for k in ["seleccione","cuales","indique"])
        res = st.multiselect("Opciones:", opts) if es_m else st.radio("Opcion:", opts, index=None)

        if st.button("Siguiente"):
            if res:
                st.session_state.respuestas.append(", ".join(res) if isinstance(res, list) else res)
                if st.session_state.paso < len(df) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- ETAPA 3: RESULTADOS ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Assessment completado")
    si = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    niv = "Avanzado" if si > 12 else "Intermedio" if si > 6 else "Inicial"
    
    try: presu = st.session_state.respuestas[15]
    except: presu = "N/A"

    st.metric("Nivel Detectado", niv)
    cont = st.radio("¿Desea contacto de un ejecutivo?", ["SI", "NO"], index=1, horizontal=True)

    if not st.session_state.enviado:
        if st.button("Finalizar y Guardar"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                col_names = ["Fecha","Nombre","Cargo","Empresa","Email","Telefono","Resultado","Presupuesto","Contacto"]
                
                nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre":u["Nombre"],"Cargo":u["Cargo"],"Empresa":u["Empresa"],"Email":u["Email"],
                    "Telefono":u["Telefono"],"Resultado":niv,"Presupuesto":presu,"Contacto":cont
                }])

                try:
                    hist = conn.read(spreadsheet=url, ttl=0).reindex(columns=col_names)
                    final = pd.concat([hist.dropna(how='all'), nuevo], ignore_index=True)
                except:
                    final = nuevo

                conn.update(spreadsheet=url, data=final)
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    else:
        st.success("Datos registrados exitosamente.")
        
        # Generacion de PDF
        pdf = InformePDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "DATOS DEL CLIENTE", 1, 1, 'C')
        pdf.set_font("Arial", '', 10)
        for k, v in st.session_state.datos_usuario.items():
            pdf.cell(40, 8, f"{clean_t(k)}:", 0, 0)
            pdf.cell(0, 8, f"{clean_t(v)}", 0, 1)
        
        pdf.ln(5)
        pdf.cell(0, 10, f"Nivel: {niv}", 0, 1)
        pdf.cell(0, 10, f"Presupuesto: {clean_t(presu)}", 0, 1)
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, "RESPUESTAS:", 0, 1)
        pdf.set_font("Arial", '', 8)
        for i, r in enumerate(st.session_state.respuestas):
            pdf.multi_cell(0, 5, f"P{i+1}: {clean_t(r)}")
            pdf.ln(1)

        st.download_button(
            label="Descargar PDF",
            data=pdf.output(dest='S').encode('latin-1', errors='replace'),
            file_name="Reporte_Madurez.pdf",
            mime="application/pdf"
        )

    if st.button("Realizar nuevo test"):
        st.session_state.clear()
        st.rerun()


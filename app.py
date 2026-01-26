import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

def leer_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                celdas = [c.text.strip() for c in fila.cells]
                if len(celdas) >= 2:
                    datos.append([celdas[0], celdas[1]])
        return pd.DataFrame(datos[1:], columns=["Clave", "Contenido"])
    except:
        return pd.DataFrame()

def normalizar(txt):
    if not txt: return ""
    t = str(txt).lower()
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    for a, b in rep.items(): t = t.replace(a, b)
    # Limpieza para búsqueda flexible
    t = re.sub(r'[^a-z0-9]', '', t)
    return t

def clean_pdf(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":""}
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
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_texto': [],
        'preguntas_texto': [],
        'datos_usuario': {},
        'enviado': False
    })

# --- ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    with st.form("reg"):
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
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < len(df_p) - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- ETAPA 3: RESULTADOS Y GENERACIÓN DE REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Evaluación Finalizada")
    
    # 1. Detección de Presupuesto para GSheets
    pres_val = "N/A"
    for p, r in zip(st.session_state.preguntas_texto, st.session_state.respuestas_texto):
        if "presupuesto" in p.lower() or "inversion" in p.lower():
            pres_val = r
            break

    si_c = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel = "Avanzado" if si_c > 12 else "Intermedio" if si_c > 6 else "Inicial"
    st.metric("Nivel de Madurez Detectado", nivel)

    st.write("---")
    st.subheader("¿Deseas profundizar en tus resultados?")
    contacto = st.radio("¿Quieres contactar a un ejecutivo para una asesoría personalizada?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("Finalizar y Registrar Resultados"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                
                data = {
                    "Fecha": [datetime.datetime.now().strftime("%d/%m/%Y %H:%M")],
                    "Nombre": [u["Nombre"]], "Cargo": [u["Cargo"]], "Empresa": [u["Empresa"]],
                    "Email": [u["Email"]], "Telefono": [u["Telefono"]], "Resultado": [nivel],
                    "Presupuesto": [pres_val], "Contacto": [contacto], "App": ["V-Final-Lunes"]
                }
                df_nuevo = pd.DataFrame(data)
                hist = conn.read(spreadsheet=url, ttl=0)
                conn.update(spreadsheet=url, data=pd.concat([hist, df_nuevo], ignore_index=True))
                
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    else:
        st.success("¡Datos registrados! Ya puede descargar su informe técnico.")
        
        # --- LÓGICA DE PDF PULIDA (12.b, 13.b, 14.a, etc.) ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN EJECUTIVO", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_pdf(f"Empresa: {u['Empresa']} | Nivel: {nivel}"), 0, 1)
        pdf.cell(0, 7, clean_pdf(f"Presupuesto: {pres_val}"), 0, 1)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. ANALISIS Y RECOMENDACIONES TECNICAS", 1, 1, 'L')
        pdf.ln(4)

        for i in range(len(st.session_state.preguntas_texto)):
            preg = st.session_state.preguntas_texto[i]
            resp = st.session_state.respuestas_texto[i]
            
            # Encabezados en el PDF
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, clean_pdf(f"Pregunta {i+1}: {preg}"))
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, clean_pdf(f"Hallazgo: {resp}"))

            # LÓGICA DE MATCH POR ID EXACTO
            recom_encontrada = ""
            # Separamos por si hay selección múltiple
            sub_respuestas = [sr.strip() for sr in resp.split(",")]
            
            for sr in sub_respuestas:
                # Extraer ID (ej: "12.b")
                match_id = re.match(r'^(\d+\.[a-z]?)', sr.lower())
                if match_id:
                    id_busqueda = match_id.group(1).strip()
                    
                    for _, row in df_rec.iterrows():
                        clave_word = str(row['Clave']).lower().strip()
                        # Si la clave del Word empieza exactamente con el ID de la respuesta
                        if clave_word.startswith(id_busqueda):
                            recom_encontrada = row['Contenido']
                            break
                if recom_encontrada: break

            if recom_encontrada:
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(0, 5, clean_pdf(f"RECOMENDACION: {recom_encontrada}"))
            else:
                pdf.set_font("Arial", 'I', 8)
                pdf.set_text_color(150, 150, 150)
                pdf.cell(0, 5, clean_pdf("(Dato informativo para analisis ejecutivo)"), 0, 1)
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(4)

        st.download_button(
            label="📥 DESCARGAR INFORME TECNICO PDF",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Reporte_Cyber_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("Reiniciar Assessment"):
        st.session_state.clear()
        st.rerun()

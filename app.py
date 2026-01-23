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
    t = re.sub(r'[^a-z0-9 ]', '', t)
    return t.strip()

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
        if st.form_submit_button("Siguiente"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre":nom,"Cargo":car,"Empresa":emp,"Email":ema,"Telefono":tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()

# --- ETAPA 2: PREGUNTAS ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total_p = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        pregunta_actual = fila['Clave']
        
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {total_p}")
        st.write(f"### {pregunta_actual}")
        
        opts = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        es_m = "múltiple" in pregunta_actual.lower() or "multiple" in pregunta_actual.lower()
        ans = st.multiselect("Seleccione:", opts) if es_m else st.radio("Opcion:", opts, index=None)

        if st.button("Continuar"):
            if ans:
                st.session_state.preguntas_texto.append(pregunta_actual)
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- ETAPA 3: RESULTADOS Y CONTACTO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Evaluación Finalizada")
    
    # 1. Identificar el presupuesto de las respuestas guardadas
    # Buscamos la respuesta a la pregunta que contenga la palabra "presupuesto" o "inversión"
    presupuesto_detectado = "No especificado"
    for preg, resp in zip(st.session_state.preguntas_texto, st.session_state.respuestas_texto):
        if "presupuesto" in preg.lower() or "inversion" in preg.lower():
            presupuesto_detectado = resp
            break

    si_c = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel = "Avanzado" if si_c > 12 else "Intermedio" if si_c > 6 else "Inicial"
    st.metric("Nivel de Madurez Detectado", nivel)

    st.write("---")
    st.subheader("¿Deseas profundizar en tus resultados?")
    contacto = st.radio("¿Quieres contactar a uno de nuestros ejecutivos para una asesoría personalizada?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("Finalizar y Registrar"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                
                # Preparamos los datos incluyendo el Presupuesto real detectado
                data = {
                    "Fecha": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
                    "Nombre": [u["Nombre"]], 
                    "Cargo": [u["Cargo"]], 
                    "Empresa": [u["Empresa"]],
                    "Email": [u["Email"]], 
                    "Telefono": [u["Telefono"]], 
                    "Resultado": [nivel],
                    "Presupuesto": [presupuesto_detectado], # <--- AQUÍ SE ENVÍA EL DATO REAL
                    "Contacto": [contacto], 
                    "App": ["V5-Final"]
                }
                df_nuevo = pd.DataFrame(data)
                hist = conn.read(spreadsheet=url, ttl=0)
                final = pd.concat([hist, df_nuevo], ignore_index=True)
                conn.update(spreadsheet=url, data=final)
                
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    else:
        st.success("¡Datos registrados con éxito!")
        
        # --- GENERACIÓN DEL PDF ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        # Datos Cliente
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN EJECUTIVO", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_pdf(f"Cliente: {u['Nombre']} | Empresa: {u['Empresa']}"), 0, 1)
        pdf.cell(0, 7, clean_pdf(f"Nivel de Madurez Detectado: {nivel}"), 0, 1)
        pdf.cell(0, 7, clean_pdf(f"Presupuesto Estimado: {presupuesto_detectado}"), 0, 1)
        pdf.ln(5)

        # Detalle de Recomendaciones
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. ANALISIS Y RECOMENDACIONES", 1, 1, 'L')
        pdf.ln(4)

        for i in range(len(st.session_state.preguntas_texto)):
            pregunta = st.session_state.preguntas_texto[i]
            respuesta = st.session_state.respuestas_texto[i]
            partes_ans = [p.strip() for p in respuesta.split(",")]
            for p in partes_ans:
                p_norm = normalizar(p)
                if not p_norm: continue
                for _, row in df_rec.iterrows():
                    clave_word_norm = normalizar(row['Clave'])
                    if p_norm in clave_word_norm or clave_word_norm in p_norm:
                        pdf.set_font("Arial", 'B', 9)
                        pdf.set_text_color(100, 100, 100)
                        pdf.multi_cell(0, 5, clean_pdf(f"Pregunta: {pregunta}"))
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font("Arial", 'I', 9)
                        pdf.multi_cell(0, 5, clean_pdf(f"Hallazgo: {p}"))
                        pdf.set_font("Arial", '', 9)
                        pdf.multi_cell(0, 5, clean_pdf(f"RECOMENDACION: {row['Contenido']}"))
                        pdf.ln(4)
                        break

        st.download_button(
            label="📥 DESCARGAR INFORME PDF COMPLETO", 
            data=pdf.output(dest='S').encode('latin-1', 'replace'), 
            file_name=f"Reporte_CS_{u['Empresa']}.pdf", 
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("Realizar nuevo Assessment"):
        st.session_state.clear()
        st.rerun()

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

# --- ETAPA 3: RESULTADOS Y GENERACIÓN DE REPORTE TÉCNICO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Evaluación Finalizada")
    
    # 1. Obtener presupuesto para registro
    pres_val = "N/A"
    for p, r in zip(st.session_state.preguntas_texto, st.session_state.respuestas_texto):
        if any(kw in p.lower() for kw in ["presupuesto", "inversion"]):
            pres_val = r
            break

    si_count = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel_detectado = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    st.metric("Nivel de Madurez", nivel_detectado)

    if not st.session_state.enviado:
        if st.button("Finalizar y Registrar"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                df_nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Empresa": u["Empresa"], "Email": u["Email"], "Nivel": nivel_detectado,
                    "Presupuesto": pres_val, "Version": "Blindada-V7"
                }])
                hist = conn.read(spreadsheet=url, ttl=0)
                conn.update(spreadsheet=url, data=pd.concat([hist, df_nuevo], ignore_index=True))
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error de guardado: {e}")
    else:
        st.success("Resultados guardados correctamente.")
        
        # --- GENERACIÓN DEL PDF CON BÚSQUEDA QUIRÚRGICA ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        # Cabecera de Resumen
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN EJECUTIVO", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_pdf(f"Empresa: {u['Empresa']} | Nivel de Madurez: {nivel_detectado}"), 0, 1)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. RECOMENDACIONES TECNICAS PERSONALIZADAS", 1, 1, 'L')
        pdf.ln(4)

        for i in range(len(st.session_state.preguntas_texto)):
            preg = st.session_state.preguntas_texto[i]
            resp = st.session_state.respuestas_texto[i]
            
            # Formato de Pregunta/Respuesta
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(70, 70, 70)
            pdf.multi_cell(0, 5, clean_pdf(f"Pregunta {i+1}: {preg}"))
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, clean_pdf(f"Hallazgo: {resp}"))

            # --- LÓGICA DE MATCH QUIRÚRGICO ---
            recoms_validas = []
            # Dividir si hay selección múltiple (coma o " y ")
            partes_resp = re.split(r',| y ', resp)
            
            for parte in partes_resp:
                parte = parte.strip().lower()
                # Extraemos el ID literal (ej: "15.b")
                # Expresión regular para capturar "Número.Letra" al inicio
                match_id = re.match(r'^(\d+\.[a-z])', parte)
                
                if match_id:
                    id_a_buscar = match_id.group(1) # Esto será "15.b" o "5.a", etc.
                    
                    for _, row in df_rec.iterrows():
                        clave_word = str(row['Clave']).lower().strip()
                        
                        # MATCH EXACTO: La clave del Word debe empezar con el ID exacto
                        # Esto evita que '15.b' haga match con '5.b'
                        if clave_word.startswith(id_a_buscar):
                            if row['Contenido'] not in recoms_validas:
                                recoms_validas.append(row['Contenido'])
            
            # Imprimir Recomendaciones
            if recoms_validas:
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(0, 60, 120) # Azul técnico
                for r_text in recoms_validas:
                    pdf.multi_cell(0, 5, clean_pdf(f"RECOMENDACION: {r_text}"))
            else:
                pdf.set_font("Arial", 'I', 8)
                pdf.set_text_color(160, 160, 160)
                pdf.cell(0, 5, clean_pdf("(Dato informativo para analisis ejecutivo)"), 0, 1)
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(4)

        st.download_button(
            label="📥 Descargar Informe Completo (PDF)",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Reporte_Cyber_{u['Empresa']}.pdf",
            mime="application/pdf"
        )

    if st.button("Reiniciar Assessment"):
        st.session_state.clear()
        st.rerun()

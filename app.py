import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re

# --- 1. CONFIGURACIÓN E IDIOMA ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# Función para leer el catálogo de recomendaciones desde Word
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
    except Exception as e:
        st.error(f"Error al leer {ruta}: {e}")
        return pd.DataFrame()

# Función para limpiar texto para el PDF (evita errores de codificación)
def clean_pdf(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":"","(":"",")":""}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'INFORME DE RECOMENDACIONES ESTRATEGICAS', 0, 1, 'C')
        self.ln(5)

# --- 2. ESTADO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro',
        'paso': 0,
        'respuestas_texto': [],
        'preguntas_texto': [],
        'datos_usuario': {},
        'enviado': False
    })

# --- 3. ETAPA 1: REGISTRO DE USUARIO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    st.write("Complete sus datos para iniciar el diagnóstico de ciberseguridad.")
    
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo*")
            car = st.text_input("Cargo*")
            emp = st.text_input("Empresa*")
        with c2:
            ema = st.text_input("Email Corporativo*")
            tel = st.text_input("Teléfono de Contacto*")
        
        if st.form_submit_button("Iniciar Assessment"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {
                    "Nombre": nom, "Cargo": car, "Empresa": emp, 
                    "Email": ema, "Telefono": tel
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Por favor, complete todos los campos obligatorios.")

# --- 4. ETAPA 2: ASSESSMENT (PREGUNTAS) ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total_p = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {total_p}")
        st.markdown(f"### {fila['Clave']}")
        
        opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        es_multiple = "múltiple" in fila['Clave'].lower() or "multiple" in fila['Clave'].lower()
        
        if es_multiple:
            ans = st.multiselect("Seleccione todas las que correspondan:", opciones)
        else:
            ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("Siguiente Pregunta"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()
            else:
                st.info("Debe seleccionar al menos una respuesta.")

# --- 5. ETAPA 3: RESULTADOS, CONTACTO Y REGISTRO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Diagnóstico Finalizado")
    
    # Cálculo de Nivel y Presupuesto
    pres_val = "N/A"
    for p, r in zip(st.session_state.preguntas_texto, st.session_state.respuestas_texto):
        if any(kw in p.lower() for kw in ["presupuesto", "inversion"]):
            pres_val = r
            break

    si_count = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    st.metric("Su Nivel de Madurez Detectado", nivel)
    st.write("---")
    
    st.subheader("🎯 ¿Desea una asesoría técnica?")
    opcion_contacto = st.radio("¿Deseas que un ejecutivo(a) senior se contacte contigo para revisar estos puntos?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("Finalizar y Registrar Resultados"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                
                df_nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": u["Nombre"],
                    "Cargo": u["Cargo"],
                    "Empresa": u["Empresa"],
                    "Email": u["Email"],
                    "Telefono": u["Telefono"],
                    "Resultado": nivel,
                    "Presupuesto": pres_val,
                    "Contacto": opcion_contacto,
                    "Version": "V-Final-Integral"
                }])
                
                hist = conn.read(spreadsheet=url, ttl=0)
                conn.update(spreadsheet=url, data=pd.concat([hist, df_nuevo], ignore_index=True))
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar en base de datos: {e}")
    else:
        st.success("Resultados registrados. Ya puede descargar su informe técnico detallado.")
        
        # --- GENERACIÓN DEL PDF CON INTELIGENCIA COMBINADA ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        # Resumen Ejecutivo
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN EJECUTIVO", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_pdf(f"Empresa: {u['Empresa']} | Cargo: {u['Cargo']}"), 0, 1)
        pdf.cell(0, 7, clean_pdf(f"Nivel de Madurez: {nivel} | Solicitud Contacto: {opcion_contacto}"), 0, 1)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. ANALISIS Y RECOMENDACIONES DETALLADAS", 1, 1, 'L')
        pdf.ln(4)

        for i in range(len(st.session_state.preguntas_texto)):
            preg = st.session_state.preguntas_texto[i]
            resp = st.session_state.respuestas_texto[i]
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, clean_pdf(f"Pregunta {i+1}: {preg}"))
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 5, clean_pdf(f"Hallazgo: {resp}"))

            # Lógica de Inteligencia de Combinación (Evita 5.b vs 15.b)
            recomendacion_final = ""
            ids_usuario = re.findall(r'(\d+\.[a-z])', resp.lower())
            ids_usuario = sorted(list(set(ids_usuario)))

            if ids_usuario:
                # PASO A: Combinación Exacta (ej: "5.a y 5.c")
                id_combinado = " y ".join(ids_usuario)
                for _, row in df_rec.iterrows():
                    clave_word = str(row['Clave']).lower().strip()
                    if clave_word == id_combinado:
                        recomendacion_final = row['Contenido']
                        break
                
                # PASO B: Si no hay combinación, buscar el ID individual
                if not recomendacion_final:
                    for id_u in ids_usuario:
                        for _, row in df_rec.iterrows():
                            clave_word = str(row['Clave']).lower().strip()
                            if clave_word == id_u:
                                recomendacion_final = row['Contenido']
                                break
                        if recomendacion_final: break

            if recomendacion_final:
                pdf.set_font("Arial", '', 9)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(0, 5, clean_pdf(f"RECOMENDACION: {recomendacion_final}"))
            else:
                pdf.set_font("Arial", 'I', 8)
                pdf.set_text_color(150, 150, 150)
                pdf.cell(0, 5, clean_pdf("(Dato para analisis de seguimiento ejecutivo)"), 0, 1)
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(4)

        st.download_button(
            label="📥 DESCARGAR INFORME TÉCNICO PDF",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Reporte_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("Reiniciar Evaluación"):
        st.session_state.clear()
        st.rerun()


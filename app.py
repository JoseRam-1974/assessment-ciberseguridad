import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re

# --- 1. CONFIGURACIÓN E IDIOMA ---
st.set_page_config(page_title="Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# Función para leer el catálogo desde Word
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

# Función para limpiar texto para el PDF (evita errores de caracteres especiales)
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

# --- 3. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nombre Completo*")
            car = st.text_input("Cargo*")
            emp = st.text_input("Empresa*")
        with c2:
            ema = st.text_input("Email Corporativo*")
            tel = st.text_input("Telefono de Contacto*")
        
        if st.form_submit_button("Iniciar Assessment"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {
                    "Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel
                }
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Complete todos los campos obligatorios.")

# --- 4. ETAPA 2: ASSESSMENT ---
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
            ans = st.multiselect("Seleccione las que correspondan:", opciones)
        else:
            ans = st.radio("Seleccione una:", opciones, index=None)

        if st.button("Siguiente"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 5. ETAPA 3: RESULTADOS Y REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Analisis Finalizado")
    
    # Calculo de Nivel y Presupuesto
    pres_val = "No declarado"
    for p, r in zip(st.session_state.preguntas_texto, st.session_state.respuestas_texto):
        if any(kw in p.lower() for kw in ["presupuesto", "inversion"]):
            pres_val = r
            break

    si_count = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    st.metric("Nivel de Madurez Detectado", nivel)
    st.write("---")
    
    st.subheader("🎯 Proximos Pasos")
    opcion_contacto = st.radio("¿Deseas que un ejecutivo(a) senior se contacte contigo para revisar el plan de accion?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("Finalizar y Registrar en Base de Datos"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                
                df_nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": u["Nombre"], "Cargo": u["Cargo"], "Empresa": u["Empresa"],
                    "Email": u["Email"], "Telefono": u["Telefono"], "Resultado": nivel,
                    "Presupuesto": pres_val, "Contacto": opcion_contacto,
                    "Version": "V8-Final-Clean"
                }])
                
                hist = conn.read(spreadsheet=url, ttl=0)
                conn.update(spreadsheet=url, data=pd.concat([hist, df_nuevo], ignore_index=True))
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar: {e}")
    else:
        st.success("¡Datos registrados exitosamente!")
        
        # --- GENERACIÓN DEL PDF ---
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
        pdf.cell(0, 7, clean_pdf(f"Nivel Detectado: {nivel} | Solicito Contacto: {opcion_contacto}"), 0, 1)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. DETALLE DE HALLAZGOS Y RECOMENDACIONES", 1, 1, 'L')
        pdf.ln(4)

        for i in range(len(st.session_state.preguntas_texto)):
            preg_original = st.session_state.preguntas_texto[i]
            resp = st.session_state.respuestas_texto[i]
            
            # Limpiar duplicidad de números (ej: quita "2. " si ya existe)
            preg_limpia = re.sub(r'^\d+\.\s*', '', preg_original)
            
            # Escribir Pregunta
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 6, clean_pdf(f"Pregunta {i+1}: {preg_limpia}"))
            
            # Escribir Hallazgo
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.set_x(15)
            pdf.multi_cell(0, 6, clean_pdf(f"Hallazgo: {resp}"))

            # Inteligencia de Combinación
            recomendacion_final = ""
            ids_usuario = re.findall(r'(\d+\.[a-z])', resp.lower())
            ids_usuario = sorted(list(set(ids_usuario)))

            if ids_usuario:
                id_comb = " y ".join(ids_usuario)
                # Buscar Combinación Exacta
                for _, row in df_rec.iterrows():
                    if str(row['Clave']).lower().strip() == id_comb:
                        recomendacion_final = row['Contenido']
                        break
                # Si no hay, buscar el primer ID individual
                if not recomendacion_final:
                    for id_u in ids_usuario:
                        for _, row in df_rec.iterrows():
                            if str(row['Clave']).lower().strip() == id_u:
                                recomendacion_final = row['Contenido']
                                break
                        if recomendacion_final: break

            if recomendacion_final:
                pdf.ln(1)
                pdf.set_x(15)
                pdf.set_font("Arial", 'I', 10)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(0, 6, clean_pdf(f"RECOMENDACION: {recomendacion_final}"))
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(5)

        st.download_button(
            label="📥 DESCARGAR INFORME TECNICO PDF",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Informe_Cyber_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("Reiniciar"):
        st.session_state.clear()
        st.rerun()


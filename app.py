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
                # Solo tomamos las dos primeras columnas si existen
                celdas = [c.text.strip() for c in fila.cells]
                if len(celdas) >= 2:
                    datos.append([celdas[0], celdas[1]])
        return pd.DataFrame(datos[1:], columns=["Clave", "Contenido"])
    except Exception as e:
        st.error(f"Error cargando {ruta}: {e}")
        return pd.DataFrame()

# ESTA FUNCIÓN ES LA CLAVE: Normaliza el texto para que el match sea infalible
def normalizar_para_match(txt):
    if not txt: return ""
    t = str(txt).lower()
    # Quitar tildes
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    for a, b in rep.items(): t = t.replace(a, b)
    # ELIMINAR TODO excepto letras y números (adiós paréntesis, puntos, comas, espacios)
    t = re.sub(r'[^a-z0-9]', '', t)
    return t

def clean_pdf(txt):
    if not txt: return ""
    # Mapeo simple para caracteres Latin-1 que soporta FPDF por defecto
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
    st.session_state.update({'etapa':'registro','paso':0,'respuestas':[],'datos_usuario':{},'enviado':False})

# --- ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Registro de Evaluación")
    with st.form("reg_form"):
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
        st.subheader(f"Pregunta {st.session_state.paso + 1} de {total_p}")
        st.write(f"### {fila['Clave']}")
        
        opts = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
        es_m = "múltiple" in fila['Clave'].lower() or "multiple" in fila['Clave'].lower()
        
        ans = st.multiselect("Seleccione opciones:", opts) if es_m else st.radio("Opcion:", opts, index=None)

        if st.button("Continuar"):
            if ans:
                st.session_state.respuestas.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- ETAPA 3: RESULTADOS Y CONTACTO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Análisis Finalizado")
    si_c = sum(1 for r in st.session_state.respuestas if "SI" in str(r).upper())
    nivel = "Avanzado" if si_c > 12 else "Intermedio" if si_c > 6 else "Inicial"
    st.metric("Nivel de Madurez Detectado", nivel)

    st.write("---")
    st.subheader("¿Deseas profundizar en tus resultados?")
    contacto = st.radio("¿Quieres contactar a uno de nuestros ejecutivos para recibir una asesoría personalizada?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("Finalizar y Registrar Resultados"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                
                # Armamos la fila exactamente como la hoja espera (10 columnas según tu error anterior)
                # Ajusta esta lista según las columnas reales de tu Drive
                nueva_fila = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": u["Nombre"],
                    "Cargo": u["Cargo"],
                    "Empresa": u["Empresa"],
                    "Email": u["Email"],
                    "Telefono": u["Telefono"],
                    "Resultado": nivel,
                    "Presupuesto": "N/A",
                    "Contacto": contacto,
                    "Comentarios": "Generado por App"
                }])

                hist = conn.read(spreadsheet=url, ttl=0)
                final = pd.concat([hist, nueva_fila], ignore_index=True)
                conn.update(spreadsheet=url, data=final)
                
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    else:
        st.success("¡Datos guardados! Ya puede descargar su informe.")
        
        # --- GENERACIÓN DEL PDF (RECOMENDACIONES) ---
        df_rec = leer_word("02. Respuestas.docx")
        # Pre-normalizamos las claves del Word de respuestas para el match
        df_rec['Match_Key'] = df_rec['Clave'].apply(normalizar_para_match)
        
        pdf = PDF()
        pdf.add_page()
        
        # Situación
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN EJECUTIVO", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_pdf(f"Cliente: {u['Nombre']} | Empresa: {u['Empresa']}"), 0, 1)
        pdf.cell(0, 7, clean_pdf(f"Nivel de Madurez: {nivel}"), 0, 1)
        pdf.ln(5)

        # Recomendaciones
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. RECOMENDACIONES TECNICAS", 1, 1, 'L')
        pdf.ln(4)

        encontradas = 0
        for resp_usuario in st.session_state.respuestas:
            # Si hay comas (multiselect), separamos para buscar cada una
            sub_respuestas = [sr.strip() for sr in resp_usuario.split(",")]
            for sr in sub_respuestas:
                sr_norm = normalizar_para_match(sr)
                if not sr_norm: continue
                
                # Buscamos la fila donde nuestra clave normalizada coincida
                match = df_rec[df_rec['Match_Key'] == sr_norm]
                
                if not match.empty:
                    encontradas += 1
                    pdf.set_font("Arial", 'B', 9)
                    pdf.multi_cell(0, 6, clean_pdf(f"> Hallazgo: {sr}"))
                    pdf.set_font("Arial", '', 9)
                    pdf.multi_cell(0, 6, clean_pdf(f"RECOMENDACION: {match.iloc[0]['Contenido']}"))
                    pdf.ln(3)

        if encontradas == 0:
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 10, "Nota: No se detectaron recomendaciones especificas. Valide la coincidencia entre archivos.")

        st.download_button(
            label="📥 DESCARGAR PLAN DE ACCIÓN (PDF)",
            data=pdf.output(dest='S').encode('latin-1'),
            file_name=f"Recomendaciones_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("Reiniciar Test"):
        st.session_state.clear()
        st.rerun()

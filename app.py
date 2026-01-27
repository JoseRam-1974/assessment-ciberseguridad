import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re

# --- 1. CONFIGURACIÓN Y ESTILO GTD CORPORACIONES ---
st.set_page_config(page_title="Gtd | Assessment Ciberseguridad", page_icon="🛡️", layout="wide")

# Inyección de CSS para alineación de marca Gtd
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    h1, h2, h3 { color: #003366 !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Botones estilo Gtd */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #003366;
        color: white;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #00ccff; color: #003366; }
    
    /* Barra de progreso degradada */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #003366 , #00ccff);
    }
    
    /* Tarjetas de preguntas */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: white;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE APOYO ---
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
        st.error(f"Error al cargar {ruta}: {e}")
        return pd.DataFrame()

def clean_pdf(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":""}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, 'INFORME TECNICO DE CIBERSEGURIDAD | GTD', 0, 1, 'C')
        self.ln(5)

# --- 3. ESTADO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro', 'paso': 0,
        'respuestas_texto': [], 'preguntas_texto': [],
        'datos_usuario': {}, 'enviado': False
    })

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.title("🛡️ Diagnóstico de Ciberseguridad")
    st.write("Bienvenido. Inicie su evaluación para recibir recomendaciones estratégicas.")
    
    with st.form("reg_form"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Completo*")
            car = st.text_input("Cargo*")
            emp = st.text_input("Empresa*")
        with col2:
            ema = st.text_input("Email Corporativo*")
            tel = st.text_input("Teléfono*")
        
        if st.form_submit_button("EMPEZAR EVALUACIÓN"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Por favor complete todos los campos.")

# --- 5. ETAPA 2: PREGUNTAS CON BARRA DE PROGRESO ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total_p = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        
        # Barra de progreso
        progreso = (st.session_state.paso + 1) / total_p
        st.progress(progreso)
        st.caption(f"Pregunta {st.session_state.paso + 1} de {total_p} | {int(progreso*100)}% completado")

        with st.container(border=True):
            # Limpiar número duplicado en pantalla si existe
            pregunta_display = re.sub(r'^\d+\.\s*', '', fila['Clave'])
            st.markdown(f"### {pregunta_display}")
            
            opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
            es_multiple = any(kw in fila['Clave'].lower() for kw in ["múltiple", "multiple", "seleccione varias"])
            
            if es_multiple:
                ans = st.multiselect("Puede seleccionar varias opciones:", opciones)
            else:
                ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("SIGUIENTE"):
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
                st.info("Seleccione una respuesta para continuar.")

# --- 6. ETAPA 3: RESULTADOS, CONTACTO Y REGISTRO ---
elif st.session_state.etapa == 'resultado':
    st.title("✅ Evaluación Completada")
    
    si_count = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    st.metric("Nivel de Madurez Detectado", nivel)
    
    with st.container(border=True):
        st.subheader("🎯 Asesoría Especializada")
        st.write("Un especialista de Gtd Corporaciones puede ayudarte a priorizar estas recomendaciones.")
        opcion_contacto = st.radio("¿Deseas que un ejecutivo(a) senior se contacte contigo?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("REGISTRAR Y GENERAR REPORTE"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                
                # Buscar presupuesto
                pres_val = next((r for p, r in zip(st.session_state.preguntas_texto, st.session_state.respuestas_texto) if "presupuesto" in p.lower()), "N/A")

                df_nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": u["Nombre"], "Cargo": u["Cargo"], "Empresa": u["Empresa"],
                    "Email": u["Email"], "Telefono": u["Telefono"], "Resultado": nivel,
                    "Presupuesto": pres_val, "Contacto_Ejecutivo": opcion_contacto,
                    "Version": "Gtd-V9-Final"
                }])
                
                hist = conn.read(spreadsheet=url, ttl=0)
                conn.update(spreadsheet=url, data=pd.concat([hist, df_nuevo], ignore_index=True))
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error de registro: {e}")
    else:
        st.success("¡Datos registrados! Descargue su informe técnico a continuación.")
        
        # --- PDF PROFESIONAL GTD ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN EJECUTIVO", 1, 1, 'L')
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_pdf(f"Empresa: {u['Empresa']} | Cargo: {u['Cargo']}"), 0, 1)
        pdf.cell(0, 7, clean_pdf(f"Nivel: {nivel} | Contacto Solicitado: {opcion_contacto}"), 0, 1)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. HALLAZGOS Y RECOMENDACIONES", 1, 1, 'L')
        pdf.ln(4)

        for i in range(len(st.session_state.preguntas_texto)):
            preg_clean = re.sub(r'^\d+\.\s*', '', st.session_state.preguntas_texto[i])
            resp = st.session_state.respuestas_texto[i]
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, clean_pdf(f"Pregunta {i+1}: {preg_clean}"))
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            pdf.set_x(15)
            pdf.multi_cell(0, 5, clean_pdf(f"Hallazgo: {resp}"))

            # Inteligencia de Match Exacto y Combinado
            recom_final = ""
            ids = sorted(list(set(re.findall(r'(\d+\.[a-z])', resp.lower()))))

            if ids:
                id_comb = " y ".join(ids)
                for _, row in df_rec.iterrows():
                    if str(row['Clave']).lower().strip() == id_comb:
                        recom_final = row['Contenido']
                        break
                if not recom_final:
                    for id_u in ids:
                        for _, row in df_rec.iterrows():
                            if str(row['Clave']).lower().strip() == id_u:
                                recom_final = row['Contenido']
                                break
                        if recom_final: break

            if recom_final:
                pdf.set_x(15)
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(0, 51, 102)
                pdf.multi_cell(0, 5, clean_pdf(f"RECOMENDACION GTD: {recom_final}"))
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(5)

        st.download_button(
            label="📥 DESCARGAR REPORTE CIBERSEGURIDAD (PDF)",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Informe_Gtd_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("REINICIAR"):
        st.session_state.clear()
        st.rerun()

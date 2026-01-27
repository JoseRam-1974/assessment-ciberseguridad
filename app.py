import streamlit as st
import pandas as pd
from docx import Document
import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import re
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL SECURESOFT ---
st.set_page_config(page_title="SecureSoft GTD | Cyber Assessment", page_icon="🛡️", layout="wide")

# Inyección de CSS para replicar el diseño de la imagen "diseño.jpg"
st.markdown("""
    <style>
    /* Fondo oscuro y tipografía profesional */
    .stApp { 
        background-color: #0b111b; 
        color: #ffffff;
    }
    
    /* Banner Principal */
    .cyber-banner {
        background: linear-gradient(90deg, #0b111b 0%, #162a4d 100%);
        padding: 40px;
        border-radius: 15px;
        border-left: 5px solid #00ccff;
        margin-bottom: 30px;
    }

    h1, h2, h3 { color: #00ccff !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Botones con estilo SecureSoft (Azul/Celeste) */
    .stButton>button {
        width: 100%;
        border-radius: 4px;
        height: 3.5em;
        background-color: #0056b3;
        color: white;
        border: 1px solid #00ccff;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton>button:hover { 
        background-color: #00ccff; 
        color: #0b111b;
        border: 1px solid #ffffff;
    }

    /* Tarjetas de preguntas */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: #121d2f;
        border-radius: 10px;
        padding: 30px;
        border: 1px solid #1e3a5f;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    /* Barra de progreso */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #0056b3, #00ccff);
    }
    
    /* Labels de inputs */
    label { color: #a1b1c7 !important; font-weight: 500 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE PROCESAMIENTO ---
def leer_word(ruta):
    try:
        doc = Document(ruta)
        datos = []
        for tabla in doc.tables:
            for fila in tabla.rows:
                celdas = [c.text.strip() for c in fila.cells]
                if len(celdas) >= 2: datos.append([celdas[0], celdas[1]])
        return pd.DataFrame(datos[1:], columns=["Clave", "Contenido"])
    except Exception:
        return pd.DataFrame()

def clean_pdf(txt):
    if not txt: return ""
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ñ":"N","¿":"","¡":""}
    t = str(txt)
    for a, b in rep.items(): t = t.replace(a, b)
    return t.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        # Logo SecureSoft en el PDF
        if os.path.exists('Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'):
            self.image('Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png', 10, 8, 50)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(0, 86, 179)
        self.cell(0, 10, 'CYBERSECURITY ASSESSMENT REPORT - 2026', 0, 1, 'R')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

# --- 3. ESTADO DE SESIÓN ---
if 'etapa' not in st.session_state:
    st.session_state.update({
        'etapa': 'registro', 'paso': 0,
        'respuestas_texto': [], 'preguntas_texto': [],
        'datos_usuario': {}, 'enviado': False
    })

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    if os.path.exists('Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png'):
        st.image('Logotipo-SECURESOFT-GTD-Color-Fondo-Transparente.png', use_container_width=True)
    st.write("---")
    if st.session_state.datos_usuario:
        st.markdown(f"👤 **Usuario:** {st.session_state.datos_usuario['Nombre']}")
        st.markdown(f"🏢 **Empresa:** {st.session_state.datos_usuario['Empresa']}")

# --- 4. ETAPA 1: REGISTRO ---
if st.session_state.etapa == 'registro':
    st.markdown("""
        <div class="cyber-banner">
            <h1>SECURESOFT GTD</h1>
            <p style="font-size: 1.2em; color: #a1b1c7;">Diagnóstico de Madurez y Resiliencia en Ciberseguridad</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("reg_form"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nombre Completo*")
            car = st.text_input("Cargo*")
            emp = st.text_input("Empresa*")
        with col2:
            ema = st.text_input("Email Corporativo*")
            tel = st.text_input("Teléfono de Contacto*")
        
        if st.form_submit_button("INICIAR EVALUACIÓN TÉCNICA"):
            if all([nom, car, emp, ema, tel]):
                st.session_state.datos_usuario = {"Nombre": nom, "Cargo": car, "Empresa": emp, "Email": ema, "Telefono": tel}
                st.session_state.etapa = 'preguntas'
                st.rerun()
            else:
                st.warning("Por favor, complete todos los campos requeridos.")

# --- 5. ETAPA 2: ASSESSMENT ---
elif st.session_state.etapa == 'preguntas':
    df_p = leer_word("01. Preguntas.docx")
    if not df_p.empty:
        total_p = len(df_p)
        fila = df_p.iloc[st.session_state.paso]
        
        # Barra de progreso visual
        progreso = (st.session_state.paso + 1) / total_p
        st.progress(progreso)
        st.caption(f"Pregunta {st.session_state.paso + 1} de {total_p} | {int(progreso*100)}% completado")

        with st.container(border=True):
            # Limpiar el número duplicado de la pregunta para la UI
            pregunta_limpia = re.sub(r'^\d+\.\s*', '', fila['Clave'])
            st.markdown(f"### {pregunta_limpia}")
            
            opciones = [o.strip() for o in fila['Contenido'].split('\n') if o.strip()]
            es_multiple = "múltiple" in fila['Clave'].lower() or "multiple" in fila['Clave'].lower()
            
            if es_multiple:
                ans = st.multiselect("Seleccione las opciones que correspondan:", opciones)
            else:
                ans = st.radio("Seleccione una opción:", opciones, index=None)

        if st.button("CONFIRMAR Y SIGUIENTE"):
            if ans:
                st.session_state.preguntas_texto.append(fila['Clave'])
                st.session_state.respuestas_texto.append(", ".join(ans) if isinstance(ans, list) else ans)
                if st.session_state.paso < total_p - 1:
                    st.session_state.paso += 1
                    st.rerun()
                else:
                    st.session_state.etapa = 'resultado'
                    st.rerun()

# --- 6. ETAPA 3: RESULTADOS Y REPORTE ---
elif st.session_state.etapa == 'resultado':
    st.title("🛡️ Diagnóstico Finalizado")
    
    si_count = sum(1 for r in st.session_state.respuestas_texto if "SI" in str(r).upper())
    nivel = "Avanzado" if si_count > 12 else "Intermedio" if si_count > 6 else "Inicial"
    
    st.metric("Índice de Madurez Detectado", nivel)
    
    with st.container(border=True):
        st.subheader("🚀 Próximos Pasos")
        st.write("Para profundizar en estos hallazgos, podemos coordinar una sesión con uno de nuestros consultores senior.")
        opcion_contacto = st.radio("¿Deseas recibir una llamada de asesoría técnica?", ["SÍ", "NO"], index=0)

    if not st.session_state.enviado:
        if st.button("REGISTRAR RESULTADOS"):
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                u = st.session_state.datos_usuario
                
                # Buscar presupuesto en respuestas
                pres_val = next((r for p, r in zip(st.session_state.preguntas_texto, st.session_state.respuestas_texto) if "presupuesto" in p.lower()), "N/A")

                df_nuevo = pd.DataFrame([{
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Nombre": u["Nombre"], "Cargo": u["Cargo"], "Empresa": u["Empresa"],
                    "Email": u["Email"], "Telefono": u["Telefono"], "Resultado": nivel,
                    "Presupuesto": pres_val, "Contacto_Ejecutivo": opcion_contacto,
                    "Version": "SecureSoft-v1.0"
                }])
                
                hist = conn.read(spreadsheet=url, ttl=0)
                conn.update(spreadsheet=url, data=pd.concat([hist, df_nuevo], ignore_index=True))
                st.session_state.enviado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error de conexión: {e}")
    else:
        st.success("✅ Registro completado. Ya puede descargar su informe confidencial.")
        
        # --- GENERACIÓN DEL PDF ---
        df_rec = leer_word("02. Respuestas.docx")
        pdf = PDF()
        pdf.add_page()
        
        # Resumen Ejecutivo
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "1. RESUMEN DE EVALUACION", 1, 1, 'L', fill=True)
        pdf.set_font("Arial", '', 10)
        u = st.session_state.datos_usuario
        pdf.ln(2)
        pdf.cell(0, 7, clean_pdf(f"Cliente: {u['Empresa']} | Responsable: {u['Nombre']} ({u['Cargo']})"), 0, 1)
        pdf.cell(0, 7, clean_pdf(f"Nivel de Madurez: {nivel} | Solicitud de Contacto: {opcion_contacto}"), 0, 1)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "2. ANALISIS DE HALLAZGOS Y RECOMENDACIONES", 1, 1, 'L', fill=True)
        pdf.ln(4)

        for i in range(len(st.session_state.preguntas_texto)):
            preg_orig = st.session_state.preguntas_texto[i]
            resp = st.session_state.respuestas_texto[i]
            
            # Formato de pregunta limpia en el informe
            preg_final = re.sub(r'^\d+\.\s*', '', preg_orig)
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, clean_pdf(f"Pregunta {i+1}: {preg_final}"))
            
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            pdf.set_x(15)
            pdf.multi_cell(0, 5, clean_pdf(f"Hallazgo Detectado: {resp}"))

            # Inteligencia de Match de Recomendaciones
            recom_final = ""
            ids = sorted(list(set(re.findall(r'(\d+\.[a-z])', resp.lower()))))

            if ids:
                id_comb = " y ".join(ids)
                # Intenta combinación exacta (ej: 5.a y 5.b)
                for _, row in df_rec.iterrows():
                    if str(row['Clave']).lower().strip() == id_comb:
                        recom_final = row['Contenido']
                        break
                # Si no, busca individual
                if not recom_final:
                    for id_u in ids:
                        for _, row in df_rec.iterrows():
                            if str(row['Clave']).lower().strip() == id_u:
                                recom_final = row['Contenido']
                                break
                        if recom_final: break

            if recom_final:
                pdf.ln(1)
                pdf.set_x(15)
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(0, 86, 179) # Azul SecureSoft
                pdf.multi_cell(0, 5, clean_pdf(f"RECOMENDACION TECNICA: {recom_final}"))
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(5)

        st.download_button(
            label="📥 DESCARGAR INFORME PDF SECURESOFT",
            data=pdf.output(dest='S').encode('latin-1', 'replace'),
            file_name=f"Assessment_SecureSoft_{u['Empresa']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if st.button("REALIZAR NUEVA EVALUACIÓN"):
        st.session_state.clear()
        st.rerun()

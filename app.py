AUTOR = "Escribe aquí tu nombre"

import streamlit as st

st.set_page_config(
    page_title="App de Diseño Experimental",
    page_icon="🌱",
    layout="wide",
)

st.title("App de Diseño Experimental")
st.subheader("Ingeniería Agrícola – Universidad de Sucre")
st.write(
    "El diseño experimental permite planear y analizar ensayos de campo de forma "
    "ordenada, para comparar tratamientos y distinguir sus efectos de la variación "
    "natural del suelo, el clima y el manejo agrícola."
)

st.header("Módulos")
modulos = [
    {
        "Diseño": "DCA — Diseño completamente al azar",
        "Cuándo se usa": "Cuando las unidades experimentales son homogéneas y los tratamientos pueden asignarse al azar.",
        "Ejemplo agrícola": "Comparar métodos de secado de yuca asignándolos al azar a muestras homogéneas.",
        "Estado": "Disponible",
    },
    {
        "Diseño": "DBCA — Diseño en bloques completos al azar",
        "Cuándo se usa": "Cuando una fuente conocida de variación permite agrupar unidades similares en bloques.",
        "Ejemplo agrícola": "Comparar fertilizantes en bloques de parcelas definidos según un gradiente de fertilidad.",
        "Estado": "En construcción",
    },
    {
        "Diseño": "DCL — Diseño en cuadrado latino",
        "Cuándo se usa": "Cuando se deben controlar dos fuentes de variación mediante filas y columnas.",
        "Ejemplo agrícola": "Comparar variedades controlando gradientes de humedad y fertilidad en el lote.",
        "Estado": "En construcción",
    },
    {
        "Diseño": "DPD — Diseño de parcelas divididas",
        "Cuándo se usa": "Cuando un factor requiere parcelas grandes y otro puede asignarse a subparcelas.",
        "Ejemplo agrícola": "Evaluar sistemas de labranza en parcelas principales y variedades en subparcelas.",
        "Estado": "En construcción",
    },
    {
        "Diseño": "Factoriales",
        "Cuándo se usa": "Cuando se estudian simultáneamente varios factores y sus posibles interacciones.",
        "Ejemplo agrícola": "Evaluar conjuntamente niveles de riego y variedades de maíz.",
        "Estado": "En construcción",
    },
    {
        "Diseño": "RSM — Metodología de superficie de respuesta",
        "Cuándo se usa": "Cuando se busca modelar y optimizar una respuesta según factores cuantitativos.",
        "Ejemplo agrícola": "Buscar la combinación de riego y fertilización que optimice el rendimiento de un cultivo.",
        "Estado": "En construcción",
    },
]
st.table(modulos)

st.header("Instrucciones de uso")
st.markdown(
    "1. Elige el módulo que corresponda a tu diseño experimental.\n"
    "2. Carga los datos del ensayo en el formato solicitado por el módulo.\n"
    "3. Revisa los resultados y su interpretación junto con los supuestos del análisis.\n"
    "4. Verifica los procedimientos y resultados con tu cálculo manual."
)

st.warning(
    "Esta app apoya el aprendizaje. El estudiante interpreta los resultados, "
    "verifica supuestos y compara con su cálculo manual."
)

with st.sidebar:
    st.header("Información del curso")
    st.write(f"Autor: {AUTOR}")
    st.write("Curso: Diseño Experimental")
    st.write("Semestre: 2026-2")

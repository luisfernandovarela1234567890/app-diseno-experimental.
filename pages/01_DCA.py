from io import BytesIO
from pathlib import Path
import warnings

import plotly.express as px
import pandas as pd
import streamlit as st
from scipy.stats import f as distribucion_f

from utils.anova_utils import (
	ajustar_dca,
	cargar_datos,
	coeficiente_variacion,
	interpretar_dca,
	resumen_tratamientos,
	tabla_anova,
	tukey,
	validar_dca,
)
from utils.diagnostico_utils import (
	grafico_qq,
	grafico_residuos_vs_ajustados,
	prueba_levene,
	prueba_shapiro,
	residuos_y_ajustados,
)


RUTA_EJEMPLO = Path("data/dca_secadores.csv")


@st.cache_data
def cargar_datos_ejemplo() -> pd.DataFrame:
	"""Carga el conjunto de datos de ejemplo y conserva el resultado en caché.

	Returns:
		Datos de humedad final para los cuatro secadores solares.
	"""
	return cargar_datos(RUTA_EJEMPLO)


@st.cache_data
def cargar_datos_subidos(contenido: bytes, nombre_archivo: str) -> pd.DataFrame:
	"""Carga en caché un archivo CSV o Excel subido por el usuario.

	Args:
		contenido: Contenido binario del archivo.
		nombre_archivo: Nombre original, usado para identificar su extensión.

	Returns:
		Datos leídos desde el archivo subido.
	"""
	archivo = BytesIO(contenido)
	archivo.name = nombre_archivo
	return cargar_datos(archivo)


st.title("Diseño completamente al azar (DCA)")
st.write(
	"El DCA compara tratamientos asignados al azar cuando las unidades experimentales "
	"son homogéneas. En este ejemplo se compara la humedad final de yuca en cuatro "
	"secadores solares, con cuatro réplicas por secador."
)

archivo_subido = st.file_uploader(
	"Carga los datos del ensayo",
	type=["csv", "xlsx"],
)

try:
	if archivo_subido is None:
		df = cargar_datos_ejemplo()
		st.caption("No se cargó un archivo; se usan los datos de ejemplo de los cuatro secadores solares.")
	else:
		df = cargar_datos_subidos(archivo_subido.getvalue(), archivo_subido.name)
except (OSError, ValueError, ImportError, pd.errors.ParserError) as error:
	st.error(f"No fue posible cargar el archivo: {error}")
	st.stop()

columnas = list(df.columns)
if not columnas:
	st.error("El archivo no contiene columnas para analizar.")
	st.stop()

columnas_categoricas = list(df.select_dtypes(exclude="number").columns)
columnas_numericas = list(df.select_dtypes(include="number").columns)
columnas_respuesta_probables = [
	columna
	for columna in columnas_numericas
	if columna.strip().casefold() not in {"id", "replica", "réplica", "repeticion", "repetición"}
]
indice_tratamiento = columnas.index(
	columnas_categoricas[0] if columnas_categoricas else columnas[0]
)
indice_respuesta = columnas.index(
	columnas_respuesta_probables[-1]
	if columnas_respuesta_probables
	else columnas_numericas[0]
	if columnas_numericas
	else columnas[0]
)

columna_tratamiento = st.selectbox(
	"Columna de tratamiento",
	options=columnas,
	index=indice_tratamiento,
)
columna_respuesta = st.selectbox(
	"Columna de respuesta numérica",
	options=columnas,
	index=indice_respuesta,
)
alfa = st.slider(
	"Nivel de significancia (alfa)",
	min_value=0.01,
	max_value=0.10,
	value=0.05,
	step=0.01,
)

# La validación precede al análisis para evitar ajustar modelos con datos incompletos o incompatibles.
errores = validar_dca(df, columna_tratamiento, columna_respuesta)
if errores:
	for error in errores:
		st.error(error)
	st.stop()

modelo = ajustar_dca(df, columna_tratamiento, columna_respuesta)
anova = tabla_anova(modelo)
resumen = resumen_tratamientos(df, columna_tratamiento, columna_respuesta)
fila_tratamientos = anova.loc[anova["Fuente"] == "Tratamientos"].iloc[0]
fila_error = anova.loc[anova["Fuente"] == "Error"].iloc[0]
p_valor = float(fila_tratamientos["p-valor"])

tab_datos, tab_anova, tab_comparaciones, tab_graficos, tab_supuestos = st.tabs(
	["Datos", "ANOVA", "Comparaciones", "Gráficos", "Supuestos"]
)

with tab_datos:
	st.subheader("Datos del ensayo")
	st.dataframe(df, width="stretch", hide_index=True)
	st.subheader("Resumen por tratamiento")
	st.dataframe(resumen, width="stretch", hide_index=True)

with tab_anova:
	st.subheader("Tabla ANOVA")
	# La tabla particiona la variación total en tratamientos y error para evaluar H0.
	formato_anova = {
		columna: "{:.4f}"
		for columna in ["gl", "SC", "CM", "F", "p-valor"]
	}
	st.dataframe(
		anova.style.format(formato_anova, na_rep="—"),
		width="stretch",
		hide_index=True,
	)

	# F crítica delimita la región de rechazo con los grados de libertad del tratamiento y del error.
	f_critica = float(
		distribucion_f.ppf(
			1 - alfa,
			float(fila_tratamientos["gl"]),
			float(fila_error["gl"]),
		)
	)
	# El CV relaciona el error experimental con la media general para contextualizar su magnitud.
	cv = coeficiente_variacion(modelo, df, columna_respuesta)
	columna_f, columna_cv = st.columns(2)
	columna_f.metric("F crítica", f"{f_critica:.4f}")
	columna_cv.metric("Coeficiente de variación", f"{cv:.4f} %")

	# La interpretación comunica la decisión sobre la igualdad de medias al nivel alfa seleccionado.
	interpretacion = interpretar_dca(anova, alfa)
	if p_valor < alfa:
		st.success(interpretacion)
	else:
		st.info(interpretacion)

with tab_comparaciones:
	st.subheader("Comparaciones múltiples de Tukey")
	if p_valor < alfa:
		# Tukey identifica qué pares de medias difieren después de detectar efecto global de tratamientos.
		with warnings.catch_warnings(record=True) as advertencias:
			warnings.simplefilter("always")
			tabla_tukey, dms = tukey(
				df,
				columna_tratamiento,
				columna_respuesta,
				alfa,
			)
		for advertencia in advertencias:
			st.warning(str(advertencia.message))
		st.dataframe(
			tabla_tukey.style.format(
				{
					"Diferencia de medias": "{:.4f}",
					"p-valor ajustado": "{:.4f}",
					"Límite inferior": "{:.4f}",
					"Límite superior": "{:.4f}",
				}
			),
			width="stretch",
			hide_index=True,
		)
		st.metric("Diferencia mínima significativa (DMS)", f"{dms:.4f}")
	else:
		st.info(
			"No se realiza Tukey porque el ANOVA no detectó diferencias "
			"estadísticamente significativas entre tratamientos al alfa seleccionado."
		)

with tab_graficos:
	st.subheader("Distribución de la respuesta por tratamiento")
	# El boxplot muestra la dispersión de las réplicas y cada observación individual.
	grafico_cajas = px.box(
		df,
		x=columna_tratamiento,
		y=columna_respuesta,
		points="all",
		labels={
			columna_tratamiento: "Tratamiento",
			columna_respuesta: columna_respuesta,
		},
	)
	st.plotly_chart(grafico_cajas, width="stretch")

	st.subheader("Media por tratamiento")
	# El gráfico de medias facilita comparar el nivel promedio de respuesta entre tratamientos.
	grafico_medias = px.bar(
		resumen,
		x=columna_tratamiento,
		y="media",
		labels={columna_tratamiento: "Tratamiento", "media": "Media"},
	)
	st.plotly_chart(grafico_medias, width="stretch")

with tab_supuestos:
	st.subheader("Diagnóstico de supuestos")
	# Shapiro-Wilk evalúa la normalidad de residuos y Levene revisa igualdad de varianzas.
	residuos, _ = residuos_y_ajustados(modelo)
	shapiro_estadistico, shapiro_p, shapiro_conclusion = prueba_shapiro(residuos, alfa)
	levene_estadistico, levene_p, levene_conclusion = prueba_levene(
		df,
		columna_tratamiento,
		columna_respuesta,
		alfa,
	)
	resultados_supuestos = pd.DataFrame(
		[
			{
				"Prueba": "Shapiro-Wilk",
				"Estadístico": shapiro_estadistico,
				"p-valor": shapiro_p,
				"Conclusión": shapiro_conclusion,
			},
			{
				"Prueba": "Levene (mediana)",
				"Estadístico": levene_estadistico,
				"p-valor": levene_p,
				"Conclusión": levene_conclusion,
			},
		]
	)
	st.dataframe(
		resultados_supuestos.style.format(
			{"Estadístico": "{:.4f}", "p-valor": "{:.4f}"}
		),
		width="stretch",
		hide_index=True,
	)

	st.markdown("**Residuos frente a valores ajustados**")
	st.plotly_chart(grafico_residuos_vs_ajustados(modelo), width="stretch")
	st.markdown("**Gráfico Q-Q normal de los residuos**")
	st.plotly_chart(grafico_qq(residuos), width="stretch")

	st.markdown(
		"**Supuestos revisados:** Shapiro-Wilk evalúa si los residuos son compatibles "
		"con una distribución normal. Levene evalúa si la variabilidad de la respuesta "
		"es semejante entre tratamientos. La independencia no se prueba con estas "
		"pruebas: se sustenta en la asignación aleatoria de las unidades experimentales "
		"y en evitar interferencia entre ellas."
	)

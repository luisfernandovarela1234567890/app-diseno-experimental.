"""Funciones reutilizables para analizar un diseño completamente al azar."""

from pathlib import Path
from typing import IO
import warnings

import numpy as np
import pandas as pd
from scipy.stats import studentized_range
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.regression.linear_model import RegressionResultsWrapper


def cargar_datos(archivo: str | Path | IO[bytes] | IO[str]) -> pd.DataFrame:
    """Carga datos desde un archivo CSV o Excel.

    Args:
        archivo: Ruta o flujo de un archivo con extensión `.csv` o `.xlsx`.

    Returns:
        Un DataFrame con los datos leídos.

    Raises:
        ValueError: Si la extensión no corresponde a CSV o Excel `.xlsx`.
    """
    # La extensión identifica el formato; para CSV, el motor de Python detecta si el separador es coma o punto y coma.
    nombre_archivo = getattr(archivo, "name", archivo)
    extension = Path(str(nombre_archivo)).suffix.lower()

    if extension == ".xlsx":
        if not isinstance(archivo, (str, Path)):
            archivo.seek(0)
        return pd.read_excel(archivo)
    if extension == ".csv":
        if not isinstance(archivo, (str, Path)):
            archivo.seek(0)
        return pd.read_csv(archivo, sep=None, engine="python")

    raise ValueError("Formato no compatible. Usa un archivo CSV o Excel (.xlsx).")


def validar_dca(df: pd.DataFrame, col_trat: str, col_resp: str) -> list[str]:
    """Valida los datos básicos requeridos para un DCA de un factor.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta numérica.

    Returns:
        Lista de errores en español; queda vacía si los datos son válidos.
    """
    errores: list[str] = []
    columnas_requeridas = [col_trat, col_resp]
    columnas_faltantes = [columna for columna in columnas_requeridas if columna not in df.columns]

    # Se verifica primero la estructura para evitar acceder a columnas inexistentes.
    if columnas_faltantes:
        errores.append(f"Faltan las columnas requeridas: {', '.join(columnas_faltantes)}.")

    columnas_presentes = [columna for columna in columnas_requeridas if columna in df.columns]
    if columnas_presentes and df[columnas_presentes].isna().any().any():
        errores.append("Hay datos faltantes en las columnas de tratamiento o respuesta.")

    if col_resp in df.columns:
        respuesta_numerica = pd.api.types.is_numeric_dtype(df[col_resp])
        respuesta_booleana = pd.api.types.is_bool_dtype(df[col_resp])
        if not respuesta_numerica or respuesta_booleana:
            errores.append(f"La columna de respuesta '{col_resp}' debe ser numérica.")

    if col_trat in df.columns:
        numero_tratamientos = df[col_trat].nunique(dropna=True)
        if numero_tratamientos < 2:
            errores.append("El DCA requiere al menos dos tratamientos.")

        # El criterio de réplica mínima es n_i >= 2 para cada tratamiento i.
        replicas_por_tratamiento = df.groupby(col_trat, dropna=True).size()
        if not replicas_por_tratamiento.empty and (replicas_por_tratamiento < 2).any():
            errores.append("Cada tratamiento debe tener al menos dos réplicas.")

    return errores


def ajustar_dca(df: pd.DataFrame, col_trat: str, col_resp: str) -> RegressionResultsWrapper:
    """Ajusta el modelo lineal de un DCA con un factor.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta numérica.

    Returns:
        Modelo OLS ajustado.
    """
    # Q() protege nombres de columna con espacios, tildes u otros caracteres especiales.
    # Modelo aditivo: Y_ij = mu + tau_i + epsilon_ij, donde i identifica tratamiento y j réplica.
    formula = f"Q({col_resp!r}) ~ C(Q({col_trat!r}))"
    modelo = ols(formula, data=df).fit()
    return modelo


def tabla_anova(modelo: RegressionResultsWrapper) -> pd.DataFrame:
    """Construye la tabla ANOVA tipo II y agrega la fila del total.

    Args:
        modelo: Modelo OLS ajustado para un DCA de un factor.

    Returns:
        Tabla con las fuentes, grados de libertad, sumas y cuadrados medios,
        estadístico F y p-valor.
    """
    # ANOVA tipo II separa la variación atribuible al tratamiento y al error.
    anova = anova_lm(modelo, typ=2)
    tabla = anova.rename(
        columns={
            "df": "gl",
            "sum_sq": "SC",
            "F": "F",
            "PR(>F)": "p-valor",
        }
    ).reset_index()
    tabla = tabla.rename(columns={"index": "Fuente"})
    tabla["Fuente"] = tabla["Fuente"].map(
        lambda fuente: "Error" if fuente == "Residual" else "Tratamientos"
    )

    # Cuadrado medio: CM = SC / gl; el total suma tratamientos y error.
    tabla["CM"] = tabla["SC"] / tabla["gl"]
    fila_total = pd.DataFrame(
        [
            {
                "Fuente": "Total",
                "gl": tabla["gl"].sum(),
                "SC": tabla["SC"].sum(),
                "F": np.nan,
                "p-valor": np.nan,
            }
        ]
    )
    fila_total["CM"] = fila_total["SC"] / fila_total["gl"]
    tabla = pd.concat([tabla, fila_total], ignore_index=True)
    return tabla[["Fuente", "gl", "SC", "CM", "F", "p-valor"]]


def resumen_tratamientos(df: pd.DataFrame, col_trat: str, col_resp: str) -> pd.DataFrame:
    """Resume el tamaño de muestra y la respuesta por tratamiento.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta numérica.

    Returns:
        DataFrame con n, total, media y desviación estándar por tratamiento.
    """
    # Para cada tratamiento: n_i = número de réplicas, total_i = suma(y_ij), media_i = total_i / n_i.
    # La desviación estándar muestral es s_i = sqrt(sum((y_ij - media_i)^2) / (n_i - 1)).
    resumen = df.groupby(col_trat, observed=True)[col_resp].agg(
        **{
            "n": "count",
            "total": "sum",
            "media": "mean",
            "desviación estándar": "std",
        }
    )
    return resumen.reset_index()


def coeficiente_variacion(
    modelo: RegressionResultsWrapper, df: pd.DataFrame, col_resp: str
) -> float:
    """Calcula el coeficiente de variación del error experimental.

    Args:
        modelo: Modelo OLS ajustado para el DCA.
        df: Datos del ensayo.
        col_resp: Nombre de la columna con la respuesta numérica.

    Returns:
        Coeficiente de variación porcentual.

    Raises:
        ValueError: Si la media general es cero y el CV no está definido.
    """
    # CV = sqrt(CME) / media general * 100; expresa el error respecto a la escala de respuesta.
    media_general = float(df[col_resp].mean())
    if media_general == 0:
        raise ValueError("No se puede calcular el CV cuando la media general es cero.")
    return float(np.sqrt(modelo.mse_resid) / media_general * 100)


def tukey(
    df: pd.DataFrame,
    col_trat: str,
    col_resp: str,
    alfa: float = 0.05,
) -> tuple[pd.DataFrame, float]:
    """Realiza Tukey y calcula la diferencia mínima significativa.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna con la respuesta numérica.
        alfa: Nivel de significancia entre cero y uno.

    Returns:
        Una tabla de comparaciones de Tukey en español y la DMS calculada.

    Raises:
        ValueError: Si alfa no está entre cero y uno.
    """
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")

    # Tukey compara todas las medias usando el error residual del modelo DCA.
    comparacion = pairwise_tukeyhsd(
        endog=df[col_resp], groups=df[col_trat], alpha=alfa
    )
    tabla_resumen = comparacion.summary().data
    tabla_tukey = pd.DataFrame(tabla_resumen[1:], columns=tabla_resumen[0]).rename(
        columns={
            "group1": "Tratamiento 1",
            "group2": "Tratamiento 2",
            "meandiff": "Diferencia de medias",
            "p-adj": "p-valor ajustado",
            "lower": "Límite inferior",
            "upper": "Límite superior",
            "reject": "Rechaza H0",
        }
    )
    for columna in [
        "Diferencia de medias",
        "p-valor ajustado",
        "Límite inferior",
        "Límite superior",
    ]:
        tabla_tukey[columna] = pd.to_numeric(tabla_tukey[columna])
    tabla_tukey["Rechaza H0"] = tabla_tukey["Rechaza H0"].map(
        {"True": True, "False": False, True: True, False: False}
    )

    tamanos = df.groupby(col_trat, observed=True).size()
    numero_tratamientos = len(tamanos)
    modelo = ajustar_dca(df, col_trat, col_resp)
    grados_libertad_error = modelo.df_resid
    cuadrado_medio_error = modelo.mse_resid
    replicas_promedio = float(tamanos.mean())

    # DMS = q(1 - alfa; tratamientos; glE) * sqrt(CME / r).
    # En diseños desbalanceados se usa el promedio de réplicas, por eso la DMS es aproximada.
    if tamanos.nunique() > 1:
        warnings.warn(
            "El diseño está desbalanceado; la DMS es aproximada y usa el promedio "
            "de réplicas por tratamiento.",
            UserWarning,
            stacklevel=2,
        )
    cuantil_q = studentized_range.ppf(
        1 - alfa, numero_tratamientos, grados_libertad_error
    )
    dms = float(cuantil_q * np.sqrt(cuadrado_medio_error / replicas_promedio))
    return tabla_tukey, dms


def interpretar_dca(tabla: pd.DataFrame, alfa: float = 0.05) -> str:
    """Interpreta la prueba F del tratamiento para la decisión del DCA.

    Args:
        tabla: Tabla ANOVA con las columnas `Fuente` y `p-valor`.
        alfa: Nivel de significancia de la prueba.

    Returns:
        Explicación sencilla de la decisión sobre la hipótesis nula.

    Raises:
        ValueError: Si falta la fila de tratamientos o alfa no está entre cero y uno.
    """
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")
    fila_tratamientos = tabla.loc[tabla["Fuente"] == "Tratamientos", "p-valor"]
    if fila_tratamientos.empty:
        raise ValueError("La tabla ANOVA debe incluir la fila 'Tratamientos'.")

    # H0: todas las medias de tratamiento son iguales; la regla es rechazar si p < alfa.
    p_valor = float(fila_tratamientos.iloc[0])
    if p_valor < alfa:
        return (
            f"Se rechaza H0 (p-valor = {p_valor:.4g} < alfa = {alfa:g}). "
            "Hay evidencia de diferencias entre al menos dos tratamientos; "
            "compara sus medias para sustentar la decisión agronómica."
        )
    return (
        f"No se rechaza H0 (p-valor = {p_valor:.4g} >= alfa = {alfa:g}). "
        "No hay evidencia suficiente de diferencias entre tratamientos para "
        "este ensayo; esto no demuestra que sus medias sean iguales."
    )

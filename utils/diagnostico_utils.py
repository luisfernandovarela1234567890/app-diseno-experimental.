"""Pruebas y gráficos para revisar supuestos de un DCA."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from statsmodels.regression.linear_model import RegressionResultsWrapper


def residuos_y_ajustados(
    modelo: RegressionResultsWrapper,
) -> tuple[pd.Series, pd.Series]:
    """Extrae residuos y valores ajustados de un modelo lineal.

    Args:
        modelo: Modelo OLS ajustado para el ensayo.

    Returns:
        Una tupla con los residuos y los valores ajustados, en ese orden.
    """
    # Residuo e_ij = y_ij - y_hat_ij; y_hat_ij es la respuesta estimada por el modelo.
    residuos = pd.Series(modelo.resid, name="Residuos")
    ajustados = pd.Series(modelo.fittedvalues, name="Valores ajustados")
    return residuos, ajustados


def prueba_shapiro(
    residuos: pd.Series | np.ndarray,
    alfa: float = 0.05,
) -> tuple[float, float, str]:
    """Evalúa la normalidad de los residuos con Shapiro-Wilk.

    Args:
        residuos: Residuos del modelo DCA.
        alfa: Nivel de significancia para la decisión.

    Returns:
        Estadístico W, p-valor y conclusión en español.

    Raises:
        ValueError: Si alfa no está entre cero y uno o hay menos de tres residuos finitos.
    """
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")
    valores = np.asarray(residuos, dtype=float).reshape(-1)
    if not np.isfinite(valores).all() or valores.size < 3:
        raise ValueError("Shapiro-Wilk requiere al menos tres residuos finitos.")

    # Shapiro-Wilk contrasta H0: los residuos provienen de una distribución normal.
    resultado = stats.shapiro(valores)
    estadistico = float(resultado.statistic)
    p_valor = float(resultado.pvalue)
    if p_valor < alfa:
        conclusion = (
            f"Se rechaza la normalidad de los residuos (p-valor = {p_valor:.4g} < "
            f"alfa = {alfa:g}); revisa este supuesto antes de interpretar el ANOVA."
        )
    else:
        conclusion = (
            f"No se rechaza la normalidad de los residuos (p-valor = {p_valor:.4g} >= "
            f"alfa = {alfa:g}); la prueba no detecta evidencia suficiente de desviación."
        )
    return estadistico, p_valor, conclusion


def prueba_levene(
    df: pd.DataFrame,
    col_trat: str,
    col_resp: str,
    alfa: float = 0.05,
) -> tuple[float, float, str]:
    """Evalúa la homogeneidad de varianzas con Levene centrada en la mediana.

    Args:
        df: Datos del ensayo.
        col_trat: Nombre de la columna que identifica los tratamientos.
        col_resp: Nombre de la columna de respuesta numérica.
        alfa: Nivel de significancia para la decisión.

    Returns:
        Estadístico de Levene, p-valor y conclusión en español.

    Raises:
        ValueError: Si alfa no es válido, faltan columnas o hay menos de dos
            tratamientos con dos observaciones cada uno.
    """
    if not 0 < alfa < 1:
        raise ValueError("El nivel alfa debe estar entre cero y uno.")
    columnas_faltantes = [
        columna for columna in (col_trat, col_resp) if columna not in df.columns
    ]
    if columnas_faltantes:
        raise ValueError(f"Faltan columnas requeridas: {', '.join(columnas_faltantes)}.")

    # Levene compara la dispersión de cada grupo alrededor de su mediana (center='median').
    grupos = [
        grupo[col_resp].dropna().to_numpy(dtype=float)
        for _, grupo in df.groupby(col_trat, observed=True)
    ]
    if len(grupos) < 2 or any(grupo.size < 2 for grupo in grupos):
        raise ValueError("Levene requiere al menos dos tratamientos con dos datos cada uno.")
    resultado = stats.levene(*grupos, center="median")
    estadistico = float(resultado.statistic)
    p_valor = float(resultado.pvalue)
    if p_valor < alfa:
        conclusion = (
            f"Se rechaza la igualdad de varianzas (p-valor = {p_valor:.4g} < alfa = "
            f"{alfa:g}); hay evidencia de varianzas distintas entre tratamientos."
        )
    else:
        conclusion = (
            f"No se rechaza la igualdad de varianzas (p-valor = {p_valor:.4g} >= "
            f"alfa = {alfa:g}); la prueba no detecta evidencia suficiente de varianzas distintas."
        )
    return estadistico, p_valor, conclusion


def grafico_residuos_vs_ajustados(modelo: RegressionResultsWrapper) -> go.Figure:
    """Crea un gráfico de residuos frente a valores ajustados.

    Args:
        modelo: Modelo OLS ajustado para el ensayo.

    Returns:
        Figura Plotly para inspeccionar patrones y cambios en la dispersión.
    """
    residuos, ajustados = residuos_y_ajustados(modelo)
    datos_grafico = pd.DataFrame(
        {"Valores ajustados": ajustados, "Residuos": residuos}
    )
    # Una nube aleatoria alrededor de cero, sin patrón de embudo, es compatible con varianza constante.
    figura = px.scatter(
        datos_grafico,
        x="Valores ajustados",
        y="Residuos",
        labels={
            "Valores ajustados": "Valores ajustados",
            "Residuos": "Residuos",
        },
    )
    figura.add_hline(y=0, line_dash="dash", line_color="gray")
    return figura


def grafico_qq(residuos: pd.Series | np.ndarray) -> go.Figure:
    """Crea un gráfico Q-Q normal para los residuos del modelo.

    Args:
        residuos: Residuos del modelo DCA.

    Returns:
        Figura Plotly para comparar cuantiles observados y normales teóricos.

    Raises:
        ValueError: Si hay menos de dos residuos finitos.
    """
    valores = np.asarray(residuos, dtype=float).reshape(-1)
    if not np.isfinite(valores).all() or valores.size < 2:
        raise ValueError("El gráfico Q-Q requiere al menos dos residuos finitos.")

    # El gráfico Q-Q compara cuantiles residuales observados con cuantiles teóricos normales.
    (cuantiles_teoricos, cuantiles_observados), (pendiente, intercepto, _) = (
        stats.probplot(valores, dist="norm", fit=True)
    )
    datos_grafico = pd.DataFrame(
        {
            "Cuantiles teóricos normales": cuantiles_teoricos,
            "Cuantiles observados de residuos": cuantiles_observados,
        }
    )
    figura = px.scatter(
        datos_grafico,
        x="Cuantiles teóricos normales",
        y="Cuantiles observados de residuos",
    )
    x_linea = np.asarray(cuantiles_teoricos)
    figura.add_trace(
        go.Scatter(
            x=x_linea,
            y=pendiente * x_linea + intercepto,
            mode="lines",
            name="Referencia normal",
        )
    )
    return figura

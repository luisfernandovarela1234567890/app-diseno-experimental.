# Instrucciones para GitHub Copilot

## Contexto del proyecto

- Este repositorio contiene una aplicación de Diseño Experimental desarrollada en Python y Streamlit para el curso de Diseño Experimental de Ingeniería Agrícola de la Universidad de Sucre.
- La aplicación debe servir como apoyo académico para estudiantes de Ingeniería Agrícola.

## Estructura del proyecto

- `app.py`: portada de la aplicación.
- `pages/`: una página por cada diseño experimental.
- `utils/`: funciones reutilizables; debe incluir `__init__.py`.
- `data/`: archivos CSV de ejemplo.
- `verificacion/`: scripts de R para verificar los análisis.

Respeta esta organización al crear o modificar código. Coloca cada componente en el directorio que le corresponde y reutiliza las funciones existentes cuando sea posible.

## Idioma y documentación

- Escribe en español todo el código nuevo, los comentarios, los docstrings y los mensajes visibles en la interfaz.
- En cada paso estadístico agrega un comentario que explique qué se calcula y por qué, con una explicación apropiada para estudiantes de Ingeniería Agrícola.
- Todas las funciones deben incluir anotaciones de tipos (*type hints*) y docstrings con estilo Google, redactados en español.

## Dependencias permitidas

Utiliza únicamente estas librerías: `streamlit`, `pandas`, `numpy`, `scipy`, `statsmodels`, `plotly` y `openpyxl`. No agregues otras dependencias sin pedir permiso.

## Análisis estadístico

- Ajusta los modelos de ANOVA con `statsmodels.formula.api.ols` y calcula la tabla con `statsmodels.stats.anova.anova_lm`, usando `typ=2`.
- Realiza las comparaciones de Tukey con `statsmodels.stats.multicomp.pairwise_tukeyhsd`.
- No inventes, estimes manualmente ni escribas resultados numéricos de ejemplo como si fueran resultados del análisis. Todos los números presentados como resultados deben proceder del cálculo ejecutado con los datos correspondientes.

## Verificación

Antes de terminar cada tarea, ejecuta el código pertinente y corrige los errores que aparezcan. Si no es posible ejecutar alguna verificación, indícalo claramente y explica el motivo.

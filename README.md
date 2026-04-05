# Modelo Predictivo de Incendios Forestales


Proyecto de Ciencia de Datos enfocado en la predicción y análisis de incendios forestales utilizando datos de la NASA,GOOGLE y CONAFOR.

##  Arquitectura de Datos
Este es el modelo Entidad-Relación que utilizaremos para estructurar nuestro Cubo OLAP:

![Modelo Entidad Relación](./doc/Drawing%202026-03-22%2009.50.44.svg)

## 📁 Estructura del Proyecto
- **01_OBTENER:** Scripts para recolectar datos de las API
- **02_LIMPIAR:** Procesamiento y limpieza de variables climáticas.
- **03_MODELAR:** Construcción del Cubo OLAP (SQLite).
- **04_INTERPRETAR:** Visualización y conclusiones
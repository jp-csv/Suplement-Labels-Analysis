# App · Buscador de suplementos herbales

App de Streamlit para explorar las 67,449 etiquetas herbales del DSLD, pensada para **desarrollo de producto**.

![Buscador](capturas/buscador.png)

## Secciones

- **Buscador:** filtra por ingrediente, palabra o frase del título, marca, forma, atributos de la etiqueta (*Vegan*, *Organic*, *Gluten Free*…), estatus y año de entrada. Muestra indicadores, formas, marcas, con qué se combina, atributos declarados, dosis (si eliges un ingrediente) y palabras de los títulos. Abajo, la lista de productos con link a la etiqueta original en el DSLD y descarga en CSV.
- **Dosis de referencia:** para un ingrediente, el rango de dosis declaradas por forma (P10 a P90, mitad central y mediana).
- **Huecos de mercado:** mapa de ingrediente × forma con el número (o porcentaje) de etiquetas.
- **Comparar marcas:** hasta tres marcas lado a lado.

Los filtros de la barra lateral se aplican a todas las secciones (en *Comparar marcas* se ignora el filtro de marca).

## Detalles

- **Variantes del nombre:** con la casilla activada, «turmeric» también incluye «turmeric co2», «turmeric 95»… (nombres que contienen esa palabra completa).
- **Dosis:** una por etiqueta (si se repite, la mediana); se convierten g y mcg a mg y se omiten otras unidades (UI, mL). Es la dosis por porción declarada.
- **Cargas masivas:** por defecto se excluyen TerraVita Premium Collection, TerraVita, Herbal Terra y Hawaii Pharm.
- Se muestran hasta 1,000 productos en la tabla; la descarga trae todos.

## Datos

`datos/` contiene tres archivos Parquet generados con `utilidades/preparar_datos.py`:

- `etiquetas.parquet`: una fila por etiqueta (producto, marca, tipo, forma, estatus, año de entrada, porción, contenido, link, si tiene mezcla).
- `ingredientes.parquet`: una fila por ingrediente declarado (nombre original y limpio, categoría, cantidad y unidad).
- `atributos.parquet`: una fila por etiqueta y atributo declarado (del JSON del DSLD).

## Correrla en local

Desde la raíz del repositorio:

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

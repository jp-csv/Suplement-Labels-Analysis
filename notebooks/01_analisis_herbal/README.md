# 01 · Análisis del mercado herbal

Notebook: `DSLD_herbal_analisis.ipynb`. Responde, con las etiquetas de suplementos herbales del DSLD, cómo es el mercado y qué espacios deja.

## Qué necesita

En tu Drive, en `MyDrive/dsld/`:
- `DSLD-full-database-CSV.zip` (obligatorio)
- `DSLD-full-database-JSON.zip` (para los atributos por año; sin él se omite solo esa sección)

## Cómo se ejecuta

Ábrelo en Colab y usa *Entorno de ejecución → Ejecutar todo*. La sección «Campos extra del JSON» crea `MyDrive/dsld/dsld_json_extra.csv` la primera vez (varios minutos) y después lo reutiliza.

Para ejecutarlo en local, define las variables de entorno `DSLD_DATA_DIR` (carpeta con los CSV descomprimidos), `DSLD_OUT_DIR` (salida), `DSLD_EXTRA_CSV` (ruta de `dsld_json_extra.csv`) y, si quieres generarlo, `DSLD_JSON_ZIP`.

## Secciones del notebook

| # | Sección | Qué responde |
|---|---|---|
| 1 | Configuración y estilo | Rutas, paleta azul, funciones de gráficas |
| 2 | Carga de datos | Lee las tablas del CSV |
| 3 | Segmento herbal | Define las 67,449 etiquetas y advierte de las cargas masivas |
| 4 | Ingredientes y limpieza | Limpia nombres de ingredientes botánicos |
| 5 | Ingredientes | ¿Cuáles aparecen más? |
| 6 | Formatos | ¿En qué formas se vende y cuánto se descontinúa cada una? |
| 7 | Rotación | ¿Qué ingredientes se descontinúan más? |
| 8 | Marcas | ¿Quién concentra el mercado? |
| 9 | Combinaciones | ¿Qué ingredientes se combinan más? |
| 10 | Dosis | ¿Qué dosis se declaran en cápsulas? |
| 11 | Ingredientes por formato | ¿Qué ingredientes dominan en cada forma? |
| 12 | Mezclas por forma | ¿En qué formas abundan las mezclas? |
| 13 | Palabras en títulos | ¿Qué palabras usan las marcas, además del ingrediente? (incluye el top 50) |
| 14 | Atributos por año | ¿Lo vegano o lo «sin azúcar» crece o cae? |
| 15 | Conclusiones y limitaciones | Resumen y advertencias |
| 16 | Exportar tablas | Guarda las tablas en CSV |
| 17 | Dashboard resumen | Seis análisis en una sola imagen |

## Qué genera

En `MyDrive/dsld/salida/`:

- `figuras/`: `00_dashboard.png` y una imagen por análisis (`01_ingredientes_top20` … `10_atributos_por_anio`). En `figuras/` de esta carpeta hay un ejemplo de cada una.
- `tablas/`: `ingredientes_top20`, `formas`, `rotacion_ingredientes`, `marcas_top10`, `combinaciones`, `dosis_capsulas`, `ingredientes_por_forma`, `mezclas_por_forma`, `palabras_titulo_top50`, además de `herbal_productos` y `herbal_ingredientes_botanicos` (datos limpios del segmento, útiles para Tableau o Power BI).

## Cosas que conviene saber

- **Cargas masivas:** TerraVita Premium Collection, TerraVita, Herbal Terra y Hawaii Pharm subieron 13,933 etiquetas por lotes. Los análisis de formatos, ingredientes, marcas, combinaciones, dosis y rotación usan **todas** las etiquetas; los de mezclas, títulos y atributos por año las excluyen (y este último también excluye marcas con más de 300 etiquetas).
- **Año de entrada = captura en el DSLD**, no lanzamiento.
- **Nombres de ingredientes:** se limpian de forma simple (minúsculas, sin paréntesis ni palabras como *organic*, *extract*, *root*). *echinacea* y *echinacea angustifolia* quedan separadas.
- **Dosis:** se excluyen la bioperina (potenciador) y la uva (nombre ambiguo); es la dosis declarada por porción.
- **Mezclas:** cuenta cualquier ingrediente de categoría *blend*, incluidas mezclas con nombre comercial.
- **Palabras en títulos:** el tema de cada palabra (atributo, beneficio, potencia…) sale de una lista hecha a mano; algunos términos son fragmentos (*john wort* es *St. John's wort*).
- Para ir a un ingrediente o palabra concretos, usa el buscador (`../02_buscador_herbal/`).

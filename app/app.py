"""
Buscador de suplementos herbales (DSLD, NIH).

App de Streamlit para explorar las etiquetas herbales del Dietary Supplement Label Database:
buscar por ingrediente, palabra del título, marca, forma o atributo, y ver gráficas, dosis
de referencia, huecos de mercado y comparaciones entre marcas.
"""
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Buscador de suplementos herbales", page_icon="🌿", layout="wide")

# --- Estilo ------------------------------------------------------------------------------
INK, INK_2, INK_3 = "#0b0b0b", "#52514e", "#8a8985"
GRID, AXIS = "#e6e5e1", "#c9c8c3"
BLUE, BLUE_DARK, BLUE_LIGHT = "#2a78d6", "#184f95", "#6da7ec"
RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ESTATUS_COLORES = alt.Scale(domain=["En mercado", "Descontinuado"], range=[BLUE_DARK, BLUE_LIGHT])
MARCAS_COLORES = [BLUE_DARK, BLUE, BLUE_LIGHT]

COMBINABLES = {"botanical", "vitamin", "mineral", "amino acid", "enzyme", "fatty acid",
               "non-nutrient/non-botanical", "animal part or source", "protein", "fiber"}
ATRIBUTOS_CLAVE = ["Gluten Free", "Dairy Free", "Vegetarian", "Vegan", "Sugar Free", "Organic", "Kosher", "Halal"]
A_MG = {"mg": 1.0, "Gram(s)": 1000.0, "g": 1000.0, "mcg": 0.001}

SIN_VALOR = set("the and with for of plus from by in to a an or your our all as per".split())
UNIDADES = set("mg mcg ml oz fl ct count capsules capsule caps cap tablets tablet tabs tab softgels softgel "
               "gummies gummy liquid powder drops fluid ounce ounces gram grams gm lb lbs pack pk each "
               "bottle serving servings vcaps vcap veggie".split())


def alto_barras(filas):
    return 34 * max(filas, 1) + 70


def estilizar(grafica, alto=None):
    if alto is not None:
        grafica = grafica.properties(height=alto)
    return (grafica
            .configure(font="sans-serif")
            .configure_view(strokeWidth=0)
            .configure_axis(gridColor=GRID, domainColor=AXIS, tickColor=AXIS, labelColor=INK_2,
                            titleColor=INK_2, labelFontSize=12, titleFontSize=12, titleFontWeight="normal")
            .configure_legend(labelColor=INK_2, titleColor=INK_2, orient="bottom", labelFontSize=12,
                              titleFontSize=12)
            .configure_title(color=INK, fontSize=15, anchor="start", subtitleColor=INK_2, subtitleFontSize=12))


def mostrar(grafica, alto=None):
    st.altair_chart(estilizar(grafica, alto), width="stretch", theme=None)


def titulo(texto, sub=None):
    return alt.TitleParams(texto, subtitle=sub or "", anchor="start")


# --- Datos -------------------------------------------------------------------------------
DATOS = Path(__file__).parent / "datos"


@st.cache_resource(show_spinner="Cargando datos…")
def cargar():  # recurso compartido: no se modifica después de cargarlo
    e = pd.read_parquet(DATOS / "etiquetas.parquet")
    i = pd.read_parquet(DATOS / "ingredientes.parquet")
    a = pd.read_parquet(DATOS / "atributos.parquet")
    for df in (e, i, a):
        for c in df.columns:
            if isinstance(df[c].dtype, pd.CategoricalDtype):
                df[c] = df[c].astype(str)
    i["mg"] = i["cantidad"] * i["unidad"].map(A_MG)
    return e, i, a


etiquetas, ingredientes, atributos = cargar()


@st.cache_resource
def opciones():
    por_ing = ingredientes.groupby("ingrediente")["dsld_id"].nunique().sort_values(ascending=False)
    por_ing = por_ing[por_ing >= 3]
    por_marca = etiquetas["marca"].value_counts()
    por_forma = etiquetas["forma"].value_counts()
    por_atr = atributos["atributo"].value_counts()
    return por_ing, por_marca, por_forma, por_atr


ING_N, MARCA_N, FORMA_N, ATR_N = opciones()


def palabras(texto):
    texto = texto.lower().replace("&", " and ")
    return [t for t in re.findall(r"[a-z]+", texto) if len(t) >= 3 and t not in SIN_VALOR and t not in UNIDADES]


def pct(x):
    return "<1 %" if 0 < x < 0.005 else f"{x:.0%}".replace("%", " %")


# --- Barra lateral: filtros --------------------------------------------------------------
st.sidebar.title("Filtros")
st.sidebar.caption("Se aplican a todas las secciones. Los nombres están en inglés, como en el DSLD.")

sel_ing = st.sidebar.multiselect(
    "Ingrediente", ING_N.index.tolist(), format_func=lambda n: f"{n} ({ING_N[n]:,})",
    placeholder="Escribe para buscar, p. ej. turmeric", select_all=False)
variantes = st.sidebar.checkbox("Incluir variantes del nombre", value=True,
                                help="Con «turmeric» también cuenta «turmeric co2», «turmeric 95 %», «organic turmeric root»…")
modo_ing = "todos"
if len(sel_ing) > 1:
    modo_ing = st.sidebar.radio("La etiqueta debe tener", ["todos", "al menos uno"], horizontal=True)
texto = st.sidebar.text_input("Palabra o frase en el título", placeholder="p. ej. immune, alcohol free")
sel_marca = st.sidebar.multiselect("Marca", MARCA_N.index.tolist(), format_func=lambda n: f"{n} ({MARCA_N[n]:,})",
                                   placeholder="Todas", select_all=False)
sel_forma = st.sidebar.multiselect("Forma", FORMA_N.index.tolist(), placeholder="Todas", select_all=False)
sel_atr = st.sidebar.multiselect("Atributos de la etiqueta", ATR_N.index.tolist(),
                                 format_func=lambda n: f"{n} ({ATR_N[n]:,})",
                                 placeholder="Cualquiera", select_all=False,
                                 help="Declarados por el fabricante. Si eliges varios, la etiqueta debe tenerlos todos.")
sel_estatus = st.sidebar.radio("Estatus", ["Todos", "En mercado", "Descontinuado"], horizontal=True)
anio_min, anio_max = int(etiquetas["anio_entrada"].min()), int(etiquetas["anio_entrada"].max())
sel_anios = st.sidebar.slider("Año de entrada al DSLD", anio_min, anio_max, (anio_min, anio_max),
                              help="Fecha en que se capturó la etiqueta, no de lanzamiento.")
excluir_masiva = st.sidebar.checkbox(
    "Excluir marcas de carga masiva", value=True,
    help="TerraVita Premium Collection, TerraVita, Herbal Terra y Hawaii Pharm subieron miles de etiquetas de golpe.")


NOMBRES = st.cache_resource(lambda: pd.Series(sorted(ingredientes["ingrediente"].unique())))()


def nombres_de(nombre):
    # El nombre exacto o, con «variantes», todos los que contienen esas palabras completas.
    if not variantes:
        return [nombre]
    return NOMBRES[NOMBRES.str.contains(r"\b" + re.escape(nombre) + r"\b", regex=True)].tolist()


def ids_de_ingrediente(nombre):
    return set(ingredientes.loc[ingredientes["ingrediente"].isin(nombres_de(nombre)), "dsld_id"])


def filtrar(con_marca=True):
    e = etiquetas
    if excluir_masiva:
        e = e[~e["carga_masiva"]]
    if sel_ing:
        conjuntos = [ids_de_ingrediente(n_) for n_ in sel_ing]
        ids = set.intersection(*conjuntos) if modo_ing == "todos" else set.union(*conjuntos)
        e = e[e["dsld_id"].isin(ids)]
    if texto.strip():
        patron = r"\b" + re.escape(texto.strip().lower()) + r"\b"
        e = e[e["producto"].str.lower().str.contains(patron, regex=True)]
    if con_marca and sel_marca:
        e = e[e["marca"].isin(sel_marca)]
    if sel_forma:
        e = e[e["forma"].isin(sel_forma)]
    if sel_atr:
        for atr in sel_atr:
            e = e[e["dsld_id"].isin(atributos.loc[atributos["atributo"] == atr, "dsld_id"])]
    if sel_estatus != "Todos":
        e = e[e["estatus"] == sel_estatus]
    e = e[e["anio_entrada"].between(*sel_anios)]
    return e


sub = filtrar()
universo = etiquetas[~etiquetas["carga_masiva"]] if excluir_masiva else etiquetas
n = len(sub)
ids_sub = set(sub["dsld_id"])
ing_sub = ingredientes[ingredientes["dsld_id"].isin(ids_sub)]

st.title("Buscador de suplementos herbales")
st.caption("Etiquetas del Dietary Supplement Label Database (DSLD, NIH) de tipo *Botanical* o "
           "*Botanical with Nutrients*. Los conteos son de etiquetas, no de productos distintos.")

SECCIONES = ["🔎 Buscador", "💊 Dosis de referencia", "🧩 Huecos de mercado", "⚖️ Comparar marcas", "ℹ️ Acerca de"]
# Solo se calcula la sección elegida (más rápido que pestañas, que calculan todo en cada cambio).
seccion = st.segmented_control("Sección", SECCIONES, default=SECCIONES[0], label_visibility="collapsed") or SECCIONES[0]


# --- Funciones de gráficas ----------------------------------------------------------------
def apilado_estatus(df, campo, top, titulo_txt, sub_txt):
    conteo = df.groupby([campo, "estatus"]).size().reset_index(name="etiquetas")
    totales = conteo.groupby(campo)["etiquetas"].sum().sort_values(ascending=False).head(top)
    conteo = conteo[conteo[campo].isin(totales.index)]
    orden = totales.index.tolist()
    barras = alt.Chart(conteo).mark_bar(stroke="white", strokeWidth=1.5).encode(
        y=alt.Y(f"{campo}:N", sort=orden, title=None, axis=alt.Axis(labelLimit=220)),
        x=alt.X("etiquetas:Q", title="Etiquetas", stack="zero", axis=alt.Axis(format=",d", tickMinStep=1)),
        color=alt.Color("estatus:N", scale=ESTATUS_COLORES, title=None),
        order=alt.Order("estatus:N", sort="descending"),
        tooltip=[alt.Tooltip(f"{campo}:N", title=campo.capitalize()), alt.Tooltip("estatus:N", title="Estatus"),
                 alt.Tooltip("etiquetas:Q", title="Etiquetas", format=",")])
    tot = totales.reset_index(name="total")
    tot["texto"] = tot["total"].map(lambda v: f"{v:,}")
    etiquetas_txt = alt.Chart(tot).mark_text(align="left", dx=4, color=INK_2, fontSize=11).encode(
        y=alt.Y(f"{campo}:N", sort=orden), x="total:Q", text="texto:N")
    return (barras + etiquetas_txt).properties(title=titulo(titulo_txt, sub_txt), height=alto_barras(len(orden)))


def barras_pct(df, campo, valor, titulo_txt, sub_txt, color=BLUE):
    df = df.copy()
    df["texto"] = df[valor].map(lambda v: f"{v:.0f} %" if v >= 1 or v == 0 else "<1 %")
    base = alt.Chart(df).encode(y=alt.Y(f"{campo}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)))
    barras = base.mark_bar(color=color).encode(
        x=alt.X(f"{valor}:Q", title="% de las etiquetas", scale=alt.Scale(domain=[0, max(df[valor].max() * 1.2, 1)])),
        tooltip=[alt.Tooltip(f"{campo}:N", title=" "), alt.Tooltip(f"{valor}:Q", title="%", format=".1f")])
    txt = base.mark_text(align="left", dx=4, color=INK_2, fontSize=11).encode(x=f"{valor}:Q", text="texto:N")
    return (barras + txt).properties(title=titulo(titulo_txt, sub_txt), height=alto_barras(len(df)))


def dosis_por_etiqueta(filas):
    d = filas.dropna(subset=["mg"])
    d = d[d["mg"] > 0]
    return d.groupby("dsld_id")["mg"].median()


# =========================================================================================
# 1. Buscador
# =========================================================================================
if seccion == SECCIONES[0]:
    if n == 0:
        st.warning("Ninguna etiqueta cumple todos los filtros. Quita alguno o prueba otra palabra (en inglés).")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Etiquetas", f"{n:,}", help="Etiquetas que cumplen los filtros")
        c1.caption(f"{pct(n / len(universo))} del segmento herbal")
        c2.metric("Marcas distintas", f"{sub['marca'].nunique():,}")
        c3.metric("Siguen en el mercado", pct((sub["estatus"] == "En mercado").mean()))
        c4.metric("Tienen una mezcla", pct(sub["tiene_mezcla"].mean()),
                  help="Al menos un ingrediente de categoría *blend* (mezcla propietaria o complejo con nombre comercial)")

        col1, col2 = st.columns(2)
        with col1:
            mostrar(apilado_estatus(sub, "forma", 7, "Formas de presentación", "Etiquetas por estatus de mercado"))
        with col2:
            mostrar(apilado_estatus(sub, "marca", 10, "Marcas con más etiquetas", "Etiquetas por estatus de mercado"))

        col1, col2 = st.columns(2)
        with col1:
            solo_bot = st.toggle("Solo ingredientes botánicos", value=True,
                                 help="Desactívalo para incluir vitaminas, minerales y otros nutrientes.")
            categorias = {"botanical"} if solo_bot else COMBINABLES
            elegidos = {x for n_ in sel_ing for x in nombres_de(n_)}
            otros = ing_sub[ing_sub["categoria"].isin(categorias) & ~ing_sub["ingrediente"].isin(elegidos)]
            acomp = otros.groupby("ingrediente")["dsld_id"].nunique().sort_values(ascending=False).head(10)
            if len(acomp):
                df = (acomp / n * 100).rename("pct").reset_index()
                sub_txt = "% de las etiquetas que también lo contienen" if sel_ing else "% de las etiquetas que lo contienen"
                mostrar(barras_pct(df, "ingrediente", "pct",
                                   "Con qué se combina" if sel_ing else "Ingredientes más frecuentes", sub_txt))
            else:
                st.info("Estas etiquetas no tienen otros ingredientes.")
        with col2:
            atr = atributos[atributos["dsld_id"].isin(ids_sub) & atributos["atributo"].isin(ATRIBUTOS_CLAVE)]
            df = (atr.groupby("atributo")["dsld_id"].nunique() / n * 100).reindex(ATRIBUTOS_CLAVE, fill_value=0)
            df = df.rename("pct").reset_index()
            mostrar(barras_pct(df, "atributo", "pct", "Atributos declarados",
                               "% de las etiquetas con cada atributo", color=BLUE_DARK))

        col1, col2 = st.columns(2)
        with col1:
            if len(sel_ing) == 1:
                dosis = dosis_por_etiqueta(ing_sub[ing_sub["ingrediente"].isin(nombres_de(sel_ing[0]))])
                if len(dosis) >= 10:
                    tope = dosis.quantile(0.95)
                    df = dosis[dosis <= tope].rename("mg").reset_index()
                    med = dosis.median()
                    hist = alt.Chart(df).mark_bar(color=BLUE, stroke="white", strokeWidth=1).encode(
                        x=alt.X("mg:Q", bin=alt.Bin(maxbins=25), title="mg por porción (sin el 5 % más alto)"),
                        y=alt.Y("count():Q", title="Etiquetas"),
                        tooltip=[alt.Tooltip("count():Q", title="Etiquetas")])
                    linea = alt.Chart(pd.DataFrame({"mg": [med]})).mark_rule(color=BLUE_DARK, strokeWidth=2).encode(x="mg:Q")
                    mostrar((hist + linea).properties(
                        title=titulo(f"Dosis declaradas de {sel_ing[0]}: mediana {med:,.0f} mg (línea)",
                                     f"Una dosis por etiqueta (n = {len(dosis):,}); g y mcg convertidos a mg")), 300)
                else:
                    st.info(f"Pocas dosis en mg para {sel_ing[0]} con estos filtros (n = {len(dosis)}).")
            else:
                st.info("Elige **un** ingrediente para ver sus dosis declaradas. "
                        "La pestaña *Dosis de referencia* las desglosa por forma.")
        with col2:
            excluir = set(palabras(texto)) | {w for n_ in sel_ing for w in palabras(n_)}
            excluir |= {w for m in sub["marca"].unique() for w in palabras(m)}
            conteo = {}
            for t in sub["producto"]:
                for w in set(palabras(t)) - excluir:
                    conteo[w] = conteo.get(w, 0) + 1
            top = sorted(conteo.items(), key=lambda kv: -kv[1])[:10]
            if top:
                df = pd.DataFrame(top, columns=["palabra", "etiquetas"])
                df["pct"] = df["etiquetas"] / n * 100
                mostrar(barras_pct(df, "palabra", "pct", "Palabras en sus títulos",
                                   "% de las etiquetas (sin marca, unidades ni lo que buscaste)"))

        st.subheader(f"Productos ({n:,})")
        MAX_FILAS = 1000
        ordenadas = sub.sort_values(["marca", "producto"])

        def armar_tabla(df):
            filas_ing = ingredientes[ingredientes["dsld_id"].isin(df["dsld_id"]) & ingredientes["categoria"].isin(COMBINABLES)]
            ing_txt = filas_ing.groupby("dsld_id")["original"].apply(lambda s: ", ".join(dict.fromkeys(s)))
            return df.assign(ingredientes=df["dsld_id"].map(ing_txt).fillna(""))[
                ["producto", "marca", "forma", "estatus", "anio_entrada", "porcion", "ingredientes", "url"]]

        st.dataframe(
            armar_tabla(ordenadas.head(MAX_FILAS)), hide_index=True, height=420,
            column_config={
                "producto": st.column_config.TextColumn("Producto", width="large"),
                "marca": "Marca", "forma": "Forma", "estatus": "Estatus",
                "anio_entrada": st.column_config.NumberColumn("Año de entrada", format="%d"),
                "porcion": "Porción",
                "ingredientes": st.column_config.TextColumn("Ingredientes", width="large"),
                "url": st.column_config.LinkColumn("Etiqueta", display_text="Ver en DSLD"),
            })
        if n > MAX_FILAS:
            st.caption(f"Se muestran las primeras {MAX_FILAS:,} (por marca y producto). La descarga trae las {n:,}.")
        st.download_button("Descargar lista completa (CSV)",
                           lambda: armar_tabla(ordenadas).to_csv(index=False).encode("utf-8-sig"),
                           file_name="productos_filtrados.csv", mime="text/csv", on_click="ignore")


# =========================================================================================
# 2. Dosis de referencia
# =========================================================================================
if seccion == SECCIONES[1]:
    st.markdown("Rango de dosis declaradas de un ingrediente **por forma de presentación**, dentro de las "
                "etiquetas que cumplen los filtros. Sirve como referencia al formular.")
    opciones_dosis = [x for x in ING_N.index[:600]]
    defecto = sel_ing[0] if len(sel_ing) == 1 and sel_ing[0] in opciones_dosis else (
        "ashwagandha" if "ashwagandha" in opciones_dosis else opciones_dosis[0])
    ing_d = st.selectbox("Ingrediente", opciones_dosis, index=opciones_dosis.index(defecto),
                         format_func=lambda x: f"{x} ({ING_N[x]:,})")
    filas = ingredientes[ingredientes["ingrediente"].isin(nombres_de(ing_d)) & ingredientes["dsld_id"].isin(ids_sub)]
    dosis = dosis_por_etiqueta(filas).rename("mg").reset_index().merge(sub[["dsld_id", "forma"]], on="dsld_id")
    resumen = (dosis.groupby("forma")["mg"]
               .describe(percentiles=[.1, .25, .5, .75, .9])[["count", "10%", "25%", "50%", "75%", "90%"]])
    resumen.columns = ["n", "p10", "q1", "mediana", "q3", "p90"]
    resumen = resumen[resumen["n"] >= 10].sort_values("n", ascending=False)
    if resumen.empty:
        st.info("No hay suficientes dosis en mg (al menos 10 por forma) con estos filtros.")
    else:
        df = resumen.reset_index()
        df["forma_n"] = df.apply(lambda r: f"{r['forma']} (n = {int(r['n']):,})", axis=1)
        orden = df["forma_n"].tolist()
        base = alt.Chart(df).encode(y=alt.Y("forma_n:N", sort=orden, title=None, axis=alt.Axis(labelLimit=260)))
        ext = base.mark_rule(color=BLUE_LIGHT, strokeWidth=2).encode(x=alt.X("p10:Q", title="mg por porción"), x2="p90:Q")
        caja = base.mark_bar(color=BLUE, height=16).encode(x="q1:Q", x2="q3:Q")
        med = base.mark_point(filled=True, color="white", stroke=BLUE_DARK, strokeWidth=2, size=70).encode(
            x="mediana:Q",
            tooltip=[alt.Tooltip("forma:N", title="Forma"), alt.Tooltip("n:Q", title="Etiquetas", format=","),
                     alt.Tooltip("p10:Q", format=",.0f"), alt.Tooltip("q1:Q", title="Q1", format=",.0f"),
                     alt.Tooltip("mediana:Q", format=",.0f"), alt.Tooltip("q3:Q", title="Q3", format=",.0f"),
                     alt.Tooltip("p90:Q", format=",.0f")])
        mostrar((ext + caja + med).properties(title=titulo(
            f"Dosis declaradas de {ing_d} por forma",
            "Línea: P10 a P90 · barra: mitad central (Q1 a Q3) · punto: mediana")), 60 + 45 * len(df))
        tabla_d = resumen.round(0).astype(int).rename(columns={
            "n": "Etiquetas", "p10": "P10", "q1": "Q1", "mediana": "Mediana", "q3": "Q3", "p90": "P90"})
        tabla_d.index.name = "Forma"
        st.dataframe(tabla_d, width="stretch")
        st.caption("Dosis por **porción** tal como se declara en la etiqueta (una por etiqueta; si se repite, la mediana). "
                   "Se convierten g y mcg a mg; otras unidades (UI, mL) se omiten. El DSLD no distingue entre polvo "
                   "crudo y extracto estandarizado, así que un mismo ingrediente puede mezclar ambos.")


# =========================================================================================
# 3. Huecos de mercado
# =========================================================================================
if seccion == SECCIONES[2]:
    st.markdown("Cuántas etiquetas hay de cada **ingrediente botánico** en cada **forma**, dentro de los filtros. "
                "Las celdas claras son combinaciones con pocas etiquetas: pueden ser una oportunidad o una señal "
                "de poca demanda; el dato no distingue entre las dos.")
    c1, c2 = st.columns([1, 1])
    n_ing = c1.slider("Número de ingredientes", 10, 40, 20, step=5)
    modo = c2.radio("Mostrar", ["Etiquetas", "% de la forma"], horizontal=True)
    bot = ing_sub[ing_sub["categoria"] == "botanical"]
    top_ing = bot.groupby("ingrediente")["dsld_id"].nunique().sort_values(ascending=False).head(n_ing).index
    formas_top = sub["forma"].value_counts().head(7).index
    if len(top_ing) == 0:
        st.info("No hay ingredientes botánicos con estos filtros.")
    else:
        celdas = (bot[bot["ingrediente"].isin(top_ing)]
                  .merge(sub[["dsld_id", "forma"]], on="dsld_id")
                  .query("forma in @formas_top")
                  .groupby(["ingrediente", "forma"])["dsld_id"].nunique().rename("etiquetas"))
        rejilla = pd.MultiIndex.from_product([top_ing, formas_top], names=["ingrediente", "forma"])
        celdas = celdas.reindex(rejilla, fill_value=0).reset_index()
        tam_forma = sub["forma"].value_counts()
        celdas["pct"] = celdas["etiquetas"] / celdas["forma"].map(tam_forma) * 100
        valor = "etiquetas" if modo == "Etiquetas" else "pct"
        celdas["texto"] = celdas[valor].map(lambda v: f"{v:,.0f}" if valor == "etiquetas" else f"{v:.1f}")
        maximo = celdas[valor].max()
        celdas["claro"] = celdas[valor] < maximo * 0.55
        orden_formas = formas_top.tolist()
        base = alt.Chart(celdas).encode(
            x=alt.X("forma:N", sort=orden_formas, title=None, axis=alt.Axis(orient="top", labelAngle=0, labelLimit=120)),
            y=alt.Y("ingrediente:N", sort=top_ing.tolist(), title=None))
        rect = base.mark_rect(stroke="white", strokeWidth=2).encode(
            color=alt.Color(f"{valor}:Q", scale=alt.Scale(range=RAMP), title="Etiquetas" if valor == "etiquetas" else "% de la forma"),
            tooltip=[alt.Tooltip("ingrediente:N", title="Ingrediente"), alt.Tooltip("forma:N", title="Forma"),
                     alt.Tooltip("etiquetas:Q", title="Etiquetas", format=","),
                     alt.Tooltip("pct:Q", title="% de la forma", format=".1f")])
        txt = base.mark_text(fontSize=11).encode(
            text="texto:N",
            color=alt.condition("datum.claro", alt.value(INK), alt.value("white")))
        mostrar((rect + txt).properties(title=titulo(
            "Ingrediente × forma",
            "Etiquetas que contienen el ingrediente en cada forma" if valor == "etiquetas"
            else "% de las etiquetas de cada forma que contienen el ingrediente")), 26 * len(top_ing) + 60)


# =========================================================================================
# 4. Comparar marcas
# =========================================================================================
if seccion == SECCIONES[3]:
    st.markdown("Compara hasta **tres marcas** dentro de los filtros (aquí se ignora el filtro de marca).")
    base_m = filtrar(con_marca=False)
    marcas_disp = base_m["marca"].value_counts()
    marcas_disp = marcas_disp[marcas_disp > 0]
    if marcas_disp.empty:
        st.info("No hay marcas con estos filtros.")
    else:
        defecto = [m for m in sel_marca if m in marcas_disp.index][:3] or marcas_disp.index[:3].tolist()
        elegidas = st.multiselect("Marcas", marcas_disp.index.tolist(), default=defecto, max_selections=3,
                                  format_func=lambda m: f"{m} ({marcas_disp[m]:,})")
        if elegidas:
            colores = alt.Scale(domain=elegidas, range=MARCAS_COLORES[:len(elegidas)])
            cols = st.columns(len(elegidas))
            for col, m in zip(cols, elegidas):
                d = base_m[base_m["marca"] == m]
                col.markdown(f"**{m}**")
                col.metric("Etiquetas", f"{len(d):,}")
                col.metric("Siguen en el mercado", pct((d["estatus"] == "En mercado").mean()))
                col.metric("Tienen una mezcla", pct(d["tiene_mezcla"].mean()))

            dm = base_m[base_m["marca"].isin(elegidas)]
            tam = dm["marca"].value_counts()

            def alto_grupos(grupos):
                return 13 * grupos * len(elegidas) + 10 * grupos + 70

            def agrupadas(df, campo, titulo_txt, sub_txt):
                return alt.Chart(df).mark_bar().encode(
                    y=alt.Y(f"{campo}:N", title=None, sort=df.groupby(campo)["pct"].sum().sort_values(ascending=False).index.tolist(),
                            axis=alt.Axis(labelLimit=220)),
                    yOffset=alt.YOffset("marca:N", sort=elegidas),
                    x=alt.X("pct:Q", title="% de las etiquetas de la marca"),
                    color=alt.Color("marca:N", scale=colores, sort=elegidas, title=None),
                    tooltip=[alt.Tooltip("marca:N", title="Marca"), alt.Tooltip(f"{campo}:N", title=" "),
                             alt.Tooltip("pct:Q", title="%", format=".1f")]
                ).properties(title=titulo(titulo_txt, sub_txt))

            col1, col2 = st.columns(2)
            with col1:
                f = dm.groupby(["marca", "forma"]).size().rename("n").reset_index()
                f["pct"] = f["n"] / f["marca"].map(tam) * 100
                f = f[f["n"] > 0]
                mostrar(agrupadas(f, "forma", "Formas", "% de las etiquetas de cada marca"), alto_grupos(f["forma"].nunique()))
            with col2:
                a = atributos[atributos["dsld_id"].isin(dm["dsld_id"]) & atributos["atributo"].isin(ATRIBUTOS_CLAVE)]
                a = a.merge(dm[["dsld_id", "marca"]], on="dsld_id").groupby(["marca", "atributo"])["dsld_id"].nunique()
                a = a.rename("n").reset_index()
                a["pct"] = a["n"] / a["marca"].map(tam) * 100
                if len(a):
                    mostrar(agrupadas(a, "atributo", "Atributos declarados", "% de las etiquetas de cada marca"), alto_grupos(a["atributo"].nunique()))
                else:
                    st.info("Estas marcas no declaran atributos.")
            ib = ingredientes[ingredientes["dsld_id"].isin(dm["dsld_id"]) & (ingredientes["categoria"] == "botanical")]
            ib = ib.merge(dm[["dsld_id", "marca"]], on="dsld_id").groupby(["marca", "ingrediente"])["dsld_id"].nunique()
            ib = ib.rename("n").reset_index()
            ib["pct"] = ib["n"] / ib["marca"].map(tam) * 100
            tops = set(ib.sort_values("n", ascending=False).groupby("marca").head(6)["ingrediente"])
            ib = ib[ib["ingrediente"].isin(tops)]
            if len(ib):
                mostrar(agrupadas(ib, "ingrediente", "Ingredientes principales",
                                  "Los 6 más frecuentes de cada marca · % de las etiquetas de cada marca"),
                        alto_grupos(len(tops)))


# =========================================================================================
# 5. Acerca de
# =========================================================================================
if seccion == SECCIONES[4]:
    st.markdown(f"""
**Datos.** Descarga completa del [DSLD](https://dsld.od.nih.gov/) (NIH, Office of Dietary Supplements),
enero de 2026. Segmento herbal: {len(etiquetas):,} etiquetas de tipo *Botanical* o *Botanical with Nutrients*.

**Cómo leerlo**
- Los datos son lo **declarado en la etiqueta**; el NIH no verifica su exactitud.
- Se cuentan **etiquetas**, no productos distintos: una misma presentación puede tener varias (tamaños, sabores).
- El **año de entrada** es cuando se capturó la etiqueta en el DSLD, no cuando salió al mercado.
- Cuatro marcas (TerraVita Premium Collection, TerraVita, Herbal Terra y Hawaii Pharm) subieron miles de etiquetas
  de golpe; por defecto se excluyen.
- Los nombres de ingredientes se **limpian** de forma aproximada (minúsculas, sin paréntesis ni palabras como
  *organic*, *extract* o *root*): *turmeric root extract* cuenta como *turmeric*.
- Los atributos (*Vegan*, *Organic*…) los declara el fabricante.
- Son datos de EE. UU.; no equivalen al mercado mexicano.
""")

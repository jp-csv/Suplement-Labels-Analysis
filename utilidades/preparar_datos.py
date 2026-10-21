#!/usr/bin/env python3
"""
preparar_datos.py - Genera los archivos Parquet que usa la app de Streamlit.

Uso:
    python utilidades/preparar_datos.py CARPETA_CSV DSLD_JSON_EXTRA.csv [CARPETA_SALIDA]

(desde la raíz del repositorio)

CARPETA_CSV            carpeta con los CSV descomprimidos de la descarga completa del DSLD
DSLD_JSON_EXTRA.csv    archivo generado por utilidades/dsld_extract_json.py (atributos de etiqueta)
CARPETA_SALIDA         por defecto app/datos

Genera:
    etiquetas.parquet     una fila por etiqueta herbal
    ingredientes.parquet  una fila por ingrediente declarado (todas las categorías)
    atributos.parquet     una fila por etiqueta y atributo (Vegan, Organic, Gluten Free...)
"""
import glob
import os
import re
import sys

import pandas as pd

HERBAL = ["Botanical", "Botanical with Nutrients"]
CARGA_MASIVA = ["TerraVita Premium Collection", "TerraVita", "Herbal Terra", "Hawaii Pharm"]
FORMA_ES = {
    "Capsule": "Cápsula", "Liquid": "Líquido", "Powder": "Polvo", "Tablet or Pill": "Tableta o pastilla",
    "Softgel Capsule": "Cápsula blanda", "Gummy or Jelly": "Gomita o jalea",
    "Other (e.g. tea bag)": "Otra (p. ej., té)", "Lozenge": "Pastilla para chupar",
    "Unknown": "Desconocida", "Bar": "Barra",
}
RUIDO = (r"\b(organic|organically grown|certified|wildcrafted|raw|dried|dry|fresh|powdered|powder|"
         r"extract|extracts|standardized|whole|herb|herbs|root|roots|leaf|leaves|flower|flowers|"
         r"seed|seeds|bark|fruit|berry|aerial parts?|rhizome|bulb|stem|concentrate|juice|oil|"
         r"tincture|and|from)\b")


def limpiar(nombre):
    s = nombre.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9\s'-]", " ", s)
    s = re.sub(RUIDO, " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def cargar(carpeta, prefijo, columnas=None):
    archivos = sorted(glob.glob(os.path.join(carpeta, f"{prefijo}_*.csv")))
    if not archivos:
        sys.exit(f"No se encontraron {prefijo}_*.csv en {carpeta}")
    return pd.concat((pd.read_csv(f, dtype=str, keep_default_na=False, usecols=columnas) for f in archivos),
                     ignore_index=True)


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    carpeta, extra_csv = sys.argv[1], sys.argv[2]
    salida = sys.argv[3] if len(sys.argv) == 4 else os.path.join("app", "datos")
    os.makedirs(salida, exist_ok=True)
    quitar_codigo = lambda s: s.str.replace(r"\s*\[.*\]$", "", regex=True)

    # --- Etiquetas -------------------------------------------------------------------
    p = cargar(carpeta, "ProductOverview")
    p["tipo"] = quitar_codigo(p["Product Type [LanguaL]"])
    p = p[p["tipo"].isin(HERBAL)].copy()
    forma = quitar_codigo(p["Supplement Form [LanguaL]"])
    etiquetas = pd.DataFrame({
        "dsld_id": p["DSLD ID"].astype("int64"),
        "producto": p["Product Name"].str.strip(),
        "marca": p["Brand Name"].str.strip(),
        "tipo": p["tipo"],
        "forma": forma.map(FORMA_ES).fillna(forma),
        "estatus": p["Market Status"].map({"On Market": "En mercado", "Off Market": "Descontinuado"}),
        "anio_entrada": p["Date Entered into DSLD"].str[:4].astype("int16"),
        "porcion": p["Serving Size"].str.strip(),
        "contenido": p["Net Contents"].str.strip(),
        "url": p["URL"],
    })
    etiquetas["carga_masiva"] = etiquetas["marca"].isin(CARGA_MASIVA)

    # --- Ingredientes ----------------------------------------------------------------
    cols = ["DSLD ID", "Ingredient", "DSLD Ingredient Categories", "Amount Per Serving", "Amount Per Serving Unit"]
    i = cargar(carpeta, "DietarySupplementFacts", cols)
    i = i[i["DSLD ID"].isin(p["DSLD ID"])]
    ingredientes = pd.DataFrame({
        "dsld_id": i["DSLD ID"].astype("int64"),
        "original": i["Ingredient"].str.strip(),
        "ingrediente": i["Ingredient"].map(limpiar),
        "categoria": i["DSLD Ingredient Categories"],
        "cantidad": pd.to_numeric(i["Amount Per Serving"], errors="coerce").astype("float32"),
        "unidad": i["Amount Per Serving Unit"].str.strip(),
    }).dropna(subset=["ingrediente"])

    resumen = ingredientes.groupby("dsld_id").agg(
        n_ingredientes=("ingrediente", "size"),
        tiene_mezcla=("categoria", lambda s: (s == "blend").any()))
    etiquetas = etiquetas.merge(resumen, left_on="dsld_id", right_index=True, how="left")
    etiquetas["n_ingredientes"] = etiquetas["n_ingredientes"].fillna(0).astype("int16")
    etiquetas["tiene_mezcla"] = etiquetas["tiene_mezcla"].fillna(False).astype(bool)

    # --- Atributos (del JSON) --------------------------------------------------------
    x = pd.read_csv(extra_csv, dtype=str, keep_default_na=False, usecols=["dsld_id", "target_groups"])
    x = x[x["dsld_id"].astype("int64").isin(etiquetas["dsld_id"])]
    atributos = (x.assign(atributo=x["target_groups"].str.split(r" \| "))
                  .explode("atributo")[["dsld_id", "atributo"]])
    atributos = atributos[atributos["atributo"].str.strip() != ""]
    atributos["dsld_id"] = atributos["dsld_id"].astype("int64")
    atributos["atributo"] = atributos["atributo"].str.strip()

    # --- Guardar (categorías para que pese poco) ------------------------------------
    for df, cats in ((etiquetas, ["marca", "tipo", "forma", "estatus"]),
                     (ingredientes, ["ingrediente", "categoria", "unidad"]),
                     (atributos, ["atributo"])):
        for c in cats:
            df[c] = df[c].astype("category")
    etiquetas.to_parquet(os.path.join(salida, "etiquetas.parquet"), index=False)
    ingredientes.to_parquet(os.path.join(salida, "ingredientes.parquet"), index=False)
    atributos.to_parquet(os.path.join(salida, "atributos.parquet"), index=False)
    print(f"Etiquetas: {len(etiquetas):,} | ingredientes: {len(ingredientes):,} | atributos: {len(atributos):,}")
    print("Guardado en", salida)


if __name__ == "__main__":
    main()

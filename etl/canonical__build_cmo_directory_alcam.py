"""Build canonical.cmo_directory_alcam — the LATAM music-CMO reference directory.

A curated 13-row reference table listing the music collective-management
societies (CMOs) that belong to ALCAM (Alianza Latinoamericana de Autores y
Compositores de Música, founded 2012; alcammusica.org). ALCAM is the LATAM
regional federation of music creator societies inside CISAC — president Juca
Novaes (UBC, Brazil).

WHY THIS EXISTS
---------------
The corpus already holds `atana.ecad` (Phase 4c.3) — a 3-row headline series
for ECAD, the Brazilian umbrella collector. ECAD aggregates and distributes
royalties for the Brazilian member societies of CISAC, of which two are ALCAM
members (ABRAMUS, UBC). This directory is the LATAM map of the creator-side
societies *upstream* of those collections — the natural join key for any
future per-society headline series across the other 11 ALCAM countries
(Tier 2 / Phase 5 candidate; see `_atana_intel/scoping_alcammusica_2026-05-25.md`).

It is NOT a classification crosswalk (those live in `canonical.domain_crosswalk`).
It is a small reference directory of entities — society acronym, country, URL,
and a `linked_atana_schema` pointer that ties ABRAMUS/UBC to the existing
`atana.ecad` collection-side data.

SOURCE
------
alcammusica.org/sociedades — captured 2026-05-25 (Wix HTML, fetched via the
Atana sandbox's `web_fetch`). Each row's official URL is the canonical pointer
to the society's own name and metadata.

OUTPUT
------
    curated/cmo_directory_alcam.parquet     (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (ZSTD) → byte-identical reruns.
MotherDuck push gated behind a token, and skipped under ATANA_ETL_SKIP_PUSH.
No file in raw/ is read, moved or modified.

Usage:
    python etl/canonical__build_cmo_directory_alcam.py
"""
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "curated"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE_URL = "https://www.alcammusica.org/sociedades"
AS_OF = date(2026, 5, 25)

COLUMNS = [
    "country",                # English name of the country
    "country_iso3",           # ISO 3166-1 alpha-3 code
    "society_acronym",        # short name (SADAIC, ABRAMUS, …)
    "society_name",           # best-known full name in ES/PT — URL is authoritative
    "url",                    # official society URL
    "in_atana_corpus",        # bool — true iff this society's data is reachable via a corpus schema
    "linked_atana_schema",    # name of the corpus schema if any (e.g. 'ecad'); NULL otherwise
    "source_url",             # ALCAM directory page this row was captured from
    "as_of",                  # capture date
]

# ── Inline directory — transcribed from alcammusica.org/sociedades, 2026-05-25 ──
# Order: alphabetical by country then by society_acronym.
# `society_name` carries the best-known canonical Spanish/Portuguese form; for
# AEI (Guatemala) the full official expansion is not visible from the ALCAM page
# and was not separately verified — the URL remains authoritative. See
# docs/methodology/cmo_directory_alcam.md §3 for the per-row notes.
ROWS = [
    ("Argentina",   "ARG", "SADAIC",     "Sociedad Argentina de Autores y Compositores de Música",
     "https://sadaic.org.ar/",          False, None),
    ("Bolivia",     "BOL", "SOBODAYCOM", "Sociedad Boliviana de Autores y Compositores de Música",
     "https://www.sobodaycom.org/",     False, None),
    ("Brazil",      "BRA", "ABRAMUS",    "Associação Brasileira de Música e Artes",
     "https://www.abramus.org.br/",     True,  "ecad"),
    ("Brazil",      "BRA", "UBC",        "União Brasileira de Compositores",
     "https://www.ubc.org.br/",         True,  "ecad"),
    ("Chile",       "CHL", "SCD",        "Sociedad Chilena del Derecho de Autor",
     "https://www.scd.cl/",             False, None),
    ("Colombia",    "COL", "SAYCO",      "Sociedad de Autores y Compositores de Colombia",
     "https://www.sayco.org/",          False, None),
    ("Costa Rica",  "CRI", "ACAM",       "Asociación de Compositores y Autores Musicales de Costa Rica",
     "https://www.acam.cr/",            False, None),
    ("Ecuador",     "ECU", "SAYCE",      "Sociedad de Autores y Compositores Ecuatorianos",
     "https://sayce.com.ec/",           False, None),
    ("Guatemala",   "GTM", "AEI",        "AEI – Guatemala (sociedad de autores; full official name not verified — see methodology)",
     "https://www.aeiguatemala.org/",   False, None),
    ("Mexico",      "MEX", "SACM",       "Sociedad de Autores y Compositores de Música",
     "https://www.sacm.org.mx/",        False, None),
    ("Paraguay",    "PRY", "APA",        "Autores Paraguayos Asociados",
     "https://www.apa.org.py/",         False, None),
    ("Peru",        "PER", "APDAYC",     "Asociación Peruana de Autores y Compositores",
     "https://www.apdayc.org.pe/",      False, None),
    ("Uruguay",     "URY", "AGADU",      "Asociación General de Autores del Uruguay",
     "https://www.agadu.org/",          False, None),
]


def build() -> pd.DataFrame:
    rows = [
        {
            "country":             r[0],
            "country_iso3":        r[1],
            "society_acronym":     r[2],
            "society_name":        r[3],
            "url":                 r[4],
            "in_atana_corpus":     r[5],
            "linked_atana_schema": r[6],
            "source_url":          SOURCE_URL,
            "as_of":               AS_OF,
        }
        for r in ROWS
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    # Deterministic order — guarantees byte-identical reruns.
    df = df.sort_values(["country", "society_acronym"]).reset_index(drop=True)
    return df


def validate(df: pd.DataFrame) -> None:
    """Self-check before writing."""
    print("Validating...")
    assert len(df) == 13, f"expected 13 rows, got {len(df)}"
    print(f"  ✓ 13 rows")

    countries = df["country"].value_counts().to_dict()
    assert countries.get("Brazil") == 2, "Brazil must have 2 societies (ABRAMUS + UBC)"
    others = [c for c, n in countries.items() if c != "Brazil"]
    assert all(countries[c] == 1 for c in others), "non-Brazil countries must have exactly 1 society"
    assert set(others) == {
        "Argentina", "Bolivia", "Chile", "Colombia", "Costa Rica", "Ecuador",
        "Guatemala", "Mexico", "Paraguay", "Peru", "Uruguay",
    }, f"unexpected country set: {sorted(others)}"
    print(f"  ✓ 12 countries (Brazil ×2, all others ×1)")

    iso = df["country_iso3"].unique().tolist()
    assert all(len(c) == 3 and c.isupper() for c in iso), f"ISO3 malformed: {iso}"
    print(f"  ✓ country_iso3 well-formed (alpha-3 uppercase)")

    bad = df[~df["url"].str.startswith(("http://", "https://"))]
    assert bad.empty, f"non-URL rows: {bad['society_acronym'].tolist()}"
    print(f"  ✓ all URLs start with http(s)://")

    # in_atana_corpus is exactly true ⇔ linked_atana_schema is not NULL
    in_corpus = df["in_atana_corpus"]
    has_link = df["linked_atana_schema"].notna()
    assert (in_corpus == has_link).all(), \
        "in_atana_corpus must be equivalent to linked_atana_schema IS NOT NULL"
    linked = df.loc[in_corpus, "society_acronym"].tolist()
    assert sorted(linked) == ["ABRAMUS", "UBC"], (
        f"only ABRAMUS + UBC should be linked (via ecad); got {sorted(linked)}")
    assert set(df.loc[in_corpus, "linked_atana_schema"]) == {"ecad"}, \
        "linked_atana_schema must be 'ecad' for the Brazilian pair"
    print(f"  ✓ linkage invariant: ABRAMUS + UBC → ecad; others NULL "
          f"({int(in_corpus.sum())}/{len(df)} in corpus)")

    # Acronyms unique
    assert df["society_acronym"].nunique() == 13, "society_acronym must be unique"
    print(f"  ✓ 13 distinct society acronyms")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "cmo_directory_alcam.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(
        f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df):,} rows, "
          f"{size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    derived_from = [
        "https://www.alcammusica.org/sociedades",
        "_atana_intel/scoping_alcammusica_2026-05-25.md",
        "docs/methodology/cmo_directory_alcam.md",
    ]
    meta = {
        "table": "cmo_directory_alcam",
        "schema": "canonical",
        "description": "LATAM music-CMO reference directory — the 13 member "
                       "societies of ALCAM (Alianza Latinoamericana de Autores "
                       "y Compositores de Música) across 12 countries, with a "
                       "linkage pointer to atana.ecad for the Brazilian pair "
                       "(ABRAMUS, UBC). A join key for any future per-society "
                       "headline series across LATAM.",
        "source": "alcammusica.org/sociedades, captured 2026-05-25. The Atana "
                  "build inlines the 13 rows verbatim from the page; the URL "
                  "of each society remains the authoritative source for its "
                  "official name.",
        "derived_from": derived_from,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "build_date": str(date.today()),
        "build_script": "etl/canonical__build_cmo_directory_alcam.py",
        "sha256_parquet": hashlib.sha256(out_path.read_bytes()).hexdigest(),
    }
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {meta_path.relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
    """Push to MotherDuck if a valid token is available (MOTHERDUCK_TOKEN env
    var or a gitignored .motherduck_token file; must be a JWT).

    Skipped entirely when ATANA_ETL_SKIP_PUSH is set — for build-only / sandbox
    runs where the Parquet is produced but the sync stays with João.
    """
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print(f"  · push skipped for atana.{schema}.{table} (ATANA_ETL_SKIP_PUSH)")
        return

    def _jwt(t) -> str:
        t = (t or "").strip()
        return t if (t.startswith("eyJ") and t.count(".") == 2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN"))
    if not token:
        tf = REPO_ROOT / ".motherduck_token"
        token = _jwt(tf.read_text()) if tf.exists() else ""
    if not token:
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no "
              f"valid token. Put a JWT in {REPO_ROOT}/.motherduck_token, then "
              f"re-run.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n:,} rows)")


def main() -> None:
    print("Building canonical.cmo_directory_alcam...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "canonical", "cmo_directory_alcam")
    print("Done.")


if __name__ == "__main__":
    main()

"""CISAC GCR 2025 — leading smaller markets by digital share → Parquet.

Phase 5a of the Atana Data expansion — fourth of four tables in `atana.cisac`
(Tier 1 of the CISAC scoping). The ten "leading smaller markets" — the
countries whose 2024 *digital* royalty market share is highest in CISAC's
data, plus their 2015–2024 digital growth.

CORPUS RELEVANCE
----------------
- **Mexico (65.1 %)** is the only LATAM country in the top-ten, and the most
  digitally collected creator economy in Latin America by this metric. It is
  the single CISAC datapoint that bites directly into Atana Note #07
  (UNCTAD × CSCM pluralism), the DANE / INEGI work, and the Authenticity
  Paradox narrative in Atana Index Vol. 1.
- The table also gives the GCR's three published large-market comparators
  in prose (USA 27.1 %, France 13.9 %, UK 11.4 %) — those live in the
  methodology note (§4), not in this table; the table stays strictly
  "leading smaller markets" as the GCR labels it.

⚠ GROWTH NULL FOR MALI
----------------------
Mali shows "—" for 2015–2024 growth in the GCR table (no 2015 baseline;
Mali joined CISAC reporting after 2015). Stored as NULL with a per-row
`notes` flag.

GRAIN
-----
One row per (year, country). 2024 only at v1 launch (10 rows).

SOURCE
------
    https://www.cisac.org/cisac-global-collections-report-2025
    GCR 2025 landing page (public).

OUTPUT
------
    raw/cisac/gcr_2025_leading_smaller_markets_digital_share.parquet (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.cisac.

Usage:
    python etl/cisac__gcr_2025_leading_smaller_markets_to_parquet.py
"""
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "cisac"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE_PAGE = "https://www.cisac.org/cisac-global-collections-report-2025"

COLUMNS = [
    "year",
    "country",
    "country_iso3",
    "digital_share_pct",
    "growth_2015_2024_pct",
    "notes",
    "source_page",
]

# Verbatim from the GCR 2025 landing page table "Leading smaller markets by
# digital share (2024) and growth 2015–2024". Order: descending digital share.
# Tuple: (country, iso3, digital_share_pct, growth_2015_2024_pct_or_None, notes_or_None)
MALI_NOTE = ("Mali growth 2015–2024 NULL — the GCR table shows '—'. Likely "
             "no 2015 baseline (Mali joined CISAC reporting after 2015).")
MEXICO_NOTE = ("Mexico is the only LATAM country in the GCR's top-10 "
               "leading-smaller-markets-by-digital-share list. SACM is the "
               "Mexican CISAC member society (see canonical.cmo_directory_alcam).")

ROWS = [
    ("Mali",        "MLI", 89.9, None,      MALI_NOTE),
    ("Vietnam",     "VNM", 89.6,  1732.5,   None),
    ("India",       "IND", 82.7, 67630.9,   None),
    ("Indonesia",   "IDN", 82.5,  2657.4,   None),
    ("Philippines", "PHL", 80.9,  9101.9,   None),
    ("Nepal",       "NPL", 78.2, 21513.2,   None),
    ("Thailand",    "THA", 69.1,  5523.0,   None),
    ("Mexico",      "MEX", 65.1,  3203.2,   MEXICO_NOTE),
    ("Hong Kong",   "HKG", 64.0,   617.0,   None),
    ("Ukraine",     "UKR", 63.3,   280.1,   None),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [{"year": 2024, "country": r[0], "country_iso3": r[1],
          "digital_share_pct": r[2], "growth_2015_2024_pct": r[3],
          "notes": r[4], "source_page": SOURCE_PAGE} for r in ROWS],
        columns=COLUMNS,
    )
    # Deterministic order: digital_share desc, country alpha for stability
    df = df.sort_values(["year", "digital_share_pct", "country"],
                        ascending=[True, False, True]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 10, f"expected 10 rows, got {len(df)}"
    print(f"  ✓ 10 rows (CISAC's published top-10 leading smaller markets, 2024)")

    iso = df["country_iso3"].tolist()
    assert len(set(iso)) == 10 and all(len(c) == 3 and c.isupper() for c in iso), \
        f"country_iso3 malformed or non-unique: {iso}"
    print(f"  ✓ country_iso3 well-formed (alpha-3, distinct)")

    # The Mali growth NULL is the one documented gap
    null_growth = df[df["growth_2015_2024_pct"].isna()]
    assert list(null_growth["country"]) == ["Mali"], \
        f"only Mali should have NULL growth; got {list(null_growth['country'])}"
    assert (null_growth["notes"].iloc[0] or "").startswith("Mali growth"), \
        "Mali row must carry the NULL-growth caveat"
    print(f"  ✓ Mali growth = NULL with caveat in notes; other 9 carry numeric growth")

    # Shares within the published range [60 %, 90 %]
    s = df["digital_share_pct"]
    assert s.min() >= 60.0 and s.max() <= 90.0, \
        f"shares outside [60, 90]: min {s.min()}, max {s.max()}"
    print(f"  ✓ digital_share_pct in [{s.min():.1f}, {s.max():.1f}] — verbatim from GCR")

    # Mexico — the LATAM cell — present and flagged
    mex = df[df["country"] == "Mexico"]
    assert len(mex) == 1
    assert mex["digital_share_pct"].iloc[0] == 65.1
    assert "LATAM" in (mex["notes"].iloc[0] or ""), "Mexico row must flag LATAM relevance"
    print(f"  ✓ Mexico 65.1 % present — the corpus's single CISAC LATAM cell, "
          f"flagged in notes")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gcr_2025_leading_smaller_markets_digital_share.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "cisac",
        "description": "CISAC Global Collections Report 2025 — the 'leading "
                       "smaller markets' by digital royalty market share, "
                       "2024, with 2015-2024 growth. 10 rows. Mexico (65.1 %) "
                       "is the only LATAM country in the GCR's top-10 and is "
                       "directly relevant to Atana Note #07 (UNCTAD × CSCM "
                       "pluralism), the DANE/INEGI work and the Authenticity "
                       "Paradox narrative.",
        "source": "CISAC Global Collections Report 2025 — public landing page, "
                  "table 'Leading smaller markets by digital share (2024) and "
                  "growth 2015–2024'.",
        "source_pages": [SOURCE_PAGE],
        "fetch_date": "2026-05-29",
        "etl_script": "etl/cisac__gcr_2025_leading_smaller_markets_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "CISAC published figures — public release",
        "grain": "one row per (year, country)",
        "row_count": int(len(df)),
        "notes": "Mali growth_2015_2024_pct = NULL (no 2015 baseline; '—' in "
                 "source). Large-market comparators (USA 27.1 %, France 13.9 %, "
                 "UK 11.4 %) stated in the GCR prose are NOT in this table — "
                 "see methodology §4 for the comparator block.",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
    """Push to MotherDuck if a valid JWT token is available.

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
              f"valid token.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main() -> None:
    print("Building atana.cisac.gcr_2025_leading_smaller_markets_digital_share...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "cisac", "gcr_2025_leading_smaller_markets_digital_share")
    print("Done.")


if __name__ == "__main__":
    main()

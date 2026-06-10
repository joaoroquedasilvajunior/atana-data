"""BRL annual exchange-rate reference series (USD + EUR) → Parquet.

Phase 6a (first item) of the Atana Data expansion — the "cheapest load-bearing
ingest in the backlog" (phase6_corpus_criterion_and_vol2_scoping.md §2.2).

WHY THIS EXISTS
---------------
`atana.ibge_comex` is R$ FOB with no USD column, so Brazil cannot join the
cross-LATAM trade comparison through `canonical.domain_crosswalk` that the
Mexican/Colombian/Costa Rican tables support via their `fx_*_usd_annual`
reference series. This ETL closes that gap with the same convention, and adds
an EUR series to unblock the EUR/BRL precision caveat flagged in Análise 24
(ECAD R$ × CISAC € comparisons used an eyeballed ~6.03 rate).

WHAT THIS INGESTS
-----------------
1. fx_brl_usd_annual — annual-average BRL per USD.
   Primary: World Bank Open Data PA.NUS.FCRF for BRA (period average; IMF IFS)
            — the SAME source/indicator as fx_mxn_usd_annual,
            fx_cop_usd_annual and fx_crc_usd_annual, for cross-table
            consistency.
   Extension: BCB SGS series 3698 (taxa de câmbio livre, dólar americano
            venda, média de período mensal) — annualised by simple mean of
            the 12 monthly values — used ONLY for years the World Bank has
            not yet published (currently 2025). `source` column says which.
   Cross-check: for overlapping years the two sources must agree within 2%.

2. fx_brl_eur_annual — annual-average BRL per EUR.
   BCB SGS series 21619 (euro venda, daily) — annualised by simple mean of
   daily observations. 1999→latest complete year.

API endpoints (open, no key):
    https://api.worldbank.org/v2/country/BRA/indicator/PA.NUS.FCRF?format=json
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.<code>/dados?formato=json
        (BCB daily series are requested in ≤10-year windows per API limits)

Raw JSON cached under raw/macro/_source/ on first run; reruns read the cache
(stable, offline, byte-identical output). Pass --refresh to re-pull.

⚠️ Convenience reference series, NOT official Atana measurements: annual simple
averages hide intra-year volatility (2020! 2025!). Any publication converting a
*flow* (trade, royalties) should use the matching-period average; converting a
*stock* at a point in time should use the period-end rate instead. Documented
in docs/methodology/macro_fx_brl.md.

OUTPUT:
    raw/macro/fx_brl_usd_annual.parquet  (+ .meta.json)   grain: year
    raw/macro/fx_brl_eur_annual.parquet  (+ .meta.json)   grain: year

Idempotent. JSON → DataFrame → DuckDB COPY (ZSTD, no pyarrow).
MotherDuck push gated (skipped when ATANA_ETL_SKIP_PUSH is set); target
schema `atana.macro` — NEW schema, João's checkpoint before first sync.

Usage:
    python etl/macro__fx_brl_annual_to_parquet.py            # cache if present
    python etl/macro__fx_brl_annual_to_parquet.py --refresh  # re-pull APIs
"""
import hashlib
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "macro"
SRC = OUT / "_source"
OUT.mkdir(parents=True, exist_ok=True)
SRC.mkdir(parents=True, exist_ok=True)

REFRESH = "--refresh" in sys.argv
FIRST_YEAR = 1994            # Plano Real
WB_URL = ("https://api.worldbank.org/v2/country/BRA/indicator/PA.NUS.FCRF"
          f"?format=json&date={FIRST_YEAR}:2035&per_page=200")
BCB_URL = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
           "?formato=json&dataInicial={d0}&dataFinal={d1}")
SGS_USD_MONTHLY = 3698       # dólar venda, média de período (mensal)
SGS_EUR_DAILY = 21619        # euro venda (diária)
TODAY = date.today()
LAST_COMPLETE_YEAR = TODAY.year - 1


def _fetch(url: str, cache_name: str) -> object:
    cache = SRC / cache_name
    if cache.exists() and not REFRESH:
        return json.loads(cache.read_text())
    req = urllib.request.Request(url, headers={"User-Agent": "atana-data ETL"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    cache.write_text(json.dumps(payload, ensure_ascii=False))
    print(f"  · fetched + cached {cache_name}")
    return payload


def fetch_worldbank() -> dict:
    """{year: rate} from WB PA.NUS.FCRF (skips null/unpublished years)."""
    payload = _fetch(WB_URL, "worldbank_pa_nus_fcrf_bra.json")
    rows = payload[1]
    return {int(r["date"]): float(r["value"])
            for r in rows if r["value"] is not None}


def fetch_bcb(code: int, cache_prefix: str) -> pd.DataFrame:
    """All observations of an SGS series since FIRST_YEAR, chunked ≤10y."""
    frames = []
    for y0 in range(FIRST_YEAR, TODAY.year + 1, 9):
        y1 = min(y0 + 8, TODAY.year)
        url = BCB_URL.format(code=code, d0=f"01/01/{y0}", d1=f"31/12/{y1}")
        payload = _fetch(url, f"{cache_prefix}_{y0}_{y1}.json")
        if payload:
            frames.append(pd.DataFrame(payload))
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset="data")
    df["year"] = df["data"].str[-4:].astype(int)
    df["valor"] = df["valor"].astype(float)
    return df


def annualise(df: pd.DataFrame, min_obs: int) -> pd.DataFrame:
    g = (df.groupby("year")["valor"].agg(["mean", "count"])
           .reset_index().rename(columns={"mean": "rate", "count": "n_obs"}))
    g = g[(g["n_obs"] >= min_obs) & (g["year"] <= LAST_COMPLETE_YEAR)]
    return g


def write_parquet(df: pd.DataFrame, table: str) -> Path:
    out = OUT / f"{table}.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out.relative_to(REPO_ROOT)} — {len(df):,} rows, "
          f"{out.stat().st_size/1024:.1f} KB")
    return out


def write_meta(out_path: Path, description: str, source: str,
               source_url: str) -> None:
    meta = {
        "table": out_path.stem,
        "description": description,
        "source": source,
        "source_url": source_url,
        "source_files": [{"file": p.name,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in sorted(SRC.glob("*.json"))],
        "fetch_date": str(TODAY),
        "etl_script": "etl/macro__fx_brl_annual_to_parquet.py",
        "etl_run_date": str(TODAY),
        "licence": "World Bank Open Data CC BY 4.0 / BCB SGS dados abertos",
    }
    p = out_path.with_suffix(".meta.json")
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {p.relative_to(REPO_ROOT)}")


def main() -> None:
    # ── 1. USD ───────────────────────────────────────────────────────────
    print("BRL/USD — World Bank primary + BCB SGS 3698 extension")
    wb = fetch_worldbank()
    bcb_m = annualise(fetch_bcb(SGS_USD_MONTHLY, "bcb_sgs3698_usd_monthly"),
                      min_obs=12)
    # SGS 3698 pre-July-1994 observations are in cruzeiros reais (pre-Plano
    # Real) — the 1994 annual mean is meaningless. WB handles the conversion;
    # the BCB side starts at 1995.
    bcb_m = bcb_m[bcb_m["year"] >= 1995]
    bcb = dict(zip(bcb_m["year"], bcb_m["rate"]))

    # Cross-check overlap (within 2%)
    bad = [(y, wb[y], bcb[y]) for y in sorted(set(wb) & set(bcb))
           if abs(wb[y] - bcb[y]) / wb[y] > 0.02]
    assert not bad, f"WB×BCB divergence >2%: {bad}"
    print(f"  · WB×BCB overlap check OK ({len(set(wb) & set(bcb))} years ≤2%)")

    rows = []
    for y in range(FIRST_YEAR, LAST_COMPLETE_YEAR + 1):
        if y in wb:
            rows.append({"year": y, "fx_brl_per_usd": round(wb[y], 6),
                         "source": "worldbank_pa_nus_fcrf", "n_obs": None})
        elif y in bcb:
            n = int(bcb_m.loc[bcb_m["year"] == y, "n_obs"].iloc[0])
            rows.append({"year": y, "fx_brl_per_usd": round(bcb[y], 6),
                         "source": "bcb_sgs_3698_annual_mean", "n_obs": n})
    usd = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    p = write_parquet(usd, "fx_brl_usd_annual")
    write_meta(p,
               "Annual-average BRL/USD exchange rate, used to derive USD "
               "views of atana.ibge_comex (R$ FOB) and other BRL tables. NOT "
               "an IBGE/BCB cultural figure — a documented convenience "
               "series. Primary: World Bank PA.NUS.FCRF (same indicator as "
               "fx_mxn/fx_cop/fx_crc); years the WB has not yet published "
               "are filled from BCB SGS 3698 (monthly mean, annualised) and "
               "flagged in `source`.",
               "World Bank PA.NUS.FCRF (BRA) + BCB SGS 3698",
               "https://data.worldbank.org/indicator/PA.NUS.FCRF?locations=BR")

    # ── 2. EUR ───────────────────────────────────────────────────────────
    print("BRL/EUR — BCB SGS 21619 (daily, annualised)")
    eur_d = annualise(fetch_bcb(SGS_EUR_DAILY, "bcb_sgs21619_eur_daily"),
                      min_obs=200)
    eur = (eur_d.rename(columns={"rate": "fx_brl_per_eur"})
                .assign(source="bcb_sgs_21619_annual_mean")
                .loc[:, ["year", "fx_brl_per_eur", "source", "n_obs"]]
                .sort_values("year").reset_index(drop=True))
    eur["fx_brl_per_eur"] = eur["fx_brl_per_eur"].round(6)
    p = write_parquet(eur, "fx_brl_eur_annual")
    write_meta(p,
               "Annual-average BRL/EUR exchange rate (mean of daily BCB SGS "
               "21619 'euro venda' observations; years with <200 obs "
               "dropped). Unblocks the A24 EUR/BRL precision caveat (ECAD R$ "
               "× CISAC € comparisons). Convenience series — see methodology "
               "for flow-vs-stock conversion guidance.",
               "BCB SGS 21619 (euro, venda, diária)",
               "https://api.bcb.gov.br/dados/serie/bcdata.sgs.21619/dados")

    # ── 3. Spot checks ───────────────────────────────────────────────────
    chk = dict(zip(usd["year"], usd["fx_brl_per_usd"]))
    assert 5.3 < chk[2024] < 5.5, chk[2024]      # WB 2024 ≈ 5.389
    assert 4.9 < chk[2023] < 5.1, chk[2023]      # ≈ 5.00
    assert 3.2 < chk[2015] < 3.5, chk[2015]      # ≈ 3.33
    echk = dict(zip(eur["year"], eur["fx_brl_per_eur"]))
    assert 5.6 < echk[2024] < 6.1, echk[2024]    # EUR/BRL 2024 ≈ 5.83
    print(f"  · spot checks OK — USD {usd['year'].min()}–{usd['year'].max()}"
          f" ({len(usd)} yrs), EUR {eur['year'].min()}–{eur['year'].max()}"
          f" ({len(eur)} yrs)")

    # ── 4. MotherDuck (gated) ────────────────────────────────────────────
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print("  · ATANA_ETL_SKIP_PUSH set — MotherDuck sync skipped "
              "(schema atana.macro is NEW; João's checkpoint).")
        return
    print("  · No push implemented in v1 — sync atana.macro manually per "
          "PUSH_INSTRUCTIONS.md after approving the new schema.")


if __name__ == "__main__":
    main()

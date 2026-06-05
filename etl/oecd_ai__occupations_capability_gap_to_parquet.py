"""OECD No. 59 — per-occupation AI Capability Gap dataset → Parquet.

Phase 5d. Third table in `atana.oecd_ai`, joining `papers_headline` (Phase 5c)
and `ai_capability_domains` (Phase 5c). This one carries the actually-useful
empirical surface from OECD No. 59: the per-occupation Capability Gap index
across the 9 domains, for ~770-880 SOC occupations.

DATA ACQUISITION (manual — see scoping memo `_atana_intel/scoping_oecd_no59_occupations_2026-06-26.md`)
-------------------------------------------------------------------------------
The OECD has published the dataset at:
    https://oecd.ai/en/site/ai-capability-indicators
(landing page) — JS-rendered, requires browser visit. Download the CSV (or XLSX
if that's the offered format) and save it at:

    atana-data/raw/oecd_ai/_source/oecd_capability_gap_occupations.csv
    (or .xlsx; the ETL auto-detects both)

If the schema below doesn't match what OECD publishes, adjust COL_MAP. The
canonical OECD column names are not yet confirmed.

GRAIN
-----
One row per O*NET SOC code. Expected row count: ~770-880.

SOURCE
------
Stuart Elliott et al. (2026). "The OECD AI Exposure Measure." OECD Artificial
Intelligence Papers No. 59. CC BY 4.0. Per-occupation dataset published at
oecd.ai/en/site/ai-capability-indicators.

Idempotent; ATANA_ETL_SKIP_PUSH guard.
"""
import hashlib, json, os, sys
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "oecd_ai"
SOURCE_DIR = OUT / "_source"
SOURCE_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_LANDING = "https://oecd.ai/en/site/ai-capability-indicators"

# The 9 capability domains, in OECD's published order (Table 6.1)
DOMAINS = [
    ("gap_language",             "Language"),
    ("gap_social_interaction",   "Social interaction"),
    ("gap_problem_solving",      "Problem solving"),
    ("gap_creativity",           "Creativity"),
    ("gap_metacognition",        "Metacognition and critical thinking"),
    ("gap_knowledge_lrn_mem",    "Knowledge, learning and memory"),
    ("gap_vision",               "Vision"),
    ("gap_manipulation",         "Manipulation"),
    ("gap_robotic_intelligence", "Robotic intelligence"),
]
DOMAIN_COLS = [c for c, _ in DOMAINS]

# The "cultural occupation" filter — SOC major group 27 = Arts, Design,
# Entertainment, Sports and Media (per Table 6.3 of the paper). Plus selected
# adjacent codes that are cultural-adjacent (teaching cultural subjects, etc.)
SOC_GROUP_CULTURAL = "27"
SOC_CULTURAL_ADJACENT_PREFIXES = (
    "25-1121",   # Art, Drama, and Music Teachers, Postsecondary
    "25-2024",   # Special Education Teachers
    "25-2032",   # Career/Technical Education Teachers
    "39-30",     # Entertainment Attendants and Related Workers
)

# Column-name mapping — OECD's published column names are TBD. Adjust this
# dict when the actual file is in hand. Keys are the OECD field names we
# expect to see (best guesses based on chapter 6 of No. 59); values are the
# canonical Atana column names. If OECD uses different names, edit here only.
COL_MAP = {
    "ONET-SOC Code":             "onet_soc_code",
    "Occupation Title":          "occupation_title",
    "Language":                  "gap_language",
    "Social Interaction":        "gap_social_interaction",
    "Problem Solving":           "gap_problem_solving",
    "Creativity":                "gap_creativity",
    "Metacognition and Critical Thinking": "gap_metacognition",
    "Knowledge, Learning and Memory":      "gap_knowledge_lrn_mem",
    "Vision":                    "gap_vision",
    "Manipulation":              "gap_manipulation",
    "Robotic Intelligence":      "gap_robotic_intelligence",
    "Total AI Capability Gap Index":        "total_capability_gap",
    "Reversed Exposure Index (Standardised)": "exposure_index_reversed",
}

CANONICAL_COLUMNS = [
    "onet_soc_code", "soc_major_group_code", "soc_major_group_label",
    "occupation_title",
    *DOMAIN_COLS,
    "total_capability_gap", "exposure_index_reversed",
    "is_cultural_occupation_us", "atana_relevance_flag",
    "cbo_2002_provisional",
    "source", "notes",
]


def find_source_file() -> Path:
    """Look for the OECD source file in raw/oecd_ai/_source/ — CSV or XLSX."""
    for ext in ("csv", "xlsx", "xls"):
        candidates = list(SOURCE_DIR.glob(f"oecd_capability_gap_occupations*.{ext}"))
        if candidates:
            return candidates[0]
    raise FileNotFoundError(
        f"\n  No OECD source file found in {SOURCE_DIR.relative_to(REPO_ROOT)}/.\n"
        f"  Download from {SOURCE_LANDING} and save as "
        f"oecd_capability_gap_occupations.{{csv,xlsx}}.\n"
        f"  See _atana_intel/scoping_oecd_no59_occupations_2026-06-26.md for details.\n"
    )


def read_source(path: Path) -> pd.DataFrame:
    """Read CSV or XLSX. Adjust here if OECD publishes in a non-standard form."""
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported source format: {path.suffix}")
    return df


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename OECD columns to Atana canonical names. Falls back to fuzzy match
    if OECD's published column headers don't exactly match the COL_MAP keys."""
    rename = {}
    for src, dst in COL_MAP.items():
        # Exact match first
        if src in df.columns:
            rename[src] = dst
            continue
        # Fuzzy: case-insensitive, trim whitespace, drop punctuation
        norm_src = src.lower().replace(",", "").replace(" ", "")
        for col in df.columns:
            if str(col).lower().replace(",", "").replace(" ", "") == norm_src:
                rename[col] = dst
                break
    df = df.rename(columns=rename)
    missing = [v for v in COL_MAP.values() if v not in df.columns]
    if missing:
        sys.stderr.write(
            f"WARNING — these canonical columns were not found after rename:\n"
            f"  {missing}\n"
            f"  Available columns in source file:\n"
            f"  {list(df.columns)}\n"
            f"  Edit COL_MAP in this ETL to match OECD's actual column names.\n"
        )
    return df


def derive_cultural_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Derive SOC major group + is_cultural_occupation_us + atana_relevance_flag."""
    df["soc_major_group_code"] = df["onet_soc_code"].astype(str).str.slice(0, 2)
    # Friendly major-group labels — OECD Table 6.3 verbatim
    MAJOR_LABELS = {
        "11": "Management", "13": "Business and Financial Operations",
        "15": "Computer and Mathematical", "17": "Architecture and Engineering",
        "19": "Life, Physical, and Social Science",
        "21": "Community and Social Service", "23": "Legal",
        "25": "Educational Instruction and Library",
        "27": "Arts, Design, Entertainment, Sports, and Media",
        "29": "Healthcare Practitioners and Technical",
        "31": "Healthcare Support",
        "33": "Protective Service",
        "35": "Food Preparation and Serving Related",
        "37": "Building and Grounds Cleaning and Maintenance",
        "39": "Personal Care and Service",
        "41": "Sales and Related",
        "43": "Office and Administrative Support",
        "45": "Farming, Fishing, and Forestry",
        "47": "Construction and Extraction",
        "49": "Installation, Maintenance, and Repair",
        "51": "Production",
        "53": "Transportation and Material Moving",
    }
    df["soc_major_group_label"] = df["soc_major_group_code"].map(MAJOR_LABELS)

    # is_cultural_occupation_us: SOC group 27 OR adjacent prefix
    is_27 = df["soc_major_group_code"] == SOC_GROUP_CULTURAL
    is_adj = df["onet_soc_code"].astype(str).str.startswith(SOC_CULTURAL_ADJACENT_PREFIXES)
    df["is_cultural_occupation_us"] = is_27 | is_adj
    df["atana_relevance_flag"] = None
    df.loc[is_27, "atana_relevance_flag"] = "★ cultural"
    df.loc[is_adj & ~is_27, "atana_relevance_flag"] = "☆ cultural-adjacent"

    # cbo_2002_provisional: NULL for v1 (Tier 2 work)
    df["cbo_2002_provisional"] = None

    return df


def build() -> pd.DataFrame:
    src_path = find_source_file()
    print(f"  reading {src_path.relative_to(REPO_ROOT)}")
    df_raw = read_source(src_path)
    print(f"  · {len(df_raw)} rows × {len(df_raw.columns)} columns in source")

    df = normalise_columns(df_raw)
    df = derive_cultural_flags(df)
    df["source"] = "OECD AI Papers No. 59"
    df["notes"] = (
        "Per-occupation AI Capability Gap Index from OECD No. 59 (May 2026). "
        "Gap range 0-4 per domain; total range 0-36 theoretical, ~12 empirical. "
        "Lower gap = higher AI exposure (counterintuitive). "
        "Reversed standardised exposure index is the OECD's preferred-for-analysis form."
    )

    # Keep only canonical columns; warn about any unmapped ones
    extra = [c for c in df.columns if c not in CANONICAL_COLUMNS]
    if extra:
        print(f"  · dropping {len(extra)} unmapped column(s): {extra[:5]}{'…' if len(extra)>5 else ''}")
    df = df[[c for c in CANONICAL_COLUMNS if c in df.columns]]
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    n = len(df)
    assert 600 < n < 1100, f"row count {n} outside expected band [600-1100]"
    print(f"  ✓ {n} occupations (within expected band 600-1100)")

    # 9 domain gap columns present
    missing_domains = [c for c in DOMAIN_COLS if c not in df.columns]
    assert not missing_domains, f"missing domain columns: {missing_domains}"
    print(f"  ✓ all 9 capability-gap columns present")

    # Gap range plausibility
    for col in DOMAIN_COLS:
        vals = df[col].dropna()
        assert vals.between(0, 4.1).all(), f"{col} has values outside [0, 4]"
    print(f"  ✓ all 9 gap columns in [0, 4] range")

    # Cultural-occupation count plausibility — SOC group 27 has ~50 detailed
    # occupations in O*NET; adjacent prefixes add a handful. Expect 30-80.
    n_cultural = int(df["is_cultural_occupation_us"].sum())
    assert 20 <= n_cultural <= 100, \
        f"cultural-occupation count {n_cultural} outside expected band [20-100]"
    print(f"  ✓ {n_cultural} cultural / cultural-adjacent occupations flagged")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "occupations_capability_gap.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame, src_path: Path) -> None:
    meta = {
        "table": out_path.stem, "schema": "oecd_ai",
        "description": "OECD AI Capability Gap Index — per-occupation dataset "
                       "from Paper No. 59 (May 2026). 9 capability-specific gaps "
                       "+ total gap + reversed-standardised exposure index, for "
                       "~770-880 O*NET SOC occupations. Atana-side derivations "
                       "add SOC major-group labels + cultural-occupation flag.",
        "source": "OECD AI Papers No. 59 — per-occupation dataset, CC BY 4.0.",
        "source_pages": [SOURCE_LANDING],
        "source_file": str(src_path.relative_to(REPO_ROOT)),
        "fetch_date": str(date.today()),
        "etl_script": "etl/oecd_ai__occupations_capability_gap_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "OECD CC BY 4.0.",
        "grain": "one row per O*NET SOC occupation",
        "row_count": int(len(df)),
        "cultural_occupation_count":
            int(df["is_cultural_occupation_us"].sum()),
        "notes": "Atana adds soc_major_group_label, is_cultural_occupation_us, "
                 "atana_relevance_flag, cbo_2002_provisional (NULL in v1). "
                 "See _atana_intel/scoping_oecd_no59_occupations_2026-06-26.md "
                 "for the SOC-to-CBO crosswalk plan (Tier 2).",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df, schema, table):
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print(f"  · push skipped for atana.{schema}.{table} (ATANA_ETL_SKIP_PUSH)")
        return
    def _jwt(t):
        t = (t or "").strip()
        return t if (t.startswith("eyJ") and t.count(".") == 2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN"))
    if not token:
        tf = REPO_ROOT / ".motherduck_token"
        token = _jwt(tf.read_text()) if tf.exists() else ""
    if not token:
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no valid token.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main():
    print("Building atana.oecd_ai.occupations_capability_gap...")
    try:
        df = build()
    except FileNotFoundError as e:
        sys.stderr.write(str(e))
        sys.exit(2)
    validate(df)
    src_path = find_source_file()
    out_path = write_parquet(df)
    write_meta(out_path, df, src_path)
    maybe_push(df, "oecd_ai", "occupations_capability_gap")
    print("Done.")


if __name__ == "__main__":
    main()

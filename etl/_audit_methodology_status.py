#!/usr/bin/env python3
"""
Audit + maintain a uniform availability-status line on every methodology note.

For each note under docs/methodology/, this script:

  1. Discovers the schema it documents and the parquet directory it points at.
  2. Asks git for the last commit that touched any of those files, and whether
     that commit is reachable from origin/main.
  3. Parses docs/manifest.md for the schema's MotherDuck-sync state.
  4. Counts tables (parquets) and row totals on the working tree.
  5. Inserts or rewrites one blockquote line near the top of the note:

         > **Status (YYYY-MM-DD):** GitHub <state> · MotherDuck <state>
         > · <N> tables / <R> rows in <path>

  Insertion rule: the status line goes immediately AFTER the title (line 1) and
  BEFORE any other header content. If a previous status line is found
  (recognized by the `> **Status (` prefix) the script rewrites it in place;
  otherwise the line is inserted fresh. The script is idempotent: running it
  twice yields the same files.

  Also prints a JSON summary table to stdout for the audit log.

Usage:
    python3 etl/_audit_methodology_status.py                # dry run, print only
    python3 etl/_audit_methodology_status.py --apply        # actually write files
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs" / "methodology"
MANIFEST = REPO / "docs" / "manifest.md"

# ─── Note → schema mapping ──────────────────────────────────────────────────
# Each note documents one schema. Some schemas live under raw/<name>/, some
# under curated/<name>/. The script tries both.
NOTE_TO_SCHEMA = {
    "anthropic_eei.md":           "anthropic_eei",
    "bcb_sgs_ip_services.md":     "bcb",
    "canonical_domain_crosswalk.md": "canonical_crosswalk",  # special
    "cisac_gcr.md":               "cisac",
    "cmo_directory_alcam.md":     "canonical_alcam",        # special
    "cr_bccr_csc.md":             "cr_bccr",
    "dane_csecc.md":              "dane",
    "ecad_headline.md":           "ecad",       # superseded — annotate
    "ecad_relatorio_anual.md":    "ecad",
    "ibge_cempre_siic_ch1.md":    "ibge_cempre",
    "ibge_comex_siic_ch10.md":    "ibge_comex",       # OG — added 2026-06-14
    "ibge_estruturais_siic_ch2.md": "ibge_estruturais",
    "ibge_pnadc_siic_ch6.md":     "ibge_pnadc",       # OG — added 2026-06-14
    "ibge_tic_siic_ch7.md":       "ibge_tic",
    "ibge_turismo_siic_ch9.md":   "ibge_turismo",
    "ifpi_gmr.md":                "ifpi",
    "inegi_csc.md":               "inegi",
    "inpi_indicadores.md":        "inpi",
    "latam_trade_by_fcs_domain.md": "canonical_latam_trade",  # special
    "lexml_genealogy.md":         "lexml",            # OG — added 2026-06-14
    "lpg_paulo_gustavo.md":       "lpg",
    "luminate_ye.md":             "luminate",
    "macro_fx_brl.md":            "macro",
    "oecd_ai_papers.md":          "oecd_ai",
    "pnab_aldir_blanc.md":        "pnab",
    "rais_mte.md":                "rais",             # OG — added 2026-06-14
    "salic_api.md":               "salic",            # OG — added 2026-06-14
    "sinca_csc.md":               "sinca",
    "tcu_pnab.md":                "tcu",
    "unctad_creative_economy.md": "unctad",           # OG — added 2026-06-14
}

# Special path overrides — the "canonical" notes don't follow raw/curated convention
SPECIAL_PATHS = {
    "canonical_crosswalk":    ["curated/domain_crosswalk.parquet"],
    "canonical_alcam":        ["curated/cmo_directory_alcam.parquet"],
    "canonical_latam_trade":  ["curated/latam_trade_by_fcs_domain.parquet"],
}


def sh(args: list[str], cwd: Path = REPO) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def find_parquet_paths(schema: str) -> list[Path]:
    if schema in SPECIAL_PATHS:
        return [REPO / p for p in SPECIAL_PATHS[schema] if (REPO / p).exists()]
    for prefix in ("curated", "raw"):
        d = REPO / prefix / schema
        if d.exists():
            # Recursive walk, but skip _source/ and _staging/ subtrees
            return sorted(p for p in d.rglob("*.parquet")
                          if "_source" not in p.parts
                          and "_staging" not in p.parts)
    return []


def last_commit_for(schema: str, paths: list[Path]) -> tuple[str | None, bool]:
    """
    Return (short_sha, on_origin). short_sha is None if no commit touched these files.
    on_origin is True iff that commit is reachable from origin/main.
    """
    pathspecs: list[str] = [str(p.relative_to(REPO)) for p in paths]
    pathspecs += [f"etl/{schema}*"]
    pathspecs += [f"docs/methodology/*{schema}*"]
    # For canonical notes, also include the build script
    if schema.startswith("canonical_"):
        pathspecs.append("etl/canonical__*.py")

    try:
        sha = sh(["git", "log", "-n", "1", "--format=%H", "--all", "--"] + pathspecs)
    except subprocess.CalledProcessError:
        return None, False
    if not sha:
        return None, False

    # Is this sha reachable from origin/main?
    try:
        sh(["git", "merge-base", "--is-ancestor", sha, "origin/main"])
        on_origin = True
    except subprocess.CalledProcessError:
        on_origin = False
    return sha[:7], on_origin


def count_rows(parquets: list[Path]) -> tuple[int, int]:
    """Sum row counts across parquets, skipping unreadable files.
    Returns (n_rows, n_bad) — n_bad is the number of corrupt / unreadable parquets."""
    if not parquets:
        return 0, 0
    n_bad = 0
    try:
        import duckdb  # type: ignore
        con = duckdb.connect(":memory:")
        total = 0
        for p in parquets:
            try:
                total += con.execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
            except Exception:
                n_bad += 1
        return total, n_bad
    except ImportError:
        try:
            import pyarrow.parquet as pq  # type: ignore
            total = 0
            for p in parquets:
                try:
                    total += pq.ParquetFile(p).metadata.num_rows
                except Exception:
                    n_bad += 1
            return total, n_bad
        except ImportError:
            return -1, 0  # unknown


# ─── Manifest parser for MotherDuck-sync hint ───────────────────────────────
def parse_md_state(schema: str, manifest_text: str) -> str:
    """
    Inspect the manifest header for the schema and return one of:
       'live'                     — fully synced
       'pending_first_sync'       — NEW schema, never synced
       'pending_resync'           — existing schema, rebuilt locally
       'unknown'                  — schema not found in manifest

    Looks at the H2 line `## atana.<name>` for normal schemas, and at the H3
    line `### canonical.<name>` for canonical-layer tables.
    """
    canonical_key_map = {
        "canonical_crosswalk":    "domain_crosswalk",
        "canonical_alcam":        "cmo_directory_alcam",
        "canonical_latam_trade":  "latam_trade_by_fcs_domain",
    }
    if schema in canonical_key_map:
        name = canonical_key_map[schema]
        header_re = re.compile(rf"^###\s+`canonical\.{re.escape(name)}`(.*)$", re.MULTILINE)
    else:
        header_re = re.compile(rf"^##\s+`atana\.{re.escape(schema)}`(.*)$", re.MULTILINE)

    m = header_re.search(manifest_text)
    if not m:
        return "unknown"
    tail = m.group(1).lower()
    # Resolution order matters: 'first sync' wins over generic 'pending'.
    if "first sync" in tail:
        return "pending_first_sync"
    if "re-sync" in tail:
        return "pending_resync"
    if "pending push" in tail:
        # 'pending push + sync' = never synced; treat as first sync.
        return "pending_first_sync"
    if "pending" in tail:
        return "pending_resync"
    if "live" in tail or "synced" in tail:
        return "live"
    return "unknown"


# ─── Status-line composer ───────────────────────────────────────────────────
def compose_status_line(date: str, schema: str, sha: str | None, on_origin: bool,
                        md_state: str, n_tables: int, n_rows: int, n_bad: int,
                        rel_path: str) -> str:
    if sha is None:
        gh = "⏳ uncommitted"
    elif on_origin:
        gh = f"✅ `{sha}` on origin/main"
    else:
        gh = f"🟡 `{sha}` local-only (not on origin/main)"

    md_emoji = {
        "live": "✅ live",
        "pending_first_sync": "⏳ pending first sync",
        "pending_resync": "🔜 pending re-sync after schema change",
        "unknown": "❓ unknown (not in manifest)",
    }[md_state]
    md = f"MotherDuck {md_emoji}"

    tbl_word = "table" if n_tables == 1 else "tables"
    row_word = "row" if n_rows == 1 else "rows"
    if n_rows < 0:
        rows_part = f"{n_tables} {tbl_word} (row count unavailable)"
    else:
        rows_part = f"{n_tables} {tbl_word} / {n_rows:,} {row_word}"
    if n_bad > 0:
        rows_part += f" · ⚠ {n_bad} corrupt parquet{'s' if n_bad != 1 else ''}"

    return (f"> **Status ({date}):** GitHub {gh} · {md} · {rows_part} in `{rel_path}`\n")


# ─── Note rewriter (idempotent) ─────────────────────────────────────────────
STATUS_LINE_PATTERN = re.compile(r"^>\s+\*\*Status\s*\(", re.IGNORECASE)


def rewrite_note(note_path: Path, status_line: str) -> tuple[str, bool]:
    """
    Return (new_text, changed_flag). Idempotent.
      - If a status line exists, replace it.
      - Else, insert it on line 2 (right after the H1 title), followed by a
        blank line if the next line isn't already blank or a blockquote.
    """
    text = note_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Find and replace any existing status line(s)
    new_lines: list[str] = []
    replaced = False
    for ln in lines:
        if STATUS_LINE_PATTERN.match(ln):
            if not replaced:
                new_lines.append(status_line)
                replaced = True
            # drop any further duplicates
        else:
            new_lines.append(ln)

    if replaced:
        new_text = "".join(new_lines)
        return new_text, new_text != text

    # Insert after the title (line 0). Skip leading blanks; insert after the
    # first non-blank line that starts with '#'.
    insert_at = 1
    for i, ln in enumerate(lines[:5]):
        if ln.lstrip().startswith("#"):
            insert_at = i + 1
            break

    new_lines = list(lines)
    # Insert a blank line + the status line + a separator if not already blockquote
    block = ["\n", status_line]
    # Ensure a blank line after the status line if the next line is non-blank
    # and not a blockquote
    next_line = new_lines[insert_at] if insert_at < len(new_lines) else ""
    if next_line.strip() and not next_line.startswith(">"):
        block.append("\n")
    new_lines[insert_at:insert_at] = block

    new_text = "".join(new_lines)
    return new_text, new_text != text


# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Actually write files. Default is dry run.")
    args = ap.parse_args()

    today = dt.date.today().isoformat()
    manifest = MANIFEST.read_text(encoding="utf-8")

    audit: list[dict] = []
    for note_name, schema in NOTE_TO_SCHEMA.items():
        note_path = DOCS / note_name
        if not note_path.exists():
            continue
        parquets = find_parquet_paths(schema)
        sha, on_origin = last_commit_for(schema, parquets)
        md_state = parse_md_state(schema, manifest)
        n_tables = len(parquets)
        n_rows, n_bad = (count_rows(parquets) if parquets else (0, 0))
        if parquets:
            # show a representative path (the dir, or the single file)
            if len(parquets) == 1:
                rel_path = str(parquets[0].relative_to(REPO))
            else:
                rel_path = str(parquets[0].parent.relative_to(REPO)) + "/"
        else:
            rel_path = "(no parquets yet)"

        status_line = compose_status_line(
            today, schema, sha, on_origin, md_state, n_tables, n_rows, n_bad, rel_path)

        audit.append({
            "note": note_name, "schema": schema,
            "github_sha": sha, "on_origin": on_origin,
            "md_state": md_state, "tables": n_tables, "rows": n_rows,
            "corrupt_parquets": n_bad,
            "path": rel_path,
            "status_line": status_line.rstrip(),
        })

        if args.apply:
            new_text, changed = rewrite_note(note_path, status_line)
            if changed:
                note_path.write_text(new_text, encoding="utf-8")
                audit[-1]["wrote"] = True
            else:
                audit[-1]["wrote"] = False

    # Print a compact summary table
    print(f"{'note':40s}  {'GitHub':35s}  {'MotherDuck':40s}  {'rows':>8s}")
    print("-" * 130)
    for row in audit:
        gh = (("⏳ uncommitted" if row['github_sha'] is None
              else f"{'✅' if row['on_origin'] else '🟡'} {row['github_sha']}")
              + ("" if row['on_origin'] or row['github_sha'] is None else " (local-only)"))
        print(f"{row['note']:40s}  {gh:35s}  {row['md_state']:40s}  {row['rows']:>8,}")

    print()
    print(json.dumps({"date": today, "applied": args.apply,
                      "n_notes": len(audit)}, indent=2))


if __name__ == "__main__":
    main()

"""Reproducible CSV → Pandas cleaning/validation → SQLite ETL for InsuranceIQ.

Run from the project root: python -m src.etl
No proprietary company data or Informatica integration is used.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / 'data' / 'insurance_claims.csv'
DB_PATH = ROOT / 'data' / 'insuranceiq.db'
REPORT_PATH = ROOT / 'data' / 'quality_summary.csv'
REQUIRED = ('incident_date', 'incident_type', 'incident_state', 'total_claim_amount', 'fraud_reported')


def transform_and_validate(source: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize dashboard columns and produce an auditable field-level quality report.

    Preserve source records (including duplicates); do not silently drop or impute data.
    """
    df = source.copy()
    df.columns = df.columns.str.strip()
    missing_cols = [col for col in REQUIRED if col not in df.columns]
    if missing_cols:
        raise ValueError('Missing required columns: ' + ', '.join(missing_cols))

    # Source IDs such as policy numbers are labels rather than quantities.
    if 'policy_number' in df:
        df['policy_number'] = df['policy_number'].astype('string')
    df['incident_date'] = pd.to_datetime(df['incident_date'], errors='coerce')
    df['total_claim_amount'] = pd.to_numeric(df['total_claim_amount'], errors='coerce')
    fraud = df['fraud_reported'].astype('string').str.strip().str.upper()
    df['fraud_status'] = fraud.map({'Y': 'Flagged', 'N': 'Not flagged'}).fillna('Unknown')

    issues = []
    for col in source.columns:
        name = col.strip()
        series = source[col]
        missing = series.isna()
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            missing = missing | series.astype('string').str.strip().str.upper().isin(['', '?', 'NA', 'N/A'])
        count = int(missing.fillna(False).sum())
        issues.append({
            'column': name,
            'missing_or_placeholder_cells': count,
            'completeness_pct': round(100 * (len(source) - count) / max(len(source), 1), 2),
        })
    report = pd.DataFrame(issues)
    return df, report


def run_pipeline(csv_path: Path = RAW_CSV, db_path: Path = DB_PATH,
                 report_path: Path | None = REPORT_PATH) -> dict:
    """Load source CSV into two SQLite tables and optional CSV quality report.

    Repeated runs replace the table contents, preventing accidental duplicate loads.
    """
    csv_path = Path(csv_path)
    db_path = Path(db_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f'CSV not found at {csv_path}. Place insurance_claims.csv in the data folder.'
        )
    raw = pd.read_csv(csv_path, dtype={'policy_number': 'string'}, low_memory=False)
    clean, quality = transform_and_validate(raw)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    staged = clean.copy()
    staged['incident_date'] = staged['incident_date'].dt.strftime('%Y-%m-%d')
    # Store all source rows; the invalid values are documented, not discarded.
    with sqlite3.connect(db_path) as conn:
        with conn:
            staged.to_sql('claims', conn, if_exists='replace', index=False)
            quality.to_sql('data_quality', conn, if_exists='replace', index=False)
            conn.execute('CREATE INDEX IF NOT EXISTS idx_claims_incident_date ON claims (incident_date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_claims_incident_state ON claims (incident_state)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_claims_incident_type ON claims (incident_type)')
            conn.execute('CREATE TABLE IF NOT EXISTS etl_runs (run_utc TEXT, source_file TEXT, source_rows INTEGER, loaded_rows INTEGER, exact_duplicates INTEGER, invalid_amounts INTEGER, invalid_dates INTEGER)')
            conn.execute('INSERT INTO etl_runs VALUES (?, ?, ?, ?, ?, ?, ?)', (
                datetime.now(timezone.utc).isoformat(), csv_path.name, len(raw), len(clean),
                int(raw.duplicated().sum()),
                int((clean['total_claim_amount'].isna() | (clean['total_claim_amount'] < 0)).sum()),
                int(clean['incident_date'].isna().sum()),
            ))
    if report_path is not None:
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        quality.to_csv(report_path, index=False)
    return {
        'source_rows': len(raw), 'loaded_rows': len(clean),
        'exact_duplicates': int(raw.duplicated().sum()),
        'invalid_amounts': int((clean['total_claim_amount'].isna() | (clean['total_claim_amount'] < 0)).sum()),
        'invalid_dates': int(clean['incident_date'].isna().sum()),
        'missing_or_placeholder_cells': int(quality['missing_or_placeholder_cells'].sum()),
        'database': str(db_path),
    }


def read_claims(db_path: Path = DB_PATH) -> pd.DataFrame:
    """Read cleaned claims from the SQLite output, restoring dates and numeric types."""
    with sqlite3.connect(db_path) as conn:
        data = pd.read_sql_query('SELECT * FROM claims', conn)
    data['incident_date'] = pd.to_datetime(data['incident_date'], errors='coerce')
    data['total_claim_amount'] = pd.to_numeric(data['total_claim_amount'], errors='coerce')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=RAW_CSV)
    parser.add_argument('--db', type=Path, default=DB_PATH)
    args = parser.parse_args()
    print(json.dumps(run_pipeline(args.csv, args.db), indent=2))

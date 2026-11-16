# InsuranceIQ — Insurance Claims Intelligence & Data Quality

A polished, interactive **Streamlit dashboard** for exploring a **public automobile insurance claims sample**. It includes claims analytics, reported-fraud indicator analysis, data-quality diagnostics, and a searchable data dictionary. A separate **Python → SQLite ETL pipeline** prepares the dashboard's persisted data.

**Tech:** Python, Pandas, SQLite, Streamlit, Plotly, unittest.

## Quick start

1. Place the public CSV at `data/insurance_claims.csv` (same dataset you have been using locally).
   [Public source CSV](https://github.com/sulaihasubi/insurance-claims-fraud-detection/blob/main/datasets/insurance_claims.csv). Verify its licensing and attribution requirements before republishing the CSV.
2. Open this project folder in VS Code.
3. Install the dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Run the ETL (extract → validate/transform → SQLite load):
   ```bash
   python -m src.etl
   ```
5. Launch the dashboard:
   ```bash
   python -m streamlit run app.py
   ```

**Note:** The app automatically builds its SQLite database from the source CSV on first run if the database is missing. Run ETL manually to view and verify its console summary.

## Tests
```bash
python -m unittest discover -s tests -v
```

## Dashboard pages
- **Overview** — key claim metrics, incident-type/state distribution, fraud flags, incident-month summaries.
- **Claims Analytics** — detailed incident category/state breakdowns and claim records.
- **Fraud Analytics** — source fraud flag distribution and average recorded claim amount by flag status.
- **Data Quality** — completeness, duplicate, invalid amount/date diagnostics and downloadable CSV.
- **Documentation** — lineage, transformation standards, searchable field dictionary, limitations.

## Deploy for recruiters (Streamlit Community Cloud)
1. Commit `app.py`, `src/`, `docs/`, `tests/`, `requirements.txt`, `.streamlit/config.toml`, and the CSV **only if its license permits republication** to a public GitHub repository. Never upload private insurance data.
2. Open https://share.streamlit.io/ and deploy the repository, selecting `app.py` as the entry point.
3. The app will create the SQLite DB from the CSV when it first starts. SQLite in free hosting is an **ephemeral local file**, so this setup is appropriate for a read-only demo, not durable operational storage.
4. Test the public link in a private browser window on mobile and desktop.

If the CSV cannot be republished, the deployment must use a different appropriately licensed dataset or an authorized retrieval mechanism. Do not publish it without reviewing its terms.

## Architecture
`Public CSV → Pandas schema and quality checks → normalized rows + quality report → SQLite → Streamlit/Plotly`

Full data flow and limits: [docs/data_lineage.md](docs/data_lineage.md).

## Responsible use
This project is a portfolio illustration using a public sample. It is not affiliated with Great American Insurance, does not access insurer systems, and does not use Informatica or SharePoint APIs. Reported fraud flags are source labels, **not proof of fraud**. Recorded claim amounts are **not confirmed payouts**.

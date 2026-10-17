# Public-release boundary and GitHub handoff

## Included

Twelve author-supplied R/Python scripts, organised by work type; portable local-path preparation; per-folder descriptions; an analysis summary; draft figure/table crosswalk; column-only CSV schemas; source hashes and a validation report. No synthetic example is presented as a study result.

## Deliberately excluded

- All PNG, TIFF, PDF and SVG figure exports, including final refined versions.
- Manuscript and supplementary-information PDFs and their extracted text.
- Actual annual study data, SHAP values, predictions, model metrics, numerical result tables, generated reports and manuscript captions.
- Interactive `.Rhistory` files, local environments and caches.
- Duplicate copies of the same data and alternate rendered figures.
- `make_table15_xlsx.mjs`: a non-R/Python export helper depending on `@oai/artifact-tool`; it is not needed by the documented public pipeline. A CSV and Word export route remains.

The supplied archive remains the fuller private backup; this public package intentionally cannot substitute for it. File hashes in the provenance manifest let the author match each prepared script to the original archive. Original data/output files were not overwritten.

## Publication status

This package is prepared for a **new public analysis repository**, separate from the private `AlbertAM-TIA/Climate-Agriculture-Dashboard` backup. Suggested repository name: `APSIM-Process-Analysis`. The earlier private dashboard repository should remain private.

No upload or public GitHub repository has been created by this preparation. The GitHub connector is available but was not connected in this session. Publication requires a connected GitHub account or uploading this folder with the user's GitHub client. Do not paste tokens/passwords into chat.

## Short upload route

Create a new public repository with the suggested name, then upload the **contents of the extracted folder**, not just its ZIP. Do not upload the original analysis archive or manuscript PDFs to that public repository. If using Git locally:

```bash
git init
git add .
git commit -m "Add curated APSIM variance and process-analysis workflows"
git branch -M main
git remote add origin https://github.com/AlbertAM-TIA/APSIM-Process-Analysis.git
git push -u origin main
```

The remote URL above is a suggested future destination, not a verified existing repository. Create it first. Select a software licence explicitly before describing the project as open source; none was imposed during preparation.

# Figure and table crosswalk

| Draft item | Analysis or production code | Required local input | Public output policy |
|---|---|---|---|
| Figure 14: SOC variance at two timescales | `analysis/02_soc_variance/`; `figures/fig14_fig15/` | Annual SOC CSV, then variance CSV | Code only; no refined donut figures |
| Figure 15: global process importance | `analysis/03_process_models/`; `figures/fig15_global_importance/`; combined figure scripts | Annual SOC/yield CSVs; derived importance and CV CSVs | Code only; no refined importance figures |
| Figure S1: signed Shapley contributions | `figures/figS1_beeswarm/` | Shapley-values and importance CSVs | Code only; no final beeswarm |
| Supplementary Table S5: SOC variance shares | Combined figure/table scripts; `tables/soc_variance/` | Variance CSV; generated `Table15_source_data.json` for Word | No study result tables included |
| Table S6: MET climate sensitivity | **Not found in the supplied archive** | Additional climate-expanded modelling inputs/code needed | No reconstruction or invented implementation |
| Figure 13 / Table 14: stacked-system additivity | **Not found in the supplied archive** | Constituent/combined scenario analysis code needed | Outside this package |
| Supplementary Tables S1–S4 | **Not found as dedicated scripts in this archive** | Original corresponding processing workflows | Outside this package |

`Table15` in filenames is a legacy working label; the supplied supplement identifies the descriptive SOC variance table as **S5**. Do not rename scientific results solely to match a working filename. Figure S1 mapping follows the supplementary signed-Shapley caption. The manuscript and supplement themselves are not included.

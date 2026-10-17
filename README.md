# APSIM-AgroProcess-XAI
An integrated workflow linking APSIM outputs with timescale-aware variance decomposition, grouped-year predictive modelling and Shapley explanations.
# APSIM process analysis: SOC timescales, grouped validation and Shapley explanations

A curated R/Python methods portfolio by **Dr Albert Muleke**, prepared from the author-supplied analysis archive. It organises reusable analysis code separately from manuscript artwork and study data.

## Start here

- [Analysis summary](docs/analysis_summary.md): purpose, approach and interpretation.
- [Figure/table index](docs/figure_table_index.md): links to manuscript-related work.
- [Reproduction guide](docs/reproduction.md): inputs, commands and limitations.
- [Public-release boundary](docs/public_release.md): what is included and withheld.
- [Source provenance](docs/source_manifest.csv): original archive member, hashes and preparation changes.

## Repository structure

| Work type | Location | Purpose |
|---|---|---|
| Data preparation | `analysis/01_data_preparation/` | Aggregate daily APSIM outputs and audit coverage |
| SOC variance analysis | `analysis/02_soc_variance/` | Compare annual and long-term descriptive variance shares |
| Process models and explanations | `analysis/03_process_models/` | Grouped-year model comparison and held-out Shapley estimates |
| Figures 14 and 15 | `figures/fig14_fig15/` | R/Python figure and source-table production |
| Global importance | `figures/fig15_global_importance/` | Standalone base-R plotting |
| Supplementary beeswarm | `figures/figS1_beeswarm/` | Signed contributions and feature-value distributions |
| SOC table export | `tables/soc_variance/` | Word table from generated source JSON |
| Alternative analyses | `exploratory/` | Earlier R approaches; not the selected manuscript pipeline |
| Checks | `tests/` | Synthetic mathematical checks, with no study observations |

## Quick check without study data

```bash
python -m venv .venv
# Activate the environment for your operating system.
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Run commands from the repository root. Study inputs and final artwork are **not included**. This is a code-focused public release, not a complete replication archive. Python dependency ranges are not a frozen original environment. R execution was not available during preparation.

## Research context

The workflow supports a Yorkshire regenerative-agriculture modelling study using APSIM, historical/future climate periods and two rotations. The manuscripts were used as private organisation guides and are not redistributed here. Figure/table numbering follows the supplied drafts and may change.

Descriptive sums-of-squares shares are not causal effects or confirmatory significance tests. Shapley values explain model predictions, not independent management effects or field validation. See the [summary](docs/analysis_summary.md) for limitations.

## Attribution and reuse

Please credit Dr Albert Muleke and the relevant eventual research publication when discussing this work. No open-source licence has been selected for this preparation; public visibility alone does not grant a software reuse licence. Third-party libraries retain their own licences. Do not infer that generic modelling or Shapley methods themselves are claimed as novel.

[Climate & Agriculture Evidence dashboard](https://climate-agriculture-evidence.shrewdkrill1.chatgpt.site/)

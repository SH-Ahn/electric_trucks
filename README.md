# Electrification of medium- and heavy-duty trucks: code

Code for a research project on the drivers and barriers of medium- and heavy-duty truck (and bus)
electrification worldwide: adoption, market structure, trade and policy.

This repository holds **code only**. Data, outputs, documentation and references live in sibling
folders of the project root and are not version-controlled:

```
electric_trucks/
├── 01_project_documentation/   research notes, progress log, research design (LaTeX)
├── 02_code/                    this repository
├── 03_data/
│   ├── 01_raw/                 untouched downloads, one folder per source (+ _download_log.csv)
│   ├── 02_processed/           tidy panels built by 02_build/
│   └── 03_purchased/           licensed truck & bus sales data (country x model x quarter)
├── 04_output/{01_figure,02_table}/
└── 05_reference/               reports and papers
└── 06_issues/<issue>/          git worktree of branch <issue> (e.g. issue1), where work happens
```

`02_code/` tracks `main`. Work for an issue is done on its branch in `06_issues/<issue>/`,
with the issue number in every commit subject (e.g. `(#1)`), and reaches `main` through a pull request.

`config.py` finds the project root by searching upward for `03_data/`; set `ET_PROJECT_ROOT` to run from a
clone elsewhere. Large downloads (BACI, Commodity Flow Survey, FAF5, TROPOMI grids) are cached in `~/.cache/electric_trucks` (`ET_CACHE`).

## Pipeline

```bash
pip install -r requirements.txt
python run_all.py --collect      # download everything, then build and explore
python run_all.py                # rebuild panels and figures from existing raw data
python run_all.py --only b05 e05 # selected scripts
```

| Stage | Script | Source / content |
|---|---|---|
| collect | `c01_iea_gevo.py` | IEA Global EV Data Explorer: EV sales, stock, shares by country, mode, powertrain |
| collect | `c02_baci_trade.py` | CEPII BACI HS17/HS22 bilateral trade, vehicle and parts lines |
| collect | `c03_comtrade.py` | UN Comtrade monthly mirror imports (e-trucks, e-buses, e-tractors), annual unit counts; resumable |
| collect | `c04_fred.py` | US heavy-truck sales, truck PPI/IP, diesel and crude prices, rates, FX |
| collect | `c05_eurostat.py` | EU registrations and stocks by motor energy, electricity prices, road freight, truck GHG |
| collect | `c06_eu_oil_bulletin.py` | EU weekly diesel prices with/without taxes, excise duties, VAT |
| collect | `c07_ember.py` | Electricity generation mix and grid CO2 intensity, yearly and monthly |
| collect | `c08_worldbank_wdi.py` | Macro, trade, energy and emissions controls; country metadata |
| collect | `c09_rdw_netherlands.py` | Dutch vehicle register: every N2/N3 truck and M2/M3 bus with fuel records |
| collect | `c10_dft_uk.py` | UK first registrations by make, model, fuel and quarter; HGVs by weight band |
| collect | `c11_statcan.py` | Canada vehicle registrations by fuel and class; monthly vehicle trade |
| collect | `c12_oica.py` | OICA commercial-vehicle sales by country |
| collect | `c13_bis_policy_rates.py` | Central bank policy rates |
| collect | `c14_census_trade.py` | US monthly HS10 trade by partner (needs `CENSUS_API_KEY`) |
| collect | `c16_vius.py` | US Vehicle Inventory and Use Survey 2021 microdata |
| collect | `c17_eurostat_freight.py` | Eurostat road freight by distance class, operation, own account, vehicle age, goods |
| collect | `c18_commodity_flow_survey.py` | US Commodity Flow Survey microdata (2017 PUF, 2022 PUMS), aggregated by mode, industry, commodity, distance |
| collect | `c19_faf5_freight.py` | Freight Analysis Framework 5.7.1 flows by mode, commodity and distance band |
| collect | `c20_germany_truck_toll_index.py` | Germany's daily truck-toll mileage index (Destatis) |
| collect | `c21_climate_trace.py` | Climate TRACE road-transport emissions by country; steel, cement, coal and ore sites |
| collect | `c22_tropomi_no2.py` | Monthly TROPOMI NO2 (KNMI TEMIS), 20 km means around zone cities, corridors, ports, steel plants |
| collect | `c23_world_port_index.py` | NGA World Port Index |
| build | `b01`-`b08` | Tidy panels: IEA, trade, energy prices, policy panel, registries, Eurostat, covariates, North America |
| build | `b09_freight_usage.py` | Freight-use panels: EU country profiles merged with ZEV shares, quarterly tonne-km, goods x distance, US CFS and FAF5, toll index |
| build | `b10_remote_sensing.py` | NO2 site and group panels, heavy-industry sites by country, road emissions by country |
| explore | `e01`-`e07` | Figures and tables in `04_output/` |
| explore | `e08_freight_usage.py`, `e09_remote_sensing.py` | Duty cycles vs adoption, short-haul freight by industry, toll index; satellite NO2 contrasts |

The hand-curated policy database (`03_data/01_raw/policy/`) is research data, kept outside the
repository; `02_build/b04_policy_panel.py` turns it into a country x quarter panel.

## Optional credentials

Read from environment variables, never committed:

- `CENSUS_API_KEY`: free key from https://api.census.gov/data/key_signup.html (needed by `c14`)
- `COMTRADE_API_KEY`: free key from https://comtradedeveloper.un.org/ (lifts the preview quota for `c03`)
- `NREL_API_KEY`: optional, for NREL/AFDC APIs (defaults to `DEMO_KEY`)

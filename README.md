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
| collect | `c24_wto_tbt.py` | WTO ePing TBT notifications on vehicles, parts, batteries, charging, fuels (bulk file, cached) |
| collect | `c25_iea_policies.py` | IEA Policies database: 13,200 energy and climate policies, all countries |
| collect | `c26_wits_tariffs.py` | WITS/UNCTAD TRAINS applied MFN tariffs for electric vs diesel trucks, tractors, buses, cars, batteries, engines |
| collect | `c27_afdc_hd_stations.py` | NREL/DOE AFDC fuelling and charging stations that accept medium or heavy vehicles |
| collect | `c28_oecd_carbon_rates_itf.py` | OECD effective carbon rates on road fuels; ITF goods-vehicle registrations and road traffic |
| collect | `c29_fmcsa_fleet_structure.py` | FMCSA Company Census: active US carriers aggregated by power units (no identifiers downloaded) |
| collect | `c30_eea_hdv_co2.py` | EEA heavy-duty CO2 monitoring: EU truck/bus registrations (Jul 2021-Jun 2025) and VECTO duty-cycle records, aggregated; exact permissible mass distribution (`--mass`) |
| collect | `c31_baci_energy_trade.py` | BACI bilateral trade in crude oil, refined products, LNG, gas, coal (exposure shares for shift-share designs) |
| collect | `c32_osm_truck_charging.py` | OpenStreetMap: truck-tagged charging sites; motorway services and rest areas in Europe (candidate sites) |
| collect | `c33_eia_state_electricity_prices.py` | EIA-861M electricity prices by US state, sector and month |
| collect | `c34_bast_truck_counts.py` | BASt counting stations: daily heavy-vehicle traffic on German motorways and federal roads, with coordinates |
| collect | `c35_carb_large_entity_fleets.py` | CARB Large Entity Reporting (2021): California large-fleet use patterns and holding periods |
| collect | `c36_eafo.py` | European Alternative Fuels Observatory: charging points by power class and for heavy-duty vehicles, AF truck/bus registrations and fleets, 34 pages |
| collect | `c37_ted_bus_truck_tenders.py` | TED procurement notices for buses and municipal trucks (Search API, eForms winners) and filtered CSV bulk award files 2017-2023 (`--bulk-only`) |
| collect | `c38_china_miit_catalogue.py` | China MIIT purchase-tax catalogues of new-energy vehicle models (Word attachments parsed via `textutil`; macOS) |
| collect | `c39_hvip_vouchers.py` | California HVIP voucher records (voucher map API) and eligible-vehicle catalog |
| build | `b01`-`b08` | Tidy panels: IEA, trade, energy prices, policy panel, registries, Eurostat, covariates, North America |
| build | `b09_freight_usage.py` | Freight-use panels: EU country profiles merged with ZEV shares, quarterly tonne-km, goods x distance, US CFS and FAF5, toll index |
| build | `b10_remote_sensing.py` | NO2 site and group panels, heavy-industry sites by country, road emissions by country |
| build | `b12_us_trade.py` | US truck, bus, parts and battery trade by segment, partner, month: units, duties, effective tariffs |
| build | `b13_wto_tbt.py` | TBT notifications tagged by topic (EV/battery/charging, emissions, safety, tyres, fuels, cyber) |
| build | `b14_iea_policies.py` | IEA policies tagged by theme and heavy-duty/freight relevance; country x year counts |
| build | `b15_eu_hdv.py` | EU heavy-duty registrations and VECTO sub-groups mapped to duty cycles and OEM groups |
| build | `b16_tariff_gaps.py` | Electric vs diesel tariff gaps by country, year and vehicle type |
| build | `b17_infrastructure_fleets_fuel_tax.py` | US truck-capable stations, US fleet-size bins, carbon rates on road fuels, ITF registrations |
| explore | `e01`-`e07` | Figures and tables in `04_output/` |
| explore | `e08_freight_usage.py`, `e09_remote_sensing.py` | Duty cycles vs adoption, short-haul freight by industry, toll index; satellite NO2 contrasts |
| explore | `e10_us_trade.py`, `e11_ntm.py` | Section 232 trade effects, reclassification, batteries and used tractors; TBT notifications |
| explore | `e12_policy_patterns.py`, `e13_eu_hdv.py` | Heavy-duty policy portfolios and sequencing (IEA); EU zero-emission shares by duty cycle, country, OEM |
| explore | `e14_tariff_bias.py`, `e15_infrastructure_fleets_fuel_tax.py`, `e16_tbt_exposure_policy_adoption.py` | Environmental bias of vehicle tariffs; charging, fleet structure and fuel taxes; TBTs vs import exposure and national policy vs adoption |
| explore | `e17_structural_facts.py` | Composition vs within decomposition; empirical Bayes OEM x country shares; mass bunching; use patterns; traffic concentration; Gulf exposure; mileage-weighted allocation |
| explore | `e18_procurement_china_hvip_eafo.py` | Home bias and Chinese brands in EU bus tenders; Chinese electric-truck model entry; HVIP vouchers; truck charging per electric truck |

The hand-curated policy database (`03_data/01_raw/policy/`) is research data, kept outside the
repository; `02_build/b04_policy_panel.py` turns it into a country x quarter panel.

## Optional credentials

Read from environment variables, never committed:

- `CENSUS_API_KEY`: free key from https://api.census.gov/data/key_signup.html (needed by `c14`)
- `COMTRADE_API_KEY`: free key from https://comtradedeveloper.un.org/ (lifts the preview quota for `c03`)
- `NREL_API_KEY`: optional, for NREL/AFDC APIs (defaults to `DEMO_KEY`)

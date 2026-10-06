"""Public bus procurement in Europe (TED), Chinese electric-truck model entry (MIIT catalogues),
California's truck vouchers (HVIP) and European truck charging (EAFO).

fig30_bus_procurement   (a) share of awarded EU bus contracts won by Chinese and by domestic brands,
                        electric vs all bus tenders, 2017-2026; (b) domestic-brand share by country;
                        (c) competition: offers per award and share of awards with non-EU tenders
fig31_china_catalogue   (a) new battery-electric and fuel-cell truck models per year by body type;
                        (b) battery capacity of new battery-electric tractors and the battery-swap
                        share; (c) firms with new electric truck models per year
fig32_hvip_eafo         (a) HVIP vouchers per year by drivetrain; (b) manufacturer shares of
                        zero-emission vouchers; (c) EU charging points for heavy-duty vehicles vs
                        battery-electric truck fleets by country
"""
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import RAW_DIR  # noqa: E402
from countries import EUROSTAT_GEO  # noqa: E402

BUS_CPV = ("34120000", "34121", "34144910")
ELECTRIC_CPV = "34144910"
E_WORDS = (r"electri|elektr|eléctr|électr|elettr|eletr|bateri|batter|zero[- ]?emis|zeroemis|\bbev\b|e-bus|ebus|"
           r"wasserstoff|hydrogen|wodór|wodor|idrogeno|hidrógeno|hydrog|trolley|elbus|el-bus|sähkö|elbuss|akumul")
CHINESE = r"\bbyd\b|yutong|higer|king ?long|golden dragon|zhongtong|skywell|ankai|foton|sunwin|yinlong|asiastar"
BRANDS = [  # (regex on winner name, brand, home country ISO3)
    (CHINESE, "Chinese brands", "CHN"), (r"solaris|ekocel", "Solaris", "POL"),
    (r"evobus|daimler|mercedes|setra", "Daimler Buses", "DEU"), (r"\bman\b|man truck", "MAN", "DEU"),
    (r"iveco|heuliez", "Iveco", "ITA"), (r"volvo", "Volvo", "SWE"), (r"scania", "Scania", "SWE"),
    (r"\bvdl\b", "VDL", "NLD"), (r"ebusco", "Ebusco", "NLD"), (r"van ?hool", "Van Hool", "BEL"),
    (r"irizar", "Irizar", "ESP"), (r"castrosua", "Castrosua", "ESP"), (r"otokar", "Otokar", "TUR"),
    (r"karsan", "Karsan", "TUR"), (r"temsa", "Temsa", "TUR"), (r"\bbmc\b", "BMC", "TUR"),
    (r"isuzu|anadolu", "Anadolu Isuzu", "TUR"), (r"alexander dennis", "Alexander Dennis", "GBR"),
    (r"wright", "Wrightbus", "GBR"), (r"\bsor\b|sor libchavy", "SOR", "CZE"), (r"škoda|skoda", "Skoda", "CZE"),
    (r"\bhess\b", "Hess", "CHE"), (r"industria italiana autobus|menarini", "IIA", "ITA"),
    (r"rampini", "Rampini", "ITA"), (r"caetano", "Caetanobus", "PRT"), (r"autosan|solbus|ursus", "Polish other",
                                                                          "POL"),
    (r"ikarus", "Ikarus", "HUN"), (r"bozankaya", "Bozankaya", "TUR")]
ISO2 = {**EUROSTAT_GEO, "GR": "GRC", "GB": "GBR", "UK": "GBR"}


def brand_of(name: str) -> tuple[str, str]:
    n = str(name).lower()
    for rx, b, home in BRANDS:
        if re.search(rx, n):
            return b, home
    return "Other or dealer", ""


def awards() -> pd.DataFrame:
    b = pd.read_csv(RAW_DIR / "ted" / "ted_can_bulk_2017_2023_buses_trucks.csv", dtype=str)
    b = b[b.CANCELLED.fillna("0") != "1"]
    cpv = b.CPV.fillna("") + " " + b.ADDITIONAL_CPVS.fillna("")
    b = b[cpv.str.contains("|".join(BUS_CPV))].copy()
    old = pd.DataFrame({"year": pd.to_numeric(b.YEAR), "buyer": b.ISO_COUNTRY_CODE.map(ISO2),
                        "winner": b.WIN_NAME, "electric": cpv[b.index].str.contains(ELECTRIC_CPV)
                        | b.TITLE.fillna("").str.lower().str.contains(E_WORDS),
                        "offers": pd.to_numeric(b.NUMBER_OFFERS, errors="coerce"),
                        "non_eu": pd.to_numeric(b.NUMBER_TENDERS_NON_EU, errors="coerce"),
                        "value": pd.to_numeric(b.AWARD_VALUE_EURO, errors="coerce"), "source": "bulk"})
    a = pd.read_csv(RAW_DIR / "ted" / "ted_notices_buses_trucks.csv", dtype=str)
    a = a[a["notice-type"].str.startswith("can", na=False) & a["winner-name"].notna()]
    a = a[a["classification-cpv"].fillna("").str.contains("|".join(BUS_CPV))]
    a["year"] = pd.to_numeric(a["publication-date"].str[:4])
    a = a[a.year >= 2024]
    new = pd.DataFrame({"year": a.year, "buyer": a["buyer-country"].str.split("|").str[0],
                        "winner": a["winner-name"].str.split("|"), "electric":
                        a["classification-cpv"].str.contains(ELECTRIC_CPV) |
                        a["title-proc"].fillna("").str.lower().str.contains(E_WORDS),
                        "offers": pd.to_numeric(a["received-submissions-type-val"].str.split("|").str[0],
                                                errors="coerce"),
                        "non_eu": np.nan, "value": pd.to_numeric(a["total-value"], errors="coerce"), "source": "api"})
    new["notice"] = a["publication-number"].values
    new = new.explode("winner")
    new["winner"] = new.winner.str.strip()
    new = new.drop_duplicates(["notice", "winner"]).drop(columns="notice")  # one row per winner and notice
    d = pd.concat([old, new], ignore_index=True)
    d = d[d.winner.notna() & d.year.between(2017, 2026)]
    bh = d.winner.map(brand_of)
    d["brand"], d["home"] = bh.str[0], bh.str[1]
    d["chinese"] = d.brand == "Chinese brands"
    d["domestic"] = (d.home == d.buyer) & (d.home != "")
    return d


def catalogue() -> pd.DataFrame:
    m = pd.read_csv(RAW_DIR / "china_miit" / "miit_nev_tax_catalogue_models.csv", dtype=str)
    m = m[m.vehicle_class.isin(["truck", "special_purpose"]) & m.powertrain.isin(["BEV", "FCEV"])].copy()
    m["year"] = pd.to_datetime(m.published).dt.year
    m = m.sort_values("published").drop_duplicates(["model_code"], keep="first")  # first listing = entry
    name = m.product_name.fillna("")
    m["body"] = np.select([name.str.contains("牵引"), name.str.contains("自卸") & ~name.str.contains("垃圾"),
                           name.str.contains("搅拌"), name.str.contains("垃圾|洗扫|清扫|清洗|洒水|抑尘|扫路|养护"),
                           name.str.contains("厢式|仓栅|载货|运输|冷藏|邮政|多用途")],
                          ["Tractor", "Dump truck", "Concrete mixer", "Sanitation", "Box, cargo, reefer"], "Other")
    m["swap"] = name.str.contains("换电")
    m["kwh"] = pd.to_numeric(m.battery_kwh.fillna("").str.extract(r"([\d.]+)")[0], errors="coerce")
    return m


def main() -> None:
    ps.use()
    d = awards()
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 4.0), gridspec_kw={"width_ratios": [1.2, 1, 1]})
    for elec, ls, lab in ((True, "-", "electric tenders"), (False, "--", "all bus tenders")):
        x = d[d.electric] if elec else d
        g = x.groupby("year").agg(chinese=("chinese", "mean"), domestic=("domestic", "mean"), n=("brand", "size"))
        axes[0].plot(g.index, 100 * g.chinese, color=ps.SLOTS[1], linestyle=ls, label=f"Chinese brands, {lab}")
        axes[0].plot(g.index, 100 * g.domestic, color=ps.SLOTS[0], linestyle=ls, label=f"Domestic brands, {lab}")
    axes[0].legend(loc="upper left", fontsize=6.5)
    axes[0].set_ylabel("% of awards")
    axes[0].set_title("(a) Awards of EU bus contracts won by\nChinese and domestic brands")
    c = d[d.year >= 2020].groupby("buyer").agg(n=("brand", "size"), domestic=("domestic", "mean"),
                                               chinese=("chinese", "mean"))
    c = c[c.n >= 80].sort_values("domestic")
    names = {"DEU": "Germany", "FRA": "France", "ITA": "Italy", "POL": "Poland", "ESP": "Spain", "PRT": "Portugal",
             "GRC": "Greece", "GBR": "UK", "IRL": "Ireland", "ROU": "Romania", "CZE": "Czechia", "BGR": "Bulgaria",
             "SWE": "Sweden", "NLD": "Netherlands", "BEL": "Belgium", "AUT": "Austria", "HUN": "Hungary",
             "SVK": "Slovakia", "LTU": "Lithuania", "NOR": "Norway", "FIN": "Finland", "DNK": "Denmark",
             "HRV": "Croatia", "SVN": "Slovenia", "LVA": "Latvia", "EST": "Estonia", "CHE": "Switzerland"}
    y = range(len(c))
    axes[1].barh(list(y), 100 * c.domestic, color=ps.SLOTS[0], height=0.6, label="Domestic brand")
    axes[1].barh(list(y), 100 * c.chinese, left=100 * c.domestic, color=ps.SLOTS[1], height=0.6,
                 label="Chinese brand")
    axes[1].set_yticks(list(y))
    axes[1].set_yticklabels([f"{names.get(i, i)} ({n:.0f})" for i, n in zip(c.index, c.n)], fontsize=7)
    axes[1].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[1].grid(axis="y", visible=False)
    axes[1].legend(loc="lower right", fontsize=6.5)
    axes[1].set_xlabel("% of awards, 2020-2026")
    axes[1].set_title("(b) Bus awards won by domestic and\nChinese brands, by buyer country")
    comp = d[d.offers.notna()].groupby("year").agg(offers=("offers", "median"),
                                                   single=("offers", lambda s: (s == 1).mean()))
    noneu = d[d.source == "bulk"].groupby("year").non_eu.apply(lambda s: (s > 0).mean())
    axes[2].plot(comp.index, 100 * comp.single, color=ps.SLOTS[3], marker="o", markersize=3,
                 label="Awards with a single offer")
    axes[2].plot(noneu.index, 100 * noneu, color=ps.SLOTS[1], marker="o", markersize=3,
                 label="Awards with a non-EU tender (to 2023)")
    axes[2].set_ylim(0, 60)
    axes[2].set_ylabel("% of awards")
    axes[2].legend(loc="upper left", fontsize=6.5)
    axes[2].set_title("(c) Competition in bus tenders")
    fig.text(0.0, -0.08, "Award notices in TED for buses (CPV 3412xxxx, 34144910); 2017-2023 from the TED CSV bulk "
             "files (one row per award), 2024-2026 from eForms notices (one row per winner). Brands mapped from winner "
             "names; dealers\nand unmapped winners count in the denominator. Domestic = brand's home country equals the "
             "buyer's. Electric = electric-bus CPV or title keywords. Source: TED; own coding.", fontsize=7,
             color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig30_bus_procurement")

    m = catalogue()
    m = m[m.year <= 2024]  # 2025-26 reduction batches list few new truck models (see note)
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 4.0), gridspec_kw={"width_ratios": [1.25, 1, 0.9]})
    bodies = {"Box, cargo, reefer": ps.SLOTS[0], "Dump truck": ps.SLOTS[1], "Tractor": ps.SLOTS[2],
              "Sanitation": ps.SLOTS[3], "Concrete mixer": ps.SLOTS[6], "Other": ps.OTHER}
    yb = m.pivot_table(index="year", columns="body", values="model_code", aggfunc="count").fillna(0)
    bottom = np.zeros(len(yb))
    for b, col in bodies.items():
        if b in yb:
            axes[0].bar(yb.index, yb[b], bottom=bottom, color=col, label=b, width=0.75, edgecolor="white",
                        linewidth=0.8)
            bottom += yb[b].values
    axes[0].legend(loc="upper left", fontsize=6.5)
    axes[0].set_title("(a) New battery-electric and fuel-cell truck\nmodels in China's tax catalogues, by body")
    tr = m[(m.body == "Tractor") & (m.powertrain == "BEV")]
    g = tr.groupby("year").agg(kwh=("kwh", "median"), swap=("swap", "mean"), n=("model_code", "size"))
    g = g[g.n >= 20]
    axes[1].plot(g.index, g.kwh, color=ps.SLOTS[0], marker="o", markersize=3)
    for yr, r in g.iterrows():
        axes[1].annotate(f"{100 * r.swap:.0f}%", (yr, r.kwh), xytext=(0, 5), textcoords="offset points",
                         ha="center", fontsize=6.5, color=ps.INK_2)
    axes[1].set_ylabel("Median battery capacity (kWh)")
    axes[1].set_xticks(list(g.index))
    axes[1].set_title("(b) New battery-electric tractors: median\nbattery (labels: battery-swap share)")
    f = m.groupby("year").firm.nunique()
    first = m.groupby("firm").year.min()
    ent = m.assign(entrant=m.firm.map(first) == m.year).groupby("year").entrant.mean()
    axes[2].bar(f.index, f.values, color=ps.SLOTS[0], width=0.7)
    for yr, v in f.items():
        axes[2].annotate(f"{100 * ent[yr]:.0f}%", (yr, v), xytext=(0, 2), textcoords="offset points", ha="center",
                         fontsize=6.5, color=ps.INK_2)
    axes[2].set_title("(c) Firms listing new electric truck models\n(labels: % of models by first-time firms)")
    fig.text(0.0, -0.08, "Battery-electric and fuel-cell trucks and special-purpose vehicles in MIIT's catalogues of new-"
             "energy vehicles exempt from (2017-2023) or eligible for reduced (2024-) purchase tax; a model counts in the "
             "year of\nits first listing; 2017-2024 (the 2025-26 batches list few new truck models). Coverage: exemption "
             "batches 14-73, reduction batches 2-34, a few batches missing. Source: MIIT; own parsing.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig31_china_catalogue")

    v = pd.read_csv(RAW_DIR / "hvip" / "hvip_vouchers.csv")
    v = v[v.redemption_status == "Redeemed"]
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 4.0), gridspec_kw={"width_ratios": [1.2, 1, 1.1]})
    dt = {"ZEV-BEV": ("Battery electric", ps.SLOTS[0]), "ZEV-FCV": ("Fuel cell", ps.SLOTS[2]),
          "HV": ("Hybrid", ps.SLOTS[3]), "Natural Gas": ("Natural gas", ps.OTHER), "ePTO": ("ePTO", ps.SLOTS[6])}
    yv = v.pivot_table(index="voucher_requested_year", columns="drivetrain", values="voucher_id",
                       aggfunc="count").fillna(0)
    bottom = np.zeros(len(yv))
    for k, (lab, col) in dt.items():
        if k in yv:
            axes[0].bar(yv.index, yv[k], bottom=bottom, color=col, label=lab, width=0.75, edgecolor="white",
                        linewidth=0.6)
            bottom += yv[k].values
    axes[0].legend(loc="upper left", fontsize=6.5)
    axes[0].set_xticks(range(2010, 2027, 4))
    axes[0].set_title("(a) California HVIP vouchers per year\nby drivetrain (none requested in 2020)")
    z = v[v.drivetrain.isin(["ZEV-BEV", "ZEV-FCV"])]
    ms = (100 * z.manufacturer.value_counts(normalize=True)).head(10).iloc[::-1]
    axes[1].barh(ms.index, ms.values, color=ps.SLOTS[0], height=0.6)
    for i, val in enumerate(ms.values):
        axes[1].annotate(f"{val:.0f}%", (val, i), xytext=(3, 0), textcoords="offset points", va="center", fontsize=6.5,
                         color=ps.INK_2)
    axes[1].tick_params(axis="y", labelsize=7)
    axes[1].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[1].grid(axis="y", visible=False)
    axes[1].set_title(f"(b) Manufacturer shares of zero-emission\nvouchers (n={len(z):,})")
    e = pd.read_csv(RAW_DIR / "eafo" / "eafo_charts_long.csv")
    hdv = e[(e.chart == "countries_overview_of_hdv_infrastructure")].pivot_table(index="period", columns="series",
                                                                               values="value", aggfunc="sum").sum(axis=1)
    fl = e[(e.chart == "fleet_overview_of_af_trucks_n2_n3") & (e.series == "BEV")].set_index("period").value
    j = pd.DataFrame({"points": hdv, "bev": fl}).dropna()
    axes[2].scatter(j.bev, j.points, s=24, color=ps.SLOTS[0], edgecolor="white", linewidth=0.5)
    for cty, r in j.iterrows():
        if r.points > 60 or r.bev > 1500:
            axes[2].annotate(cty, (r.bev, r.points), xytext=(3, 2), textcoords="offset points", fontsize=6.5,
                             color=ps.INK_2)
    axes[2].set_xscale("log")
    axes[2].set_yscale("log")
    axes[2].set_xlabel("Battery-electric trucks in the fleet (N2/N3)")
    axes[2].set_ylabel("Charging points for heavy-duty vehicles")
    axes[2].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[2].set_title("(c) Truck charging points vs electric truck\nfleet, EU countries (AFIR reporting, 2026)")
    fig.text(0.0, -0.08, "(a)-(b) Redeemed HVIP vouchers (CARB/CALSTART voucher map); 2026 to date. (c) Points dedicated to "
             "or exclusively for heavy-duty vehicles, latest quarter; fleets from EAFO. Sources: HVIP; EAFO.",
             fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig32_hvip_eafo")

    # printed summaries for the design document
    g = d.groupby(["year", "electric"]).agg(n=("brand", "size"), chinese=("chinese", "mean"),
                                           domestic=("domestic", "mean")).unstack()
    print(g.round(3).to_string())
    print("by country 2020-26:\n", c.round(3).to_string())
    print("brands (electric, 2024-26):", (100 * d[(d.year >= 2024) & d.electric].brand.value_counts(
        normalize=True)).round(1).head(12).to_dict())
    print("competition:", comp.round(2).to_dict(), "non-EU:", noneu.round(3).to_dict())
    print("catalogue models by year x powertrain:", m.groupby(["year", "powertrain"]).size().unstack().fillna(0)
          .astype(int).to_dict())
    print("tractors:", g.round(1).to_string() if False else tr.groupby("year").agg(kwh=("kwh", "median"), swap=(
        "swap", "mean"), n=("model_code", "size")).round(2).to_string())
    print("firms:", f.to_dict(), "entrant share:", ent.round(2).to_dict())
    print("top firms (all years):", m.firm.value_counts().head(10).to_dict())
    zz = z.assign(y=z.voucher_requested_year)
    print("ZEV vouchers:", len(z), "amount $m", round(z.amount.sum() / 1e6), "small fleet:", (z.small_fleet == "Yes").mean()
          .round(3), "drayage:", (z.drayage_operations == "Yes").mean().round(3), "DAC:", (z.dac == "Yes").mean().round(3),
          "public:", z.pub_or_priv.fillna("").str.startswith("Public").mean().round(3))
    top = z.purchaser_company.value_counts()
    print("top-10 purchaser share:", round(top.head(10).sum() / len(z), 3), "purchasers:", top.size)
    print("vocations:", z.vocation.value_counts().head(8).to_dict())
    print("by GVW:", z.groupby("gross_vehicle_weight").amount.agg(["size", "mean"]).round(0).to_dict())
    print("EAFO HDV points vs BEV fleet:\n", j.sort_values("points", ascending=False).to_string())


if __name__ == "__main__":
    main()

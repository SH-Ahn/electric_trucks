"""Facts that inform the structural model and the empirical designs (empirical_strategy.pdf).

fig27_eu_structure        (a) EU countries' gap to the EU zero-emission share of certified trucks,
                          split into duty-cycle composition and within-duty-cycle adoption;
                          (b) battery-electric shares by OEM group x country, raw vs empirical
                          Bayes posterior; (c) permissible mass of new N2 trucks and vans,
                          battery-electric vs diesel (bunching at 4,250 kg)
fig28_use_infrastructure  (a) use patterns of California's large fleets (CARB Large Entity
                          Reporting); (b) holding periods; (c) concentration of heavy-vehicle
                          traffic across German motorway counting stations (BASt)
fig29_exposure_allocation (a) exposure to Gulf oil supply vs the 2026 change in pre-tax diesel
                          prices; (b) where zero-emission trucks are vs where new-truck mileage
                          is, by VECTO sub-group (annual mileages of Regulation (EU) 2019/1242)
tab_eb_oem_country.tex    empirical Bayes summary for OEM group x country cells
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plot_style as ps  # noqa: E402
from config import PROC_DIR, RAW_DIR, TAB_DIR  # noqa: E402
from countries import iso3_from_m49  # noqa: E402

# annual mileage (km) by VECTO sub-group, Regulation (EU) 2019/1242, Annex I, Table 4
MILEAGE = {"4-UD": 60_000, "4-RD": 78_000, "4-LH": 98_000, "5-RD": 78_000, "5-LH": 116_000, "9-RD": 73_000,
           "9-LH": 108_000, "10-RD": 68_000, "10-LH": 107_000}
GULF = {"SAU", "IRQ", "ARE", "KWT", "QAT", "IRN", "OMN", "BHR"}
NAMES = {"DEU": "Germany", "FRA": "France", "ESP": "Spain", "POL": "Poland", "ITA": "Italy", "NLD": "Netherlands",
         "BEL": "Belgium", "SWE": "Sweden", "AUT": "Austria", "CZE": "Czechia", "NOR": "Norway", "DNK": "Denmark",
         "FIN": "Finland", "LTU": "Lithuania", "ROU": "Romania", "PRT": "Portugal", "HUN": "Hungary", "IRL": "Ireland",
         "GBR": "UK", "USA": "US", "SVK": "Slovakia", "SVN": "Slovenia", "BGR": "Bulgaria", "GRC": "Greece",
         "HRV": "Croatia", "LVA": "Latvia", "EST": "Estonia", "LUX": "Luxembourg", "CYP": "Cyprus", "MLT": "Malta"}


def decomposition() -> pd.DataFrame:
    v = pd.read_csv(PROC_DIR / "eu_hdv_vecto_subgroups.csv")
    v = v[(v.period == 2024) & v.subgroup.isin(MILEAGE)]
    v["zev"] = v.vehicles.where(v.powertrain == "Zero emission", 0)
    cell = v.groupby(["iso3", "subgroup"])[["vehicles", "zev"]].sum()
    eu = cell.groupby("subgroup").sum()
    w_eu, s_eu = eu.vehicles / eu.vehicles.sum(), eu.zev / eu.vehicles
    rows = []
    for c, g in cell.groupby("iso3"):
        g = g.droplevel(0)
        if g.vehicles.sum() < 1500:
            continue
        w = (g.vehicles / g.vehicles.sum()).reindex(w_eu.index, fill_value=0)
        s = (g.zev / g.vehicles).reindex(w_eu.index).fillna(s_eu)
        comp = ((w - w_eu) * (s + s_eu) / 2).sum()
        within = (((w + w_eu) / 2) * (s - s_eu)).sum()
        rows.append({"iso3": c, "n": g.vehicles.sum(), "share": 100 * g.zev.sum() / g.vehicles.sum(),
                     "composition": 100 * comp, "within": 100 * within})
    d = pd.DataFrame(rows).sort_values("share")
    d.attrs["eu_share"] = 100 * eu.zev.sum() / eu.vehicles.sum()
    return d


def eb_oem_country() -> tuple[pd.DataFrame, dict]:
    r = pd.read_csv(PROC_DIR / "eu_hdv_registrations.csv")
    t = r[(r.segment == "Truck") & r.mass_class.isin(["7.5-16t", "16-26t", ">26t"]) & (r.period == 2024)
          & (r.iso3 != "ITA")].copy()
    t["bev"] = t.vehicles.where(t.powertrain == "Battery electric", 0)
    t["diesel"] = t.vehicles.where(t.powertrain == "Diesel", 0)
    c = t.groupby(["iso3", "oem_group"])[["vehicles", "bev", "diesel"]].sum()
    c = c[c.vehicles >= 5].copy()
    c["raw"] = c.bev / c.vehicles
    ctry = c.groupby("iso3")[["bev", "vehicles"]].sum()
    c["prior_mean"] = (ctry.bev / ctry.vehicles).reindex(c.index.get_level_values(0)).values
    c["diesel_share_in_country"] = c.diesel / c.groupby("iso3").diesel.transform("sum")
    # beta-binomial moments around the country mean: true between-OEM variance net of sampling noise
    dev = c.raw - c.prior_mean
    noise = (c.prior_mean * (1 - c.prior_mean) / c.vehicles).mean()
    tau2 = max(np.average(dev ** 2, weights=c.vehicles) - noise, 1e-6)
    m = np.clip(c.prior_mean, 1e-4, 1 - 1e-4)
    strength = np.maximum(m * (1 - m) / tau2 - 1, 1)  # a + b of the Beta prior
    c["posterior"] = (c.bev + m * strength) / (c.vehicles + strength)
    within = c.assign(post_dm=c.posterior - c.prior_mean)
    x, y, wt = within.diesel_share_in_country, within.post_dm, within.vehicles
    xm, ym = np.average(x, weights=wt), np.average(y, weights=wt)
    slope = np.sum(wt * (x - xm) * (y - ym)) / np.sum(wt * (x - xm) ** 2)
    stats = {"cells": len(c), "sd_raw": 100 * np.sqrt(np.average(dev ** 2, weights=c.vehicles)),
             "sd_true": 100 * np.sqrt(tau2), "slope_pp_per_10pp": 100 * slope * 0.1,
             "leader_below_country": np.mean([g.loc[g.diesel.idxmax(), "posterior"] < g.prior_mean.iloc[0]
                                              for _, g in c.groupby("iso3") if len(g) >= 3])}
    return c.reset_index(), stats


def hormuz() -> pd.DataFrame:
    e = pd.read_csv(RAW_DIR / "baci" / "baci_hs17_V202601_energy.csv.gz", dtype={"hs6": str})
    e = e[e.hs6.isin(["270900", "271000"]) & e.year.isin([2023, 2024])].copy()
    e["exp_iso"] = e.exporter.map(iso3_from_m49)
    e["imp_iso"] = e.importer.map(iso3_from_m49)
    g = e.assign(gulf=e.exp_iso.isin(GULF)).groupby(["imp_iso", "gulf"]).value_kusd.sum().unstack(fill_value=0)
    expo = (100 * g[True] / g.sum(axis=1)).rename("gulf_share")
    p = pd.read_csv(PROC_DIR / "diesel_prices_monthly.csv", parse_dates=["month"])
    p["price"] = p.diesel_net_eur_l.fillna(p.diesel_usd_l)
    base = p[p.month == "2026-01-01"].set_index("iso3").price
    late = p[p.month.between("2026-07-01", "2026-09-01")].groupby("iso3").price.mean()
    d = pd.DataFrame({"gulf_share": expo, "dprice": 100 * (late / base - 1)}).dropna()
    return d[(d.index.str.len() == 3) & (d.index != "MLT")]  # Malta regulates fuel prices


def allocation() -> pd.DataFrame:
    v = pd.read_csv(PROC_DIR / "eu_hdv_vecto_subgroups.csv")
    v = v[(v.period == 2024) & v.subgroup.isin(MILEAGE)]
    g = v.assign(zev=v.vehicles.where(v.powertrain == "Zero emission", 0)).groupby("subgroup")[["vehicles", "zev"]].sum()
    g["km"] = g.vehicles * pd.Series(MILEAGE)
    g["zev_km"] = g.zev * pd.Series(MILEAGE)
    out = pd.DataFrame({"share_of_trucks": 100 * g.vehicles / g.vehicles.sum(), "share_of_km": 100 * g.km / g.km.sum(),
                        "share_of_zev": 100 * g.zev / g.zev.sum(), "zev_share": 100 * g.zev / g.vehicles})
    out.attrs["unit"] = 100 * g.zev.sum() / g.vehicles.sum()
    out.attrs["km_weighted"] = 100 * g.zev_km.sum() / g.km.sum()
    return out.loc[list(MILEAGE)]


def grid_weighting() -> dict:
    r = pd.read_csv(PROC_DIR / "eu_hdv_registrations.csv")
    t = r[(r.segment == "Truck") & r.mass_class.isin(["7.5-16t", "16-26t", ">26t"]) & (r.period == 2024)]
    cov = pd.read_csv(PROC_DIR / "country_year_covariates.csv", usecols=["iso3", "year", "grid_gco2_kwh"])
    grid = cov[cov.year == 2024].set_index("iso3").grid_gco2_kwh
    by = t.pivot_table(index="iso3", columns="powertrain", values="vehicles", aggfunc="sum").fillna(0)
    by = by.join(grid, how="inner")
    return {k: np.average(by.grid_gco2_kwh, weights=by[k]) for k in ("Battery electric", "Diesel")}


def main() -> None:
    ps.use()
    dec = decomposition()
    eb, st = eb_oem_country()
    mass = pd.read_csv(RAW_DIR / "eea_hdv" / "eea_hdv_mass_distribution.csv")
    n2 = mass[(mass.period >= 2023) & (mass.category == "N2") & mass.mass_kg.between(3500, 12000)]

    fig, axes = plt.subplots(1, 3, figsize=(11.8, 4.2), gridspec_kw={"width_ratios": [1.05, 1, 1.15]})
    d = dec.tail(14)
    y = range(len(d))
    axes[0].barh(list(y), d.composition, color=ps.SLOTS[1], height=0.6, label="Duty-cycle composition")
    axes[0].barh(list(y), d.within, left=np.where(np.sign(d.within) == np.sign(d.composition), d.composition, 0),
                 color=ps.SLOTS[0], height=0.6, label="Adoption within duty cycles")
    axes[0].axvline(0, color=ps.BASELINE, linewidth=0.8)
    axes[0].set_yticks(list(y))
    axes[0].set_yticklabels([f"{NAMES.get(i, i)} ({s:.1f}%)" for i, s in zip(d.iso3, d.share)], fontsize=7)
    axes[0].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[0].grid(axis="y", visible=False)
    axes[0].legend(loc="lower right", fontsize=6.5)
    axes[0].set_xlabel("Percentage points")
    axes[0].set_title(f"(a) Gap to the EU zero-emission share\n({dec.attrs['eu_share']:.1f}%), certified trucks 2024-25")
    sz = 6 + 60 * eb.vehicles / eb.vehicles.max()
    axes[1].scatter(100 * eb.raw, 100 * eb.posterior, s=sz, color=ps.SLOTS[0], alpha=0.6, edgecolor="white",
                    linewidth=0.4)
    ytop = 100 * eb.posterior.max() * 1.25
    axes[1].plot([0, ytop], [0, ytop], color=ps.MUTED, linestyle="--", linewidth=0.8)
    axes[1].set_xlim(-1, 102)
    axes[1].set_ylim(-0.5, ytop)
    axes[1].set_xlabel("Raw battery-electric share (%)")
    axes[1].set_ylabel("Empirical Bayes posterior (%)")
    axes[1].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[1].set_title(f"(b) OEM group x country cells (n={st['cells']}),\ntrucks >7.5 t, 2024-25")
    axes[1].annotate(f"SD of raw shares {st['sd_raw']:.1f} pp;\nSD net of noise {st['sd_true']:.1f} pp;\n"
                     "small cells at 60-100% shrink to ~10%", (0.35, 0.80), xycoords="axes fraction", fontsize=7,
                     color=ps.INK_2)
    bins = np.arange(3500, 12051, 250)
    for pt, col in (("Diesel", ps.OTHER), ("Battery electric", ps.SLOTS[0])):
        x = n2[n2.powertrain == pt]
        h, _ = np.histogram(x.mass_kg, bins=bins, weights=x.vehicles)
        axes[2].step(bins[:-1], 100 * h / h.sum(), where="post", color=col, linewidth=1.4, label=pt)
    for kg, lab, yy in ((4250, "4,250 kg: licence\nderogation for\nalternative-fuel vans", 0.62),
                        (7490, "7.5 t", 0.62), (11990, "12 t", 0.62)):
        axes[2].axvline(kg, color=ps.MUTED, linewidth=0.7, linestyle=":")
        axes[2].annotate(lab, (kg, axes[2].get_ylim()[1] * yy), xytext=(4, 0), textcoords="offset points",
                         fontsize=6.5, color=ps.MUTED, va="center", ha="left" if kg < 11000 else "right")
    axes[2].legend(loc="center right", fontsize=7)
    axes[2].set_xlabel("Technically permissible maximum mass (kg)")
    axes[2].set_ylabel("% of registrations (250 kg bins)")
    axes[2].set_title("(c) New N2 trucks and vans by permissible\nmass, Jul 2023-Jun 2025")
    fig.text(0.0, -0.08, "(a) VECTO sub-groups with defined duty cycles; gap = composition + within (symmetric shift-share "
             "decomposition); countries with at least 1,500 certified trucks. (b) Beta-binomial shrinkage towards the country "
             "mean;\ncells with at least 5 trucks, Italy excluded. (c) N2 = goods vehicles of 3.5-12 t. Source: EEA "
             "heavy-duty CO2 monitoring data; own calculations.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig27_eu_structure")

    carb = pd.read_csv(RAW_DIR / "carb" / "carb_ler_vehicle_tables.csv")
    groups = {"day_cab_tractor": ("Day-cab tractors", ps.SLOTS[0]), "sleeper_cab_tractor": ("Sleeper-cab tractors",
              ps.SLOTS[1]), "other_vehicles": ("Other trucks and vans", ps.SLOTS[2])}
    ind = {"returns_to_base_daily": "Return to base\ndaily", "parked_over_8h_at_base": "Parked >8 h\nat base",
           "fuels_at_home_base": "Fuel at\nhome base", "daily_mileage": "<=100 miles\nper day"}
    vals = {}
    for g in groups:
        x = carb[carb.group == g]
        out = {}
        for topic in ind:
            s = x[x.topic == topic].set_index("row").vehicles
            out[topic] = 100 * (s.get("Operate up to 100 miles", 0) if topic == "daily_mileage" else s.get("Yes", 0)) / s.sum()
        vals[g] = out
    vals = pd.DataFrame(vals)
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 3.9), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    xs = np.arange(len(ind))
    for k, (g, (lab, col)) in enumerate(groups.items()):
        axes[0].bar(xs + (k - 1) * 0.26, vals[g], width=0.26, color=col, label=lab)
    axes[0].set_xticks(xs)
    axes[0].set_xticklabels(list(ind.values()), fontsize=7)
    axes[0].set_ylim(0, 105)
    axes[0].legend(loc="upper right", fontsize=6.5)
    axes[0].set_title("(a) Use patterns of California's large fleets\n(% of owned vehicles, 2021 reporting)")
    yk = carb[carb.topic == "years_kept"].pivot_table(index="group", columns="row", values="vehicles")
    order = ["Less than 4", "5 to 10", "11 to 15", "16 to 20", "More than 20"]
    yk = 100 * yk[order].div(yk[order].sum(axis=1), axis=0)
    left = np.zeros(3)
    shades = [ps.SLOTS[1], ps.SLOTS[3], ps.SLOTS[0], ps.SLOTS[6], ps.OTHER]
    for o, col in zip(order, shades):
        vv = yk.loc[list(groups), o].values
        axes[1].barh(range(3), vv, left=left, color=col, height=0.6, label=o, edgecolor="white", linewidth=1)
        left += vv
    axes[1].set_yticks(range(3))
    axes[1].set_yticklabels([groups[g][0] for g in groups], fontsize=7)
    axes[1].set_xlim(0, 100)
    axes[1].grid(False)
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=6.5, title="Years kept",
                   title_fontsize=6.5)
    axes[1].set_title("(b) Holding period after purchase\n(% of owned vehicles)")
    b = pd.read_csv(RAW_DIR / "bast" / "bast_counting_stations_annual.csv")
    m = b[(b.road_class == "A") & (b.year == 2024)].dropna(subset=["aadt_heavy"]).sort_values("aadt_heavy",
                                                                                             ascending=False)
    cum = 100 * m.aadt_heavy.cumsum() / m.aadt_heavy.sum()
    xs2 = 100 * np.arange(1, len(m) + 1) / len(m)
    axes[2].plot(xs2, cum.values, color=ps.SLOTS[0])
    axes[2].plot([0, 100], [0, 100], color=ps.MUTED, linestyle="--", linewidth=0.8)
    top20 = cum.values[int(0.2 * len(m)) - 1]
    axes[2].annotate(f"Top 20% of stations:\n{top20:.0f}% of heavy traffic", (20, top20), xytext=(12, -28),
                     textcoords="offset points", fontsize=7, color=ps.INK_2,
                     arrowprops={"arrowstyle": "-", "color": ps.MUTED, "linewidth": 0.6})
    axes[2].set_xlabel("% of motorway counting stations (busiest first)")
    axes[2].set_ylabel("% of heavy-vehicle traffic")
    axes[2].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[2].set_title(f"(c) Heavy-vehicle traffic across German\nmotorway counting stations, 2024 (n={len(m):,})")
    fig.text(0.0, -0.1, "(a)-(b) CARB Large Entity Reporting, 2021: 1,866 large entities and government fleets, 386,286 "
             "vehicles over 8,500 lb in California; electric vehicles were 0.11%. (c) Average daily heavy-vehicle "
             "traffic (>3.5 t),\nBASt automatic counting stations on motorways. Sources: CARB; BASt.", fontsize=7,
             color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig28_use_infrastructure")

    h = hormuz()
    al = allocation()
    gw = grid_weighting()
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), gridspec_kw={"width_ratios": [1, 1.25]})
    axes[0].scatter(h.gulf_share, h.dprice, s=20, color=ps.SLOTS[0], edgecolor="white", linewidth=0.5)
    for iso, r in h.iterrows():
        if iso in ("USA", "GBR", "DEU", "FRA", "POL", "GRC", "ITA", "ESP", "NLD", "SWE", "LTU", "HUN", "BGR", "FIN",
                   "SVN"):
            axes[0].annotate(NAMES.get(iso, iso), (r.gulf_share, r.dprice), xytext=(3, 2), textcoords="offset points",
                             fontsize=6.5, color=ps.INK_2)
    rho = h.corr().iloc[0, 1]
    axes[0].set_xlabel("Gulf share of crude and refined-oil imports, 2023-24 (%)")
    axes[0].set_ylabel("Change in pre-tax diesel price, Jan to Jul-Sep 2026 (%)")
    axes[0].grid(axis="x", color=ps.GRID, linewidth=0.6)
    axes[0].set_title(f"(a) Exposure to Gulf supply and the 2026\ndiesel shock (r = {rho:.2f}, n = {len(h)})")
    xs = np.arange(len(al))
    axes[1].bar(xs - 0.2, al.share_of_km, width=0.4, color=ps.OTHER, label="Share of new-truck mileage")
    axes[1].bar(xs + 0.2, al.share_of_zev, width=0.4, color=ps.SLOTS[0], label="Share of zero-emission trucks")
    axes[1].set_xticks(xs)
    axes[1].set_xticklabels(al.index, fontsize=7.5)
    axes[1].legend(loc="upper left", fontsize=7)
    axes[1].set_ylabel("%")
    axes[1].set_title(f"(b) Where zero-emission trucks are vs where the km are,\nEU 2024-25: {al.attrs['unit']:.1f}% "
                      f"of trucks, {al.attrs['km_weighted']:.1f}% of mileage")
    fig.text(0.0, -0.08, "(a) EU countries (except Malta, which regulates fuel prices) and US; pre-tax prices from the EU "
             "Weekly Oil Bulletin (US: retail). "
             "Gulf = Saudi Arabia, Iraq, UAE, Kuwait, Qatar, Iran, Oman, Bahrain; BACI HS 2709 and 2710.\n(b) VECTO "
             "sub-groups (4/9 rigid, 5/10 tractor; UD urban, RD regional, LH long-haul delivery) weighted by the annual "
             "mileages of Regulation (EU) 2019/1242. Sources: BACI; EU Oil Bulletin; EEA.", fontsize=7, color=ps.MUTED)
    fig.tight_layout()
    ps.save(fig, "fig29_exposure_allocation")

    tab = pd.DataFrame({"Value": [st["cells"], st["sd_raw"], st["sd_true"], st["slope_pp_per_10pp"],
                                  100 * st["leader_below_country"]]},
                       index=["OEM group x country cells (trucks >7.5 t, 2024-25)", "SD of raw BEV shares around "
                              "country mean (pp)", "SD of true shares, net of sampling noise (pp)",
                              "Posterior BEV share per +10 pp of diesel share in country (pp)",
                              "Countries where the diesel leader is below the country mean (%)"])
    tab.to_latex(TAB_DIR / "tab_eb_oem_country.tex", float_format="%.2f", position="htbp", escape=True,
                 label="tab:eboem", caption="Empirical Bayes estimates of battery-electric shares by OEM group and "
                 "country (beta-binomial shrinkage towards the country mean). Source: EEA heavy-duty CO2 monitoring data.")
    print(dec.round(2).to_string())
    print(st)
    print(eb.sort_values("vehicles", ascending=False).head(12)[["iso3", "oem_group", "vehicles", "raw", "posterior",
                                                                  "diesel_share_in_country"]].round(3).to_string())
    print(h.round(1).sort_values("gulf_share").to_string(), "\ncorr", round(rho, 2))
    print(al.round(1).to_string(), al.attrs)
    print("grid-weighted g/kWh:", {k: round(v) for k, v in gw.items()})
    print("CARB indicators (%):\n", vals.round(0).to_string())
    print("BASt top-20% share:", round(top20, 1), "stations", len(m))
    r = pd.read_csv(PROC_DIR / "eu_hdv_registrations.csv")
    t = r[(r.segment == "Truck") & r.mass_class.isin(["7.5-16t", "16-26t", ">26t"])].copy()
    t["m"] = t.month.str[5:7]
    s = t.assign(bev=t.vehicles.where(t.powertrain == "Battery electric", 0)).groupby("m")[["bev", "vehicles"]].sum()
    print("BEV share by calendar month (%):", (100 * s.bev / s.vehicles).round(2).to_dict())


if __name__ == "__main__":
    main()

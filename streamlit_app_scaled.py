
import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Medical Drone Cost Calculator - Trinity F90+ (Scaled)", layout="wide")

# ---------- Helpers ----------
def fmt_currency(x):
    try:
        return f"${x:,.2f}"
    except Exception:
        return "—"

def battery_wear_per_flight(pack_cost, usable_kwh, cycle_life, kwh_per_flight):
    if usable_kwh <= 0 or cycle_life <= 0:
        return 0.0
    return (pack_cost / (usable_kwh * cycle_life)) * kwh_per_flight

def diesel_rate_per_kwh(diesel_price_per_liter, sfc_l_per_kwh):
    # Simple LCOE proxy: $/kWh = diesel $/L * liters/kWh
    return diesel_price_per_liter * sfc_l_per_kwh

# ---------- Sidebar Inputs ----------
st.sidebar.title("Inputs")
st.sidebar.caption("Adjust assumptions to update costs.")

with st.sidebar.expander("Mission & Energy", expanded=True):
    distance_km_rt = st.number_input("Round-trip distance (km)", 1, 10000, 160, step=5)
    wh_per_km = st.number_input("Cruise draw (Wh/km)", 1.0, 50.0, 5.0, step=0.5)
    vtol_overhead_wh = st.number_input("VTOL + reserves overhead (Wh)", 0, 5000, 200, step=10)
    kwh_per_flight = (distance_km_rt * wh_per_km + vtol_overhead_wh) / 1000.0
    st.caption(f"Estimated energy per flight: **{kwh_per_flight:.3f} kWh**")

with st.sidebar.expander("Throughput & Scaling", expanded=True):
    monthly_flights_required = st.number_input("Flights required per month", 0, 100000, 60, step=5)
    operating_days_per_month = st.number_input("Operating days per month", 1, 31, 26, step=1)
    
    st.markdown("**Daily capacity method:**")
    capacity_method = st.radio(
        "Choose how to define theoretical daily capacity:",
        ["By total flight distance", "By number of flights"],
        help="Distance method accounts for battery/endurance limits; flight count method uses cycle time"
    )
    
    if capacity_method == "By total flight distance":
        max_distance_per_day = st.number_input("Max round-trip distance per aircraft per day (km)", 
                                               10, 10000, 800, step=10,
                                               help="Total distance aircraft can fly per day (battery/endurance limit)")
        theoretical_capacity_per_day = math.floor(max_distance_per_day / distance_km_rt) if distance_km_rt > 0 else 0
        st.caption(f"→ Theoretical capacity: **{theoretical_capacity_per_day} flights/day** ({max_distance_per_day} km ÷ {distance_km_rt} km/flight)")
    else:
        ops_hours_per_day = st.number_input("Operational hours per day", 1, 24, 10, step=1)
        cycle_time_hours = st.number_input("Average cycle time per flight (hrs)", 0.25, 24.0, 2.0, step=0.25,
                                           help="Total time from takeoff to ready-for-next-flight, incl. flight & turnaround.")
        theoretical_capacity_per_day = math.floor(ops_hours_per_day / cycle_time_hours) if cycle_time_hours > 0 else 0
        st.caption(f"→ Theoretical capacity: **{theoretical_capacity_per_day} flights/day** ({ops_hours_per_day} hrs ÷ {cycle_time_hours} hrs/flight)")
        
        # Warning if cycle time is too long
        if cycle_time_hours > ops_hours_per_day:
            st.warning(f"⚠️ Cycle time ({cycle_time_hours}h) exceeds daily operating hours ({ops_hours_per_day}h)")
    
    st.markdown("---")
    st.markdown("**Operational constraints:**")
    utilization_rate = st.slider("Fleet utilization rate (%)", 50, 100, 85, step=5,
                                  help="Accounts for maintenance downtime, scheduling inefficiencies, crew availability") / 100.0
    
    weather_availability = st.slider("Weather availability (%)", 50, 100, 90, step=5,
                                     help="% of days flyable (rain, wind, visibility restrictions)") / 100.0
    
    geofence_restrictions = st.slider("Geofence/regulatory availability (%)", 50, 100, 95, step=5,
                                      help="% of planned routes not blocked by airspace restrictions") / 100.0
    
    # Combined availability factor
    combined_availability = utilization_rate * weather_availability * geofence_restrictions
    
    # Capacity calculation with restrictions
    effective_capacity_per_day = math.floor(theoretical_capacity_per_day * combined_availability)
    effective_capacity_per_month = effective_capacity_per_day * operating_days_per_month
    
    aircraft_needed = math.ceil(monthly_flights_required / max(1, effective_capacity_per_month)) if monthly_flights_required > 0 else 0
    
    # Add spare aircraft option
    include_spare = st.checkbox("Add +1 spare aircraft for maintenance rotation", value=True,
                                help="Recommended for 24/7 medical operations")
    if include_spare and aircraft_needed > 0:
        aircraft_total = aircraft_needed + 1
    else:
        aircraft_total = aircraft_needed
    
    st.caption(f"**Theoretical:** {theoretical_capacity_per_day} flights/day → **Effective:** {effective_capacity_per_day} flights/day ({combined_availability*100:.1f}% availability)")
    st.caption(f"**Monthly capacity/aircraft:** {effective_capacity_per_month} flights → **Aircraft needed:** {aircraft_needed} (+ {1 if include_spare else 0} spare) = **{aircraft_total} total**")

with st.sidebar.expander("Power Source", expanded=True):
    power_choice = st.selectbox("Select power", ["Grid", "Diesel generator"])
    base_grid_rate = st.number_input("Grid electricity price ($/kWh)", 0.00, 5.00, 0.10, step=0.01)
    diesel_price_per_liter = st.number_input("Diesel price ($/L)", 0.00, 10.00, 1.10, step=0.05)
    sfc_l_per_kwh = st.number_input("Generator specific fuel consumption (L/kWh)", 0.05, 1.00, 0.30, step=0.01,
                                    help="Typical small gensets: 0.27–0.35 L/kWh")
    effective_rate = base_grid_rate if power_choice == "Grid" else diesel_rate_per_kwh(diesel_price_per_liter, sfc_l_per_kwh)

with st.sidebar.expander("Capital (USD)", expanded=False):
    st.caption("Items marked *scale per aircraft*. Laptop & fridge default to site-level (no scaling).")
    airframe = st.number_input("Airframe (Trinity F90+)*", 0.0, 1e6, 21500.0, step=50.0)
    batteries = st.number_input("Batteries (2 extra packs)*", 0.0, 1e6, 2400.0, step=50.0)
    charging = st.number_input("Charging & power*", 0.0, 1e6, 900.0, step=50.0)
    comms = st.number_input("BVLOS comms (LTE, links)*", 0.0, 1e6, 1000.0, step=50.0)
    antennas = st.number_input("Antennas/mast/RC spares*", 0.0, 1e6, 900.0, step=50.0)
    tools = st.number_input("Tools/spares/field kit*", 0.0, 1e6, 800.0, step=50.0)

    laptop = st.number_input("Rugged GCS laptop (site-level)", 0.0, 1e6, 2500.0, step=50.0)
    fridge = st.number_input("Base fridge (site-level)", 0.0, 1e6, 1000.0, step=50.0)
    cold_chain = st.number_input("Cold box + PCM + logger*", 0.0, 1e6, 650.0, step=50.0)

    scale_laptop = st.checkbox("Scale laptop per aircraft", value=False)
    scale_fridge = st.checkbox("Scale fridge per aircraft", value=False)

with st.sidebar.expander("Per‑flight & Battery", expanded=True):
    battery_pack_cost = st.number_input("Battery pack cost ($)", 0.0, 1e6, 1095.0, step=5.0)
    usable_kwh = st.number_input("Usable capacity per pack (kWh)", 0.1, 5.0, 0.8, step=0.05)
    cycle_life = st.number_input("Cycle life (charges)", 1, 5000, 400, step=10)
    cold_chain_consumables = st.number_input("Cold chain consumables ($/flight)", 0.0, 1000.0, 1.00, step=0.10)
    wear_parts = st.number_input("Wear parts ($/flight)", 0.0, 1000.0, 0.50, step=0.10)
    data_per_flight = st.number_input("Telemetry data ($/flight)", 0.0, 1000.0, 0.10, step=0.05)

with st.sidebar.expander("Monthly Ops & Staffing", expanded=False):
    # Cellular can scale with fleet or be site-level
    cellular_data = st.number_input("Cellular data ($/month)", 0.0, 1e6, 50.0, step=5.0)
    cellular_scales = st.checkbox("Cellular data scales with aircraft", value=True)

    insurance_annual = st.number_input("Annual insurance ($/year)", 0.0, 1e6, 3000.0, step=50.0)
    software_subs = st.number_input("Software subscriptions ($/mo)", 0.0, 1e6, 50.0, step=5.0)
    facility_rent = st.number_input("Facility/hangar rent ($/mo)", 0.0, 1e6, 100.0, step=10.0)

    st.markdown("---")
    st.caption("FTE per **aircraft** (24/7 ≈ 4.8 FTE per role). Add site overhead if needed.")
    pilot_salary_per_fte = st.number_input("Pilot salary per FTE ($/mo)", 0.0, 1e6, 800.0, step=10.0)
    pilot_fte_per_ac = st.number_input("Pilot FTE per aircraft", 0.0, 50.0, 4.8, step=0.1)
    tech_salary_per_fte = st.number_input("Technician salary per FTE ($/mo)", 0.0, 1e6, 400.0, step=10.0)
    tech_fte_per_ac = st.number_input("Technician FTE per aircraft", 0.0, 50.0, 4.8, step=0.1)
    cold_chain_salary_per_fte = st.number_input("Cold chain coord salary per FTE ($/mo)", 0.0, 1e6, 300.0, step=10.0)
    cold_chain_fte_per_ac = st.number_input("Cold chain FTE per aircraft", 0.0, 50.0, 4.8, step=0.1)

    site_overhead_staff_cost = st.number_input("Additional site overhead staff ($/mo)", 0.0, 1e6, 0.0, step=10.0)

# ---------- Scaling logic ----------
# Use aircraft_total (includes spare if selected) for capital and staffing
per_aircraft_capex = airframe + batteries + charging + comms + antennas + tools + cold_chain
site_capex = (laptop * (aircraft_total if scale_laptop else 1)) + (fridge * (aircraft_total if scale_fridge else 1))
total_capital = per_aircraft_capex * max(1, aircraft_total) + site_capex
amort_months = 36
monthly_capital_amort = total_capital / amort_months if amort_months > 0 else 0.0

# Per-flight variable costs
battery_degradation = battery_wear_per_flight(battery_pack_cost, usable_kwh, cycle_life, kwh_per_flight)
electricity_per_flight = kwh_per_flight * effective_rate
per_flight_cost = battery_degradation + electricity_per_flight + cold_chain_consumables + wear_parts + data_per_flight

# Monthly fixed ops (scale cellular if flagged). Base station power ~18.25 kWh/month per site
cellular_total = cellular_data * (aircraft_total if cellular_scales else 1)
base_station_power_cost = effective_rate * 18.25
monthly_insurance = insurance_annual / 12.0
monthly_fixed_ops = cellular_total + base_station_power_cost + facility_rent + monthly_insurance + software_subs

# Monthly variable
monthly_variable_cost = per_flight_cost * monthly_flights_required

# Staffing (scale per aircraft_total + site overhead)
monthly_staff = (pilot_salary_per_fte * pilot_fte_per_ac + tech_salary_per_fte * tech_fte_per_ac + cold_chain_salary_per_fte * cold_chain_fte_per_ac) * max(1, aircraft_total)
monthly_staff += site_overhead_staff_cost

# Totals
total_monthly = monthly_fixed_ops + monthly_variable_cost + monthly_staff + monthly_capital_amort
annual_total = total_monthly * 12.0

ops_cost_per_flight = (monthly_fixed_ops + monthly_variable_cost + monthly_staff) / monthly_flights_required if monthly_flights_required > 0 else 0.0
total_cost_per_flight = total_monthly / monthly_flights_required if monthly_flights_required > 0 else 0.0
cost_per_km = (total_cost_per_flight / distance_km_rt) if distance_km_rt > 0 else 0.0

# ---------- Header ----------
st.title("Medical Drone Cost Calculator ")
st.subheader("Fleet-aware cost model with operational constraints")

# ---------- KPI Cards ----------
kpi_cols = st.columns(6)
kpi_cols[0].metric("Aircraft total", f"{aircraft_total}", delta=f"+{1 if include_spare else 0} spare" if aircraft_total > 0 else None)
kpi_cols[1].metric("Effective capacity/mo", f"{effective_capacity_per_month}", delta=f"{combined_availability*100:.0f}% avail.")
kpi_cols[2].metric("Per‑flight (ops only)", fmt_currency(ops_cost_per_flight))
kpi_cols[3].metric("Per‑flight (with CapEx)", fmt_currency(total_cost_per_flight))
kpi_cols[4].metric("Per‑km (with CapEx)", fmt_currency(cost_per_km))
kpi_cols[5].metric("Monthly total", fmt_currency(total_monthly))

st.caption(f"Effective electricity rate: **${effective_rate:.2f}/kWh**  "
           f"{'(Grid)' if power_choice=='Grid' else f'(Diesel: ${diesel_price_per_liter:.2f}/L × {sfc_l_per_kwh:.2f} L/kWh)'}")

st.markdown("---")

# ---------- Breakdown ----------
left, right = st.columns([1.1, 0.9])

with left:
    st.markdown("### Per‑flight breakdown")    
    pf = pd.DataFrame({
        "Component": ["Battery wear", "Electricity", "Cold chain", "Wear parts", "Data"],
        "USD/flight": [battery_degradation, electricity_per_flight, cold_chain_consumables, wear_parts, data_per_flight],
    })
    st.dataframe(pf, use_container_width=True)
    st.caption(f"""
      - Energy per flight: **{kwh_per_flight:.3f} kWh**   
                -   Electricity rate: **${effective_rate:.2f}/kWh**  
      - Battery wear: **{fmt_currency(battery_degradation)}**/flight
   """)    

    st.markdown("### Monthly breakdown")
    mo = pd.DataFrame({
        "Category": ["Fixed ops", "Variable ops", "Staff", "Capital amortization"],
        "USD/month": [monthly_fixed_ops, monthly_variable_cost, monthly_staff, monthly_capital_amort],
    })
    st.dataframe(mo, use_container_width=True)

with right:
    st.markdown("### Capital summary (scaled)")    
    cap = pd.DataFrame({
        "Item": ["Per‑aircraft bundle × N", "Site-level items"],
        "USD": [(per_aircraft_capex * max(1, aircraft_total)), site_capex],
    })
    st.dataframe(cap, use_container_width=True)
    st.write("**Total capital (scaled):**", fmt_currency(total_capital))
    st.write("**Monthly amortization:**", fmt_currency(monthly_capital_amort))

st.markdown("---")

# ---------- Operational constraints visualization ----------
st.markdown("### Operational constraints & capacity")
constraint_cols = st.columns(3)
with constraint_cols[0]:
    st.metric("Utilization rate", f"{utilization_rate*100:.0f}%", help="Fleet efficiency factor")
with constraint_cols[1]:
    st.metric("Weather availability", f"{weather_availability*100:.0f}%", help="Flyable days due to weather")
with constraint_cols[2]:
    st.metric("Geofence/regulatory", f"{geofence_restrictions*100:.0f}%", help="Routes not blocked by airspace")

st.caption(f"**Combined availability:** {combined_availability*100:.1f}% = {utilization_rate*100:.0f}% × {weather_availability*100:.0f}% × {geofence_restrictions*100:.0f}%")

# Show capacity method used
if capacity_method == "By total flight distance":
    cap_df = pd.DataFrame({
        "Metric": ["Flights required (mo)", "Max distance/aircraft/day (km)", "Theoretical capacity/aircraft/day", "Effective capacity/aircraft/day", "Effective capacity/aircraft/mo", "Aircraft needed (ops)", "Spare aircraft", "Total aircraft"],
        "Value": [monthly_flights_required, max_distance_per_day, theoretical_capacity_per_day, effective_capacity_per_day, effective_capacity_per_month, aircraft_needed, (1 if include_spare else 0), aircraft_total]
    })
else:
    cap_df = pd.DataFrame({
        "Metric": ["Flights required (mo)", "Ops hours/day", "Cycle time (hrs)", "Theoretical capacity/aircraft/day", "Effective capacity/aircraft/day", "Effective capacity/aircraft/mo", "Aircraft needed (ops)", "Spare aircraft", "Total aircraft"],
        "Value": [monthly_flights_required, ops_hours_per_day, cycle_time_hours, theoretical_capacity_per_day, effective_capacity_per_day, effective_capacity_per_month, aircraft_needed, (1 if include_spare else 0), aircraft_total]
    })
st.dataframe(cap_df, use_container_width=True)

# ---------- Export ----------
st.markdown("### Export assumptions & results")    
if st.button("Download CSV"):
    export = {
        "distance_km_rt": distance_km_rt,
        "wh_per_km": wh_per_km,
        "vtol_overhead_wh": vtol_overhead_wh,
        "kwh_per_flight": kwh_per_flight,
        "power_choice": power_choice,
        "effective_rate": effective_rate,
        "diesel_price_per_liter": diesel_price_per_liter,
        "sfc_l_per_kwh": sfc_l_per_kwh,
        "monthly_flights_required": monthly_flights_required,
        "operating_days_per_month": operating_days_per_month,
        "capacity_method": capacity_method,
        "utilization_rate": utilization_rate,
        "weather_availability": weather_availability,
        "geofence_restrictions": geofence_restrictions,
        "combined_availability": combined_availability,
        "theoretical_capacity_per_day": theoretical_capacity_per_day,
        "effective_capacity_per_day": effective_capacity_per_day,
        "effective_capacity_per_month": effective_capacity_per_month,
        "aircraft_needed": aircraft_needed,
        "include_spare": include_spare,
        "aircraft_total": aircraft_total,
        "per_aircraft_capex": per_aircraft_capex,
        "site_capex": site_capex,
        "total_capital": total_capital,
        "amort_months": 36,
        "monthly_capital_amort": monthly_capital_amort,
        "battery_pack_cost": battery_pack_cost,
        "usable_kwh": usable_kwh,
        "cycle_life": cycle_life,
        "per_flight_cost_components": {
            "battery_wear": battery_degradation,
            "electricity": electricity_per_flight,
            "cold_chain": cold_chain_consumables,
            "wear_parts": wear_parts,
            "data": data_per_flight,
        },
        "monthly_fixed_ops": monthly_fixed_ops,
        "monthly_variable_cost": monthly_variable_cost,
        "monthly_staff": monthly_staff,
        "total_monthly": total_monthly,
        "annual_total": annual_total,
        "ops_cost_per_flight": ops_cost_per_flight,
        "total_cost_per_flight": total_cost_per_flight,
        "cost_per_km": cost_per_km,
    }
    
    # Add method-specific fields
    if capacity_method == "By total flight distance":
        export["max_distance_per_day"] = max_distance_per_day
    else:
        export["ops_hours_per_day"] = ops_hours_per_day
        export["cycle_time_hours"] = cycle_time_hours
    
    df = pd.json_normalize(export)
    csv = df.to_csv(index=False)
    st.download_button("Save CSV", data=csv, file_name="drone_cost_results_scaled.csv", mime="text/csv")

st.markdown("""
---
**Notes**
- **Capacity method**: Choose between distance-based (better for battery/endurance limits) or cycle time-based (better for operational tempo modeling).
- **Distance method**: Enter the maximum total round-trip distance an aircraft can fly per day. The app calculates flights/day by dividing by your per-flight distance.
- **Cycle time method**: Enter operational hours and average cycle time (flight + turnaround). The app calculates flights/day.
- **Diesel $/kWh** is computed from fuel price and generator specific fuel consumption (SFC, L/kWh). Typical small gensets: 0.27–0.35 L/kWh.
- **Operational constraints**: Effective capacity accounts for utilization rate (maintenance, scheduling), weather restrictions (rain, wind, visibility), and geofencing/regulatory airspace limitations.
- **Scaling**: The app computes aircraft needed from monthly flight demand and per‑aircraft effective capacity. Capital and staffing scale with total fleet size (including spare).
- **Spare aircraft**: Recommended for 24/7 medical operations to ensure service continuity during maintenance.
- **Site‑level items**: Laptop and fridge default to one per site; toggle scaling if you need one per aircraft.
- **Battery wear**: (Pack price / (usable kWh × cycle life)) × energy per flight.
""")
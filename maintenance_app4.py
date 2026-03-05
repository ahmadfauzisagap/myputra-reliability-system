import os

# 1. Get the folder where THIS script is running
current_folder = os.getcwd()
print(f"📍 Your Project Folder is: {current_folder}")

# 2. Create the hidden .streamlit folder there
streamlit_folder = os.path.join(current_folder, ".streamlit")
if not os.path.exists(streamlit_folder):
    os.makedirs(streamlit_folder)

# 3. Create the config file with LIGHT BLUE Background
config_path = os.path.join(streamlit_folder, "config.toml")

marine_theme = """
[theme]
primaryColor = "#0054A6"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
"""

with open(config_path, "w") as f:
    f.write(marine_theme)

print(f"✅ Success! Config file saved at: {config_path}")
print("👉 Now Stop the app and Run 'streamlit run maintenance_app.py' again.")
# -----------------------------

import streamlit as st
import numpy as np
import pandas as pd
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt

# ==========================================
# PART 1: SYSTEM CONFIGURATION & STATE
# ==========================================
st.set_page_config(page_title="MyPutRa Machinery Reliability Suite {Beta}", layout="wide")
st.title("⚓ Reliability System & Decision Support System")
st.markdown("**Author:** Ahmad Fauzi | **MyPutRa Reliability System")

# Initialize Session State for Machinery/Component Data
if 'fleet_data' not in st.session_state:
    # Default: 100 Rows
    data = {
        "Equipment Name": [f"Equipment {i+1}" for i in range(100)],
        "Total Failures": [0] * 100,
        "Observation Years": [1.0] * 100,
        "Calculated λ": [0.0] * 100,
        "MTBF (Months)": [0.0] * 100,   # <--- NEW COLUMN
        "Reliability (R)": [1.0] * 100  # New Column
    }
    st.session_state['fleet_data'] = pd.DataFrame(data)

# Fix: Ensure we always have 100 rows if the app reloads
elif len(st.session_state['fleet_data']) < 100:
    rows_to_add = 100 - len(st.session_state['fleet_data'])
    new_data = {
        "Equipment Name": [f"New Equipment {i+1}" for i in range(rows_to_add)],
        "Total Failures": [0] * rows_to_add,
        "Observation Years": [1.0] * rows_to_add,
        "Calculated λ": [0.0] * rows_to_add,
        "MTBF (Months)": [0.0] * rows_to_add, # <--- NEW COLUMN
        "Reliability (R)": [1.0] * rows_to_add
    }
    new_df = pd.DataFrame(new_data)
    st.session_state['fleet_data'] = pd.concat([st.session_state['fleet_data'], new_df], ignore_index=True)

# Define Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🔧 1. Fuzzy Maintenance", 
    "📦 2. AHP Optimisation", 
    "📊 3. Machinery Data Management",
    "📊 4. Search & Analyze",  # <--- NEW TAB 4
    "📦 5. TFN Analysis",  # <--- NEW TAB 5
    "🤖 6. AI Maintenance Advisor",  # <--- NEW TAB
    "🧠 7. RCA Tool",      # New Tab 7
    "📦 8. Spares Opt",    # New Tab 8
    "🚀 9. Master Dashboard",  # NEW TAB 9
    "⚙️ 10. PMS & Inventory"  # NEW TAB 10
])

# ==========================================
# TAB 3: FLEET DATA MANAGEMENT (With MTBF)
# ==========================================
with tab3:
    st.header("Machinery/Component Reliability Database")

    # --- 1. IMPORT FROM EXCEL ---
    with st.expander("📂 Import Data from Excel/CSV", expanded=False):
        st.info("Required Columns: 'Equipment Name', 'Total Failures', 'Observation Years'")
        
        uploaded_file = st.file_uploader("Upload File", type=["xlsx", "xls", "csv"])
        
        if uploaded_file is not None:
            if st.button("🚀 Process & Load Data"):
                try:
                    # Determine file type
                    if uploaded_file.name.endswith('.csv'):
                        df_imported = pd.read_csv(uploaded_file)
                    else:
                        df_imported = pd.read_excel(uploaded_file)
                        
                    # SAVE IT TO THE SESSION STATE (This is the magic line!)
                    st.session_state['machinery_data'] = df_imported
                    
                    st.success("Data uploaded and saved to memory!")
                    
                    # Clean headers
                    df_imported.columns = df_imported.columns.str.strip()
                    required_cols = ['Equipment Name', 'Total Failures', 'Observation Years']
                    
                    if all(col in df_imported.columns for col in required_cols):
                        # Init calculated columns
                        df_imported['Calculated λ'] = 0.0
                        df_imported['MTBF (Months)'] = 0.0  # <--- NEW
                        df_imported['Reliability (R)'] = 1.0
                        
                        # Pad to 100 rows if needed
                        current_rows = len(df_imported)
                        if current_rows < 100:
                            rows_needed = 100 - current_rows
                            empty_data = pd.DataFrame({
                                "Equipment Name": [f"Slot {i+1}" for i in range(rows_needed)],
                                "Total Failures": [0]*rows_needed,
                                "Observation Years": [1.0]*rows_needed,
                                "Calculated λ": [0.0]*rows_needed,
                                "MTBF (Months)": [0.0]*rows_needed, # <--- NEW
                                "Reliability (R)": [1.0]*rows_needed
                            })
                            df_imported = pd.concat([df_imported, empty_data], ignore_index=True)
                        
                        st.session_state['fleet_data'] = df_imported.iloc[:100]
                        st.success(f"✅ Loaded {current_rows} rows successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Missing columns! Found: {df_imported.columns.tolist()}")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")

    # --- 2. SETTINGS ---
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search_query = st.text_input("🔍 Search Equipment", placeholder="Type name...")
    with c2:
        mission_time = st.number_input("Mission Time (t) [Years]", min_value=0.1, value=1.0, step=0.5)
    with c3:
        st.caption(f"Reliability Calc for **{mission_time} Years**")

    # --- 3. CALCULATIONS ---
    df_calc = st.session_state['fleet_data'].copy()
    
    # A. Calculate Lambda
    df_calc["Calculated λ"] = df_calc.apply(
        lambda x: x["Total Failures"] / x["Observation Years"] if x["Observation Years"] > 0 else 0, axis=1
    )
    
    # B. Calculate MTBF (Months) = (1 / Lambda) * 12
    # If Lambda is 0 (No failures), set MTBF to 0 (or infinite representation)
    df_calc["MTBF (Months)"] = df_calc["Calculated λ"].apply(
        lambda x: (1 / x * 12) if x > 0 else 0
    )
    
    # C. Calculate Reliability R = e^(-λt)
    df_calc["Reliability (R)"] = np.exp(-1 * df_calc["Calculated λ"] * mission_time)

    # Save calculations back
    st.session_state['fleet_data'] = df_calc
    
    # --- SYNC TO TAB 5 ---
    # We send this data to Tab 5 so the Sensitivity Analysis works automatically.
    # We also rename the column because Tab 5 expects "Failure Rate (λ)"
    df_sync = df_calc.copy()
    df_sync.rename(columns={'Calculated λ': 'Failure Rate (λ)'}, inplace=True)
    st.session_state['shared_df'] = df_sync

    # --- 4. DISPLAY ---
    if search_query:
        df_display = df_calc[df_calc['Equipment Name'].str.contains(search_query, case=False, na=False)]
    else:
        df_display = df_calc

    edited_df = st.data_editor(
        df_display,
        column_config={
            "Equipment Name": st.column_config.TextColumn("Equipment Name"),
            "Total Failures": st.column_config.NumberColumn("Failures", min_value=0),
            "Observation Years": st.column_config.NumberColumn("Obs. Years", min_value=0.1),
            "Calculated λ": st.column_config.NumberColumn("λ (Fail Rate)", disabled=True, format="%.4f"),
            
            # --- NEW MTBF COLUMN CONFIG ---
            "MTBF (Months)": st.column_config.NumberColumn(
                "MTBF (Months)",
                help="Mean Time Between Failures in Months",
                format="%.1f",
                disabled=True
            ),
            # ------------------------------
            
            "Reliability (R)": st.column_config.ProgressColumn(
                "Reliability %", 
                format="%.2f", 
                min_value=0, 
                max_value=1
            )
        },
        num_rows="fixed", 
        hide_index=True, 
        use_container_width=True, 
        height=400
    )

    if st.button("💾 Save Changes"):
        st.session_state['fleet_data'].update(edited_df)
        st.success("Database updated!")
        
       

# ==========================================
# TAB 1: FUZZY LOGIC (Safety Priority Logic)
# ==========================================
with tab1:
    st.header("Condition-Based Maintenance (Qualitative Input)")
    
    # --- 1. LINK TO TAB 3 DATABASE ---
    default_run_hours = 2000
    selected_equip_name = "Manual Simulation"

    if 'shared_df' in st.session_state and st.session_state['shared_df'] is not None:
        st.success("✅ Linked to Fleet Database (Tab 3)")
        df_link = st.session_state['shared_df']
        equip_list = df_link['Equipment Name'].unique().tolist()
        selected_equip_name = st.selectbox("Select Equipment to Analyze:", equip_list)
        
        try:
            row = df_link[df_link['Equipment Name'] == selected_equip_name].iloc[0]
            if 'Observation Years' in row:
                calc_hours = int(row['Observation Years'] * 8760)
                default_run_hours = min(calc_hours, 20000)
                st.caption(f"ℹ️ Auto-filled Running Hours based on {row['Observation Years']:.1f} years of observation.")
        except:
            pass 
    else:
        st.warning("⚠️ No Database Found. Using Manual Mode. (Upload CSV in Tab 3 to link)")

    st.divider()
    
    # Remove cache to ensure slider updates trigger fresh logic
    def create_fuzzy_system():
        # Variables
        failure_risk = ctrl.Antecedent(np.arange(0, 101, 1), 'failure_risk')
        vibration = ctrl.Antecedent(np.arange(0, 11, 1), 'vibration')
        temperature = ctrl.Antecedent(np.arange(0, 121, 1), 'temperature') 
        pressure = ctrl.Antecedent(np.arange(0, 11, 1), 'pressure')        
        maintenance_action = ctrl.Consequent(np.arange(0, 101, 1), 'maintenance_action')

        # Membership Functions
        failure_risk['low'] = fuzz.trimf(failure_risk.universe, [0, 0, 40])
        failure_risk['medium'] = fuzz.trimf(failure_risk.universe, [20, 50, 80])
        failure_risk['high'] = fuzz.trimf(failure_risk.universe, [60, 100, 100])

        vibration['normal'] = fuzz.trimf(vibration.universe, [0, 0, 5])
        vibration['warning'] = fuzz.trimf(vibration.universe, [4, 6, 8])
        vibration['critical'] = fuzz.trimf(vibration.universe, [7, 10, 10])

        temperature['normal'] = fuzz.trimf(temperature.universe, [0, 0, 85])
        temperature['warning'] = fuzz.trimf(temperature.universe, [80, 95, 105])
        temperature['critical'] = fuzz.trimf(temperature.universe, [100, 120, 120])

        pressure['critical'] = fuzz.trimf(pressure.universe, [0, 0, 3]) 
        pressure['warning'] = fuzz.trimf(pressure.universe, [2, 4, 5])
        pressure['normal'] = fuzz.trimf(pressure.universe, [4, 10, 10])

        maintenance_action['run'] = fuzz.trimf(maintenance_action.universe, [0, 0, 50])
        maintenance_action['monitor'] = fuzz.trimf(maintenance_action.universe, [25, 50, 75])
        maintenance_action['stop'] = fuzz.trimf(maintenance_action.universe, [50, 100, 100])

        # --- SAFETY PRIORITY LOGIC FIX ---
        
        # 1. Define the "Critical Condition"
        # If ANY of these are true, the machine is in danger.
        is_critical = (
            failure_risk['high'] | 
            vibration['critical'] | 
            temperature['critical'] | 
            pressure['critical']
        )
        
        # 2. Define the "Warning Condition"
        is_warning = (
            failure_risk['medium'] | 
            vibration['warning'] | 
            temperature['warning'] | 
            pressure['warning']
        )
        
        # Rule 1: CRITICAL -> STOP
        rule1 = ctrl.Rule(is_critical, maintenance_action['stop'])
        
        # Rule 2: WARNING -> MONITOR
        # CRITICAL FIX: We add "& (~is_critical)"
        # This says: "Only trigger Monitor if we are NOT already Critical."
        rule2 = ctrl.Rule(is_warning & (~is_critical), maintenance_action['monitor'])
        
        # Rule 3: NORMAL -> RUN
        rule3 = ctrl.Rule(
            failure_risk['low'] & 
            vibration['normal'] & 
            temperature['normal'] & 
            pressure['normal'], 
            maintenance_action['run']
        )
        
        system = ctrl.ControlSystem([rule1, rule2, rule3])
        return ctrl.ControlSystemSimulation(system), maintenance_action, failure_risk, vibration, temperature, pressure

    # Unpack variables
    advisor, action_variable, risk_var, vib_var, temp_var, press_var = create_fuzzy_system()

    # Inputs
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        st.subheader(f"1. Age: {selected_equip_name}")
        hours = st.number_input("Running Hours", 0, 20000, default_run_hours, step=100)
        eta = st.number_input("Characteristic Life (η)", value=8000)
        beta = st.number_input("Shape Parameter (β)", value=1.5)
        
        st.markdown("---")
        st.subheader("2. Sensor Readings")
        options = ["Low", "Slightly Low", "Normal", "Slightly High", "High"]
        vib_cat = st.select_slider("Vibration Level", options=options, value="Normal")
        temp_cat = st.select_slider("Temperature", options=options, value="Normal")
        press_cat = st.select_slider("Pressure", options=options, value="Normal")

    with col_f2:
        # Mappings
        vib_map = {"Low": 0.5, "Slightly Low": 1.5, "Normal": 2.0, "Slightly High": 6.5, "High": 9.0}
        vib_input = vib_map[vib_cat]
        temp_map = {"Low": 40, "Slightly Low": 60, "Normal": 70, "Slightly High": 95, "High": 115}
        temp_input = temp_map[temp_cat]
        press_map = {"Low": 1.0, "Slightly Low": 3.0, "Normal": 6.0, "Slightly High": 8.0, "High": 9.0}
        press_input = press_map[press_cat]

        # Calculate Logic
        reliability = np.exp(-((hours / eta) ** beta))
        risk_prob = (1.0 - reliability) * 100
        
        advisor.input['failure_risk'] = risk_prob
        advisor.input['vibration'] = vib_input
        advisor.input['temperature'] = temp_input
        advisor.input['pressure'] = press_input
        advisor.compute()
        
        # Get result
        fuzzy_score = advisor.output['maintenance_action']
        
        # Override Logic
        override_active = False
        reasons = []
        if temp_input > 105: 
            override_active = True
            reasons.append("High Temperature")
        if press_input < 2.0:
            override_active = True
            reasons.append("Low Lube Oil Pressure")

        if override_active:
            decision_score = 100.0
            st.error("🚨 EMERGENCY TRIP ACTIVATED (Score: 100.0)")
            st.write(f"**TRIP CAUSE:** {', '.join(reasons)}")
        else:
            decision_score = fuzzy_score
            st.info(f"📊 Failure Probability (Weibull): **{risk_prob:.2f}%**")
            
            if decision_score >= 70: st.error(f"🔴 CRITICAL ACTION REQUIRED (Score: {decision_score:.2f})")
            elif decision_score >= 40: st.warning(f"🟠 WARNING LEVEL (Score: {decision_score:.2f})")
            else: st.success(f"🟢 NORMAL OPERATION (Score: {decision_score:.2f})")

        # Main Decision Graph
        st.write("### Decision Logic Graph")
        try:
            plt.close('all') 
            action_variable.view(sim=advisor)
            if override_active: plt.vlines(x=100, ymin=0, ymax=1, colors='r', linewidth=5)
            
            plt.gcf().set_size_inches(4, 1.5)           
            plt.tick_params(axis='both', labelsize=4)   
            plt.ylabel("Membership", fontsize=4)        
            plt.xlabel("Action", fontsize=4)            
            plt.legend(fontsize=4, loc='center right')  
            
            st.pyplot(plt.gcf())
            plt.clf() 
        except Exception as e:
            st.error(f"Graph Error: {e}")

    # --- 4-GRID SENSORS ---
    st.markdown("---")
    st.subheader("⚙️ Sensor Analysis")
    
    row1_1, row1_2 = st.columns(2)
    row2_1, row2_2 = st.columns(2)

    with row1_1:
        st.write("**1. Failure Risk**")
        try:
            plt.close('all')
            risk_var.view()
            plt.vlines(x=risk_prob, ymin=0, ymax=1, colors='r', linestyles='dashed')
            plt.gcf().set_size_inches(3, 1.5) 
            plt.tick_params(axis='both', labelsize=4)   
            plt.ylabel("Membership", fontsize=4)        
            plt.xlabel("Action", fontsize=4)            
            plt.legend(fontsize=4, loc='center right')  
            st.pyplot(plt.gcf())  
            plt.clf()
        except: pass

    with row1_2:
        st.write(f"**2. Vibration ({vib_cat})**") 
        try:
            plt.close('all')
            vib_var.view()
            plt.vlines(x=vib_input, ymin=0, ymax=1, colors='r', linestyles='dashed')
            plt.gcf().set_size_inches(3, 1.5) 
            plt.tick_params(axis='both', labelsize=4)   
            plt.ylabel("Membership", fontsize=4)        
            plt.xlabel("Action", fontsize=4)            
            plt.legend(fontsize=4, loc='center right')  
            st.pyplot(plt.gcf())
            plt.clf()
        except: pass

    with row2_1:
        st.write(f"**3. Temperature ({temp_cat})**") 
        try:
            plt.close('all')
            temp_var.view()
            plt.vlines(x=temp_input, ymin=0, ymax=1, colors='r', linestyles='dashed')
            plt.gcf().set_size_inches(3, 1.5) 
            plt.tick_params(axis='both', labelsize=4)   
            plt.ylabel("Membership", fontsize=4)        
            plt.xlabel("Action", fontsize=4)            
            plt.legend(fontsize=4, loc='center right')  
            st.pyplot(plt.gcf())
            plt.clf()
        except: pass

    with row2_2:
        st.write(f"**4. Pressure ({press_cat})**") 
        try:
            plt.close('all')
            press_var.view()
            plt.vlines(x=press_input, ymin=0, ymax=1, colors='r', linestyles='dashed')
            plt.gcf().set_size_inches(3, 1.5) 
            plt.tick_params(axis='both', labelsize=4)   
            plt.ylabel("Membership", fontsize=4)        
            plt.xlabel("Action", fontsize=4)            
            plt.legend(fontsize=4, loc='center right')  
            st.pyplot(plt.gcf())
            plt.clf()
        except: pass
    
    

# ==========================================
# TAB 2: AHP SPARE PART OPTIMISATION (The Master Sender)
# ==========================================
import math 

with tab2:
    st.header("AHP-Based Spare Part Optimisation")
    st.markdown("This module links with **Tab 3** to pull real failure rates.")
    
    # Check if database has data
    if 'fleet_data' in st.session_state and not st.session_state['fleet_data'].empty:
        df = st.session_state['fleet_data']
        all_equipment = df["Equipment Name"].tolist()

    ahp_weights = {
        "Criticality": 0.2803, "Lead Time": 0.2078, "Annual Usage": 0.1555,
        "Availability of Substitutes": 0.0860, "Cost of Spare Part": 0.0725,
        "Deterioration Rate": 0.0478, "Obsolescence Rate": 0.0465,
        "Commonality": 0.0383, "Cost of Holding": 0.0337, "Stockout Impact": 0.0315
    }

    # Ensure list exists
    if 'fleet_data' in st.session_state and not st.session_state['fleet_data'].empty:
        equip_list = st.session_state['fleet_data']['Equipment Name'].tolist()
    else:
        equip_list = ["Default Equipment"]

    col_a1, col_a2 = st.columns(2)
    
    with col_a1:
        st.subheader("1. Select Equipment")
        # We give this a key so Streamlit doesn't reset it randomly
        selected_equip_name = st.selectbox("Choose Equipment:", equip_list, key="tab2_master_select")
        
        # --- CRITICAL FIX: SEND SIGNAL TO TAB 5 ---
        # This single line fixes the "No Tab 2 selection active" error
        st.session_state['selected_equipment'] = selected_equip_name
        # ------------------------------------------
        
        # Pull Data
        if 'fleet_data' in st.session_state:
            row = st.session_state['fleet_data'][st.session_state['fleet_data']['Equipment Name'] == selected_equip_name].iloc[0]
            linked_lambda = row['Calculated λ']
        else:
            linked_lambda = 0.5

        st.info(f"🔗 Linked λ for **{selected_equip_name}**: **{linked_lambda:.4f}**")
        
        st.subheader("2. Part Attributes")
        user_scores = {}
        user_scores["Criticality"] = st.slider("Criticality", 1.0, 10.0, 9.0, 0.5)
        user_scores["Lead Time"] = st.slider("Lead Time", 1.0, 10.0, 8.0, 0.5)
        user_scores["Annual Usage"] = st.slider("Annual Usage", 1.0, 10.0, 7.0, 0.5)
        user_scores["Availability of Substitutes"] = st.slider("Availability of Substitutes", 1.0, 10.0, 8.0, 0.5)
        user_scores["Stockout Impact"] = st.slider("Stockout Impact", 1.0, 10.0, 5.0, 0.5)

    with col_a2:
        st.subheader("3. Economic & Technical")
        user_scores["Cost of Spare Part"] = st.slider("Cost of Spare Part", 1.0, 10.0, 6.0, 0.5)
        user_scores["Cost of Holding"] = st.slider("Cost of Holding Inventory", 1.0, 10.0, 4.0, 0.5)
        user_scores["Deterioration Rate"] = st.slider("Deterioration Rate", 1.0, 10.0, 2.0, 0.5)
        user_scores["Obsolescence Rate"] = st.slider("Obsolescence Rate", 1.0, 10.0, 3.0, 0.5)
        user_scores["Commonality"] = st.slider("Commonality", 1.0, 10.0, 5.0, 0.5)

   # --- UPDATED CALCULATION BLOCK ---
    
    # 1. Create a copy of the scores for the math engine
    calc_scores = user_scores.copy()
    
    # 2. INVERSE LOGIC: High Availability = Low Stocking Priority
    calc_scores["Availability of Substitutes"] = 11.0 - user_scores["Availability of Substitutes"]
    
    # Note: You can also uncomment these lines below later if you decide that 
    # highly expensive or fast-deteriorating parts should ALSO lower the priority to hold stock!
    # calc_scores["Cost of Spare Part"] = 11.0 - user_scores["Cost of Spare Part"]
    # calc_scores["Cost of Holding"] = 11.0 - user_scores["Cost of Holding"]
    # calc_scores["Deterioration Rate"] = 11.0 - user_scores["Deterioration Rate"]
    # calc_scores["Obsolescence Rate"] = 11.0 - user_scores["Obsolescence Rate"]

    # 3. Compute final scores using the adjusted values
    composite_score = sum((calc_scores[k]/10.0) * v for k, v in ahp_weights.items())
    raw_index = composite_score * linked_lambda
    final_rank_index = raw_index
    
    # Logic Override
    override_triggered = False
    
    # Rule 1: High Criticality (8+) + Medium Lead Time (4+)
    if user_scores["Criticality"] >= 8 and user_scores["Lead Time"] >= 4:
        if final_rank_index < 0.51:
            final_rank_index = 0.65 
            override_triggered = True

    # Rule 2: Moderate Criticality (5+) + High Lead Time (7+) -> Force Safety Stock
    elif user_scores["Criticality"] >= 5 and user_scores["Lead Time"] >= 7:
        if final_rank_index < 0.51:
            final_rank_index = 0.65 
            override_triggered = True

    # Rule 3: Low Criticality (<= 3) + Low Lead Time (<= 3) -> Force Run To Failure
    elif user_scores["Criticality"] <= 3 and user_scores["Lead Time"] <= 3:
        final_rank_index = 0.15 
        override_triggered = True

    final_rank_index = min(final_rank_index, 1.0)

    # --- Results ---
    st.divider()
    res_col1, res_col2 = st.columns([1, 1])
    
    strategy_str = "None"
    
    with res_col1:
        st.subheader("🏆 Optimisation Results")
        if override_triggered: st.warning("⚠️ **LOGISTICS OVERRIDE ACTIVE**")
        st.metric(label="Stock Priority Index (SPI)", value=f"{final_rank_index:.4f}")
        
        base_demand = math.ceil(linked_lambda)
        if base_demand < 1: base_demand = 1 

        if final_rank_index >= 0.81:
            strategy_str = "Strategic Holding"
            st.error(f"### 🚨 {strategy_str}")
            rec_qty = base_demand + 2
            st.markdown(f"**👉 Recommendation:** Hold **{rec_qty} units** / year")

        elif final_rank_index >= 0.51:
            strategy_str = "Safety Stock"
            st.warning(f"### 🛑 {strategy_str}")
            rec_qty = base_demand + 1
            st.markdown(f"**👉 Recommendation:** Hold **{rec_qty} units** / year")

        elif final_rank_index >= 0.21:
            strategy_str = "Just In Time (JIT)"
            st.info(f"### 📊 {strategy_str}")
            st.markdown(f"**👉 Recommendation:** Plan for **{base_demand} units**, hold **0-1**.")

        else:
            strategy_str = "Run To Failure (RTF)"
            st.success(f"### 📉 {strategy_str}")
            st.markdown("**👉 Recommendation:** Hold **0 units**.")

        st.session_state['ahp_handoff'] = {
            'equip_name': selected_equip_name,
            'annual_lambda': linked_lambda,
            'strategy': strategy_str,
            'priority_index': final_rank_index
        }

    with res_col2:
        st.subheader("Weight Contribution")
        # UPDATED: Uses `calc_scores` so the graph visually shows the inversion!
        st.bar_chart(pd.DataFrame.from_dict({k:(calc_scores[k]/10)*v for k,v in ahp_weights.items()}, orient='index', columns=['Contribution']))

# ==========================================
# TAB 4: SEARCH & ANALYZE (Fixed Column Detection)
# ==========================================
import numpy as np
import matplotlib.pyplot as plt

with tab4:
    st.header("🔎 Equipment Reliability Analyzer")
    st.markdown("Select equipment from your database to analyze specific reliability curves.")
    
    st.divider()

    # --- 1. DATA LOADING ---
    df_search = None
    if 'shared_df' in st.session_state and st.session_state['shared_df'] is not None:
        df_search = st.session_state['shared_df'].copy()
        
        # --- SMART COLUMN DETECTOR ---
        # 1. List of columns available
        all_cols = df_search.columns
        target_col = None
        
        # 2. Priority Check: Look for specific standard names first
        priority_names = ['Calculated λ', 'Failure Rate (λ)', 'Lambda', 'Failure Rate', 'Fail Rate']
        for name in priority_names:
            if name in all_cols:
                target_col = name
                break
        
        # 3. Fuzzy Check: Look for "Rate" or "Lambda" BUT EXCLUDE "Total" or "Count"
        if target_col is None:
            for c in all_cols:
                c_low = c.lower()
                # Must contain 'rate' or 'lambda', and MUST NOT contain 'total'
                if ('rate' in c_low or 'lambda' in c_low or 'λ' in c_low) and ('total' not in c_low):
                    target_col = c
                    break
        
        # 4. Ultimate Fallback (if nothing else works)
        if target_col is None:
            target_col = all_cols[1] # Default to 2nd column
            
        # Ensure numeric
        df_search[target_col] = pd.to_numeric(df_search[target_col], errors='coerce')
        
        # Check for Link
        linked_item = st.session_state.get('selected_equipment', None)
        
        if linked_item:
            st.success(f"🔗 **Linked to Tab 2:** Analyzing **{linked_item}**")
            st.caption(f"Using Data Column: `{target_col}`") # Debug info for you
        else:
            st.info("ℹ️ Select equipment in Tab 2 to auto-link here, or choose manually below.")

    else:
        st.error("❌ No data found. Please upload data in Tab 3.")
        st.stop()

    # --- 2. SELECTOR LOGIC ---
    equip_list = df_search['Equipment Name'].unique().tolist()
    
    # Logic: If linked, hide the dropdown. If not, show it.
    if linked_item and linked_item in equip_list:
        selected_search_item = linked_item
    else:
        selected_search_item = st.selectbox(
            "Select Equipment to Analyze:", 
            equip_list, 
            index=0,
            key="tab4_manual_select"
        )

    # --- 3. GET DATA FOR SELECTION ---
    row = df_search[df_search['Equipment Name'] == selected_search_item].iloc[0]
    fail_rate = row[target_col]
    
    # Calculate MTBF
    # Avoid division by zero
    if fail_rate > 0:
        mtbf_val = (1 / fail_rate) * 12 # Months
    else:
        mtbf_val = 0 # Infinite theoretically, but 0 for display safety

    # Display Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Equipment Name", selected_search_item)
    c2.metric("Failure Rate (λ)", f"{fail_rate:.4f} /yr")
    
    if mtbf_val > 0:
        c3.metric("MTBF", f"{mtbf_val:.1f} Months")
    else:
        c3.metric("MTBF", "N/A (λ=0)")

    st.divider()

    # --- 4. RELIABILITY PROJECTION ---
    st.subheader(f"📈 Reliability Projection: {selected_search_item}")
    
    col_p1, col_p2 = st.columns([1, 2])
    
    with col_p1:
        # User Inputs for Projection
        beta = st.number_input("Shape Parameter (β)", value=1.0, step=0.1, help="β=1: Random Failures (Normal), β>1: Wear Out")
        horizon = st.slider("Projection Horizon (Years)", 1, 20, 5)
    
    with col_p2:
        # Generate Curve
        t = np.linspace(0, horizon, 100)
        
        if fail_rate > 0:
            eta = 1 / fail_rate
        else:
            eta = 1000 # Large number so curve stays high
            
        R_t = np.exp(- (t / eta) ** beta)
        
        # Plot
        fig, ax = plt.subplots(figsize=(6, 2.5))
        ax.plot(t, R_t, color='purple', linewidth=2, label=f'Reliability (β={beta})')
        ax.set_title(f"Reliability vs Time ({selected_search_item})")
        ax.set_xlabel("Time (Years)")
        ax.set_ylabel("Reliability Probability")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        ax.set_ylim(0, 1.1)
        
        st.pyplot(fig)
        
    st.caption("This chart projects the probability that the equipment will perform without failure over time. A steep drop means high failure rate.")


# ==========================================
# TAB 5: DYNAMIC ANALYSIS (Link with Manual Override)
# ==========================================
import matplotlib.pyplot as plt
import numpy as np

with tab5:
    st.header("📚 Hybrid Reliability Framework")
    st.markdown("""
    **Reference:** A Hybrid Reliability Framework for Spare Part Optimisation Under Uncertainty of Marine Vessel Systems  
    *Ahmad Fauzi Sagap et.al (2025)* **Journal:** PLATFORM - A Journal of Engineering (Vol. 9, No. 4) | **Publisher:** UTP Press
    """)
    
    st.divider()

    # --- INTERNAL DATA LOADING ---
    df_research = None
    
    if 'shared_df' in st.session_state and st.session_state['shared_df'] is not None:
        df_research = st.session_state['shared_df'].copy()
        
        # Rename columns to match requirements
        df_research.rename(columns={
            'λ (Fail Rate)': 'Failure Rate (λ)',   
            'Fail Rate': 'Failure Rate (λ)',       
            'Equipment': 'Equipment Name'          
        }, inplace=True)
        
    else:
        st.warning("⚠️ No Data in Tab 3. Using Default Placeholders.")
        generic_data = {
            "Equipment Name": [f"Equipment {i+1}" for i in range(5)],
            "Failure Rate (λ)": [0.5000] * 5 
        }
        df_research = pd.DataFrame(generic_data)

    # Validate Column Exists
    if 'Failure Rate (λ)' not in df_research.columns:
        st.error(f"❌ Critical Error: Column 'Failure Rate (λ)' missing. Columns found: {list(df_research.columns)}")
        st.stop()

    # --- MAIN ANALYSIS SECTION ---
    st.subheader("Fuzzy Sensitivity Analysis (±15% Range)")
    st.markdown("The **Blue Triangle** is fixed (Original Data). The **Red Line** moves to show sensitivity.")
    
    # --- SMART SELECTION LOGIC ---
    equip_list = df_research["Equipment Name"].tolist()
    linked_item = st.session_state.get('selected_equipment', None)
    
    # Check if we have a valid link from Tab 2
    is_linked = False
    if linked_item and linked_item in equip_list:
        is_linked = True
    
    # SELECTION INTERFACE
    col_sel, col_status = st.columns([2, 1])
    
    with col_status:
        # The Checkbox Control
        if is_linked:
            use_link = st.checkbox("🔗 Link to Tab 2", value=True, help="Uncheck to select manually")
        else:
            use_link = False
            st.caption("No Tab 2 selection active")

    with col_sel:
        if use_link and is_linked:
            # LOCKED MODE: Force the selection to match Tab 2
            selected_research_item = linked_item
            st.info(f"**Analyzing:** {selected_research_item}")
        else:
            # MANUAL MODE: Show the dropdown
            selected_research_item = st.selectbox(
                "Select System to Simulate:",
                equip_list,
                index=0
            )

    # --- GET VALUES FOR SELECTED ITEM ---
    item_row = df_research[df_research["Equipment Name"] == selected_research_item].iloc[0]
    
    try:
        base_lambda = item_row["Failure Rate (λ)"]
    except:
        base_lambda = item_row.iloc[1]

    # B. SLIDER CONTROLS
    if base_lambda <= 0:
        base_lambda = 0.0001 
    static_lower = base_lambda * 0.85
    static_upper = base_lambda * 1.15
    
    safe_step = max(base_lambda * 0.005, 0.0001)
    
    col_slide, col_val = st.columns([3, 1])
    with col_slide:
        lambda_final = st.slider(
            f"Adjust Failure Rate (λ) [Range: {static_lower:.4f} - {static_upper:.4f}]", 
            min_value=float(static_lower), 
            max_value=float(static_upper), 
            value=float(base_lambda),
            step=safe_step,
            format="%.4f"
        )
    with col_val:
        st.metric(label=r"Fuzzy Failure Rate ($\bar{\lambda}$)", value=f"{lambda_final:.4f}")

    # --- TOP METRICS ROW ---
    c1, c2, c3 = st.columns(3)
    c1.metric(label=r"Crisp Failure Rate ($\lambda$)", value=f"{base_lambda:.4f}")
    c2.metric("Shift Amount", f"{(lambda_final - base_lambda):.4f}")
    c3.metric(label=r"Membership ($\mu$) at New $\bar{\lambda}$", value=f"{max(0, 1 - abs(lambda_final - base_lambda) / (base_lambda * 0.15)):.2f}")
    
    st.markdown("---") 

    # --- SPLIT LAYOUT (Graphs vs Metrics) ---
    col_graph, col_metrics = st.columns([2, 1]) 
    
    # RIGHT SIDE: METRICS
    with col_metrics:
        st.markdown("#### 📊 Impact Analysis")
        
        # 1. MTBF
        if lambda_final > 0:
            mtbf_months = (1 / lambda_final) * 12
        else:
            mtbf_months = 0
        st.info(f"**MTBF:** {mtbf_months:.1f} Months")
        
        st.markdown("##### Check Reliability at Year:")
        
        # 2. TIME SLIDER
        check_year = st.slider("Mission Time (Years):", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        
        # 3. Calculate Reliability
        reliability_val = np.exp(-lambda_final * check_year)
        reliability_pct = reliability_val * 100
        
        st.metric(f"Reliability @ Year {check_year}", f"{reliability_pct:.2f}%")
        
        if reliability_pct > 80:
            st.success("✅ HEALTHY")
        elif reliability_pct > 50:
            st.warning("⚠️ MONITOR")
        else:
            st.error("🚨 CRITICAL")

    # LEFT SIDE: GRAPHS
    with col_graph:
        # --- GRAPH 1: FUZZY TRIANGLE ---
        try:
            fig_tfn = plt.figure(figsize=(6, 2.5), dpi=300)
            x_static = [static_lower, base_lambda, static_upper]
            y_static = [0, 1, 0]
            
            plt.plot(x_static, y_static, color='#0054A6', linewidth=2, label='Original Fuzzy Set')
            plt.fill_between(x_static, y_static, color='#0054A6', alpha=0.1)
            plt.vlines(lambda_final, 0, 1, colors='red', linestyles='dashed', linewidth=2, label=r'Selected $\bar{\lambda}$')
            plt.vlines(base_lambda, 0, 1, colors='grey', linestyles='dotted', alpha=0.5)

            plt.title(f"Sensitivity Analysis: {selected_research_item}", fontsize=9)
            plt.xlabel(r"Failure Rate ($\lambda$)", fontsize=7)
            plt.ylabel(r"Membership ($\mu$)", fontsize=7)
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.xlim(static_lower * 0.95, static_upper * 1.05)
            plt.ylim(0, 1.1)
            plt.legend(fontsize=6, loc='upper right')
            st.pyplot(fig_tfn, use_container_width=False)
            
        except Exception as e:
            st.error(f"Graph 1 Error: {e}")

        st.markdown("") 

        # --- GRAPH 2: RELIABILITY CURVE ---
        try:
            fig_rel = plt.figure(figsize=(6, 3), dpi=300)
            
            # X-Axis Range
            max_time_plot = max(5.0, check_year * 1.5)
            t_values = np.linspace(0, max_time_plot, 100)
            
            # 1. GREEN FIXED LINE (Original Base Lambda)
            R_base = np.exp(-base_lambda * t_values)
            plt.plot(t_values, R_base, color='green', linewidth=2, label=r'Base Curve ($\lambda$=' + f'{base_lambda:.3f})')
            
            # 2. DYNAMIC CURVE (Faint Red)
            R_new = np.exp(-lambda_final * t_values)
            plt.plot(t_values, R_new, color='red', linestyle='--', alpha=0.3, linewidth=1)

            # 3. RED DOTTED CROSSHAIR
            plt.vlines(check_year, 0, reliability_val, colors='red', linestyles='dotted', linewidth=2)
            plt.hlines(reliability_val, 0, check_year, colors='red', linestyles='dotted', linewidth=2)
            
            # Intersection Dot
            plt.plot(check_year, reliability_val, 'ro', markersize=6)
            
            # Text Label
            plt.text(check_year + (max_time_plot*0.02), reliability_val + 0.05, 
                     f"{reliability_pct:.1f}%", fontsize=9, color='red', fontweight='bold')
            
            # Label for Year Axis
            plt.text(check_year, 0.02, f"Year {check_year}", fontsize=7, color='red', ha='center')

            plt.title("Reliability Curve vs. Time", fontsize=9)
            plt.xlabel("Time (Years)", fontsize=7)
            plt.ylabel("Reliability Probability", fontsize=7)
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.ylim(0, 1.1)
            plt.xlim(0, max_time_plot)
            plt.legend(fontsize=6, loc='upper right')
            
            st.pyplot(fig_rel, use_container_width=False)
            
        except Exception as e:
            st.error(f"Graph 2 Error: {e}")
            
            
# ==========================================
# TAB 6: AI RELIABILITY ADVISOR (Fixed Column Selection)
# ==========================================
import google.generativeai as genai
import time

with tab6:
    st.header("🤖 AI Maintenance Advisor (Powered by Gemini)")
    st.markdown("This tool uses **Google Gemini** to analyze your fleet data.")
    
    st.divider()

    # --- 1. SETUP API ---
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.warning("⚠️ No Google API Key found.")
        st.stop()
    
    genai.configure(api_key=api_key)

    # --- 2. PREPARE DATA ---
    if 'shared_df' in st.session_state and st.session_state['shared_df'] is not None:
        df_ai = st.session_state['shared_df'].copy()
        
        # --- CRITICAL FIX: FIND THE CORRECT LAMBDA COLUMN ---
        # We search specifically for 'failure rate' or 'lambda'
        target_col = None
        
        # 1. Try exact match first
        if 'Calculated λ' in df_ai.columns:
            target_col = 'Calculated λ'
        elif 'Failure Rate (λ)' in df_ai.columns:
            target_col = 'Failure Rate (λ)'
        else:
            # 2. Fuzzy search if exact match fails
            cols_lower = [c.lower() for c in df_ai.columns]
            for c in df_ai.columns:
                if 'rate' in c.lower() and ('fail' in c.lower() or 'lambda' in c.lower() or 'λ' in c.lower()):
                    target_col = c
                    break
        
        # Default fallback if nothing found
        if not target_col:
            target_col = df_ai.columns[1] # Guess the second column
            
        # Ensure it's numeric
        df_ai[target_col] = pd.to_numeric(df_ai[target_col], errors='coerce')
        
        # Get Top 20 Items based on Lambda
        top_failures = df_ai.nlargest(20, target_col) 
        
        st.subheader(f"📊 Analysis Target: Top {len(top_failures)} Critical Items")
        
        # --- DISPLAY THE CORRECT COLUMNS ---
        with st.expander("View Raw Data", expanded=True):
            # We explicitly show Equipment Name and the found Lambda column
            st.dataframe(
                top_failures[['Equipment Name', target_col]], 
                use_container_width=True
            )
            
    else:
        st.error("❌ No data found in Tab 3.")
        st.stop()

    # --- 3. MODEL SELECTOR ---
    st.subheader("⚙️ AI Configuration")
    
    try:
        my_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                my_models.append(m.name)
        
        selected_model_name = st.selectbox(
            "Select AI Model (Choose 1.5-Flash or Pro):", 
            my_models,
            index=0
        )
        st.caption(f"Using Model: `{selected_model_name}`")
        
    except Exception as e:
        st.error(f"Could not list models. Try updating your library: {e}")
        st.stop()

    # --- 4. EXECUTE ANALYSIS ---
    st.divider()
    if st.button("🚀 Generate Full Report"):
        
        model = genai.GenerativeModel(selected_model_name)
        
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        batches = list(chunker(top_failures, 5)) 
        progress_bar = st.progress(0)
        
        for i, batch_df in enumerate(batches):
            batch_num = i + 1
            st.markdown(f"### 📋 Part {batch_num} of {len(batches)}")
            
            with st.spinner(f"Analyzing Batch {batch_num}..."):
                try:
                    # Send the Lambda data to the AI
                    data_summary = batch_df[['Equipment Name', target_col]].to_string(index=False)
                    
                    prompt = f"""
                    You are a Senior Reliability/Maintenance Engineer.
                    Analyze this batch of equipment. The column '{target_col}' represents the Failure Rate (Lambda).
                    
                    Data:
                    {data_summary}
                    
                    **OUTPUT FORMAT:**
                    Produce a Markdown Table with columns: 
                    | Equipment Name | Root Cause | Maintenance Strategy | Spares Action |
                    """

                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                    
                    time.sleep(5) 
                    
                except Exception as e:
                    st.error(f"Error: {e}")
            
            progress_bar.progress((i + 1) / len(batches))

        st.success("✅ Analysis Complete!")
        
        
# ==========================================
# TAB 7: ROOT CAUSE ANALYSIS (Linked to Tab 2)
# ==========================================
with tab7:
    st.header("🧠 Root Cause Analysis (5 Whys)")
    st.markdown("Use this tool to investigate the **failure modes** identified in your analysis.")
    
    st.divider()

    # --- 1. CHECK IF DATA EXISTS IN MEMORY FIRST ---
    if 'fleet_data' not in st.session_state:
        st.warning("⚠️ Please upload your machinery data in Tab 3 first to unlock this tool.")
    else:
        # --- 2. LINK LOGIC ---
        # Default values (Empty if not linked)
        def_problem = ""
        def_equip = ""
        
        # Check for the signal from Tab 2
        if 'selected_equipment' in st.session_state:
            linked_item = st.session_state['selected_equipment']
            
            # Show the link status
            st.success(f"🔗 **Linked to Tab 2:** Starting RCA for **{linked_item}**")
            
            # Auto-fill the variables
            def_equip = linked_item
            def_problem = f"Failure of {linked_item}" # Auto-generate a title
        else:
            st.info("ℹ️ Select equipment in Tab 2 to auto-fill details here.")

        # --- 3. DEFINE PROBLEM ---
        col_rca1, col_rca2 = st.columns([1, 1])
        
        with col_rca1:
            problem_statement = st.text_input("📝 Problem Statement", value=def_problem, placeholder="e.g., Main Engine Fuel Pump Failure")
            failure_date = st.date_input("Date of Failure")
        
        with col_rca2:
            equipment_tag = st.text_input("Equipment Tag / ID", value=def_equip)
            team_members = st.text_input("Investigation Team", placeholder="e.g., Chief Engineer, 2nd Engineer")

        st.divider()

        # --- 4. THE 5 WHYS ---
        st.subheader("❓ The 5 Whys")
        
        why_1 = st.text_input("1. Why did it fail?", placeholder="e.g., The bearing seized.")
        why_2 = st.text_input("2. Why did that happen?", placeholder="e.g., No lubrication reached the bearing.")
        why_3 = st.text_input("3. Why?", placeholder="e.g., The oil filter was completely clogged.")
        why_4 = st.text_input("4. Why?", placeholder="e.g., Maintenance was missed for 6 months.")
        why_5 = st.text_input("5. Why (Root Cause)?", placeholder="e.g., No tracking system for filter changes.")

        # --- 5. GENERATE REPORT ---
        if st.button("📄 Generate RCA Summary"):
            if problem_statement and why_5:
                st.success("RCA Report Generated!")
                
                report_text = f"""
                **RCA REPORT: {problem_statement}**
                **Date:** {failure_date} | **Tag:** {equipment_tag} | **Team:** {team_members}
                
                **Analysis Chain:**
                1. {why_1}
                2. ⬇️ {why_2}
                3. ⬇️ {why_3}
                4. ⬇️ {why_4}
                5. 🔴 **ROOT CAUSE:** {why_5}
                
                **Recommended Action:**
                Implement corrective measures to address: *{why_5}*
                """
                st.info(report_text)
                
                # Optional: Allow download
                st.download_button("📥 Download Report", report_text, file_name=f"RCA_{equipment_tag}.txt")
            else:
                st.error("Please fill in the Problem Statement and the 5th Why to generate a report.")
    
# ==========================================
# TAB 8: SPARE PARTS OPTIMIZER (Time-Based)
# ==========================================
import math
import datetime
import altair as alt

with tab8:
    st.header("📦 Spare Parts Strategy (Time-Based)")
    st.markdown("Calculate **Next Failure Date** and **Order Deadlines** based on reliability data.")
    
    st.divider()
    
    # --- 1. RECEIVE DATA & STRATEGY ---
    def_name = "Generic Part"
    def_lambda = 0.5  # Default failures per year
    active_strategy = "None"
    
    if 'ahp_handoff' in st.session_state:
        data = st.session_state['ahp_handoff']
        st.success(f"🔗 **Linked to Tab 2:** Analyzing **{data['equip_name']}**")
        st.info(f"📋 **Active Strategy:** {data['strategy']}")
        
        def_name = data['equip_name']
        active_strategy = data['strategy']
        def_lambda = data['annual_lambda']
        
        # Avoid division by zero
        if def_lambda <= 0: def_lambda = 0.01

    # --- 2. RELIABILITY INPUTS ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        part_name = st.text_input("Spare Part Name", def_name)
        # We assume the user inputs the actual 'Lead Time Days' here because 
        # the slider in Tab 2 (1-10) is a relative score, not actual days.
        lead_time = st.number_input("Lead Time (Days)", value=30, help="Days for part to arrive after ordering")
        
    with c2:
        # User enters when they last installed a new part
        last_replaced = st.date_input("Last Replaced Date", value=datetime.date.today() - datetime.timedelta(days=90))
        
    with c3:
        # Display MTBF for reference
        mtbf_years = 1 / def_lambda
        mtbf_days = mtbf_years * 365
        st.metric("Estimated MTBF", f"{int(mtbf_days)} Days", help="Mean Time Between Failures (1/λ)")

    st.divider()

    # --- 3. CALCULATE KEY DATES ---
    
    # A. Predict Next Failure
    # Formula: Last Date + MTBF
    predicted_failure_date = last_replaced + datetime.timedelta(days=mtbf_days)
    
    # B. Calculate "Order By" Date
    # If RTF: We wait until failure to order (Order Date = Failure Date)
    # If JIT/Strategic: We order early so it arrives BEFORE failure (Order Date = Failure - Lead Time)
    if "Run To Failure" in active_strategy:
        order_date = predicted_failure_date
        strategy_note = "Wait for failure, then order."
        is_rtf = True
    else:
        order_date = predicted_failure_date - datetime.timedelta(days=lead_time)
        strategy_note = f"Order {lead_time} days before failure to prevent downtime."
        is_rtf = False
        
    # C. Status Check
    today = datetime.date.today()
    days_until_order = (order_date - today).days
    
    # --- 4. DISPLAY RESULTS ---
    st.subheader(f"🗓️ Procurement Timeline: {part_name}")
    
    m1, m2, m3 = st.columns(3)
    
    m1.metric("📅 Next Predicted Failure", predicted_failure_date.strftime("%d %b %Y"))
    
    # Color code the Order Date
    if days_until_order < 0:
        m2.metric("🛒 Order By Date", order_date.strftime("%d %b %Y"), "OVERDUE", delta_color="inverse")
    elif days_until_order < 14:
        m2.metric("🛒 Order By Date", order_date.strftime("%d %b %Y"), f"{days_until_order} Days Left", delta_color="off")
    else:
        m2.metric("🛒 Order By Date", order_date.strftime("%d %b %Y"), f"in {days_until_order} Days")
        
    m3.caption(f"**Strategy Logic:** {strategy_note}")
    
    # --- 5. VISUAL TIMELINE (Altair Gantt) ---
    st.markdown("### ⏳ Lifecycle Visualization")
    
    # Create data for timeline bars
    timeline_data = [
        {"Task": "Operational Life", "Start": last_replaced, "End": predicted_failure_date, "Color": "#4caf50", "Label": "Running"},
        {"Task": "Lead Time Window", "Start": order_date, "End": predicted_failure_date, "Color": "#ff9800", "Label": "Shipping Time"}
    ]
    
    if is_rtf:
        # For RTF, Lead Time starts AFTER failure
        arrival_date = predicted_failure_date + datetime.timedelta(days=lead_time)
        timeline_data[1] = {"Task": "Downtime (Waiting for Part)", "Start": predicted_failure_date, "End": arrival_date, "Color": "#f44336", "Label": "Downtime"}
        
    df_timeline = pd.DataFrame(timeline_data)
    
    # Generate Chart
    chart = alt.Chart(df_timeline).mark_bar(cornerRadius=5, height=20).encode(
        x=alt.X('Start', title='Date'),
        x2='End',
        y=alt.Y('Task', sort=None, title=None), # Hide Y title
        color=alt.Color('Color', scale=None),
        tooltip=['Task', 'Start', 'End', 'Label']
    ).properties(height=150)
    
    # Add "Today" line
    today_line = alt.Chart(pd.DataFrame({'Date': [today]})).mark_rule(color='red', strokeDash=[5,5]).encode(
        x='Date'
    )
    
    st.altair_chart(chart + today_line, use_container_width=True)
    
    if is_rtf:
        st.warning(f"⚠️ **Strategy Warning:** Since this is **Run To Failure**, you will experience **{lead_time} days of downtime** after the failure occurs (Red Bar).")
    else:
        st.success(f"✅ **Strategy Success:** If you order on **{order_date.strftime('%d %b')}**, the part arrives exactly when the old one is predicted to fail (Orange Bar matches Green End).")
        
         
    
    
# ==========================================
# TAB 9: INTEGRATED MASTER DASHBOARD (Synced)
# ==========================================
import altair as alt
import math
import pandas as pd
import numpy as np

with tab9:
    st.header("🚀 Integrated Reliability Dashboard")
    st.markdown("A unified view of **Reliability**, **Inventory**, and **Research** metrics for the selected asset.")
    st.divider()

    # --- 1. DATA SYNCHRONIZATION ---
    target_equip = st.session_state.get('selected_equipment', None)
    
    if not target_equip:
        st.warning("⚠️ No equipment selected. Please go to **Tab 2** and select an asset to generate this dashboard.")
        st.stop()
        
    if 'shared_df' in st.session_state and st.session_state['shared_df'] is not None:
        df_dash = st.session_state['shared_df']
        try:
            row = df_dash[df_dash['Equipment Name'] == target_equip].iloc[0]
            if 'Calculated λ' in df_dash.columns: val_lambda = row['Calculated λ']
            elif 'Failure Rate (λ)' in df_dash.columns: val_lambda = row['Failure Rate (λ)']
            else: val_lambda = row.iloc[1] 
        except IndexError:
            st.error(f"❌ Error: Could not find data for '{target_equip}'.")
            st.stop()
    else:
        st.error("❌ Database not loaded.")
        st.stop()

    # --- 2. RE-CALCULATE KEY METRICS ---
    
    # A. RELIABILITY
    if val_lambda > 0:
        mtbf_days = (1 / val_lambda) * 365
        reliability_1yr = math.exp(-val_lambda * 1) * 100
    else:
        mtbf_days = 0
        reliability_1yr = 100

    # B. STRATEGY (PULL EXACT FROM TAB 2)
    strat_name = "Safety Stock" # Fallback
    if 'ahp_handoff' in st.session_state:
        strat_name = st.session_state['ahp_handoff']['strategy']

    if "Strategic" in strat_name: strat_color = "red"
    elif "Safety" in strat_name: strat_color = "orange"
    elif "Just In Time" in strat_name: strat_color = "blue"
    else: strat_color = "green"

    # C. INVENTORY (Aligned with Tab 2 Logic)
    lead_time = 30 
    daily_usage = val_lambda / 365
    base_annual_demand = math.ceil(val_lambda) if val_lambda > 0 else 1

    # Dynamic Label and Buffer based on Strategy
    if "Strategic Holding" in strat_name:
        buffer_qty = 2
        stock_label = "Strategic Holding"
    elif "Safety Stock" in strat_name:
        buffer_qty = 1
        stock_label = "Safety Stock"
    else:
        buffer_qty = 0
        stock_label = "Buffer Stock"

    # Total Annual Matches Tab 2 exactly
    total_annual_plan = base_annual_demand + buffer_qty

    # Logistics Math
    rop = math.ceil(daily_usage * lead_time) + buffer_qty
    
    if "Run To Failure" in strat_name:
        eoq = 1
    else:
        if val_lambda > 0:
            eoq = math.ceil(math.sqrt((2 * val_lambda * 50) / (150 * 0.2)))
        else:
            eoq = 1

    # --- 3. DASHBOARD LAYOUT ---
    st.subheader(f"Asset Status: {target_equip}")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🛑 Failure Rate (λ)", f"{val_lambda:.4f} /yr")
    m2.metric("⏳ MTBF", f"{int(mtbf_days)} Days")
    m3.metric("📉 Reliability (1 Yr)", f"{reliability_1yr:.1f}%")
    
    if strat_color == "red": m4.error(f"**Strategy:**\n{strat_name}")
    elif strat_color == "orange": m4.warning(f"**Strategy:**\n{strat_name}")
    elif strat_color == "blue": m4.info(f"**Strategy:**\n{strat_name}")
    else: m4.success(f"**Strategy:**\n{strat_name}")

    st.divider()

    # ROW 2: VISUAL COMPARISON
    col_viz1, col_viz2 = st.columns(2)
    
    with col_viz1:
        st.markdown("#### 📉 Reliability Decay Curve")
        t = np.linspace(0, 5, 50) 
        r_t = np.exp(-val_lambda * t)
        
        chart_df = pd.DataFrame({"Time (Years)": t, "Reliability": r_t})
        
        c = alt.Chart(chart_df).mark_area(
            line={'color':'darkgreen'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='white', offset=0),
                       alt.GradientStop(color='darkgreen', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x='Time (Years)',
            y=alt.Y('Reliability', axis=alt.Axis(format='%')),
            tooltip=['Time (Years)', 'Reliability']
        ).properties(height=200)
        
        st.altair_chart(c, use_container_width=True)

    with col_viz2:
        st.markdown("#### 📦 Inventory Consumption Model")
        sim_days = 365
        stock = []
        curr = rop + eoq
        for d in range(sim_days):
            curr -= daily_usage
            if curr <= rop:
                curr += eoq 
            stock.append(curr)
            
        stock_df = pd.DataFrame({"Day": range(sim_days), "Stock": stock})
        
        c2 = alt.Chart(stock_df).mark_line(color='#0070f3').encode(
            x='Day',
            y='Stock'
        ).properties(height=200)
        
        st.altair_chart(c2, use_container_width=True)

    st.divider()

    # ROW 3: DETAILED TABLES
    c_inv, c_fuzzy = st.columns(2)
    
    with c_inv:
        st.info("📦 **Inventory Plan (Aligned with Tab 2 & 8)**")
        st.dataframe(pd.DataFrame({
            "Metric": [stock_label, "Reorder Point (ROP)", "Order Quantity (EOQ)", "Total Annual Plan"],
            "Value": [f"{buffer_qty} Units", f"{rop} Units", f"{eoq} Units", f"{total_annual_plan} Units"]
        }), hide_index=True, use_container_width=True)
        
    with c_fuzzy:
        st.warning("📚 **Fuzzy Uncertainty Range (Tab 5)**")
        lower = val_lambda * 0.85
        upper = val_lambda * 1.15
        st.dataframe(pd.DataFrame({
            "Scenario": ["Best Case (-15%)", "Baseline", "Worst Case (+15%)"],
            "Projected λ": [f"{lower:.4f}", f"{val_lambda:.4f}", f"{upper:.4f}"]
        }), hide_index=True, use_container_width=True)
        
        
       
        
# ==========================================
# TAB 10: PLANNED MAINTENANCE & LIVE INVENTORY
# ==========================================
import datetime as dt
import pandas as pd
import math

with tab10:
    st.header("⚙️ PMS & Live Inventory Ledger")
    st.markdown("Execute scheduled work orders and automatically track your live warehouse stock.")
    st.divider()
    
    # --- RESET BUTTON FOR DEMO PURPOSES ---
    if st.button("🔄 Reset Warehouse Memory", type="primary"):
        if 'live_inventory' in st.session_state:
            del st.session_state['live_inventory']
        if 'pms_tasks' in st.session_state:
            del st.session_state['pms_tasks']
        st.rerun()

    # --- 1. INITIALIZE & SYNC LIVE DATABASE ---
    if 'shared_df' in st.session_state and st.session_state['shared_df'] is not None:
        current_equip_list = st.session_state['shared_df']['Equipment Name'].unique().tolist()
    else:
        current_equip_list = [f"Equipment {i}" for i in range(1, 11)]

    if 'live_inventory' not in st.session_state:
        st.session_state['live_inventory'] = {}
        
    keys_to_delete = []
    for eq in st.session_state['live_inventory'].keys():
        if eq not in current_equip_list:
            keys_to_delete.append(eq)
    for k in keys_to_delete:
        del st.session_state['live_inventory'][k]
        
    for eq in current_equip_list:
        if eq not in st.session_state['live_inventory']:
            # 🔥 DEFAULT STOCK CHANGED TO 2 HERE
            st.session_state['live_inventory'][eq] = {
                'Stock': 2, 'ROP': 2, 'EOQ': 5, 'Strategy': 'Pending Analysis'
            }

    if 'pms_tasks' not in st.session_state:
        st.session_state['pms_tasks'] = pd.DataFrame(columns=[
            'Work Order', 'Equipment', 'Task', 'Interval (Days)', 'Parts Needed', 'Last Done', 'Next Due'
        ])
        
    df_pms = st.session_state['pms_tasks']
    df_pms = df_pms[df_pms['Equipment'].isin(current_equip_list)]
        
    existing_tasks = df_pms['Equipment'].tolist()
    new_tasks = []
    today = dt.date.today()
    
    for i, eq in enumerate(current_equip_list):
        if eq not in existing_tasks:
            last_done = today - dt.timedelta(days=80)
            new_tasks.append({
                'Work Order': f"WO-2026-{100 + len(existing_tasks) + i}",
                'Equipment': eq,
                'Task': 'Routine Inspection & Overhaul',
                'Interval (Days)': 90,
                'Parts Needed': 1 if "Engine" not in str(eq) else 4,
                'Last Done': last_done,
                'Next Due': last_done + dt.timedelta(days=90)
            })
            
    if new_tasks:
        df_pms = pd.concat([df_pms, pd.DataFrame(new_tasks)], ignore_index=True)
        
    st.session_state['pms_tasks'] = df_pms.reset_index(drop=True)

    # --- 2. LINK TO TAB 2 (AHP OPTIMISATION) ---
    if 'ahp_handoff' in st.session_state:
        handoff = st.session_state['ahp_handoff']
        sync_eq = handoff['equip_name']
        strat = handoff['strategy']
        lam = handoff['annual_lambda']
        
        if sync_eq in st.session_state['live_inventory']:
            lead_time = 30 
            daily_usage = lam / 365
            
            if "Strategic Holding" in strat: buffer = 2
            elif "Safety Stock" in strat: buffer = 1
            else: buffer = 0
                
            calc_rop = math.ceil(daily_usage * lead_time) + buffer
            calc_eoq = 1 if "Run To Failure" in strat else (math.ceil(math.sqrt((2 * lam * 50) / (150 * 0.2))) if lam > 0 else 1)
            
            st.session_state['live_inventory'][sync_eq]['ROP'] = calc_rop
            st.session_state['live_inventory'][sync_eq]['EOQ'] = calc_eoq
            st.session_state['live_inventory'][sync_eq]['Strategy'] = strat

    # --- 3. WORK ORDER EXECUTION CONSOLE ---
    st.subheader("🛠️ Execute Maintenance & Logistics")
    
    df_tasks = st.session_state['pms_tasks']
    wo_list = df_tasks['Work Order'].tolist()
    
    col_exec1, col_exec2, col_exec3 = st.columns([2, 2, 2])
    
    with col_exec1:
        selected_wo = st.selectbox("Select Work Order:", wo_list)
        
    with col_exec2:
        wo_details = df_tasks[df_tasks['Work Order'] == selected_wo].iloc[0]
        eq_target = wo_details['Equipment']
        st.info(f"**Target:** {eq_target}\n\n**Requires:** {wo_details['Parts Needed']} parts")
        
    with col_exec3:
        eq_name = wo_details['Equipment']
        parts_req = wo_details['Parts Needed']
        current_stock = st.session_state['live_inventory'][eq_name]['Stock']
        eoq_qty = st.session_state['live_inventory'][eq_name]['EOQ']
        
        if st.button("✅ Complete Maintenance", use_container_width=True):
            if current_stock >= parts_req:
                st.session_state['live_inventory'][eq_name]['Stock'] -= parts_req
                
                idx = df_tasks.index[df_tasks['Work Order'] == selected_wo].tolist()[0]
                st.session_state['pms_tasks'].at[idx, 'Last Done'] = dt.date.today()
                st.session_state['pms_tasks'].at[idx, 'Next Due'] = dt.date.today() + dt.timedelta(days=int(wo_details['Interval (Days)']))
                
                st.success(f"Job logged! {parts_req} parts consumed.")
                st.rerun()
            else:
                st.error(f"❌ Need {parts_req} parts, but only have {current_stock}.")
                
        if st.button(f"📦 Receive Shipment (+{eoq_qty} units)", use_container_width=True):
            st.session_state['live_inventory'][eq_name]['Stock'] += eoq_qty
            st.success(f"Restocked {eoq_qty} units for {eq_name}!")
            st.rerun()

    st.divider()

    # --- 4. LIVE DASHBOARDS ---
    col_dash1, col_dash2 = st.columns([1, 1.2])

    with col_dash1:
        st.subheader("📅 Maintenance Schedule")
        today = dt.date.today()
        
        def check_status(due_date):
            if due_date < today: return "🚨 Overdue"
            elif (due_date - today).days <= 14: return "⚠️ Due Soon"
            else: return "✅ Scheduled"
            
        display_tasks = st.session_state['pms_tasks'].copy()
        display_tasks['Status'] = display_tasks['Next Due'].apply(check_status)
        
        st.dataframe(
            display_tasks[['Work Order', 'Equipment', 'Next Due', 'Status']], 
            hide_index=True, 
            use_container_width=True
        )

    with col_dash2:
        st.subheader("📦 Live Digital Warehouse")
        st.caption("💡 Double-click any number in the 'Stock' column to manually adjust your inventory.")
        
        inv_df = pd.DataFrame.from_dict(st.session_state['live_inventory'], orient='index').reset_index()
        inv_df.rename(columns={'index': 'Equipment Name'}, inplace=True)
        
        def check_stock(row):
            if row['Stock'] == 0: return "🔴 OUT OF STOCK"
            elif row['Stock'] <= row['ROP']: return "🟡 Reorder Needed"
            else: return "🟢 Healthy"
            
        inv_df['Status'] = inv_df.apply(check_stock, axis=1)
        
        # 🔥 UPGRADED: st.data_editor instead of st.dataframe
        edited_df = st.data_editor(
            inv_df[['Equipment Name', 'Stock', 'ROP', 'EOQ', 'Strategy', 'Status']], 
            hide_index=True, 
            use_container_width=True,
            # Lock everything except the 'Stock' column so users don't break the math
            disabled=['Equipment Name', 'ROP', 'EOQ', 'Strategy', 'Status'],
            key="warehouse_editor"
        )

        # 🔥 SYNC EDITS BACK TO MEMORY
        changes_made = False
        for index, row in edited_df.iterrows():
            eq_name = row['Equipment Name']
            new_stock = int(row['Stock'])
            
            # If the user typed a new number, save it and trigger a refresh
            if st.session_state['live_inventory'][eq_name]['Stock'] != new_stock:
                st.session_state['live_inventory'][eq_name]['Stock'] = new_stock
                changes_made = True
                
        if changes_made:
            st.rerun() # Refresh the page immediately to update the 'Status' color
        
       
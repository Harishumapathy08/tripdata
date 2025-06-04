import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO
import os

# --- DB SETUP ---
DB_PATH = "data/trips.db"
os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver TEXT NOT NULL,
    disp_date TEXT NOT NULL,
    invoice_no TEXT,
    customer TEXT,
    destination TEXT,
    invoice_date TEXT,
    vehicle TEXT,
    out_time TEXT,
    in_time TEXT,
    out_km INTEGER,
    in_km INTEGER,
    diff_km INTEGER
)
""")
conn.commit()

# --- CONSTANTS ---
drivers = ["Prem", "Ajith", "Wilson"]

def generate_time_options():
    times = []
    for hour in range(0, 24):
        for minute in (0, 15, 30, 45):
            t_24h = f"{hour:02d}:{minute:02d}"
            dt_obj = datetime.strptime(t_24h, "%H:%M")
            t_12h = dt_obj.strftime("%I:%M %p")
            times.append((t_24h, t_12h))
    return times

time_options = generate_time_options()

def format_time_12h(t24):
    dt_obj = datetime.strptime(t24, "%H:%M")
    return dt_obj.strftime("%I:%M %p")

# --- FUNCTIONS ---

def add_trip(data):
    c.execute("""
    INSERT INTO trips (driver, disp_date, invoice_no, customer, destination, invoice_date, vehicle,
                       out_time, in_time, out_km, in_km, diff_km)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
    conn.commit()

def get_all_trips():
    c.execute("SELECT * FROM trips")
    rows = c.fetchall()
    columns = ["id", "Driver", "Disp Date", "Invoice No", "Customer", "Destination",
               "Invoice Date", "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"]
    return pd.DataFrame(rows, columns=columns)

def delete_trip_by_id(trip_id):
    c.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()

# --- STREAMLIT UI ---

st.set_page_config(page_title="🚛 Trip Entry Form", layout="wide")
st.title("🚛 Trip Entry Form")

# --- Add Trip Form ---
st.subheader("➕ Add Trip Record")

with st.form("trip_form"):
    selected_driver = st.selectbox("Driver", drivers)
    col1, col2, col3 = st.columns(3)

    disp_date = col1.date_input("Disp Date")
    invoice_no = col2.text_input("Invoice No")
    customer = col3.text_input("Customer")

    destination = col1.text_input("Destination")
    invoice_date = col2.date_input("Invoice Date")
    vehicle = col3.text_input("Vehicle")

    out_time_24h = col1.selectbox("Out Time", options=[opt[0] for opt in time_options],
                                  format_func=lambda x: dict(time_options)[x])
    in_time_24h = col2.selectbox("In Time", options=[opt[0] for opt in time_options],
                                 format_func=lambda x: dict(time_options)[x])

    out_km = col3.number_input("Out KM", min_value=0, step=1)
    in_km = col1.number_input("In KM", min_value=0, step=1)
    diff_km = max(0, in_km - out_km)

    submitted = st.form_submit_button("Submit")

    if submitted:
        if in_km < out_km:
            st.error("In KM cannot be less than Out KM.")
        else:
            add_trip((
                selected_driver,
                disp_date.strftime("%Y-%m-%d"),
                invoice_no.strip(),
                customer.strip(),
                destination.strip(),
                invoice_date.strftime("%Y-%m-%d"),
                vehicle.strip(),
                out_time_24h,
                in_time_24h,
                out_km,
                in_km,
                diff_km
            ))
            st.success(f"✅ Trip added for {selected_driver}. Please refresh to see updated data.")
            st.stop()  # Prevent further execution after submission

# --- View Trips ---
st.subheader("📋 View Trips")

df = get_all_trips()

if df.empty:
    st.info("No trips found. Please add trip records.")
else:
    driver_filter = st.selectbox("Select Driver to View", ["All"] + drivers)

    if driver_filter != "All":
        filtered_df = df[df["Driver"] == driver_filter].copy()
    else:
        filtered_df = df.copy()

    if filtered_df.empty:
        st.info(f"No records found for {driver_filter}.")
    else:
        filtered_df = filtered_df.reset_index(drop=True)
        filtered_df["S.No."] = filtered_df.index + 1
        filtered_df["Out Time"] = filtered_df["Out Time"].apply(format_time_12h)
        filtered_df["In Time"] = filtered_df["In Time"].apply(format_time_12h)

        cols_to_show = ["S.No.", "Driver", "Disp Date", "Invoice No", "Customer", "Destination",
                        "Invoice Date", "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"]

        st.dataframe(filtered_df[cols_to_show], use_container_width=True)

        sno_to_delete = st.number_input("Enter S.No. to Delete", min_value=1, max_value=len(filtered_df), step=1)

        if st.button("🗑 Delete Trip"):
            if sno_to_delete in filtered_df["S.No."].values:
                trip_id = int(filtered_df.loc[filtered_df["S.No."] == sno_to_delete, "id"].values[0])
                delete_trip_by_id(trip_id)
                st.success(f"🗑 Deleted trip S.No. {sno_to_delete}. Please refresh to update.")
                st.stop()  # Stop to prevent rerun-related errors
            else:
                st.error("Invalid S.No. entered. Please enter a valid serial number.")

        # --- Download Excel with Sheets per Driver ---
        def convert_df_to_excel(df_export):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for driver in df_export["Driver"].unique():
                    df_driver = df_export[df_export["Driver"] == driver].drop(columns=["S.No."])
                    df_driver.to_excel(writer, sheet_name=driver[:31], index=False)
            output.seek(0)
            return output.read()

        excel_data = convert_df_to_excel(filtered_df[cols_to_show])

        st.download_button(
            label="⬇️ Download Trips by Driver (Excel)",
            data=excel_data,
            file_name="trip_data_by_driver.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

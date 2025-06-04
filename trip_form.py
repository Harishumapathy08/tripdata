import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time

# Constants
DB_FILE = "data/trip_data.db"
drivers = ["Prem", "Ajith", "Wilson"]
columns = [
    "S.No.", "Driver", "Disp Date", "Invoice No", "Customer", "Destination",
    "Invoice Date", "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"
]

# Create data folder if not exists
import os
os.makedirs("data", exist_ok=True)

# --- Database functions ---

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver TEXT,
            disp_date TEXT,
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

def add_trip(trip):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
        INSERT INTO trips (driver, disp_date, invoice_no, customer, destination, invoice_date, vehicle,
                           out_time, in_time, out_km, in_km, diff_km)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, trip)
        conn.commit()

def get_all_trips():
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT * FROM trips", conn)
    return df

def get_driver_trips(driver):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT * FROM trips WHERE driver=?", conn, params=(driver,))
    return df

def delete_trip(trip_id):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM trips WHERE id=?", (trip_id,))
        conn.commit()

# --- Time input with AM/PM ---

def time_with_am_pm(label, key_prefix):
    # Get time input in 24-hour format
    t_24 = st.time_input(label, key=key_prefix+"_time")
    am_pm = st.selectbox("AM/PM", options=["AM", "PM"], key=key_prefix+"_ampm")

    hour = t_24.hour
    minute = t_24.minute

    # Convert 24-hour to correct hour based on AM/PM selection
    if am_pm == "AM" and hour >= 12:
        hour -= 12
    elif am_pm == "PM" and hour < 12:
        hour += 12

    # Format display hour
    display_hour = hour if 1 <= hour <= 12 else (hour % 12) or 12
    time_str = f"{display_hour:02d}:{minute:02d} {am_pm}"

    return time_str

# --- Streamlit App ---

st.set_page_config(layout="wide")
st.title("🚛 Trip Entry Form")

init_db()

st.subheader("➕ Add Trip Record")

with st.form("trip_form"):
    selected_driver = st.selectbox("Driver", drivers)
    col1, col2, col3 = st.columns(3)
    disp_date = col1.date_input("Disp Date")
    inv_no = col2.text_input("Invoice No")
    customer = col3.text_input("Customer")

    destination = col1.text_input("Destination")
    inv_date = col2.date_input("Invoice Date")
    vehicle = col3.text_input("Vehicle")

    out_time = time_with_am_pm("Out Time", "out")
    in_time = time_with_am_pm("In Time", "in")

    out_km = col3.number_input("Out KM", min_value=0, step=1)
    in_km = col1.number_input("In KM", min_value=0, step=1)
    diff_km = max(in_km - out_km, 0)

    submitted = st.form_submit_button("Submit")

    if submitted:
        # Prepare trip data tuple
        trip_data = (
            selected_driver,
            disp_date.strftime("%Y-%m-%d"),
            inv_no.strip(),
            customer.strip(),
            destination.strip(),
            inv_date.strftime("%Y-%m-%d"),
            vehicle.strip(),
            out_time,
            in_time,
            out_km,
            in_km,
            diff_km
        )
        add_trip(trip_data)
        st.success(f"✅ Trip added for {selected_driver}")

st.subheader("📋 View Trips")

driver_filter = st.selectbox("Select Driver to View", drivers, key="view_driver")
driver_df = get_driver_trips(driver_filter)

if driver_df.empty:
    st.info("No records found for this driver.")
else:
    # Show with S.No. as index from 1
    driver_df = driver_df.reset_index(drop=True)
    driver_df.index += 1
    st.dataframe(driver_df[["driver", "disp_date", "invoice_no", "customer", "destination",
                            "invoice_date", "vehicle", "out_time", "in_time", "out_km",
                            "in_km", "diff_km"]], use_container_width=True)

    # Delete trip by id
    trip_ids = driver_df["id"].tolist()
    sno_to_delete = st.number_input("Enter S.No. to Delete", min_value=1, max_value=len(trip_ids), step=1)

if st.button("🗑 Delete Trip"):
    delete_trip(sno_to_delete)
    st.success(f"🗑 Deleted trip S.No. {sno_to_delete}")
    st.stop()

st.subheader("⬇️ Download All Trips Data as Excel")

all_trips_df = get_all_trips()

if not all_trips_df.empty:
    # Reorder columns & format dates for Excel
    all_trips_df = all_trips_df.rename(columns={
        "driver": "Driver", "disp_date": "Disp Date", "invoice_no": "Invoice No",
        "customer": "Customer", "destination": "Destination", "invoice_date": "Invoice Date",
        "vehicle": "Vehicle", "out_time": "Out Time", "in_time": "In Time",
        "out_km": "Out KM", "in_km": "In KM", "diff_km": "Diff in KM"
    })

    all_trips_df = all_trips_df[[
        "Driver", "Disp Date", "Invoice No", "Customer", "Destination", "Invoice Date",
        "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"
    ]]

    towrite = pd.ExcelWriter("data/trip_data_export.xlsx", engine="openpyxl")
    all_trips_df.to_excel(towrite, index=False, sheet_name="All Trips")
    towrite.save()

    with open("data/trip_data_export.xlsx", "rb") as f:
        data_bytes = f.read()

    st.download_button(
        label="Download Excel File",
        data=data_bytes,
        file_name="trip_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No trips to export yet.")

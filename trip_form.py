import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date, time

st.set_page_config(layout="wide")

# --- Constants ---
DATABASE = "data/trips.db"
TABLE_NAME = "trip_records"
drivers = ["Prem", "Ajith", "Wilson"]
columns = [
    "S.No.", "Driver", "Disp Date", "Invoice No", "Customer", "Destination",
    "Invoice Date", "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"
]

# --- DB Setup ---
conn = sqlite3.connect(DATABASE, check_same_thread=False)
c = conn.cursor()

c.execute(f'''
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
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
''')
conn.commit()

# --- Helper functions ---
def time_options():
    """Generate time strings in 15-min intervals with AM/PM format."""
    times = []
    for hour in range(0,24):
        for minute in (0,15,30,45):
            dt = time(hour=hour, minute=minute)
            times.append(dt.strftime("%I:%M %p"))
    return times

def insert_trip(data):
    c.execute(f'''
        INSERT INTO {TABLE_NAME} 
        (driver, disp_date, invoice_no, customer, destination, invoice_date, vehicle, out_time, in_time, out_km, in_km, diff_km)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()

def fetch_all_trips():
    c.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY driver, disp_date")
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["id"] + columns[1:])
    if df.empty:
        return df
    df.insert(0, "S.No.", range(1, len(df)+1))
    return df

def fetch_trips_by_driver(driver):
    c.execute(f"SELECT * FROM {TABLE_NAME} WHERE driver = ? ORDER BY disp_date", (driver,))
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["id"] + columns[1:])
    if df.empty:
        return df
    df.insert(0, "S.No.", range(1, len(df)+1))
    return df

def delete_trip_by_id(db_id):
    c.execute(f"DELETE FROM {TABLE_NAME} WHERE id = ?", (db_id,))
    conn.commit()

def export_to_excel(df):
    import io
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="All Trips")
    processed_data = output.getvalue()
    return processed_data

# --- UI ---

st.title("🚛 Trip Entry Form")

st.subheader("➕ Add Trip Record")
with st.form("trip_form"):
    selected_driver = st.selectbox("Driver", drivers)
    col1, col2, col3 = st.columns(3)
    disp_date = col1.date_input("Disp Date", date.today())
    inv_no = col2.text_input("Invoice No")
    customer = col3.text_input("Customer")

    destination = col1.text_input("Destination")
    inv_date = col2.date_input("Invoice Date", date.today())
    vehicle = col3.text_input("Vehicle")

    time_choices = time_options()
    out_time = col1.selectbox("Out Time", options=time_choices)
    in_time = col2.selectbox("In Time", options=time_choices)

    out_km = col3.number_input("Out KM", min_value=0, value=0)
    in_km = col1.number_input("In KM", min_value=0, value=0)
    diff_km = max(in_km - out_km, 0)

    submitted = st.form_submit_button("Submit")

    if submitted:
        # Save trip
        insert_trip((
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
        ))
        st.success(f"✅ Trip added for {selected_driver}")

st.subheader("📋 View & Manage Trips")

driver_filter = st.selectbox("Select Driver to View", drivers)
df = fetch_trips_by_driver(driver_filter)

if df.empty:
    st.info("No records found for this driver.")
else:
    st.dataframe(df[columns], use_container_width=True)

    sno_to_delete = st.number_input("Enter S.No. to Delete", min_value=1, max_value=len(df), step=1)
    if st.button("🗑 Delete Trip"):
        # Get DB ID of the row to delete
        db_id = int(df.loc[df["S.No."] == sno_to_delete, "id"].values[0])
        delete_trip_by_id(db_id)
        st.success(f"🗑 Deleted trip S.No. {sno_to_delete}")
        st.experimental_rerun()

# --- Export all trips ---

st.subheader("⬇️ Export All Trips to Excel")

all_trips_df = fetch_all_trips()
if all_trips_df.empty:
    st.info("No trips to export yet.")
else:
    excel_bytes = export_to_excel(all_trips_df[columns])
    st.download_button(
        label="Download Excel File",
        data=excel_bytes,
        file_name="trip_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

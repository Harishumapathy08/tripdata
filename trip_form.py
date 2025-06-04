import streamlit as st
import pandas as pd
import sqlite3
import io
import os

st.set_page_config(layout="wide")
DB_FILE = "data/trips.db"

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

# Driver list
drivers = ["Prem", "Ajith", "Wilson"]

# Columns of the trips table
columns = [
    "SNo", "Driver", "DispDate", "InvoiceNo", "Customer", "Destination",
    "InvoiceDate", "Vehicle", "OutTime", "InTime", "OutKM", "InKM", "DiffKM"
]

# Initialize SQLite connection and create table if not exists
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS trips (
    SNo INTEGER PRIMARY KEY AUTOINCREMENT,
    Driver TEXT,
    DispDate TEXT,
    InvoiceNo TEXT,
    Customer TEXT,
    Destination TEXT,
    InvoiceDate TEXT,
    Vehicle TEXT,
    OutTime TEXT,
    InTime TEXT,
    OutKM INTEGER,
    InKM INTEGER,
    DiffKM INTEGER
)
''')
conn.commit()

def add_trip(data):
    c.execute('''
        INSERT INTO trips (
            Driver, DispDate, InvoiceNo, Customer, Destination,
            InvoiceDate, Vehicle, OutTime, InTime, OutKM, InKM, DiffKM
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()

def get_trips(driver=None):
    if driver and driver != "All":
        c.execute("SELECT * FROM trips WHERE Driver = ?", (driver,))
    else:
        c.execute("SELECT * FROM trips")
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    return df

def delete_trip(sno):
    c.execute("DELETE FROM trips WHERE SNo = ?", (sno,))
    conn.commit()

# Title
st.title("🚛 Trip Entry Form")

# --- Add Trip Form ---
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

    # OutTime and InTime dropdown (15-min increments)
    times = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0,15,30,45)]
    out_time = col1.selectbox("Out Time", times)
    in_time = col2.selectbox("In Time", times)

    out_km = col3.number_input("Out KM", min_value=0, step=1)
    in_km = col1.number_input("In KM", min_value=0, step=1)
    diff_km = in_km - out_km if in_km >= out_km else 0

    submitted = st.form_submit_button("Submit")

    if submitted:
        data = (
            selected_driver,
            disp_date.strftime("%Y-%m-%d"),
            inv_no,
            customer,
            destination,
            inv_date.strftime("%Y-%m-%d"),
            vehicle,
            out_time,
            in_time,
            out_km,
            in_km,
            diff_km
        )
        add_trip(data)
        st.success(f"✅ Trip added for {selected_driver}")

# --- View Trips ---
st.subheader("📋 View Trips")
driver_filter = st.selectbox("Select Driver to View", ["All"] + drivers)
df = get_trips(driver_filter)

if not df.empty:
    st.dataframe(df.drop(columns=["SNo"]), use_container_width=True)

    sno_to_delete = st.number_input("Enter S.No. to Delete", min_value=1, step=1)
if st.button("🗑 Delete Trip"):
    delete_trip(sno_to_delete)
    st.success(f"🗑 Deleted trip S.No. {sno_to_delete}")
    st.stop()


    # Generate Excel file for download
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Save all drivers in separate sheets
        for drv in drivers:
            drv_df = get_trips(drv)
            if not drv_df.empty:
                drv_df.drop(columns=["SNo"]).to_excel(writer, sheet_name=drv, index=False)
    buffer.seek(0)

    st.download_button(
        "⬇️ Download All Trip Data (Excel)",
        data=buffer,
        file_name="trip_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No records found for this driver.")

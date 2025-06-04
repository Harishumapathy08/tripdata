import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

st.set_page_config(layout="wide")

# --- DB Setup ---
conn = sqlite3.connect("data/trips.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
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
''')
conn.commit()

drivers = ["Prem", "Ajith", "Wilson"]

# --- Helper functions ---
def insert_trip(data):
    c.execute('''
        INSERT INTO trips (
            driver, disp_date, invoice_no, customer, destination,
            invoice_date, vehicle, out_time, in_time, out_km, in_km, diff_km
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()

def fetch_trips(driver=None):
    if driver:
        c.execute("SELECT * FROM trips WHERE driver = ? ORDER BY id", (driver,))
    else:
        c.execute("SELECT * FROM trips ORDER BY id")
    rows = c.fetchall()
    columns = ["id", "Driver", "Disp Date", "Invoice No", "Customer", "Destination", 
               "Invoice Date", "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"]
    return pd.DataFrame(rows, columns=columns)

def delete_trip_by_id(trip_id):
    c.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()

# --- UI ---

st.title("🚛 Trip Entry Form with SQLite DB")

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

    # Time dropdowns: Hours, Minutes, AM/PM
    hours = [f"{h:02d}" for h in range(1,13)]
    minutes = [f"{m:02d}" for m in range(0,60)]
    am_pm = ["AM", "PM"]

    out_hour = col1.selectbox("Out Time - Hour", hours, key="out_hour")
    out_min = col2.selectbox("Out Time - Minute", minutes, key="out_min")
    out_ampm = col3.selectbox("Out Time - AM/PM", am_pm, key="out_ampm")
    out_time = f"{out_hour}:{out_min} {out_ampm}"

    in_hour = col1.selectbox("In Time - Hour", hours, key="in_hour")
    in_min = col2.selectbox("In Time - Minute", minutes, key="in_min")
    in_ampm = col3.selectbox("In Time - AM/PM", am_pm, key="in_ampm")
    in_time = f"{in_hour}:{in_min} {in_ampm}"

    out_km = col1.number_input("Out KM", min_value=0, step=1)
    in_km = col2.number_input("In KM", min_value=0, step=1)
    diff_km = in_km - out_km if in_km >= out_km else 0

    submitted = st.form_submit_button("Submit")

    if submitted:
        # Validate times by converting to 24h to check ordering
        try:
            out_dt = datetime.strptime(out_time, "%I:%M %p")
            in_dt = datetime.strptime(in_time, "%I:%M %p")
        except Exception:
            st.error("Invalid time format.")
            st.stop()

        # Save record
        insert_trip((
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
        ))
        st.success(f"✅ Trip added for {selected_driver}")

# --- View Trips ---
st.subheader("📋 View Trips")

driver_filter = st.selectbox("Select Driver to View", drivers, key="view_driver")
df = fetch_trips(driver_filter)

if df.empty:
    st.info("No records found for this driver.")
else:
    # Add S.No column for display (index + 1)
    df_display = df.copy()
    df_display["S.No."] = range(1, len(df_display) + 1)
    cols_to_show = ["S.No.", "Driver", "Disp Date", "Invoice No", "Customer", "Destination",
                    "Invoice Date", "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"]
    st.dataframe(df_display[cols_to_show], use_container_width=True)

    sno_to_delete = st.number_input("Enter S.No. to Delete", min_value=1, max_value=len(df_display), step=1)
if st.button("🗑 Delete Trip"):
    delete_trip(sno_to_delete)
    st.success(f"🗑 Deleted trip S.No. {sno_to_delete}")
    st.stop()


    # Download button - export all trips to Excel
    df_all = fetch_trips()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for drv in drivers:
            drv_df = df_all[df_all["Driver"] == drv]
            if not drv_df.empty:
                drv_df.drop(columns=["id"], inplace=True)
                drv_df.to_excel(writer, sheet_name=drv, index=False)
    output.seek(0)
    st.download_button("⬇️ Download All Trip Data (Excel)", data=output, file_name="trip_data.xlsx")


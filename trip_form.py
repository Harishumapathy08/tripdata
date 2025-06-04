import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime, time, timedelta
from openpyxl import load_workbook

st.set_page_config(layout="wide")
DATA_FILE = "data/trip_data.xlsx"
os.makedirs("data", exist_ok=True)

drivers = ["Prem", "Ajith", "Wilson"]
columns = [
    "S.No.", "Driver", "Disp Date", "Invoice No", "Customer", "Destination",
    "Invoice Date", "Vehicle", "Out Time", "In Time", "Out KM", "In KM", "Diff in KM"
]

def load_data():
    if os.path.exists(DATA_FILE):
        all_data = pd.DataFrame(columns=columns)
        xls = pd.ExcelFile(DATA_FILE, engine='openpyxl')
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            all_data = pd.concat([all_data, df], ignore_index=True)
        return all_data
    else:
        return pd.DataFrame(columns=columns)

def save_to_driver_sheet(driver, df):
    if os.path.exists(DATA_FILE):
        book = load_workbook(DATA_FILE)
        if driver in book.sheetnames:
            del book[driver]
        book.save(DATA_FILE)

    with pd.ExcelWriter(DATA_FILE, engine='openpyxl', mode='a' if os.path.exists(DATA_FILE) else 'w') as writer:
        df.to_excel(writer, sheet_name=driver, index=False)

def generate_time_options():
    # Generate times from 00:00 to 23:45 in 15-min intervals
    times = []
    current = datetime.strptime("00:00", "%H:%M")
    end = datetime.strptime("23:45", "%H:%M")
    while current <= end:
        times.append(current.strftime("%H:%M"))
        current += timedelta(minutes=15)
    return times

st.title("🚛 Trip Entry Form")

df = load_data()

time_options = generate_time_options()

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

    out_time = col1.selectbox("Out Time", options=time_options)
    in_time = col2.selectbox("In Time", options=time_options)

    out_km = col3.number_input("Out KM", 0)
    in_km = col1.number_input("In KM", 0)
    diff_km = in_km - out_km if in_km >= out_km else 0

    submitted = st.form_submit_button("Submit")

    if submitted:
        # No need to validate time format because dropdown guarantees correct format
        driver_df = df[df["Driver"] == selected_driver].copy()
        new_row = [
            len(driver_df) + 1,
            selected_driver,
            disp_date,
            inv_no,
            customer,
            destination,
            inv_date,
            vehicle,
            out_time,
            in_time,
            out_km,
            in_km,
            diff_km
        ]
        new_entry = pd.DataFrame([new_row], columns=columns)
        driver_df = pd.concat([driver_df, new_entry], ignore_index=True)
        save_to_driver_sheet(selected_driver, driver_df)
        st.success(f"✅ Trip added for {selected_driver}")
        df = load_data()

st.subheader("📋 View Trips")
driver_filter = st.selectbox("Select Driver to View", drivers)
filtered_df = df[df["Driver"] == driver_filter]

if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)

    delete_index = st.number_input("Enter S.No. to Delete", min_value=1, step=1)
    if st.button("🗑 Delete Trip"):
        filtered_df = filtered_df[filtered_df["S.No."] != delete_index]
        filtered_df.reset_index(drop=True, inplace=True)
        filtered_df["S.No."] = range(1, len(filtered_df) + 1)
        save_to_driver_sheet(driver_filter, filtered_df)
        st.success(f"🗑 Trip deleted from {driver_filter}'s sheet.")
        df = load_data()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for drv in drivers:
            temp_df = df[df["Driver"] == drv]
            if not temp_df.empty:
                temp_df.to_excel(writer, sheet_name=drv, index=False)
    buffer.seek(0)
    st.download_button("⬇️ Download All Trip Data", data=buffer, file_name="trip_data.xlsx")
else:
    st.info("No records found for this driver.")

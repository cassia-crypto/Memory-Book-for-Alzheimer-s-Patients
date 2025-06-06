import streamlit as st
import os
import face_recognition
import cv2
import numpy as np
import pickle
from PIL import Image
import uuid
from datetime import datetime

st.set_page_config(page_title="Memory Book", layout="centered")

def load_css(css_file):
    try:
        with open(css_file, encoding='utf-8') as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Failed to load CSS file: {e}")

# Theme toggle in sidebar
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
toggle = st.sidebar.checkbox("🌗 Dark Mode", value=st.session_state.dark_mode)
st.session_state.dark_mode = toggle
mode_text = "🌙 Dark Mode" if st.session_state.dark_mode else "☀️ Light Mode"
st.sidebar.markdown(f"**Current Theme:** {mode_text}")
css_file = "dark.css" if st.session_state.dark_mode else "light.css"
load_css(css_file)

st.markdown("""
    <h1 style="margin-bottom: 0;">AI Memory Book</h1>
    <h6 style="margin-top: 0; font-weight: normal; color: gray;">
        Memory Book for Alzheimer's Patients
    </h6>
""", unsafe_allow_html=True)

# Sidebar settings
st.sidebar.header("⚙️ Detection Settings")
model_choice = st.sidebar.radio("Face Detection Model:", ["Fast (hog)", "Accurate (cnn)"])
resize_factor = st.sidebar.slider("Resize image for processing", 0.25, 1.0, 0.5, step=0.05)

# Page navigation in sidebar
page = st.sidebar.radio("Navigate:", ["Home", "Memory Book", "Historical Photos"])

# Setup directories and memory book
HISTORY_DIR = "history_photos"
os.makedirs(HISTORY_DIR, exist_ok=True)

def load_memory_book():
    try:
        with open("memory_book.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return []

def save_memory_book(book):
    with open("memory_book.pkl", "wb") as f:
        pickle.dump(book, f)

memory_book = load_memory_book()
known_encodings = [entry["encoding"] for entry in memory_book]
known_names = [entry["name"] for entry in memory_book]

if page == "Home":
    # Centered file uploader on main page
    uploaded_file = st.file_uploader("📷 Upload a Family Photo", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        img_array = np.array(image)

        # Resize image
        small_img = cv2.resize(img_array, (0, 0), fx=resize_factor, fy=resize_factor)

        # Detect faces
        model_used = "hog"
        face_locations = face_recognition.face_locations(small_img, model=model_used)
        face_encodings = face_recognition.face_encodings(small_img, face_locations)

        st.write(f"✅ Detected {len(face_encodings)} face(s) using **{model_used}** model.")

        new_entries = []
        for i, (face_encoding, face_location) in enumerate(zip(face_encodings, face_locations)):
            name = "Unknown"

            if known_encodings:
                face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if face_distances[best_match_index] < 0.5:
                    name = known_names[best_match_index]

            col1, col2 = st.columns([2, 3])
            with col1:
                st.write(f"👤 Detected Name: **{name}**")
            with col2:
                wrong_name = st.checkbox("Is this incorrect?", key=f"wrong_{i}")

            if wrong_name or name == "Unknown":
                correct_name = st.text_input("✏️ Enter correct name:", key=f"correct_{i}")
                if correct_name:
                    name = correct_name
                    new_entries.append({
                        "encoding": face_encoding,
                        "name": name,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

            top, right, bottom, left = [int(v / resize_factor) for v in face_location]
            cv2.rectangle(img_array, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(img_array, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Save new entries
        for new_entry in new_entries:
            is_duplicate = any(
                face_recognition.compare_faces([e["encoding"]], new_entry["encoding"], tolerance=0.4)[0]
                for e in memory_book
            )
            if not is_duplicate:
                memory_book.append(new_entry)
                st.success(f"✅ Added '{new_entry['name']}' to Memory Book.")
            else:
                st.warning(f"⚠️ '{new_entry['name']}' already exists in Memory Book.")

        save_memory_book(memory_book)

        # Save and show annotated photo
        history_path = os.path.join(HISTORY_DIR, f"{uuid.uuid4().hex}.jpg")
        cv2.imwrite(history_path, cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
        st.image(img_array, caption="📸 Annotated Image", channels="RGB")

elif page == "Memory Book":
    st.header("📖 View and Edit Memory Book")

    if memory_book:
        for idx, entry in enumerate(memory_book):
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                st.write(f"👤 Name: **{entry['name']}**")
                if "timestamp" in entry:
                    st.caption(f"🕓 Added on: {entry['timestamp']}")
            with col2:
                new_name = st.text_input("Update name:", value=entry['name'], key=f"edit_{idx}")
            with col3:
                if st.button("🗑️ Delete", key=f"delete_{idx}"):
                    memory_book.pop(idx)
                    save_memory_book(memory_book)
                    st.rerun()

            if new_name != entry['name']:
                memory_book[idx]["name"] = new_name
                save_memory_book(memory_book)
                st.success(f"✅ Updated name to '{new_name}'")
    else:
        st.info("Memory Book is empty.")

elif page == "Historical Photos":
    st.header("🖼️ Historical Annotated Photos")

    photo_files = sorted(os.listdir(HISTORY_DIR), reverse=True)
    if photo_files:
        for photo_file in photo_files:
            st.image(os.path.join(HISTORY_DIR, photo_file), use_column_width=True)
    else:
        st.info("No historical photos yet.")

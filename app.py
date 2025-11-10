import streamlit as st
import pandas as pd
import json
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === Konfiguracja strony ===
st.set_page_config(page_title="Zawody wędkarskie", layout="wide", page_icon="🎣")

# === Stałe ===
DATA_FILE = "zawody_data.json"
FONT_FILE = "DejaVuSans.ttf"

# === Czcionka PDF ===
if os.path.exists(FONT_FILE):
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', FONT_FILE))
        FONT_AVAILABLE = True
    except Exception as e:
        FONT_AVAILABLE = False
        print("Nie udało się zarejestrować czcionki:", e)
else:
    FONT_AVAILABLE = False

# === Funkcje pomocnicze ===
def zapisz_dane(S):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(S, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Błąd zapisu danych: {e}")

def wczytaj_dane():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def reset_zawody():
    st.session_state["S"] = {
        "nazwa_zawodow": "",
        "liczba_zawodnikow": 0,
        "liczba_stanowisk": 0,
        "liczba_sektorow": 0,
        "sektory": {},
        "zawodnicy": [],
    }
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except Exception as e:
            st.warning(f"Nie udało się usunąć pliku danych: {e}")

def parse_positions(input_str):
    if not input_str or not input_str.strip():
        return []
    parts = [p.strip() for p in input_str.split(',') if p.strip()]
    positions = []
    for p in parts:
        if '-' in p:
            bounds = p.split('-')
            if len(bounds) != 2:
                raise ValueError(f"Niepoprawny zakres: '{p}'")
            start, end = bounds
            if not (start.strip().isdigit() and end.strip().isdigit()):
                raise ValueError(f"Zakres musi zawierać liczby: '{p}'")
            a, b = int(start), int(end)
            if a > b:
                raise ValueError(f"Początek większy niż koniec: '{p}'")
            positions.extend(range(a, b + 1))
        else:
            if not p.isdigit():
                raise ValueError(f"Niepoprawny numer: '{p}'")
            positions.append(int(p))
    return sorted(set(positions))

def parse_big_fish_sum(input_str):
    if not input_str or not str(input_str).strip():
        return 0, []
    parts = [p.strip() for p in str(input_str).split(',') if p.strip()]
    total, invalid = 0, []
    for p in parts:
        if p.isdigit():
            total += int(p)
        else:
            invalid.append(p)
    return total, invalid

def generuj_pdf_reportlab(df_sorted, nazwa_zawodow=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    if FONT_AVAILABLE:
        for name in ['Heading1', 'Heading2', 'Normal']:
            styles[name].fontName = 'DejaVu'

    if nazwa_zawodow:
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", styles['Heading1']))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("📊 Ranking końcowy", styles['Heading2']))
    elements.append(Spacer(1, 8))

    data = [["Miejsce", "Imię", "Sektor", "Stanowisko", "Waga (g)", "Miejsce w sektorze"]]
    for _, row in df_sorted.iterrows():
        data.append([
            int(row['miejsce_ogolne']),
            row['imie'],
            row['sektor'],
            row['stanowisko'],
            row.get('waga', 0),
            int(row['miejsce_w_sektorze'])
        ])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("📌 Podsumowanie sektorów", styles['Heading2']))
    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading3']))
        data = [["Imię", "Stanowisko", "Waga (g)", "Miejsce w sektorze", "Miejsce ogólne"]]
        for _, row in grupa.iterrows():
            data.append([
                row['imie'],
                row['stanowisko'],
                row.get('waga', 0),
                int(row['miejsce_w_sektorze']),
                int(row['miejsce_ogolne'])
            ])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# === Inicjalizacja danych ===
if "S" not in st.session_state:
    dane = wczytaj_dane()
    st.session_state["S"] = dane if dane else {
        "nazwa_zawodow": "",
        "liczba_zawodnikow": 0,
        "liczba_stanowisk": 0,
        "liczba_sektorow": 0,
        "sektory": {},
        "zawodnicy": []
    }

S = st.session_state["S"]

# === Sidebar ===
st.sidebar.title("🧭 Nawigacja")
page = st.sidebar.radio(
    "Wybierz etap:",
    ["⚙️ Konfiguracja", "📍 Sektory", "👥 Zawodnicy", "🏁 Wyniki i PDF"]
)

st.sidebar.divider()
st.sidebar.button("🧹 Resetuj zawody", on_click=reset_zawody)

# === Główna zawartość ===
st.markdown("<h1 style='text-align:center'>🎣🏆 Panel organizatora zawodów 🏆🎣</h1>", unsafe_allow_html=True)

# === 1️⃣ KONFIGURACJA ===
if page.startswith("⚙️"):
    st.subheader("⚙️ Ustawienia zawodów")
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow", ""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 200, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk:", 1, 1000, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 50, S["liczba_sektorow"] or 3)
    if st.button("💾 Zapisz ustawienia"):
        zapisz_dane(S)
        st.toast("Dane zapisane!")

# === 2️⃣ SEKTORY ===
elif page.startswith("📍"):
    st.subheader("📍 Definicja sektorów")
    st.markdown("_Wpisz stanowiska w formacie np. `1-5,7,10-12`_")

    sektory_tmp = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        current = S["sektory"].get(nazwa, [])
        default = ",".join(map(str, current)) if current else ""
        sektory_tmp[nazwa] = st.text_input(f"Sektor {nazwa}:", value=default)

    if st.button("💾 Zapisz sektory"):
        parsed, all_pos = {}, []
        try:
            for nazwa, tekst in sektory_tmp.items():
                parsed[nazwa] = parse_positions(tekst)
                all_pos.extend(parsed[nazwa])
            if len(all_pos) != len(set(all_pos)):
                raise ValueError("Duplikaty stanowisk między sektorami.")
            S["sektory"] = parsed
            zapisz_dane(S)
            st.success("Sektory zapisane!")
        except Exception as e:
            st.error(str(e))

# === 3️⃣ ZAWODNICY ===
elif page.startswith("👥"):
    st.subheader("👥 Lista zawodników")
    wszystkie_stanowiska = sorted(sum(S["sektory"].values(), [])) if S["sektory"] else []
    if not wszystkie_stanowiska:
        st.warning("Najpierw zdefiniuj sektory.")
    else:
        df = pd.DataFrame(S["zawodnicy"]) if S["zawodnicy"] else pd.DataFrame(columns=["imie","stanowisko","sektor","waga","big_fish_raw"])
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "imie": "Imię i nazwisko",
                "stanowisko": st.column_config.NumberColumn("Stanowisko"),
                "sektor": "Sektor",
                "waga": st.column_config.NumberColumn("Waga (g)", min_value=0, step=10),
                "big_fish_raw": "Big fish (g)",
            }
        )
        S["zawodnicy"] = edited.to_dict("records")
        zapisz_dane(S)
        st.toast("Lista zawodników zapisana!")

# === 4️⃣ WYNIKI ===
elif page.startswith("🏁"):
    st.subheader("🏁 Wyniki końcowe i eksport PDF")
    if not S["zawodnicy"]:
        st.warning("Brak zawodników do wyświetlenia.")
    else:
        df = pd.DataFrame(S["zawodnicy"]).copy()
        df["waga"] = df["waga"].fillna(0)
        df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
        df_sorted = df.sort_values(["miejsce_w_sektorze","waga"], ascending=[True, False])
        df_sorted["miejsce_ogolne"] = range(1, len(df_sorted)+1)

        st.dataframe(df_sorted[["miejsce_ogolne","imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

        pdf_bytes = generuj_pdf_reportlab(df_sorted, S.get("nazwa_zawodow",""))
        st.download_button(
            label="💾 Pobierz PDF",
            data=pdf_bytes,
            file_name="wyniki_zawodow.pdf",
            mime="application/pdf"
        )

st.markdown("<p style='text-align:center; font-size:13px'>© Wojciech Mierzejewski 2026</p>", unsafe_allow_html=True)

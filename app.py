import streamlit as st
import pandas as pd
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# --- Rejestracja czcionki obsługującej polskie znaki ---
pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))

# --- Ścieżka do pliku przechowującego dane ---
DATA_FILE = "zawody_data.json"

# ---------------------------------------------------------
# ✅ Funkcja obsługująca zakresy stanowisk typu:
#    1-5, 1,2,3, 1-3,7,10-12
# ---------------------------------------------------------
def parse_stanowiska(text):
    stanowiska = []
    parts = text.split(",")

    for p in parts:
        p = p.strip()
        if "-" in p:
            try:
                start, end = p.split("-")
                start, end = int(start), int(end)
                if start <= end:
                    stanowiska.extend(range(start, end + 1))
            except:
                pass
        elif p.isdigit():
            stanowiska.append(int(p))

    return stanowiska


# --- Funkcje pomocnicze ---
def zapisz_dane(S):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=2)

def wczytaj_dane():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
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
        "etap": 1
    }
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)


# ---------------------------------------------------------
# ✅ Funkcja generowania PDF
# ---------------------------------------------------------
def generuj_pdf_reportlab(df_sorted, nazwa_zawodow=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    if nazwa_zawodow:
        header_style = styles['Heading1']
        header_style.fontName = 'DejaVu'
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", header_style))
        elements.append(Spacer(1, 15))

    heading_style = styles['Heading2']
    heading_style.fontName = 'DejaVu'
    elements.append(Paragraph("📊 Ranking końcowy (wszyscy zawodnicy)", heading_style))
    elements.append(Spacer(1, 10))

    data = [["Miejsce", "Imię", "Sektor", "Stanowisko", "Waga", "Miejsce w sektorze"]]
    for _, row in df_sorted.iterrows():
        data.append([
            int(row['miejsce_ogolne']),
            row['imie'],
            row['sektor'],
            row['stanowisko'],
            row['waga'],
            int(row['miejsce_w_sektorze'])
        ])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'DejaVu'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("📌 Podsumowanie sektorów", heading_style))
    elements.append(Spacer(1, 10))

    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading3']))
        data = [["Imię", "Stanowisko", "Waga", "Miejsce w sektorze", "Miejsce ogólne"]]

        for _, row in grupa.sort_values(by="waga", ascending=False).iterrows():
            data.append([
                row['imie'],
                row['stanowisko'],
                row['waga'],
                int(row['miejsce_w_sektorze']),
                int(row['miejsce_ogolne'])
            ])

        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,0), (-1,-1), 'DejaVu'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ================================
# ✅ INICJALIZACJA
# ================================
if "S" not in st.session_state:
    dane = wczytaj_dane()
    if dane:
        st.session_state["S"] = dane
    else:
        reset_zawody()

S = st.session_state["S"]

st.set_page_config(page_title="Zawody wędkarskie", layout="wide")
st.markdown("<h1 style='font-size:28px; text-align:center'>🎣🏆 Panel organizatora zawodów wędkarskich 🏆🎣</h1>", unsafe_allow_html=True)
st.markdown("<h1 style='font-size:14px; text-align:center'>© Wojciech Mierzejewski 2026</h1>", unsafe_allow_html=True)

st.button("🧹 Resetuj zawody", on_click=reset_zawody)

# ================================
# ✅ ETAP 1 — Ustawienia
# ================================
if S["etap"] == 1:

    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow", ""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 40, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 100, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 10, S["liczba_sektorow"] or 3)

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_dane(S)

# ================================
# ✅ ETAP 2 — DEFINICJA SEKTORÓW
# ================================
elif S["etap"] == 2:

    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)

    sektory = {}
    zajete_stanowiska = set()   # ✅ walidacja

    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        default_val = ",".join(str(x) for x in S["sektory"].get(nazwa, []))

        pola = st.text_input(
            f"Sektor {nazwa} – podaj stanowiska (np. 1-5 lub 1-3,7,10-12):",
            value=default_val,
            key=f"sektor_{nazwa}"
        )

        if pola.strip():
            wynik = parse_stanowiska(pola)

            # ✅ Walidacja nakładających się stanowisk
            kolizje = [x for x in wynik if x in zajete_stanowiska]
            if kolizje:
                st.error(f"🚫 Te stanowiska nakładają się z innym sektorem: {kolizje}")
            else:
                sektory[nazwa] = wynik
                zajete_stanowiska.update(wynik)

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("💾 Zapisz sektory"):
            if len(sektory) != S["liczba_sektorow"]:
                st.error("❌ Nie wszystkie sektory mają poprawne stanowiska!")
            else:
                S["sektory"] = sektory
                S["etap"] = 3
                zapisz_dane(S)
    with col2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1
            zapisz_dane(S)

# ================================
# ✅ ETAP 3 — Zawodnicy
# ================================
elif S["etap"] == 3:

    st.markdown("<h3 style='font-size:20px'>👤 Krok 3: Dodawanie zawodników</h3>", unsafe_allow_html=True)

    for nazwa, stanowiska in S["sektory"].items():
        st.write(f"**Sektor {nazwa}:** {stanowiska}")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("✏️ Edytuj sektory"):
            S["etap"] = 2
            zapisz_dane(S)
    with col2:
        if st.button("➡️ Przejdź do wprowadzenia wyników"):
            if len(S["zawodnicy"]) == 0:
                st.warning("⚠️ Najpierw dodaj zawodników.")
            else:
                S["etap"] = 4
                zapisz_dane(S)

    wszystkie_dozwolone = sorted(sum(S["sektory"].values(), []))
    zajete = [z["stanowisko"] for z in S["zawodnicy"]]
    dostepne = [s for s in wszystkie_dozwolone if s not in zajete]

    if dostepne:
        col1, col2 = st.columns([2,1])
        with col1:
            imie = st.text_input("Imię i nazwisko zawodnika:", key="new_name")
        with col2:
            stano = st.selectbox("Stanowisko", dostepne, key="new_stanowisko")

        if st.button("➕ Dodaj zawodnika"):
            if not imie.strip():
                st.warning("Podaj imię i nazwisko.")
            else:
                sek = next((k for k, v in S["sektory"].items() if stano in v), None)
                S["zawodnicy"].append(
                    {"imie": imie.strip(), "stanowisko": stano, "sektor": sek, "waga": 0}
                )
                zapisz_dane(S)

    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")
        for i, z in enumerate(S["zawodnicy"]):
            col1, col2, col3 = st.columns([2,1,1])

            with col1:
                z["imie"] = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
                z["waga"] = st.number_input("Waga (g)", 0, 1000000, z["waga"], step=10, key=f"waga_{i}")

            with col2:
                wszystkie_dozwolone = sorted(sum(S["sektory"].values(), []))
                zajete = [x["stanowisko"] for j,x in enumerate(S["zawodnicy"]) if j!=i]
                dostepne = [s for s in wszystkie_dozwolone if s not in zajete or s==z["stanowisko"]]

                if z["stanowisko"] not in dostepne:
                    dostepne.append(z["stanowisko"])
                dostepne = sorted(set(dostepne))

                try:
                    idx = dostepne.index(z["stanowisko"])
                except ValueError:
                    idx = 0

                z["stanowisko"] = st.selectbox("Stan.", dostepne, index=idx, key=f"stan_{i}")

            with col3:
                st.write(f"**Sektor {z['sektor']}**")

            if st.button("🗑️ Usuń", key=f"del_{i}"):
                del S["zawodnicy"][i]
                zapisz_dane(S)
                st.experimental_rerun()

# ================================
# ✅ ETAP 4 — Wyniki
# ================================
elif S["etap"] == 4:

    st.markdown("<h3 style='font-size:20px'>⚖️ Krok 4: Wprowadzenie wyników (waga ryb)</h3>", unsafe_allow_html=True)

    if not S["zawodnicy"]:
        st.warning("Brak zawodników. Wróć i dodaj ich najpierw.")
        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
            zapisz_dane(S)

    else:
        for i,z in enumerate(S["zawodnicy"]):
            st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            z["waga"] = st.number_input("Waga (g)", 0, 1000000, z["waga"], step=10, key=f"waga_{i}")
        zapisz_dane(S)

        df = pd.DataFrame(S["zawodnicy"])
        df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")

        df_sorted = pd.DataFrame()
        for miejsce in sorted(df["miejsce_w_sektorze"].unique()):
            grupa = df[df["miejsce_w_sektorze"] == miejsce].sort_values(by="waga", ascending=False)
            df_sorted = pd.concat([df_sorted, grupa])

        df_sorted["miejsce_ogolne"] = range(1, len(df_sorted)+1)

        st.markdown("<h4 style='font-size:18px'>📊 Ranking końcowy (wszyscy zawodnicy)</h4>", unsafe_allow_html=True)
        st.dataframe(df_sorted[["miejsce_ogolne","imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

        st.markdown("<h4 style='font-size:18px'>📌 Podsumowanie sektorów</h4>", unsafe_allow_html=True)
        for sektor, grupa in df_sorted.groupby("sektor"):
            st.write(f"**Sektor {sektor}**")
            tabela = grupa.sort_values(by="waga", ascending=False)[["imie","stanowisko","waga","miejsce_w_sektorze","miejsce_ogolne"]]
            st.dataframe(tabela, hide_index=True)

        pdf_bytes = generuj_pdf_reportlab(df_sorted, S.get("nazwa_zawodow", ""))
        st.download_button(
            label="💾 Pobierz wyniki jako PDF",
            data=pdf_bytes,
            file_name="wyniki_zawodow.pdf",
            mime="application/pdf"
        )


st.markdown("<h1 style='font-size:14px; text-align:center'>© Wojciech Mierzejewski 2026</h1>", unsafe_allow_html=True)

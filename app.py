import streamlit as st
import pandas as pd
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# --- Ścieżka do pliku przechowującego dane ---
DATA_FILE = "zawody_data.json"
FONT_FILE = "DejaVuSans.ttf"  # Dołącz do projektu lub pobierz z internetu

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

def generuj_pdf_reportlab(df_sorted, nazwa_zawodow=""):
    # Rejestracja czcionki obsługującej polskie znaki
    pdfmetrics.registerFont(TTFont('DejaVu', FONT_FILE))
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    styles['Heading1'].fontName = 'DejaVu'
    styles['Heading2'].fontName = 'DejaVu'
    styles['Heading3'].fontName = 'DejaVu'
    styles['Normal'].fontName = 'DejaVu'

    # --- Nagłówek ---
    if nazwa_zawodow:
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", styles['Heading1']))
        elements.append(Spacer(1, 15))

    # --- Ranking ogólny ---
    elements.append(Paragraph("📊 Ranking końcowy (wszyscy zawodnicy)", styles['Heading2']))
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

    # --- Podsumowanie sektorów ---
    elements.append(Paragraph("📌 Podsumowanie sektorów", styles['Heading2']))
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

# --- Inicjalizacja stanu ---
if "S" not in st.session_state:
    dane = wczytaj_dane()
    if dane:
        st.session_state["S"] = dane
    else:
        st.session_state["S"] = {
            "nazwa_zawodow": "",
            "liczba_zawodnikow": 0,
            "liczba_stanowisk": 0,
            "liczba_sektorow": 0,
            "sektory": {},
            "zawodnicy": [],
            "etap": 1
        }

S = st.session_state["S"]
st.set_page_config(page_title="Zawody wędkarskie", layout="wide")
st.markdown("<h1 style='font-size:28px'>🎣 Panel organizatora zawodów wędkarskich by Wojtek Mierzejewski</h1>", unsafe_allow_html=True)

# --- Reset ---
st.button("🧹 Resetuj zawody", on_click=reset_zawody)

# --- ETAPY ---
if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow", ""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 40, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 100, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 10, S["liczba_sektorow"] or 3)
    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_dane(S)

elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)
    # Informacja o przewidywanej liczbie zawodników na sektor
    base = S["liczba_zawodnikow"] // S["liczba_sektorow"]
    remainder = S["liczba_zawodnikow"] % S["liczba_sektorow"]
    info = []
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        ilosc = base + (1 if i < remainder else 0)
        info.append(f"Sektor {nazwa}: {ilosc} zawodników")
    st.info("ℹ️ Przewidywana liczba zawodników na sektor:\n" + "\n".join(info))
    if remainder != 0:
        st.warning(f"⚠️ Nie wszystkie sektory mają równą liczbę zawodników. Jeden sektor może mieć o 1 zawodnika więcej.")

    sektory = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        pola = st.text_input(f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
                             value=",".join(map(str, S["sektory"].get(nazwa, []))),
                             key=f"sektor_{nazwa}")
        if pola.strip():
            try:
                sektory[nazwa] = [int(x.strip()) for x in pola.split(",") if x.strip().isdigit()]
            except ValueError:
                st.warning(f"⚠️ Błędne dane w sektorze {nazwa}. Użyj tylko liczb i przecinków.")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("💾 Zapisz sektory"):
            wszystkie = []
            for s in sektory.values():
                wszystkie.extend(s)
            duplikaty = [x for x in wszystkie if wszystkie.count(x) > 1]
            if duplikaty:
                st.error(f"Powtórzone stanowiska: {sorted(set(duplikaty))}")
            else:
                S["sektory"] = sektory
                S["etap"] = 3
                zapisz_dane(S)
    with col2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1
            zapisz_dane(S)

# ETAP 3 i 4 pozostają takie same jak w poprzedniej wersji
# w ETAP 4 dodajemy st.download_button z BytesIO
# st.download_button(label="💾 Pobierz wyniki jako PDF", data=pdf_bytes, file_name="wyniki_zawodow.pdf", mime="application/pdf")
# Komunikat dla użytkowników mobilnych można dodać w formie st.info

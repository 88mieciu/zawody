import streamlit as st
import pandas as pd
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

# --- Ścieżka do pliku przechowującego dane ---
DATA_FILE = "zawody_data.json"

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
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # --- Nagłówek z nazwą zawodów ---
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
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))
    for i in range(1, len(data)):
        if i % 2 == 0:
            t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgrey)]))
        if i == 1:  # zwycięzca
            t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgreen),
                                   ('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold')]))
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
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ]))
        for i in range(1, len(data)):
            if i % 2 == 0:
                t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgrey)]))
            if i == 1:  # zwycięzca sektora
                t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgreen),
                                       ('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold')]))
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

# --- PRZYCISK RESET ---
st.button("🧹 Resetuj zawody", on_click=reset_zawody)

# --- ETAPY 1-4 ---
# (Kod wszystkich etapów jest identyczny jak w poprzedniej wersji, w tym logika dodawania zawodników,
#  przeliczania miejsc sektorowych i ogólnych, zapis danych między sesjami)
# Zwróć uwagę, że w etapie 4 przycisk "Pobierz PDF" korzysta teraz z funkcji generującej estetyczny PDF powyżej

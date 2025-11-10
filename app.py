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

# ---------------------------
# --- Konfiguracja plików ---
# ---------------------------
DATA_FILE = "zawody_data.json"
FONT_FILE = "DejaVuSans.ttf"  # umieść plik czcionki w katalogu aplikacji

# Rejestracja czcionki (jeśli dostępna)
if os.path.exists(FONT_FILE):
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', FONT_FILE))
        FONT_AVAILABLE = True
    except Exception as e:
        FONT_AVAILABLE = False
        print("Nie udało się zarejestrować czcionki DejaVu:", e)
else:
    FONT_AVAILABLE = False

# ---------------------------
# --- Utility / helpers ---
# ---------------------------

def zapisz_dane(S):
    """Zapisuje stan S do pliku JSON (bezpiecznie)."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(S, f, ensure_ascii=False, indent=2)
        st.success("Dane zapisane ✅")
    except Exception as e:
        st.error(f"Błąd zapisu danych: {e}")

@st.cache_data
def wczytaj_dane():
    """Wczytuje plik JSON (cache'owane by nie czytać przy każdej interakcji)."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def reset_zawody():
    """Resetuje stan aplikacji i usuwa plik danych (jeśli istnieje)."""
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
        try:
            os.remove(DATA_FILE)
            st.success("Plik z danymi usunięty.")
        except Exception as e:
            st.warning(f"Nie udało się usunąć pliku danych: {e}")

def parse_positions(input_str):
    """
    Parsuje ciąg taki jak "1-5,7,10-12" na listę unikalnych intów: [1,2,3,4,5,7,10,11,12]
    Zwraca listę intów lub rzuca ValueError przy niepoprawnym formacie.
    """
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
            a = int(start.strip())
            b = int(end.strip())
            if a > b:
                raise ValueError(f"W zakresie początek nie może być większy niż koniec: '{p}'")
            positions.extend(list(range(a, b+1)))
        else:
            if not p.isdigit():
                raise ValueError(f"Niepoprawny numer stanowiska: '{p}'")
            positions.append(int(p))
    # unikalne, posortowane
    uniq = sorted(set(positions))
    return uniq

def parse_big_fish_sum(input_str):
    """
    Parsuje ciąg wag oddzielonych przecinkami, np. "500,1200, 350"
    Zwraca tuple (sum_of_valid_weights:int, invalid_parts:list)
    """
    if not input_str or not str(input_str).strip():
        return 0, []
    parts = [p.strip() for p in str(input_str).split(',') if p.strip()]
    total = 0
    invalid = []
    for p in parts:
        # dopuszczamy liczby całkowite dodatnie
        if p.lstrip('+-').isdigit():
            try:
                val = int(p)
                if val < 0:
                    invalid.append(p)
                else:
                    total += val
            except:
                invalid.append(p)
        else:
            invalid.append(p)
    return total, invalid

def generuj_pdf_reportlab(df_sorted, nazwa_zawodow=""):
    """Generuje PDF z reportlab (zwraca BytesIO)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # jeżeli zarejestrowaliśmy czcionkę, ustawiamy jej użycie w stylach
    if FONT_AVAILABLE:
        for name in ['Heading1','Heading2','Heading3','Normal']:
            try:
                styles[name].fontName = 'DejaVu'
            except Exception:
                pass

    # Nagłówek
    if nazwa_zawodow:
        h1 = styles['Heading1']
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", h1))
        elements.append(Spacer(1, 12))

    # Ranking ogólny
    h2 = styles['Heading2']
    elements.append(Paragraph("📊 Ranking końcowy (wszyscy zawodnicy)", h2))
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
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]
    if FONT_AVAILABLE:
        t_style.append(('FONTNAME', (0,0), (-1,-1), 'DejaVu'))
    t.setStyle(TableStyle(t_style))
    elements.append(t)
    elements.append(Spacer(1, 16))

    # Podsumowanie sektorów
    elements.append(Paragraph("📌 Podsumowanie sektorów", h2))
    elements.append(Spacer(1, 8))
    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading3']))
        data = [["Imię", "Stanowisko", "Waga (g)", "Miejsce w sektorze", "Miejsce ogólne"]]
        for _, row in grupa.sort_values(by="waga", ascending=False).iterrows():
            data.append([
                row['imie'],
                row['stanowisko'],
                row.get('waga', 0),
                int(row['miejsce_w_sektorze']),
                i

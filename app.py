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

# --- Ustawienia pliku danych i czcionki ---
DATA_FILE = "zawody_data.json"
FONT_FILE = "DejaVuSans.ttf"  # umieść plik czcionki w katalogu aplikacji

# --- Rejestracja czcionki (jeśli jest dostępna) ---
if os.path.exists(FONT_FILE):
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', FONT_FILE))
        FONT_AVAILABLE = True
    except Exception as e:
        FONT_AVAILABLE = False
        print("Nie udało się zarejestrować czcionki DejaVu:", e)
else:
    FONT_AVAILABLE = False


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
        try:
            os.remove(DATA_FILE)
        except:
            pass


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
    uniq = sorted(set(positions))
    return uniq


def parse_big_fish_sum(input_str):
    if not input_str or not str(input_str).strip():
        return 0, []
    parts = [p.strip() for p in str(input_str).split(',') if p.strip()]
    total = 0
    invalid = []
    for p in parts:
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
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    if FONT_AVAILABLE:
        for name in ['Heading1', 'Heading2', 'Heading3', 'Normal']:
            try:
                styles[name].fontName = 'DejaVu'
            except Exception:
                pass

    if nazwa_zawodow:
        h1 = styles['Heading1']
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", h1))
        elements.append(Spacer(1, 12))

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
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]
    if FONT_AVAILABLE:
        t_style.append(('FONTNAME', (0, 0), (-1, -1), 'DejaVu'))
    t.setStyle(TableStyle(t_style))
    elements.append(t)
    elements.append(Spacer(1, 16))

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
                int(row['miejsce_ogolne'])
            ])
        t = Table(data, repeatRows=1)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]
        if FONT_AVAILABLE:
            t_style.append(('FONTNAME', (0, 0), (-1, -1), 'DejaVu'))
        t.setStyle(TableStyle(t_style))
        elements.append(t)
        elements.append(Spacer(1, 12))

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

# --- Ustawienia strony ---
st.set_page_config(page_title="Zawody wędkarskie", layout="wide")
st.markdown(
    "<h1 style='font-size:28px; text-align:center'>🎣🏆 Panel organizatora zawodów wędkarskich 🏆🎣</h1>",
    unsafe_allow_html=True
)

if not FONT_AVAILABLE:
    st.warning("Aby PDF poprawnie wyświetlał polskie znaki, umieść plik 'DejaVuSans.ttf' w katalogu aplikacji.")

st.button("🧹 Resetuj zawody", on_click=reset_zawody)

# --- ETAP 1: KONFIGURACJA ---
if S["etap"] == 1:
    st.markdown("<h3>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow", ""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 200, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 1000, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 50, S["liczba_sektorow"] or 3)

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_dane(S)

# --- ETAP 2: DEFINICJA SEKTORÓW ---
elif S["etap"] == 2:
    st.markdown("<h3>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)

    # 🔹 podpowiedź o liczbie zawodników na sektor
    if S["liczba_zawodnikow"] > 0 and S["liczba_sektorow"] > 0:
        base = S["liczba_zawodnikow"] // S["liczba_sektorow"]
        remainder = S["liczba_zawodnikow"] % S["liczba_sektorow"]
        info = []
        for i in range(S["liczba_sektorow"]):
            nazwa = chr(65 + i)
            count = base + (1 if i < remainder else 0)
            info.append(f"Sektor {nazwa}: {count} zawodników")
        st.info("ℹ️ Sugerowany podział zawodników na sektory:\n" + "\n".join(info))

    st.markdown("_Wpisz numery stanowisk lub zakresy, np. `1-5,7,10-12`_")

    sektory_tmp = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        current = S["sektory"].get(nazwa, [])
        default = ",".join(map(str, current)) if current else ""
        pola = st.text_input(f"Sektor {nazwa} – stanowiska:", value=default, key=f"sektor_{nazwa}")
        sektory_tmp[nazwa] = pola

        # pokazujemy licznik stanowisk, jeśli da się sparsować
        try:
            count = len(parse_positions(pola))
            if count > 0:
                st.caption(f"➡️ Liczba stanowisk: {count}")
        except ValueError as e:
            st.warning(f"⚠️ {e}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Zapisz sektory"):
            parsed = {}
            all_positions = []
            error = False
            msgs = []
            for nazwa, txt in sektory_tmp.items():
                try:
                    pos = parse_positions(txt)
                except ValueError as e:
                    error = True
                    msgs.append(f"Sektor {nazwa}: {e}")
                    pos = []
                parsed[nazwa] = pos
                all_positions.extend(pos)

            dup = sorted([x for x in set(all_positions) if all_positions.count(x) > 1])
            if dup:
                error = True
                msgs.append(f"Powtórzone stanowiska między sektorami: {dup}")

            if error:
                for m in msgs:
                    st.error(m)
            else:
                S["sektory"] = parsed
                S["etap"] = 3
                zapisz_dane(S)
                st.success("✅ Sektory zapisane.")
    with col2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1
            zapisz_dane(S)

# (reszta etapów 3–4 bez zmian — Twoja logika działała bardzo dobrze)

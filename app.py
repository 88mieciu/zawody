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

# --- Ustawienia plików ---
DATA_FILE = "zawody_data.json"
FONT_FILE = "DejaVuSans.ttf"

# --- Rejestracja czcionki ---
if os.path.exists(FONT_FILE):
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', FONT_FILE))
        FONT_AVAILABLE = True
    except Exception as e:
        FONT_AVAILABLE = False
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
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except:
            pass
    st.session_state["S"] = DEFAULT_STATE.copy()
    zapisz_dane(st.session_state["S"])
    st.rerun()


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
            a, b = bounds
            if not (a.strip().isdigit() and b.strip().isdigit()):
                raise ValueError(f"Zakres musi zawierać liczby: '{p}'")
            a, b = int(a), int(b)
            if a > b:
                raise ValueError(f"W zakresie początek nie może być większy niż koniec: '{p}'")
            positions.extend(list(range(a, b + 1)))
        else:
            if not p.isdigit():
                raise ValueError(f"Niepoprawny numer stanowiska: '{p}'")
            positions.append(int(p))
    return sorted(set(positions))


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
            styles[name].fontName = 'DejaVu'

    if nazwa_zawodow:
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", styles['Heading1']))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("📊 Ranking końcowy (wszyscy zawodnicy)", styles['Heading2']))
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
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]
    if FONT_AVAILABLE:
        style.append(('FONTNAME', (0, 0), (-1, -1), 'DejaVu'))
    t.setStyle(TableStyle(style))
    elements.append(t)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("📌 Podsumowanie sektorów", styles['Heading2']))
    elements.append(Spacer(1, 8))

    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading3']))
        data = [["Imię", "Stanowisko", "Waga (g)", "Miejsce w sektorze", "Miejsce ogólne"]]
        for _, row in grupa.sort_values(by="waga", ascending=False).iterrows():
            data.append([
                row['imie'], row['stanowisko'], row.get('waga', 0),
                int(row['miejsce_w_sektorze']), int(row['miejsce_ogolne'])
            ])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle(style))
        elements.append(t)
        elements.append(Spacer(1, 12))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# --- Inicjalizacja stanu ---
DEFAULT_STATE = {
    "nazwa_zawodow": "",
    "liczba_zawodnikow": 0,
    "liczba_stanowisk": 0,
    "liczba_sektorow": 0,
    "sektory": {},
    "zawodnicy": [],
    "etap": 1
}

if "S" not in st.session_state:
    dane = wczytaj_dane()
    if isinstance(dane, dict):
        for k, v in DEFAULT_STATE.items():
            if k not in dane:
                dane[k] = v
        st.session_state["S"] = dane
    else:
        st.session_state["S"] = DEFAULT_STATE.copy()
S = st.session_state["S"]

# --- Ustawienia strony ---
st.set_page_config(page_title="Zawody wędkarskie", layout="wide")

# --- Sidebar ---
st.sidebar.title("🎣 Nawigacja")
menu = st.sidebar.radio(
    "Wybierz etap:",
    ["⚙️ Ustawienia", "📍 Sektory", "👤 Zawodnicy", "⚖️ Wyniki"]
)

st.sidebar.divider()
st.sidebar.button("🧹 Resetuj zawody", on_click=reset_zawody)

if not FONT_AVAILABLE:
    st.sidebar.warning("Brak czcionki 'DejaVuSans.ttf' — PDF może nie mieć polskich znaków.")

# Synchronizacja etapu
mapa = {
    "⚙️ Ustawienia": 1,
    "📍 Sektory": 2,
    "👤 Zawodnicy": 3,
    "⚖️ Wyniki": 4
}
S["etap"] = mapa[menu]
zapisz_dane(S)

# --- Tytuł główny ---
st.markdown("<h1 style='text-align:center;'>🏆 Panel organizatora zawodów wędkarskich 🎣</h1>", unsafe_allow_html=True)

# --- ETAP 1 ---
if S["etap"] == 1:
    st.header("⚙️ Krok 1: Ustawienia zawodów")
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow", ""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 500, S.get("liczba_zawodnikow", 10))
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 2000, S.get("liczba_stanowisk", 10))
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 50, S.get("liczba_sektorow", 3))
    zapisz_dane(S)

# --- ETAP 2 ---
elif S["etap"] == 2:
    st.header("📍 Krok 2: Definicja sektorów")
    if S["liczba_zawodnikow"] and S["liczba_sektorow"]:
        base = S["liczba_zawodnikow"] // S["liczba_sektorow"]
        rem = S["liczba_zawodnikow"] % S["liczba_sektorow"]
        txt = "\n".join(
            [f"Sektor {chr(65+i)}: {base + (1 if i < rem else 0)} zawodników" for i in range(S["liczba_sektorow"])]
        )
        st.info(f"ℹ️ Przewidywana liczba zawodników na sektor:\n{txt}")

    st.markdown("_Wpisz stanowiska jako zakresy lub numery (np. 1-5,7,10-12)._")

    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        default = ",".join(map(str, S["sektory"].get(nazwa, [])))
        txt = st.text_input(f"Sektor {nazwa} – stanowiska:", value=default, key=f"sektor_{nazwa}")
        try:
            parsed = parse_positions(txt)
            S["sektory"][nazwa] = parsed
            if parsed:
                st.caption(f"➡️ Liczba stanowisk: {len(parsed)}")
        except ValueError as e:
            st.error(str(e))
    zapisz_dane(S)

# --- ETAP 3 ---
elif S["etap"] == 3:
    st.header("👤 Krok 3: Dodawanie zawodników")
    wszystkie = sorted(sum(S["sektory"].values(), []))
    zajete = [z["stanowisko"] for z in S["zawodnicy"]]
    wolne = [x for x in wszystkie if x not in zajete]

    col1, col2 = st.columns([2, 1])
    with col1:
        imie = st.text_input("Imię i nazwisko zawodnika:", key="new_name")
    with col2:
        stanowisko = st.selectbox("Stanowisko:", wolne if wolne else [""], key="new_stanowisko")

    if st.button("➕ Dodaj zawodnika"):
        if imie.strip() and stanowisko:
            sek = next((k for k, v in S["sektory"].items() if stanowisko in v), None)
            S["zawodnicy"].append({"imie": imie.strip(), "stanowisko": stanowisko, "sektor": sek, "waga": 0, "big_fish_raw": ""})
            zapisz_dane(S)
            st.rerun()

    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")
        for i, z in enumerate(S["zawodnicy"]):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                z["imie"] = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
                z["waga"] = st.number_input("Waga główna (g)", 0, 1000000, z.get("waga", 0), step=10, key=f"waga_{i}")
                z["big_fish_raw"] = st.text_input("Big fish (g) — oddzielone przecinkami:", value=z.get("big_fish_raw",""), key=f"bf_{i}")
            with col2:
                wszystkie = sorted(sum(S["sektory"].values(), []))
                zajete = [x["stanowisko"] for j, x in enumerate(S["zawodnicy"]) if j != i]
                dost = [s for s in wszystkie if s not in zajete or s == z["stanowisko"]]
                z["stanowisko"] = st.selectbox("Stan.", dost, index=dost.index(z["stanowisko"]), key=f"stan_{i}")
            with col3:
                st.write(f"**Sektor {z['sektor']}**")
            if st.button("🗑️ Usuń", key=f"del_{i}"):
                del S["zawodnicy"][i]
                zapisz_dane(S)
                st.rerun()
    zapisz_dane(S)

# --- ETAP 4 ---
elif S["etap"] == 4:
    st.header("⚖️ Krok 4: Wprowadzenie wyników")
    if not S["zawodnicy"]:
        st.warning("Brak zawodników.")
    else:
        for i, z in enumerate(S["zawodnicy"]):
            st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            waga = st.number_input("Waga główna (g)", 0, 10000000, z.get("waga", 0), step=10, key=f"waga_bazowa_{i}")
            big_raw = st.text_input("Big fish (g):", value=z.get("big_fish_raw",""), key=f"big_raw_{i}")
            z["big_fish_raw"] = big_raw
            suma, inval = parse_big_fish_sum(big_raw)
            if inval:
                st.warning(f"Nieprawidłowe wartości Big fish dla {z['imie']}: {inval}")
            z["waga"] = waga + suma
        zapisz_dane(S)

        df = pd.DataFrame(S["zawodnicy"]).copy()
        df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
        df_sorted = pd.concat([
            df[df["miejsce_w_sektorze"] == m].sort_values(by="waga", ascending=False)
            for m in sorted(df["miejsce_w_sektorze"].unique())
        ])
        df_sorted["miejsce_ogolne"] = range(1, len(df_sorted) + 1)

        st.subheader("📊 Ranking końcowy")
        st.dataframe(df_sorted[["miejsce_ogolne","imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

        st.subheader("📌 Podsumowanie sektorów")
        for sektor, grupa in df_sorted.groupby("sektor"):
            st.write(f"**Sektor {sektor}**")
            st.dataframe(
                grupa.sort_values(by="waga", ascending=False)[["imie","stanowisko","waga","miejsce_w_sektorze","miejsce_ogolne"]],
                hide_index=True
            )

        pdf_bytes = generuj_pdf_reportlab(df_sorted, S.get("nazwa_zawodow", ""))
        st.download_button("💾 Pobierz wyniki jako PDF", data=pdf_bytes, file_name="wyniki_zawodow.pdf", mime="application/pdf")

st.markdown("<p style='text-align:center; font-size:13px;'>© Wojciech Mierzejewski 2026</p>", unsafe_allow_html=True)

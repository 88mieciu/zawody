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
FONT_FILE = "DejaVuSans.ttf"

# --- Rejestracja czcionki ---
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
    st.session_state["S"] = DEFAULT_STATE.copy()
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except:
            pass


def parse_positions(input_str):
    """Parsuje np. '1-5,7,10-12' → [1,2,3,4,5,7,10,11,12]"""
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
                raise ValueError(f"Początek zakresu nie może być większy niż koniec: '{p}'")
            positions.extend(range(a, b + 1))
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
            val = int(p)
            if val >= 0:
                total += val
            else:
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
        for n in ['Heading1', 'Heading2', 'Heading3', 'Normal']:
            try:
                styles[n].fontName = 'DejaVu'
            except Exception:
                pass

    if nazwa_zawodow:
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", styles['Heading1']))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("📊 Ranking końcowy", styles['Heading2']))
    elements.append(Spacer(1, 8))

    data = [["Miejsce", "Imię", "Sektor", "Stanowisko", "Waga (g)", "Miejsce w sektorze"]]
    for _, r in df_sorted.iterrows():
        data.append([
            int(r['miejsce_ogolne']),
            r['imie'],
            r['sektor'],
            r['stanowisko'],
            r.get('waga', 0),
            int(r['miejsce_w_sektorze'])
        ])

    t = Table(data, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]
    if FONT_AVAILABLE:
        style.append(('FONTNAME', (0, 0), (-1, -1), 'DejaVu'))
    t.setStyle(TableStyle(style))
    elements.append(t)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("📌 Podsumowanie sektorów", styles['Heading2']))
    elements.append(Spacer(1, 8))
    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading3']))
        data = [["Imię", "Stanowisko", "Waga (g)", "Miejsce w sektorze", "Miejsce ogólne"]]
        for _, r in grupa.sort_values(by="waga", ascending=False).iterrows():
            data.append([
                r['imie'],
                r['stanowisko'],
                r.get('waga', 0),
                int(r['miejsce_w_sektorze']),
                int(r['miejsce_ogolne'])
            ])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle(style))
        elements.append(t)
        elements.append(Spacer(1, 12))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# --- Domyślny stan aplikacji ---
DEFAULT_STATE = {
    "nazwa_zawodow": "",
    "liczba_zawodnikow": 0,
    "liczba_stanowisk": 0,
    "liczba_sektorow": 0,
    "sektory": {},
    "zawodnicy": [],
    "etap": 1
}

# --- Inicjalizacja stanu ---
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
st.markdown(
    "<h1 style='font-size:28px; text-align:center'>🎣🏆 Panel organizatora zawodów wędkarskich 🏆🎣</h1>",
    unsafe_allow_html=True
)

if not FONT_AVAILABLE:
    st.warning("Aby PDF poprawnie wyświetlał polskie znaki, umieść plik 'DejaVuSans.ttf' w katalogu aplikacji.")

st.button("🧹 Resetuj zawody", on_click=reset_zawody)

# --- ETAP 1 ---
if S["etap"] == 1:
    st.markdown("<h3>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow", ""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 200, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk:", 1, 1000, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 50, S["liczba_sektorow"] or 3)
    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_dane(S)

# --- ETAP 2 ---
elif S["etap"] == 2:
    st.markdown("<h3>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)
    if S["liczba_zawodnikow"] > 0 and S["liczba_sektorow"] > 0:
        base = S["liczba_zawodnikow"] // S["liczba_sektorow"]
        rem = S["liczba_zawodnikow"] % S["liczba_sektorow"]
        info = [f"Sektor {chr(65+i)}: {base + (1 if i < rem else 0)} zawodników" for i in range(S["liczba_sektorow"])]
        st.info("ℹ️ Sugerowany podział zawodników:\n" + "\n".join(info))
    st.markdown("_Wpisz stanowiska lub zakresy, np. `1-5,7,10-12`_")

    sektory_tmp = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        current = S["sektory"].get(nazwa, [])
        default = ",".join(map(str, current)) if current else ""
        pola = st.text_input(f"Sektor {nazwa} – stanowiska:", default, key=f"sektor_{nazwa}")
        sektory_tmp[nazwa] = pola
        try:
            cnt = len(parse_positions(pola))
            if cnt > 0:
                st.caption(f"➡️ Liczba stanowisk: {cnt}")
        except ValueError as e:
            st.warning(f"⚠️ {e}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Zapisz sektory"):
            parsed, all_pos, errors = {}, [], []
            for nazwa, txt in sektory_tmp.items():
                try:
                    pos = parse_positions(txt)
                    parsed[nazwa] = pos
                    all_pos += pos
                except ValueError as e:
                    errors.append(f"Sektor {nazwa}: {e}")
            dup = [x for x in set(all_pos) if all_pos.count(x) > 1]
            if dup:
                errors.append(f"Powtórzone stanowiska: {dup}")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                S["sektory"] = parsed
                S["etap"] = 3
                zapisz_dane(S)
                st.success("✅ Sektory zapisane.")
    with c2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1
            zapisz_dane(S)

# --- ETAP 3 ---
elif S["etap"] == 3:
    st.markdown("<h3>👤 Krok 3: Dodawanie zawodników</h3>", unsafe_allow_html=True)
    for nazwa, stanowiska in S["sektory"].items():
        st.write(f"**Sektor {nazwa}:** {stanowiska}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ Edytuj sektory"):
            S["etap"] = 2
            zapisz_dane(S)
    with col2:
        if st.button("➡️ Przejdź do wyników"):
            if not S["zawodnicy"]:
                st.warning("⚠️ Dodaj zawodników.")
            else:
                S["etap"] = 4
                zapisz_dane(S)

    all_positions = sorted(sum(S["sektory"].values(), []))
    zajete = [z["stanowisko"] for z in S["zawodnicy"]]
    dostepne = [p for p in all_positions if p not in zajete]

    if dostepne:
        imie = st.text_input("Imię i nazwisko zawodnika:")
        stano = st.selectbox("Stanowisko:", dostepne)
        if st.button("➕ Dodaj zawodnika"):
            if not imie.strip():
                st.warning("Podaj imię i nazwisko.")
            else:
                sek = next((k for k, v in S["sektory"].items() if stano in v), None)
                S["zawodnicy"].append({"imie": imie.strip(), "stanowisko": stano, "sektor": sek, "waga": 0, "big_fish_raw": ""})
                zapisz_dane(S)
                st.experimental_rerun()

    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")
        for i, z in enumerate(S["zawodnicy"]):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                z["imie"] = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
                z["waga"] = st.number_input("Waga (g)", 0, 1_000_000, z.get("waga", 0), step=10, key=f"waga_{i}")
                z["big_fish_raw"] = st.text_input("Big fish (g) – np. 500,1200:", z.get("big_fish_raw",""), key=f"bf_{i}")
            with c2:
                wszystkie = sorted(sum(S["sektory"].values(), []))
                zajete = [x["stanowisko"] for j,x in enumerate(S["zawodnicy"]) if j!=i]
                dostepne = [s for s in wszystkie if s not in zajete or s==z["stanowisko"]]
                if z["stanowisko"] not in dostepne:
                    dostepne.append(z["stanowisko"])
                idx = dostepne.index(z["stanowisko"]) if z["stanowisko"] in dostepne else 0
                z["stanowisko"] = st.selectbox("Stan.", dostepne, index=idx, key=f"stan_{i}")
            with c3:
                st.write(f"**Sektor {z['sektor']}**")
            if st.button("🗑️ Usuń", key=f"del_{i}"):
                del S["zawodnicy"][i]
                zapisz_dane(S)
                st.experimental_rerun()
        zapisz_dane(S)

# --- ETAP 4 ---
elif S["etap"] == 4:
    st.markdown("<h3>⚖️ Krok 4: Wprowadzenie wyników</h3>", unsafe_allow_html=True)
    if not S["zawodnicy"]:
        st.warning("Brak zawodników.")
        if st.button("⬅️ Wróć"):
            S["etap"] = 3
            zapisz_dane(S)
    else:
        for i, z in enumerate(S["zawodnicy"]):
            st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            waga_bazowa = st.number_input("Waga główna (g):", 0, 10_000_000, z.get("waga", 0), key=f"wb_{i}")
            big_raw = st.text_input("Big fish (g) – np. 500,1200:", z.get("big_fish_raw",""), key=f"br_{i}")
            z["big_fish_raw"] = big_raw
            big_sum, invalid = parse_big_fish_sum(big_raw)
            if invalid:
                st.warning(f"Nieprawidłowe wartości: {invalid}")
            z["waga"] = waga_bazowa + big_sum
        zapisz_dane(S)

        df = pd.DataFrame(S["zawodnicy"]).copy()
        df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
        df_sorted = df.sort_values(by=["miejsce_w_sektorze","waga"], ascending=[True,False]).reset_index(drop=True)
        df_sorted["miejsce_ogolne"] = range(1, len(df_sorted)+1)

        st.markdown("<h4>📊 Ranking końcowy</h4>", unsafe_allow_html=True)
        st.dataframe(df_sorted[["miejsce_ogolne","imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

        st.markdown("<h4>📌 Podsumowanie sektorów</h4>", unsafe_allow_html=True)
        for sektor, grupa in df_sorted.groupby("sektor"):
            st.write(f"**Sektor {sektor}**")
            st.dataframe(grupa[["imie","stanowisko","waga","miejsce_w_sektorze","miejsce_ogolne"]], hide_index=True)

        pdf = generuj_pdf_reportlab(df_sorted, S.get("nazwa_zawodow", ""))
        st.download_button("💾 Pobierz PDF", pdf, "wyniki_zawodow.pdf", "application/pdf")

# --- Stopka ---
st.markdown("<p style='text-align:center;font-size:14px;'>© Wojciech Mierzejewski 2026</p>", unsafe_allow_html=True)

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

# =========================
# === Konfiguracja app ====
# =========================
st.set_page_config(page_title="Zawody wędkarskie", layout="wide", page_icon="🎣")

DATA_FILE = "zawody_data.json"
FONT_FILE = "DejaVuSans.ttf"  # opcjonalna czcionka do PDF (polskie znaki)

# Rejestracja czcionki do PDF (jeśli dostępna)
if os.path.exists(FONT_FILE):
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', FONT_FILE))
        FONT_AVAILABLE = True
    except Exception as e:
        FONT_AVAILABLE = False
        print("Nie udało się zarejestrować czcionki DejaVu:", e)
else:
    FONT_AVAILABLE = False

# =========================
# === Funkcje pomocnicze ==
# =========================
def zapisz_dane(S):
    """Zapisuje stan do pliku JSON (bezpiecznie)."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(S, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Błąd zapisu danych: {e}")

def wczytaj_dane():
    """Wczytuje plik JSON, zwraca dict lub None."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def reset_zawody():
    """Resetuje stan i usuwa plik danych (jeśli istnieje)."""
    st.session_state["S"] = DEFAULT_STATE.copy()
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except Exception:
            pass
    st.experimental_rerun()

def parse_positions(input_str):
    """
    Parsuje "1-5,7,10-12" -> [1,2,3,4,5,7,10,11,12]
    Zwraca listę unikalnych, posortowanych intów lub rzuca ValueError.
    """
    if not input_str or not str(input_str).strip():
        return []
    parts = [p.strip() for p in str(input_str).split(',') if p.strip()]
    positions = []
    for p in parts:
        if '-' in p:
            bounds = p.split('-')
            if len(bounds) != 2:
                raise ValueError(f"Niepoprawny zakres: '{p}'")
            a_s, b_s = bounds
            if not (a_s.strip().isdigit() and b_s.strip().isdigit()):
                raise ValueError(f"Zakres musi zawierać liczby: '{p}'")
            a = int(a_s.strip()); b = int(b_s.strip())
            if a > b:
                raise ValueError(f"W zakresie początek nie może być większy niż koniec: '{p}'")
            positions.extend(range(a, b+1))
        else:
            if not p.isdigit():
                raise ValueError(f"Niepoprawny numer stanowiska: '{p}'")
            positions.append(int(p))
    return sorted(set(positions))

def parse_big_fish_sum(input_str):
    """
    Parsuje "500,1200" -> (1700, [])
    Zwraca (sum, invalid_list)
    """
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
            except Exception:
                invalid.append(p)
        else:
            invalid.append(p)
    return total, invalid

def generuj_pdf_reportlab(df_sorted, nazwa_zawodow=""):
    """Generuje PDF i zwraca BytesIO."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    if FONT_AVAILABLE:
        for name in ['Heading1','Heading2','Heading3','Normal']:
            try:
                styles[name].fontName = 'DejaVu'
            except Exception:
                pass

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
        t2 = Table(data, repeatRows=1)
        t2.setStyle(TableStyle(t_style))
        elements.append(t2)
        elements.append(Spacer(1, 12))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# =========================
# === Domyślny stan ======
# =========================
DEFAULT_STATE = {
    "nazwa_zawodow": "",
    "liczba_zawodnikow": 0,
    "liczba_stanowisk": 0,
    "liczba_sektorow": 0,
    "sektory": {},
    "zawodnicy": [],
    "etap": 1
}

# =========================
# === Inicjalizacja S ====
# =========================
if "S" not in st.session_state:
    dane = wczytaj_dane()
    if isinstance(dane, dict):
        # uzupełnij brakujące klucze
        for k, v in DEFAULT_STATE.items():
            if k not in dane:
                dane[k] = v
        st.session_state["S"] = dane
    else:
        st.session_state["S"] = DEFAULT_STATE.copy()

S = st.session_state["S"]

# =========================
# === Styling (sidebar) ==
# =========================
st.markdown(
    """
    <style>
    /* delikatny "aplikacyjny" wygląd: ciemniejszy sidebar, lekki kontener */
    .css-1d391kg { background: linear-gradient(180deg,#0f172a,#071026); }
    .css-1d391kg .css-1v3fvcr { color: #fff; }
    .main-container {
        background: linear-gradient(180deg,#f8fafc,#f1f5f9);
        padding:18px;
        border-radius:10px;
        box-shadow: 0 6px 18px rgba(2,6,23,0.06);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# === Sidebar (nawigacja) =
# =========================
with st.sidebar:
    st.markdown("## 🧭 Nawigacja")
    page = st.radio(
        "Wybierz etap:",
        ("1️⃣ Konfiguracja", "2️⃣ Definicja sektorów", "3️⃣ Zawodnicy", "4️⃣ Wyniki i PDF"),
        index=(S.get("etap",1)-1 if 1 <= S.get("etap",1) <=4 else 0)
    )

    # synchronizuj S["etap"] z wyborem w sidebar
    try:
        selected_etap = {"1️⃣ Konfiguracja":1, "2️⃣ Definicja sektorów":2, "3️⃣ Zawodnicy":3, "4️⃣ Wyniki i PDF":4}[page]
        if S.get("etap") != selected_etap:
            S["etap"] = selected_etap
            zapisz_dane(S)
    except Exception:
        pass

    st.markdown("---")
    if st.button("🧹 Resetuj zawody"):
        reset_zawody()
    st.markdown("---")
    st.caption("© Wojciech Mierzejewski 2026")

# =========================
# === Główny panel =======
# =========================
st.markdown("<div class='main-container'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align:center'>🎣🏆 Panel organizatora zawodów 🏆🎣</h1>", unsafe_allow_html=True)

if not FONT_AVAILABLE:
    st.warning("Aby PDF poprawnie wyświetlał polskie znaki, umieść plik 'DejaVuSans.ttf' w katalogu aplikacji.")

# ---------- ETAP 1: KONFIGURACJA ----------
if S["etap"] == 1:
    st.header("⚙️ Krok 1: Ustawienia zawodów")
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow",""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 500, int(S.get("liczba_zawodnikow") or 10))
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 2000, int(S.get("liczba_stanowisk") or 10))
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 50, int(S.get("liczba_sektorow") or 3))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Zapisz konfigurację"):
            zapisz_dane(S)
            st.success("Dane zapisane.")
    with col2:
        if st.button("➡️ Przejdź do sektory"):
            S["etap"] = 2
            zapisz_dane(S)
            st.experimental_rerun()

# ---------- ETAP 2: DEFINICJA SEKTORÓW ----------
elif S["etap"] == 2:
    st.header("📍 Krok 2: Definicja sektorów")
    # podpowiedź sugerowanego rozkładu
    if S["liczba_zawodnikow"] > 0 and S["liczba_sektorow"] > 0:
        base = S["liczba_zawodnikow"] // S["liczba_sektorow"]
        remainder = S["liczba_zawodnikow"] % S["liczba_sektorow"]
        info = [f"Sektor {chr(65+i)}: {base + (1 if i < remainder else 0)} zawodników" for i in range(S["liczba_sektorow"])]
        st.info("ℹ️ Sugerowany podział zawodników:\n" + "\n".join(info))

    st.markdown("_Wpisz stanowiska lub zakresy, np. `1-5,7,10-12`_")

    sektory_tmp = {}
    for i in range(int(S.get("liczba_sektorow") or 0)):
        nazwa = chr(65 + i)
        current = S["sektory"].get(nazwa, [])
        default = ",".join(map(str, current)) if current else ""
        pola = st.text_input(f"Sektor {nazwa} – stanowiska:", value=default, key=f"sektor_{nazwa}")
        sektory_tmp[nazwa] = pola
        # pokaż liczbę stanowisk dla tego pola
        try:
            cnt = len(parse_positions(pola))
            if cnt > 0:
                st.caption(f"➡️ Liczba stanowisk w tym wpisie: {cnt}")
        except ValueError as e:
            st.warning(f"⚠️ {e}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Zapisz sektory"):
            parsed = {}
            all_positions = []
            errors = []
            for nazwa, txt in sektory_tmp.items():
                try:
                    pos = parse_positions(txt)
                    parsed[nazwa] = pos
                    all_positions.extend(pos)
                except ValueError as e:
                    errors.append(f"Sektor {nazwa}: {e}")
            # sprawdź duplikaty między sektorami
            dup = sorted([x for x in set(all_positions) if all_positions.count(x) > 1])
            if dup:
                errors.append(f"Powtórzone stanowiska między sektorami: {dup}")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                S["sektory"] = parsed
                S["etap"] = 3
                zapisz_dane(S)
                st.success("Sektory zapisane.")
    with c2:
        if st.button("⬅️ Wróć do konfiguracji"):
            S["etap"] = 1
            zapisz_dane(S)
            st.experimental_rerun()

# ---------- ETAP 3: ZAWODNICY ----------
elif S["etap"] == 3:
    st.header("👤 Krok 3: Dodawanie zawodników")
    if not S.get("sektory"):
        st.warning("Najpierw zdefiniuj sektory.")
    else:
        st.subheader("Zdefiniowane sektory")
        for nazwa, stanowiska in S["sektory"].items():
            st.write(f"**Sektor {nazwa}:** {stanowiska}")

        col_a, col_b = st.columns([3,1])
        with col_a:
            new_name = st.text_input("Imię i nazwisko zawodnika:", key="new_name_input")
        with col_b:
            wszystkie = sorted(sum(S["sektory"].values(), []))
            zajete = [z["stanowisko"] for z in S["zawodnicy"]]
            dostepne = [p for p in wszystkie if p not in zajete]
            new_st = st.selectbox("Stanowisko:", options=(dostepne if dostepne else ["Brak dostępnych"]), key="new_st_input")

        if st.button("➕ Dodaj zawodnika"):
            if not new_name.strip():
                st.warning("Podaj imię i nazwisko.")
            elif new_st == "Brak dostępnych":
                st.warning("Brak dostępnych stanowisk.")
            else:
                sek = next((k for k, v in S["sektory"].items() if new_st in v), None)
                S["zawodnicy"].append({"imie": new_name.strip(), "stanowisko": new_st, "sektor": sek, "waga": 0, "big_fish_raw": ""})
                zapisz_dane(S)
                st.experimental_rerun()

        if S["zawodnicy"]:
            st.subheader("📋 Lista zawodników")
            for i, z in enumerate(S["zawodnicy"]):
                c1, c2, c3 = st.columns([3,1,1])
                with c1:
                    z["imie"] = st.text_input(f"Imię {i+1}", z["imie"], key=f"imie_{i}")
                    z["waga"] = st.number_input("Waga (g)", 0, 10_000_000, int(z.get("waga",0)), step=10, key=f"waga_{i}")
                    z["big_fish_raw"] = st.text_input("Big fish (g) — np. 500,1200", z.get("big_fish_raw",""), key=f"bf_{i}")
                with c2:
                    wszystkie = sorted(sum(S["sektory"].values(), []))
                    zajete = [x["stanowisko"] for j,x in enumerate(S["zawodnicy"]) if j!=i]
                    dostepne_local = [s for s in wszystkie if s not in zajete or s==z["stanowisko"]]
                    if z["stanowisko"] not in dostepne_local:
                        dostepne_local.append(z["stanowisko"])
                    try:
                        idx = dostepne_local.index(z["stanowisko"])
                    except ValueError:
                        idx = 0
                    z["stanowisko"] = st.selectbox("Stan.", options=dostepne_local, index=idx, key=f"stan_{i}")
                with c3:
                    st.write(f"**Sektor {z.get('sektor')}**")
                if st.button("🗑️ Usuń", key=f"del_{i}"):
                    del S["zawodnicy"][i]
                    zapisz_dane(S)
                    st.experimental_rerun()
            # po pętli zapisz zmiany
            zapisz_dane(S)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➡️ Przejdź do wyników"):
                if not S["zawodnicy"]:
                    st.warning("Dodaj zawodników najpierw.")
                else:
                    S["etap"] = 4
                    zapisz_dane(S)
                    st.experimental_rerun()
        with col2:
            if st.button("⬅️ Wróć do sektorów"):
                S["etap"] = 2
                zapisz_dane(S)
                st.experimental_rerun()

# ---------- ETAP 4: WYNIKI I PDF ----------
elif S["etap"] == 4:
    st.header("⚖️ Krok 4: Wprowadzenie wyników i PDF")
    if not S["zawodnicy"]:
        st.warning("Brak zawodników.")
    else:
        for i, z in enumerate(S["zawodnicy"]):
            st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            waga_b = st.number_input(f"Waga bazowa — {z['imie']}", 0, 10_000_000, int(z.get("waga",0)), step=10, key=f"wb_{i}")
            big_raw = st.text_input(f"Big fish (g) — {z['imie']}", value=z.get("big_fish_raw",""), key=f"br_{i}")
            S["zawodnicy"][i]["big_fish_raw"] = big_raw
            big_sum, invalid = parse_big_fish_sum(big_raw)
            if invalid:
                st.warning(f"Nieprawidłowe Big fish dla {z['imie']}: {invalid} — zostaną zignorowane.")
            S["zawodnicy"][i]["waga"] = int(waga_b + big_sum)

        if st.button("💾 Zapisz wagi i przelicz"):
            zapisz_dane(S)
            st.success("Wagi zapisane.")
            st.experimental_rerun()

        # Przygotuj ranking
        df = pd.DataFrame(S["zawodnicy"]).copy()
        if df.empty:
            st.info("Brak danych do wyświetlenia.")
        else:
            df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
            df_sorted = pd.DataFrame()
            for miejsce in sorted(df["miejsce_w_sektorze"].unique()):
                grupa = df[df["miejsce_w_sektorze"] == miejsce].sort_values(by="waga", ascending=False)
                df_sorted = pd.concat([df_sorted, grupa])
            df_sorted = df_sorted.reset_index(drop=True)
            df_sorted["miejsce_ogolne"] = range(1, len(df_sorted)+1)

            st.subheader("📊 Ranking końcowy")
            st.dataframe(df_sorted[["miejsce_ogolne","imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

            st.subheader("📌 Podsumowanie sektorów")
            for sektor, grupa in df_sorted.groupby("sektor"):
                st.write(f"**Sektor {sektor}**")
                st.dataframe(grupa[["imie","stanowisko","waga","miejsce_w_sektorze","miejsce_ogolne"]], hide_index=True)

            pdf_bytes = generuj_pdf_reportlab(df_sorted, S.get("nazwa_zawodow",""))
            st.download_button("💾 Pobierz wyniki jako PDF", data=pdf_bytes, file_name="wyniki_zawodow.pdf", mime="application/pdf")

st.markdown("</div>", unsafe_allow_html=True)

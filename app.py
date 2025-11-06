import streamlit as st
import pandas as pd
import json
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

st.set_page_config(page_title="Zawody wędkarskie", layout="wide")
SAVE_FILE = "zawody_state.json"

# -----------------------------
# Funkcje zapisu/odczytu stanu
# -----------------------------
def load_state():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

def save_state():
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state["S"], f, ensure_ascii=False, indent=2)

# -----------------------------
# Inicjalizacja stanu
# -----------------------------
loaded = load_state()
if "S" not in st.session_state:
    st.session_state["S"] = loaded if loaded else {
        "liczba_zawodnikow": 10,
        "liczba_stanowisk": 10,
        "liczba_sektorow": 3,
        "sektory": {},
        "zawodnicy": [],
        "etap": 1
    }
S = st.session_state["S"]

# -----------------------------
# Nagłówek
# -----------------------------
st.markdown("<h1 style='font-size:28px'>🎣 Panel organizatora zawodów wędkarskich</h1>", unsafe_allow_html=True)

# -----------------------------
# Reset zawodów
# -----------------------------
with st.form("form_reset"):
    reset = st.form_submit_button("🧹 Resetuj zawody")
    if reset:
        st.session_state["S"] = {
            "liczba_zawodnikow": 10,
            "liczba_stanowisk": 10,
            "liczba_sektorow": 3,
            "sektory": {},
            "zawodnicy": [],
            "etap": 1
        }
        save_state()
        st.experimental_rerun()

# -----------------------------
# ETAP 1 — Konfiguracja zawodów
# -----------------------------
if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)

    liczba_zawodnikow_default = S.get("liczba_zawodnikow", 10)
    if liczba_zawodnikow_default < 1: liczba_zawodnikow_default = 10
    liczba_stanowisk_default = S.get("liczba_stanowisk", 10)
    if liczba_stanowisk_default < 1: liczba_stanowisk_default = 10
    liczba_sektorow_default = S.get("liczba_sektorow", 3)
    if liczba_sektorow_default < 1: liczba_sektorow_default = 3

    with st.form("form_etap1"):
        liczba_zawodnikow = st.number_input(
            "Liczba zawodników:", min_value=1, max_value=200, value=liczba_zawodnikow_default
        )
        liczba_stanowisk = st.number_input(
            "Liczba stanowisk:", min_value=1, max_value=200, value=liczba_stanowisk_default
        )
        liczba_sektorow = st.number_input(
            "Liczba sektorów:", min_value=1, max_value=20, value=liczba_sektorow_default
        )

        submit = st.form_submit_button("➡️ Dalej – definiuj sektory")
        if submit:
            S["liczba_zawodnikow"] = liczba_zawodnikow
            S["liczba_stanowisk"] = liczba_stanowisk
            S["liczba_sektorow"] = liczba_sektorow
            S["etap"] = 2
            save_state()
            st.experimental_rerun()

# -----------------------------
# ETAP 2 — Definicja sektorów
# -----------------------------
elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)

    zawodnicy = S.get("liczba_zawodnikow", 10)
    sektory_n = S.get("liczba_sektorow", 3)
    base = zawodnicy // sektory_n
    extra = zawodnicy % sektory_n

    st.markdown("### 🔢 Rekomendowana liczba stanowisk w sektorach:")
    txt = ""
    for i in range(sektory_n):
        nazwa = chr(65 + i)
        if i < extra:
            txt += f"✅ **Sektor {nazwa}: {base + 1} zawodników** (o 1 więcej)\n\n"
        else:
            txt += f"✅ **Sektor {nazwa}: {base} zawodników**\n\n"
    st.info(txt)

    with st.form("form_etap2"):
        sektory = {}
        for i in range(sektory_n):
            nazwa = chr(65 + i)
            key = f"sektor_{nazwa}"
            if key not in st.session_state or not isinstance(st.session_state[key], str):
                val = S.get("sektory", {}).get(nazwa, [])
                st.session_state[key] = ",".join(map(str, val)) if isinstance(val, list) else ""

            pola = st.text_input(
                f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
                value=st.session_state[key],
                key=key
            )
            if pola.strip():
                lista = [int(x) for x in pola.split(",") if x.strip().isdigit()]
                if lista:
                    sektory[nazwa] = lista

        submit_save = st.form_submit_button("💾 Zapisz sektory")
        if submit_save:
            if len(sektory) != sektory_n or any(len(v)==0 for v in sektory.values()):
                st.error("Wszystkie sektory muszą mieć przynajmniej jedno stanowisko.")
            else:
                flat = sum(sektory.values(), [])
                duplikaty = [x for x in flat if flat.count(x) > 1]
                if duplikaty:
                    st.error(f"Powtórzone stanowiska: {sorted(set(duplikaty))}")
                else:
                    S["sektory"] = sektory
                    S["etap"] = 3
                    save_state()
                    st.experimental_rerun()

    with st.form("form_wstecz2"):
        submit_back = st.form_submit_button("⬅️ Wstecz")
        if submit_back:
            S["etap"] = 1
            save_state()
            st.experimental_rerun()

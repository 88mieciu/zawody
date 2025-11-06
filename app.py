import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Zawody wędkarskie", layout="wide")

SAVE_FILE = "zawody_state.json"

# -------------------------------
# 🔄 FUNKCJE ZAPISU / ODCZYTU STANU
# -------------------------------

def load_state():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Błąd odczytu pliku: {e}")
            return None
    return None

def save_state():
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state["S"], f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Błąd zapisu pliku: {e}")

# -------------------------------
# 🧠 Inicjalizacja stanu
# -------------------------------

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

# -------------------------------
# ✔️ Obsługa bezpiecznego rerun
# -------------------------------

if st.session_state.get("force_rerun"):
    st.session_state["force_rerun"] = False
    st.experimental_rerun()

# -------------------------------
# 🔝 Nagłówek
# -------------------------------

st.markdown("🎣 Panel organizatora zawodów wędkarskich by Wojtek Mierzejewski", unsafe_allow_html=True)

# -------------------------------
# 🧹 RESET
# -------------------------------

if st.button("🧹 Resetuj zawody"):
    st.session_state["S"] = {
        "liczba_zawodnikow": 10,
        "liczba_stanowisk": 10,
        "liczba_sektorow": 3,
        "sektory": {},
        "zawodnicy": [],
        "etap": 1
    }
    save_state()
    st.session_state["force_rerun"] = True
    st.stop()

# -------------------------------
# ✅ ETAP 1 — KONFIGURACJA ZAWODÓW
# -------------------------------

if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)

    old_hash = str(S)

    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 200, S["liczba_zawodnikow"])
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 200, S["liczba_stanowisk"])
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 20, S["liczba_sektorow"])

    if str(S) != old_hash:
        save_state()

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        save_state()

# -------------------------------
# ✅ ETAP 2 — DEFINICJA SEKTORÓW
# -------------------------------

elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)

    # Wyliczenie rekomendacji
    zawodnicy = S["liczba_zawodnikow"]
    sektory_n = S["liczba_sektorow"]

    base = zawodnicy // sektory_n
    extra = zawodnicy % sektory_n

    # Informacja o stanowiskach
    st.markdown("### 🔢 Rekomendowana liczba stanowisk w sektorach:")
    txt = ""
    for i in range(sektory_n):
        nazwa = chr(65 + i)
        if i < extra:
            txt += f"✅ **Sektor {nazwa}: {base + 1} zawodników** (o 1 więcej)\n\n"
        else:
            txt += f"✅ **Sektor {nazwa}: {base} zawodników**\n\n"
    st.info(txt)

    # Pola do wpisywania stanowisk
    sektory = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        pola = st.text_input(
            f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
            value=",".join(map(str, S["sektory"].get(nazwa, []))),
            key=f"sektor_{nazwa}"
        )
        if pola.strip():
            # Walidacja wprowadzonych danych
            valid_stations = []
            for x in pola.split(","):
                x = x.strip()
                if x.isdigit():
                    station = int(x)
                    if 1 <= station <= S["liczba_stanowisk"]:
                        valid_stations.append(station)
                    else:
                        st.warning(f"Stanowisko {station} jest poza zakresem (1-{S['liczba_stanowisk']})")
            sektory[nazwa] = valid_stations

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("💾 Zapisz sektory"):
            flat = sum(sektory.values(), [])
            duplikaty = list({x for x in flat if flat.count(x) > 1})
            
            if duplikaty:
                st.error(f"Znaleziono duplikaty stanowisk: {duplikaty}")
            else:
                S["sektory"] = sektory
                save_state()
                st.success("Sektory zostały zapisane!")

    with col2:
        if st.button("⬅️ Wróć do ustawień"):
            S["etap"] = 1
            save_state()

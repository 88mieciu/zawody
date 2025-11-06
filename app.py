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
    if st.form_submit_button("🧹 Resetuj zawody"):
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

    liczba_zawodnikow_default = S.get("liczba_zawodnikow")
    if not isinstance(liczba_zawodnikow_default, int) or liczba_zawodnikow_default < 1:
        liczba_zawodnikow_default = 10

    liczba_stanowisk_default = S.get("liczba_stanowisk")
    if not isinstance(liczba_stanowisk_default, int) or liczba_stanowisk_default < 1:
        liczba_stanowisk_default = 10

    liczba_sektorow_default = S.get("liczba_sektorow")
    if not isinstance(liczba_sektorow_default, int) or liczba_sektorow_default < 1:
        liczba_sektorow_default = 3

    with st.form("form_etap1"):
        liczba_zawodnikow = st.number_input(
            "Liczba zawodników:", min_value=1, max_value=200,
            value=liczba_zawodnikow_default
        )
        liczba_stanowisk = st.number_input(
            "Liczba stanowisk:", min_value=1, max_value=200,
            value=liczba_stanowisk_default
        )
        liczba_sektorow = st.number_input(
            "Liczba sektorów:", min_value=1, max_value=20,
            value=liczba_sektorow_default
        )

        if st.form_submit_button("➡️ Dalej – definiuj sektory"):
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

            # inicjalizacja w session_state
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

        if st.form_submit_button("💾 Zapisz sektory"):
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
        if st.form_submit_button("⬅️ Wstecz"):
            S["etap"] = 1
            save_state()
            st.experimental_rerun()

# -----------------------------
# ETAP 3 — Dodawanie zawodników
# -----------------------------
elif S["etap"] == 3:
    st.markdown("<h3 style='font-size:20px'>👤 Krok 3: Dodawanie zawodników</h3>", unsafe_allow_html=True)

    st.subheader("Zdefiniowane sektory:")
    for nazwa, stanowiska in S["sektory"].items():
        st.write(f"**Sektor {nazwa}:** {stanowiska}")

    wszystkie = sorted(sum(S["sektory"].values(), []))
    zajete = [z["stanowisko"] for z in S["zawodnicy"]]
    dostepne = [s for s in wszystkie if s not in zajete]

    with st.form("form_dodaj_zawodnika"):
        imie = st.text_input("Imię i nazwisko zawodnika:", key="new_name")
        stano = st.selectbox("Stanowisko", dostepne, key="new_stanowisko")
        if st.form_submit_button("➕ Dodaj zawodnika") and imie.strip():
            sek = next((k for k, v in S["sektory"].items() if stano in v), None)
            if sek:
                S["zawodnicy"].append({
                    "imie": imie.strip(),
                    "stanowisko": stano,
                    "sektor": sek,
                    "waga": 0
                })
                save_state()
                st.experimental_rerun()
            else:
                st.error("Wybrane stanowisko nie należy do żadnego sektora!")

    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")
        for i, z in enumerate(S["zawodnicy"]):
            col1, col2, col3 = st.columns([3,1,1])
            key_waga = f"waga_{i}"
            if key_waga not in st.session_state:
                st.session_state[key_waga] = z.get("waga", 0)

            with col1:
                new_name = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
                if new_name != z["imie"]:
                    z["imie"] = new_name
                    save_state()

            with col2:
                zajete_inne = [x["stanowisko"] for j, x in enumerate(S["zawodnicy"]) if j != i]
                dostepne_stan = [s for s in wszystkie if s not in zajete_inne or s == z["stanowisko"]]
                idx = dostepne_stan.index(z["stanowisko"]) if z["stanowisko"] in dostepne_stan else 0
                new_stan = st.selectbox("Stan.", dostepne_stan, index=idx, key=f"stan_{i}")
                if new_stan != z["stanowisko"]:
                    z["stanowisko"] = new_stan
                    z["sektor"] = next(k for k,v in S["sektory"].items() if new_stan in v)
                    save_state()

            with col3:
                if st.button("🗑️ Usuń", key=f"del_{i}"):
                    del S["zawodnicy"][i]
                    if key_waga in st.session_state:
                        del st.session_state[key_waga]
                    save_state()
                    st.experimental_rerun()

    with st.form("form_przejdz4"):
        if st.form_submit_button("➡️ Przejdź do wyników") and S["zawodnicy"]:
            S["etap"] = 4
            save_state()
            st.experimental_rerun()
        elif st.form_submit_button("➡️ Przejdź do wyników") and not S["zawodnicy"]:
            st.warning("Dodaj przynajmniej jednego zawodnika.")

# -----------------------------
# ETAP 4 — Wprowadzanie wyników + PDF
# -----------------------------
elif S["etap"] == 4:
    st.markdown("<h3 style='font-size:20px'>⚖️ Krok 4: Wprowadzenie wyników</h3>", unsafe_allow_html=True)

    if not S["zawodnicy"]:
        st.warning("Brak zawodników.")
        if st.button("⬅️ Wróć"):
            S["etap"] = 3
            save_state()
            st.experimental_rerun()
    else:
        for i, z in enumerate(S["zawodnicy"]):
            key_waga = f"waga_{i}"
            if key_waga not in st.session_state:
                st.session_state[key_waga] = z.get("waga", 0)

            col1, col2 = st.columns([2,1])
            with col1:
                st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            with col2:
                new_waga = st.number_input(
                    "Waga (g)", 0, 120000, st.session_state[key_waga], step=10, key=key_waga
                )
                z["waga"] = new_waga
                save_state()

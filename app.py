import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Zawody wędkarskie", layout="wide")

# ---------------------- FUNKCJE ZAPISU I ODCZYTU ----------------------

def zapisz_stan():
    """Zapisuje stan zawodów do pliku JSON."""
    try:
        with open("stan_zawodow.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state["S"], f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")

def wczytaj_stan():
    """Wczytuje stan zawodów z pliku JSON (jeśli istnieje)."""
    try:
        if os.path.exists("stan_zawodow.json"):
            with open("stan_zawodow.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return None

# ---------------------- INICJALIZACJA STANU ----------------------

if "S" not in st.session_state:
    stan_z_pliku = wczytaj_stan()
    if stan_z_pliku:
        st.session_state["S"] = stan_z_pliku
    else:
        st.session_state["S"] = {
            "liczba_zawodnikow": 0,
            "liczba_stanowisk": 0,
            "liczba_sektorow": 0,
            "sektory": {},
            "zawodnicy": [],
            "etap": 1
        }

S = st.session_state["S"]

# ---------------------- NAGŁÓWEK ----------------------

st.markdown("<h1 style='font-size:28px'>🎣 Panel organizatora zawodów wędkarskich by Wojtek Mierzejewski</h1>", unsafe_allow_html=True)


# ---------------------- RESET ----------------------

if st.button("🧹 Resetuj zawody"):
    st.session_state["S"] = {
        "liczba_zawodnikow": 0,
        "liczba_stanowisk": 0,
        "liczba_sektorow": 0,
        "sektory": {},
        "zawodnicy": [],
        "etap": 1
    }
    zapisz_stan()


# ---------------------- ETAP 1 ----------------------

if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)

    n1 = st.number_input("Liczba zawodników:", 1, 40, S["liczba_zawodnikow"] or 10)
    n2 = st.number_input("Liczba stanowisk na łowisku:", 1, 100, S["liczba_stanowisk"] or 10)
    n3 = st.number_input("Liczba sektorów:", 1, 10, S["liczba_sektorow"] or 3)

    # automatyczny zapis przy każdej zmianie
    if (n1 != S["liczba_zawodnikow"]) or (n2 != S["liczba_stanowisk"]) or (n3 != S["liczba_sektorow"]):
        S["liczba_zawodnikow"] = n1
        S["liczba_stanowisk"] = n2
        S["liczba_sektorow"] = n3
        zapisz_stan()

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_stan()


# ---------------------- ETAP 2 ----------------------

elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)
    sektory = {}

    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        pola = st.text_input(
            f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
            value=",".join(map(str, S["sektory"].get(nazwa, []))),
            key=f"sektor_{nazwa}"
        )
        if pola.strip():
            sektory[nazwa] = [int(x.strip()) for x in pola.split(",") if x.strip().isdigit()]

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("💾 Zapisz sektory"):
            # kontrola duplikatów
            wszystkie = sum(sektory.values(), [])
            duplikaty = [x for x in wszystkie if wszystkie.count(x) > 1]

            if duplikaty:
                st.error(f"Powtórzone stanowiska: {sorted(set(duplikaty))}")
            else:
                S["sektory"] = sektory
                S["etap"] = 3
                zapisz_stan()

    with col2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1
            zapisz_stan()


# ---------------------- ETAP 3 ----------------------

elif S["etap"] == 3:
    st.markdown("<h3 style='font-size:20px'>👤 Krok 3: Dodawanie zawodników</h3>", unsafe_allow_html=True)

    st.subheader("Zdefiniowane sektory:")
    for nazwa, stanowiska in S["sektory"].items():
        st.write(f"**Sektor {nazwa}:** {stanowiska}")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("✏️ Edytuj sektory"):
            S["etap"] = 2
            zapisz_stan()

    with col2:
        if st.button("➡️ Przejdź do wprowadzenia wyników"):
            if len(S["zawodnicy"]) == 0:
                st.warning("⚠️ Najpierw dodaj zawodników.")
            else:
                S["etap"] = 4
                zapisz_stan()

    wszystkie_dozwolone = sorted(sum(S["sektory"].values(), []))
    zajete = [z["stanowisko"] for z in S["zawodnicy"]]
    dostepne = [s for s in wszystkie_dozwolone if s not in zajete]

    if dostepne:
        col1, col2 = st.columns([2, 1])
        with col1:
            imie = st.text_input("Imię i nazwisko zawodnika:", key="new_name")
        with col2:
            stano = st.selectbox("Stanowisko", dostepne, key="new_stanowisko")

        if st.button("➕ Dodaj zawodnika"):
            if imie.strip():
                sek = next((k for k, v in S["sektory"].items() if stano in v), None)
                S["zawodnicy"].append(
                    {"imie": imie.strip(), "stanowisko": stano, "sektor": sek, "waga": 0}
                )
                zapisz_stan()
            else:
                st.warning("Podaj imię i nazwisko.")

    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")
        for i, z in enumerate(S["zawodnicy"]):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                nowa_nazwa = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
                if nowa_nazwa != z["imie"]:
                    z["imie"] = nowa_nazwa
                    zapisz_stan()

            with col2:
                wszystkie = sorted(sum(S["sektory"].values(), []))
                zajete = [x["stanowisko"] for j, x in enumerate(S["zawodnicy"]) if j != i]
                dostepne = [s for s in wszystkie if s not in zajete or s == z["stanowisko"]]

                idx = dostepne.index(z["stanowisko"]) if z["stanowisko"] in dostepne else 0

                nowe_stan = st.selectbox("Stan.", dostepne, index=idx, key=f"stan_{i}")
                if nowe_stan != z["stanowisko"]:
                    z["stanowisko"] = nowe_stan
                    zapisz_stan()

            with col3:
                st.write(f"**Sektor {z['sektor']}**")

            with col4:
                if st.button("🗑️ Usuń", key=f"del_{i}"):
                    del S["zawodnicy"][i]
                    zapisz_stan()
                    st.experimental_rerun()


# ---------------------- ETAP 4 ----------------------

elif S["etap"] == 4:
    st.markdown("<h3 style='font-size:20px'>⚖️ Krok 4: Wprowadzenie wyników (waga ryb)</h3>", unsafe_allow_html=True)

    if not S["zawodnicy"]:
        st.warning("Brak zawodników.")
        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
            zapisz_stan()

    else:
        for i, z in enumerate(S["zawodnicy"]):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            with col2:
                nowa_waga = st.number_input("Waga (g)", 0, 100000, z["waga"], step=10, key=f"waga_{i}")
                if nowa_waga != z["waga"]:
                    z["waga"] = nowa_waga
                    zapisz_stan()

        if st.button("🏆 Pokaż wyniki końcowe"):
            df = pd.DataFrame(S["zawodnicy"])
            df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
            df_sorted = df.sort_values(by=["miejsce_w_sektorze", "waga"], ascending=[True, False])

            st.dataframe(df_sorted, hide_index=True)

        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
            zapisz_stan()


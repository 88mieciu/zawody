import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Zawody wędkarskie", layout="wide")

STAN_FILE = "stan_zawodow.json"

# --- Funkcje do zapisu i odczytu stanu ---
def zapisz_stan(S):
    try:
        with open(STAN_FILE, "w") as f:
            json.dump(S, f)
    except Exception as e:
        st.error(f"Nie udało się zapisać stanu: {e}")

def wczytaj_stan():
    if os.path.exists(STAN_FILE):
        try:
            with open(STAN_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Nie udało się wczytać stanu: {e}")
    return None

# --- Inicjalizacja stanu ---
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

st.markdown("<h1 style='font-size:28px'>🎣 Panel organizatora zawodów wędkarskich by Wojtek Mierzejewski</h1>", unsafe_allow_html=True)

# --- PRZYCISK RESET ---
if st.button("🧹 Resetuj zawody"):
    st.session_state["S"] = {
        "liczba_zawodnikow": 0,
        "liczba_stanowisk": 0,
        "liczba_sektorow": 0,
        "sektory": {},
        "zawodnicy": [],
        "etap": 1
    }
    zapisz_stan(st.session_state["S"])

# --- ETAP 1: KONFIGURACJA ---
if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 40, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 100, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 10, S["liczba_sektorow"] or 3)

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_stan(S)  # ✅ zapis po konfiguracji

# --- ETAP 2: DEFINICJA SEKTORÓW ---
elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)
    sektory = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        pola = st.text_input(f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
                             value=",".join(map(str, S["sektory"].get(nazwa, []))),
                             key=f"sektor_{nazwa}")
        if pola.strip():
            try:
                sektory[nazwa] = [int(x.strip()) for x in pola.split(",") if x.strip().isdigit()]
            except ValueError:
                st.warning(f"⚠️ Błędne dane w sektorze {nazwa}. Użyj tylko liczb i przecinków.")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("💾 Zapisz sektory"):
            wszystkie = []
            for s in sektory.values():
                wszystkie.extend(s)
            duplikaty = [x for x in wszystkie if wszystkie.count(x) > 1]
            if duplikaty:
                st.error(f"Powtórzone stanowiska: {sorted(set(duplikaty))}")
            else:
                S["sektory"] = sektory
                S["etap"] = 3
                zapisz_stan(S)  # ✅ zapis po zapisaniu sektorów
    with col2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1

# --- ETAP 3: DODAWANIE ZAWODNIKÓW ---
elif S["etap"] == 3:
    st.markdown("<h3 style='font-size:20px'>👤 Krok 3: Dodawanie zawodników</h3>", unsafe_allow_html=True)
    st.subheader("Zdefiniowane sektory:")
    for nazwa, stanowiska in S["sektory"].items():
        st.write(f"**Sektor {nazwa}:** {stanowiska}")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("✏️ Edytuj sektory"):
            S["etap"] = 2
    with col2:
        if st.button("➡️ Przejdź do wprowadzenia wyników"):
            if len(S["zawodnicy"]) == 0:
                st.warning("⚠️ Najpierw dodaj zawodników.")
            else:
                S["etap"] = 4

    wszystkie_dozwolone = sorted(sum(S["sektory"].values(), []))
    zajete = [z["stanowisko"] for z in S["zawodnicy"]]
    dostepne = [s for s in wszystkie_dozwolone if s not in zajete]

    if dostepne:
        col1, col2 = st.columns([2,1])
        with col1:
            imie = st.text_input("Imię i nazwisko zawodnika:", key="new_name")
        with col2:
            stano = st.selectbox("Stanowisko", dostepne, key="new_stanowisko")

        if st.button("➕ Dodaj zawodnika"):
            if not imie.strip():
                st.warning("Podaj imię i nazwisko.")
            else:
                sek = next((k for k, v in S["sektory"].items() if stano in v), None)
                S["zawodnicy"].append(
                    {"imie": imie.strip(), "stanowisko": stano, "sektor": sek, "waga": 0}
                )
                zapisz_stan(S)  # ✅ zapis po dodaniu zawodnika

    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")
        for i, z in enumerate(S["zawodnicy"]):
            col1, col2, col3, col4 = st.columns([2,1,1,1])
            with col1:
                z["imie"] = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
            with col2:
                wszystkie_dozwolone = sorted(sum(S["sektory"].values(), []))
                zajete = [x["stanowisko"] for j,x in enumerate(S["zawodnicy"]) if j!=i]
                dostepne = [s for s in wszystkie_dozwolone if s not in zajete or s==z["stanowisko"]]
                if z["stanowisko"] not in dostepne:
                    dostepne = sorted(dostepne + [z["stanowisko"]]) if z["stanowisko"] else dostepne
                try:
                    idx = dostepne.index(z["stanowisko"])
                except ValueError:
                    idx = 0
                z["stanowisko"] = st.selectbox("Stan.", dostepne, index=idx, key=f"stan_{i}")
            with col3:
                st.write(f"**Sektor {z['sektor']}**")
            with col4:
                if st.button("🗑️ Usuń", key=f"del_{i}"):
                    del S["zawodnicy"][i]
                    zapisz_stan(S)  # ✅ zapis po usunięciu zawodnika

# --- ETAP 4: WPROWADZANIE WYNIKÓW I PODSUMOWANIE ---
elif S["etap"] == 4:
    st.markdown("<h3 style='font-size:20px'>⚖️ Krok 4: Wprowadzenie wyników (waga ryb)</h3>", unsafe_allow_html=True)

    if not S["zawodnicy"]:
        st.warning("Brak zawodników. Wróć i dodaj ich najpierw.")
        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
    else:
        # Wprowadzanie wag
        for i,z in enumerate(S["zawodnicy"]):
            col1, col2 = st.columns([2,1])
            with col1:
                st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            with col2:
                z["waga"] = st.number_input("Waga (g)", 0, 100000, z["waga"], step=10, key=f"waga_{i}")
                zapisz_stan(S)  # ✅ zapis po wpisaniu każdej wagi

        if st.button("🏆 Pokaż wyniki końcowe"):
            df = pd.DataFrame(S["zawodnicy"])
            df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
            df_sorted = df.sort_values(by=["miejsce_w_sektorze","waga"], ascending=[True,False])

            st.markdown("<h4 style='font-size:18px'>📊 Ranking końcowy (wszyscy zawodnicy)</h4>", unsafe_allow_html=True)
            st.dataframe(df_sorted[["imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

            st.markdown("<h4 style='font-size:18px'>📌 Podsumowanie sektorów</h4>", unsafe_allow_html=True)
            for sektor, grupa in df_sorted.groupby("sektor"):
                st.write(f"**Sektor {sektor}**")
                tabela = grupa.sort_values(by="waga", ascending=False)[["imie","stanowisko","waga","miejsce_w_sektorze"]]
                st.dataframe(tabela, hide_index=True)

            # --- Eksport do TXT ---
            txt_lines = ["📊 Ranking końcowy (wszyscy zawodnicy):\n"]
            txt_lines.append("Imię\tSektor\tStanowisko\tWaga\tMiejsce w sektorze")
            for _, row in df_sorted.iterrows():
                txt_lines.append(f"{row['imie']}\t{row['sektor']}\t{row['stanowisko']}\t{row['waga']}\t{int(row['miejsce_w_sektorze'])}")

            txt_lines.append("\n📌 Podsumowanie sektorów:\n")
            for sektor, grupa in df_sorted.groupby("sektor"):
                txt_lines.append(f"\nSektor {sektor}")
                tabela = grupa.sort_values(by="waga", ascending=False)[["imie","stanowisko","waga","miejsce_w_sektorze"]]
                txt_lines.append("Imię\tStanowisko\tWaga\tMiejsce w sektorze")
                for _, row in tabela.iterrows():
                    txt_lines.append(f"{row['imie']}\t{row['stanowisko']}\t{row['waga']}\t{int(row['miejsce_w_sektorze'])}")

            txt_data = "\n".join(txt_lines)
            st.download_button("💾 Pobierz wyniki jako TXT", data=txt_data,
                               file_name="wyniki_zawodow.txt", mime="text/plain")

        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3

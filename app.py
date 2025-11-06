import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Zawody wędkarskie", layout="wide")

SAVE_FILE = "zawody_state.json"

# ---------------------------- ŁADOWANIE STANU ----------------------------

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
        json.dump(st.session_state["S"], f, indent=4, ensure_ascii=False)

# ----------------------- INICJALIZACJA STANU ------------------------------

if "S" not in st.session_state:
    loaded = load_state()
    if loaded:
        st.session_state["S"] = loaded
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

# ------------------------------ INTERFEJS ---------------------------------

st.markdown("<h1 style='font-size:28px'>🎣 Panel organizatora zawodów wędkarskich by Wojtek Mierzejewski</h1>",
            unsafe_allow_html=True)

# --- RESET ---
if st.button("🧹 Resetuj zawody"):
    st.session_state["S"] = {
        "liczba_zawodnikow": 0,
        "liczba_stanowisk": 0,
        "liczba_sektorow": 0,
        "sektory": {},
        "zawodnicy": [],
        "etap": 1
    }
    save_state()
    st.success("Zresetowano zawody.")
    st.stop()

# --------------------------- ETAP 1: KONFIG -------------------------------

if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)

    old_vals = (S["liczba_zawodnikow"], S["liczba_stanowisk"], S["liczba_sektorow"])

    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 200, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 200, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 20, S["liczba_sektorow"] or 3)

    if (S["liczba_zawodnikow"], S["liczba_stanowisk"], S["liczba_sektorow"]) != old_vals:
        save_state()

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        save_state()

# --------------------------- ETAP 2: SEKTORY ------------------------------

elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)

    # ✅ informacja o podziale uczestników
    zaw = S["liczba_zawodnikow"]
    sek = S["liczba_sektorow"]

    base = zaw // sek
    extra = zaw % sek

    if extra == 0:
        st.info(f"✅ Każdy sektor powinien mieć po **{base} stanowisk**.")
    else:
        st.info(
            f"ℹ️ Zawodnicy nie dzielą się po równo.\n\n"
            f"- **{sek - extra} sektorów** będzie miało po **{base} stanowisk**,\n"
            f"- **{extra} sektory** będą miały po **{base + 1} stanowisk**."
        )

    sektory = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        pola = st.text_input(
            f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
            value=",".join(map(str, S["sektory"].get(nazwa, []))),
            key=f"sektor_{nazwa}"
        )

        if pola.strip():
            sektory[nazwa] = [int(x) for x in pola.replace(" ", "").split(",") if x.isdigit()]

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
                save_state()

    with col2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1
            save_state()

# --------------------------- ETAP 3: ZAWODNICY ----------------------------

elif S["etap"] == 3:
    st.markdown("<h3 style='font-size:20px'>👤 Krok 3: Dodawanie zawodników</h3>", unsafe_allow_html=True)

    st.subheader("Zdefiniowane sektory:")
    for nazwa, stanowiska in S["sektory"].items():
        st.write(f"**Sektor {nazwa}:** {stanowiska}")

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("✏️ Edytuj sektory"):
            S["etap"] = 2
            save_state()
    with col2:
        if st.button("➡️ Przejdź do wprowadzenia wyników"):
            if not S["zawodnicy"]:
                st.warning("⚠️ Najpierw dodaj zawodników.")
            else:
                S["etap"] = 4
                save_state()

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
            if imie.strip():
                sektor = next((k for k,v in S["sektory"].items() if stano in v), None)
                S["zawodnicy"].append({
                    "imie": imie.strip(),
                    "stanowisko": stano,
                    "sektor": sektor,
                    "waga": 0
                })
                save_state()
            else:
                st.warning("Podaj imię i nazwisko.")

    # edycja listy zawodników
    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")

        for i, z in enumerate(S["zawodnicy"]):
            col1, col2, col3, col4 = st.columns([2,1,1,1])

            with col1:
                new_name = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
                if new_name != z["imie"]:
                    z["imie"] = new_name
                    save_state()

            with col2:
                wszystkie = sorted(sum(S["sektory"].values(), []))
                zajete = [x["stanowisko"] for j,x in enumerate(S["zawodnicy"]) if j != i]
                dostepne = [s for s in wszystkie if s not in zajete] + [z["stanowisko"]]

                dostepne = sorted(set(dostepne))
                idx = dostepne.index(z["stanowisko"])

                new_pos = st.selectbox("Stan.", dostepne, index=idx, key=f"stan_{i}")
                if new_pos != z["stanowisko"]:
                    z["stanowisko"] = new_pos
                    z["sektor"] = next((k for k,v in S["sektory"].items() if new_pos in v), None)
                    save_state()

            with col3:
                st.write(f"**Sektor {z['sektor']}**")

            with col4:
                if st.button("🗑️ Usuń", key=f"del_{i}"):
                    del S["zawodnicy"][i]
                    save_state()
                    st.experimental_rerun()

# --------------------------- ETAP 4: WAGI ----------------------------

elif S["etap"] == 4:
    st.markdown("<h3 style='font-size:20px'>⚖️ Krok 4: Wprowadzenie wyników (waga ryb)</h3>", unsafe_allow_html=True)

    if not S["zawodnicy"]:
        st.warning("Brak zawodników.")
        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
            save_state()
    else:

        for i, z in enumerate(S["zawodnicy"]):
            col1, col2 = st.columns([2,1])

            with col1:
                st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")

            with col2:
                new_waga = st.number_input("Waga (g)", 0, 100000, z["waga"], step=10, key=f"waga_{i}")
                if new_waga != z["waga"]:
                    z["waga"] = new_waga
                    save_state()

        if st.button("🏆 Pokaż wyniki końcowe"):
            df = pd.DataFrame(S["zawodnicy"])
            df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
            df_sorted = df.sort_values(by=["miejsce_w_sektorze","waga"], ascending=[True,False])

            st.markdown("<h4 style='font-size:18px'>📊 Ranking końcowy</h4>", unsafe_allow_html=True)
            st.dataframe(df_sorted[["imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

            # eksport TXT
            lines = ["Ranking końcowy:\n"]
            for _, r in df_sorted.iterrows():
                lines.append(f"{r['imie']}\t{r['sektor']}\t{r['stanowisko']}\t{r['waga']}\t{int(r['miejsce_w_sektorze'])}")

            txt = "\n".join(lines)

            st.download_button("💾 Pobierz TXT", txt, "wyniki.txt", "text/plain")

        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
            save_state()

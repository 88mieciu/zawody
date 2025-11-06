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
            data = json.load(open(SAVE_FILE, "r", encoding="utf-8"))
            keys = {"liczba_zawodnikow","liczba_stanowisk","liczba_sektorow","sektory","zawodnicy","etap"}
            if not keys.issubset(data.keys()):
                return None
            return data
        except (json.JSONDecodeError, IOError):
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
    st.experimental_rerun()

# -----------------------------
# ETAP 1 — Konfiguracja zawodów
# -----------------------------
if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)

    with st.form("form_etap1"):
        liczba_zawodnikow = st.number_input(
            "Liczba zawodników:", 1, 200, S["liczba_zawodnikow"])
        liczba_stanowisk = st.number_input(
            "Liczba stanowisk na łowisku:", 1, 200, S["liczba_stanowisk"])
        liczba_sektorow = st.number_input(
            "Liczba sektorów:", 1, 20, S["liczba_sektorow"])

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

    zawodnicy = S["liczba_zawodnikow"]
    sektory_n = S["liczba_sektorow"]
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
            pola = st.text_input(
                f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
                value=",".join(map(str, S["sektory"].get(nazwa, []))),
                key=f"sektor_{nazwa}"
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

    if st.button("⬅️ Wstecz"):
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

    # inicjalizacja kluczy session_state dla wag
    for i, z in enumerate(S["zawodnicy"]):
        key = f"waga_{i}"
        if key not in st.session_state:
            st.session_state[key] = z.get("waga", 0)

    with st.form("form_etap3"):
        imie = st.text_input("Imię i nazwisko zawodnika:", key="new_name")
        stano = st.selectbox("Stanowisko", dostepne, key="new_stanowisko")
        submit_add = st.form_submit_button("➕ Dodaj zawodnika")
        if submit_add:
            if imie.strip():
                sek = next((k for k, v in S["sektory"].items() if stano in v), None)
                if sek:
                    S["zawodnicy"].append({"imie": imie.strip(), "stanowisko": stano, "sektor": sek, "waga":0})
                    save_state()
                    st.experimental_rerun()
                else:
                    st.error("Wybrane stanowisko nie należy do żadnego sektora!")

    if st.button("⬅️ Wróć do sektorów"):
        S["etap"] = 2
        save_state()
        st.experimental_rerun()

    if st.button("➡️ Przejdź do wyników"):
        if len(S["zawodnicy"]) > 0:
            S["etap"] = 4
            save_state()
            st.experimental_rerun()
        else:
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
            col1, col2 = st.columns([2,1])
            with col1:
                st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            with col2:
                key = f"waga_{i}"
                waga = st.session_state.get(key, z.get("waga",0))
                new_waga = st.number_input("Waga (g)", 0, 120000, int(waga), step=10, key=key)
                st.session_state[key] = new_waga
                z["waga"] = new_waga

        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
            save_state()
            st.experimental_rerun()

        if st.button("🏆 Pokaż wyniki końcowe"):
            df = pd.DataFrame(S["zawodnicy"])
            df["waga"] = pd.to_numeric(df["waga"], errors="coerce").fillna(0)
            df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
            df_sorted = df.sort_values(by=["miejsce_w_sektorze","waga"], ascending=[True,False])

            st.subheader("📊 Ranking końcowy – wszyscy zawodnicy")
            st.dataframe(df_sorted, hide_index=True)

            st.subheader("📌 Wyniki sektorów")
            for sektor, grupa in df_sorted.groupby("sektor"):
                st.write(f"**Sektor {sektor}**")
                st.dataframe(grupa, hide_index=True)

            # Generowanie PDF
            def export_to_pdf(df, sektory_grouped):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4
                y = height - 40
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, y, "🎣 Wyniki zawodów wędkarskich")
                y -= 30

                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, y, "📊 Ranking końcowy – wszyscy zawodnicy")
                y -= 20
                c.setFont("Helvetica", 12)
                for i, row in df.iterrows():
                    miejsce = int(row['miejsce_w_sektorze'])
                    text = f"{i+1}. {row['imie']} | Sektor: {row['sektor']} | Stan.: {row['stanowisko']} | Waga: {row['waga']}g | Miejsce w sektorze: {miejsce}"
                    c.drawString(50, y, text[:90])
                    y -= 15
                    if y < 50:
                        c.showPage()
                        y = height - 40

                c.showPage()
                c.save()
                buffer.seek(0)
                return buffer

            pdf_file = export_to_pdf(df_sorted, df_sorted.groupby("sektor"))
            st.download_button(
                label="⬇️ Pobierz wyniki do PDF",
                data=pdf_file,
                file_name="wyniki_zawodow.pdf",
                mime="application/pdf"
            )


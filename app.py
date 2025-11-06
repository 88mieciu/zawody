import streamlit as st
import pandas as pd
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

# --- Ścieżka do pliku przechowującego dane ---
DATA_FILE = "zawody_data.json"

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

# --- Funkcja resetu ---
def reset_zawody():
    st.session_state["S"] = {
        "liczba_zawodnikow": 0,
        "liczba_stanowisk": 0,
        "liczba_sektorow": 0,
        "sektory": {},
        "zawodnicy": [],
        "etap": 1
    }
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

# --- Funkcja generowania PDF z wynikami ---
def generuj_pdf_reportlab(df_sorted):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    heading = styles['Heading1']

    # --- Ranking ogólny ---
    elements.append(Paragraph("📊 Ranking końcowy (wszyscy zawodnicy)", heading))
    elements.append(Spacer(1, 10))

    data = [["Miejsce", "Imię", "Sektor", "Stanowisko", "Waga", "Miejsce w sektorze"]]
    for _, row in df_sorted.iterrows():
        data.append([
            int(row['miejsce_ogolne']),
            row['imie'],
            row['sektor'],
            row['stanowisko'],
            row['waga'],
            int(row['miejsce_w_sektorze'])
        ])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # --- Podsumowanie sektorów ---
    elements.append(Paragraph("📌 Podsumowanie sektorów", heading))
    elements.append(Spacer(1, 10))

    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading2']))
        data = [["Imię", "Stanowisko", "Waga", "Miejsce w sektorze"]]
        for _, row in grupa.sort_values(by="waga", ascending=False).iterrows():
            data.append([
                row['imie'],
                row['stanowisko'],
                row['waga'],
                int(row['miejsce_w_sektorze'])
            ])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- Inicjalizacja stanu ---
if "S" not in st.session_state:
    dane = wczytaj_dane()
    if dane:
        st.session_state["S"] = dane
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

st.set_page_config(page_title="Zawody wędkarskie", layout="wide")
st.markdown("<h1 style='font-size:28px'>🎣 Panel organizatora zawodów wędkarskich by Wojtek Mierzejewski</h1>", unsafe_allow_html=True)

# --- PRZYCISK RESET ---
st.button("🧹 Resetuj zawody", on_click=reset_zawody)

# --- ETAP 1: KONFIGURACJA ---
if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 40, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 100, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 10, S["liczba_sektorow"] or 3)

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_dane(S)

# --- ETAP 2: DEFINICJA SEKTORÓW ---
elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)

    if S["liczba_zawodnikow"] > 0 and S["liczba_sektorow"] > 0:
        base = S["liczba_zawodnikow"] // S["liczba_sektorow"]
        remainder = S["liczba_zawodnikow"] % S["liczba_sektorow"]
        zawodnicy_info = []
        for i in range(S["liczba_sektorow"]):
            nazwa = chr(65 + i)
            ilosc = base + (1 if i < remainder else 0)
            zawodnicy_info.append(f"Sektor {nazwa}: {ilosc} zawodników")
        st.info("ℹ️ Przewidywana liczba zawodników na sektor:\n" + "\n".join(zawodnicy_info))
        if remainder != 0:
            st.warning(f"⚠️ Nie wszystkie sektory mają równą liczbę zawodników. Jeden sektor może mieć o 1 zawodnika więcej.")

    sektory = {}
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        pola = st.text_input(
            f"Sektor {nazwa} – podaj stanowiska (np. 1,2,3):",
            value=",".join(map(str, S["sektory"].get(nazwa, []))),
            key=f"sektor_{nazwa}"
        )
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
                zapisz_dane(S)
    with col2:
        if st.button("⬅️ Wstecz"):
            S["etap"] = 1
            zapisz_dane(S)

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
            zapisz_dane(S)
    with col2:
        if st.button("➡️ Przejdź do wprowadzenia wyników"):
            if len(S["zawodnicy"]) == 0:
                st.warning("⚠️ Najpierw dodaj zawodników.")
            else:
                S["etap"] = 4
                zapisz_dane(S)

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
                zapisz_dane(S)

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
                    zapisz_dane(S)
                    st.experimental_rerun()

# --- ETAP 4: WPROWADZANIE WYNIKÓW I PODSUMOWANIE ---
elif S["etap"] == 4:
    st.markdown("<h3 style='font-size:20px'>⚖️ Krok 4: Wprowadzenie wyników (waga ryb)</h3>", unsafe_allow_html=True)

    if not S["zawodnicy"]:
        st.warning("Brak zawodników. Wróć i dodaj ich najpierw.")
        if st.button("⬅️ Wróć do zawodników"):
            S["etap"] = 3
            zapisz_dane(S)
    else:
        for i,z in enumerate(S["zawodnicy"]):
            col1, col2 = st.columns([2,1])
            with col1:
                st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            with col2:
                z["waga"] = st.number_input("Waga (g)", 0, 100000, z["waga"], step=10, key=f"waga_{i}")
        zapisz_dane(S)

        # --- Wyświetlenie wyników ---
        df = pd.DataFrame(S["zawodnicy"])
        df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")
        df["miejsce_ogolne"] = df["waga"].rank(ascending=False, method="min")
        df_sorted = df.sort_values(by=["miejsce_ogolne","waga"], ascending=[True,False])

        st.markdown("<h4 style='font-size:18px'>📊 Ranking końcowy (wszyscy zawodnicy)</h4>", unsafe_allow_html=True)
        st.dataframe(df_sorted[["miejsce_ogolne","imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

        st.markdown("<h4 style='font-size:18px'>📌 Podsumowanie sektorów</h4>", unsafe_allow_html=True)
        for sektor, grupa in df_sorted.groupby("sektor"):
            st.write(f"**Sektor {sektor}**")
            tabela = grupa.sort_values(by="waga", ascending=False)[["imie","stanowisko","waga","miejsce_w_sektorze"]]
            st.dataframe(tabela, hide_index=True)

        # --- Pobieranie PDF ---
        pdf_bytes = generuj_pdf_reportlab(df_sorted)
        st.download_button(
            label="💾 Pobierz wyniki jako PDF",
            data=pdf_bytes,
            file_name="wyniki_zawodow.pdf",
            mime="application/pdf"
        )

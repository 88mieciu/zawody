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
FONT_FILE = "DejaVuSans.ttf"  # umieść plik czcionki w katalogu aplikacji

# --- Rejestracja czcionki (jeśli jest dostępna) ---
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
    st.session_state["S"] = {
        "nazwa_zawodow": "",
        "liczba_zawodnikow": 0,
        "liczba_stanowisk": 0,
        "liczba_sektorow": 0,
        "sektory": {},
        "zawodnicy": [],
        "etap": 1
    }
    if os.path.exists(DATA_FILE):
        try:
            os.remove(DATA_FILE)
        except:
            pass


def parse_positions(input_str):
    """
    Parsuje ciąg taki jak "1-5,7,10-12" na listę unikalnych intów: [1,2,3,4,5,7,10,11,12]
    Zwraca listę intów lub rzuca ValueError przy niepoprawnym formacie.
    """
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
            a = int(start.strip())
            b = int(end.strip())
            if a > b:
                raise ValueError(f"W zakresie początek nie może być większy niż koniec: '{p}'")
            positions.extend(list(range(a, b+1)))
        else:
            if not p.isdigit():
                raise ValueError(f"Niepoprawny numer stanowiska: '{p}'")
            positions.append(int(p))
    # unikalne, posortowane
    uniq = sorted(set(positions))
    return uniq


def parse_big_fish_sum(input_str):
    """
    Parsuje ciąg wag oddzielonych przecinkami, np. "500,1200, 350"
    Zwraca tuple (sum_of_valid_weights:int, invalid_parts:list)
    """
    if not input_str or not str(input_str).strip():
        return 0, []
    parts = [p.strip() for p in str(input_str).split(',') if p.strip()]
    total = 0
    invalid = []
    for p in parts:
        # dopuszczamy liczby całkowite dodatnie
        if p.lstrip('+-').isdigit():
            try:
                val = int(p)
                if val < 0:
                    invalid.append(p)
                else:
                    total += val
            except:
                invalid.append(p)
        else:
            invalid.append(p)
    return total, invalid


def generuj_pdf_reportlab(df_sorted, nazwa_zawodow=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # jeżeli zarejestrowaliśmy czcionkę, ustawiamy jej użycie w stylach
    if FONT_AVAILABLE:
        for name in ['Heading1','Heading2','Heading3','Normal']:
            try:
                styles[name].fontName = 'DejaVu'
            except Exception:
                pass

    # --- Nagłówek z nazwą zawodów ---
    if nazwa_zawodow:
        h1 = styles['Heading1']
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", h1))
        elements.append(Spacer(1, 12))

    # --- Ranking ogólny (pokazuje tylko końcową wagę) ---
    h2 = styles['Heading2']
    elements.append(Paragraph("📊 Ranking końcowy (wszyscy zawodnicy)", h2))
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

    # --- Podsumowanie sektorów (pokazuje tylko końcową wagę) ---
    elements.append(Paragraph("📌 Podsumowanie sektorów", h2))
    elements.append(Spacer(1, 8))
    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading3']))
        data = [["Imię", "Stanowisko", "Waga (g)", "Miejsce w sektorze", "Miejsce ogólne"]]
        for _, row in grupa.sort_values(by="waga", ascending=False).iterrows():
            data.append([
                row['imie'],
                row['stanowisko'],
                row.get('waga', 0),
                int(row['miejsce_w_sektorze']),
                int(row['miejsce_ogolne'])
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
        elements.append(Spacer(1, 12))

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
            "nazwa_zawodow": "",
            "liczba_zawodnikow": 0,
            "liczba_stanowisk": 0,
            "liczba_sektorow": 0,
            "sektory": {},
            "zawodnicy": [],
            "etap": 1
        }

S = st.session_state["S"]

# ustawienia strony
st.set_page_config(page_title="Zawody wędkarskie", layout="wide")
st.markdown(
    "<h1 style='font-size:28px; text-align:center'>🎣🏆 Panel organizatora zawodów wędkarskich 🏆🎣</h1>",
    unsafe_allow_html=True
)

# informacja o braku czcionki (jeśli nie ma pliku)
if not FONT_AVAILABLE:
    st.warning("Aby PDF poprawnie wyświetlał polskie znaki, umieść plik 'DejaVuSans.ttf' w katalogu aplikacji.")

# --- PRZYCISK RESET ---
st.button("🧹 Resetuj zawody", on_click=reset_zawody)

# --- ETAP 1: KONFIGURACJA ---
if S["etap"] == 1:
    st.markdown("<h3 style='font-size:20px'>⚙️ Krok 1: Ustawienia zawodów</h3>", unsafe_allow_html=True)
    S["nazwa_zawodow"] = st.text_input("Nazwa zawodów:", S.get("nazwa_zawodow", ""))
    S["liczba_zawodnikow"] = st.number_input("Liczba zawodników:", 1, 200, S["liczba_zawodnikow"] or 10)
    S["liczba_stanowisk"] = st.number_input("Liczba stanowisk na łowisku:", 1, 1000, S["liczba_stanowisk"] or 10)
    S["liczba_sektorow"] = st.number_input("Liczba sektorów:", 1, 50, S["liczba_sektorow"] or 3)

    if st.button("➡️ Dalej – definiuj sektory"):
        S["etap"] = 2
        zapisz_dane(S)

# --- ETAP 2: DEFINICJA SEKTORÓW (z obsługą zakresów) ---
elif S["etap"] == 2:
    st.markdown("<h3 style='font-size:20px'>📍 Krok 2: Definicja sektorów</h3>", unsafe_allow_html=True)

    # Informacja o przewidywanej liczbie zawodników w sektorach
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

    st.markdown("_W polu możesz wpisać pojedyncze numery i zakresy, np.: `1-5,7,10-12`_")

    sektory_tmp = {}
    # pokaż istniejące wartości jeśli są
    for i in range(S["liczba_sektorow"]):
        nazwa = chr(65 + i)
        current = S["sektory"].get(nazwa, [])
        default = ",".join(map(str, current)) if current else ""
        pola = st.text_input(f"Sektor {nazwa} – podaj stanowiska (np. 1-5,7,10-12):", value=default, key=f"sektor_{nazwa}")
        sektory_tmp[nazwa] = pola

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("💾 Zapisz sektory"):
            # spróbuj sparsować wszystkie sektory i wykryć duplikaty
            parsed = {}
            all_positions = []
            error = False
            error_msgs = []
            for nazwa, tekst in sektory_tmp.items():
                try:
                    positions = parse_positions(tekst)
                except ValueError as e:
                    error = True
                    error_msgs.append(f"Sektor {nazwa}: {e}")
                    positions = []
                parsed[nazwa] = positions
                all_positions.extend(positions)

            # sprawdź duplikaty między sektorami
            dup = sorted([x for x in set(all_positions) if all_positions.count(x) > 1])
            if dup:
                error = True
                error_msgs.append(f"Powtórzone stanowiska między sektorami: {dup}")

            if error:
                for m in error_msgs:
                    st.error(m)
            else:
                S["sektory"] = parsed
                S["etap"] = 3
                zapisz_dane(S)
                st.success("Sektory zapisane.")
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
                # dodajemy pole big_fish_raw jako string (puste domyślnie)
                S["zawodnicy"].append(
                    {"imie": imie.strip(), "stanowisko": stano, "sektor": sek, "waga": 0, "big_fish_raw": ""}
                )
                zapisz_dane(S)

    if S["zawodnicy"]:
        st.subheader("📋 Lista zawodników")
        for i, z in enumerate(S["zawodnicy"]):
            col1, col2, col3 = st.columns([2,1,1])
            with col1:
                z["imie"] = st.text_input(f"Zawodnik {i+1}", z["imie"], key=f"imie_{i}")
                # pole wagi pod imieniem
                z["waga"] = st.number_input("Waga główna (g)", 0, 1000000, z.get("waga", 0), step=10, key=f"waga_{i}")
                # pole big fish (surowy string) - zapisujemy surowy wpis
                z["big_fish_raw"] = st.text_input("Big fish (g) — wpisz wagi oddzielone przecinkami (np. 500,1200):", value=z.get("big_fish_raw",""), key=f"bigfish_{i}")
                # NIE wyświetlamy sum big fish ani totalu tutaj
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
        # Wprowadzanie wag i big fish: zapisujemy surowe dane, przeliczamy sumę i dodajemy do z['waga']
        for i, z in enumerate(S["zawodnicy"]):
            st.write(f"**{z['imie']}** ({z['sektor']}, st. {z['stanowisko']})")
            # waga główna (edytowalna)
            waga_bazowa = st.number_input("Waga główna (g)", 0, 10000000, z.get("waga", 0), step=10, key=f"waga_bazowa_{i}")
            # big fish raw (surowy string)
            big_raw = st.text_input("Big fish (g) — wpisz wagi oddzielone przecinkami (np. 500,1200):", value=z.get("big_fish_raw",""), key=f"big_raw_{i}")
            # zapisz surowy string
            z["big_fish_raw"] = big_raw

            # oblicz sumę big fish (ale NIE wyświetlamy sumy ani totalu użytkownikowi)
            big_sum, invalid = parse_big_fish_sum(big_raw)
            # jeśli są nieprawidłowe części, pokaż ostrzeżenie ale nie blokuj
            if invalid:
                st.warning(f"Nieprawidłowe wartości Big fish dla {z['imie']}: {invalid} — zostaną zignorowane przy sumowaniu.")
            # finalna waga zapisana do z['waga'] — nadpisujemy waga bazowa + suma big fish
            z["waga"] = waga_bazowa + big_sum

        zapisz_dane(S)

        # Przygotowanie DataFrame na potrzeby rankingów:
        df = pd.DataFrame(S["zawodnicy"]).copy()
        # miejsce w sektorze liczone po z['waga'] (już zawiera big fish sumę)
        df["miejsce_w_sektorze"] = df.groupby("sektor")["waga"].rank(ascending=False, method="min")

        # Ranking ogólny wg miejsc sektorowych (1-ki sektorowe najpierw)
        df_sorted = pd.DataFrame()
        for miejsce in sorted(df["miejsce_w_sektorze"].unique()):
            grupa = df[df["miejsce_w_sektorze"] == miejsce].sort_values(by="waga", ascending=False)
            df_sorted = pd.concat([df_sorted, grupa])
        df_sorted["miejsce_ogolne"] = range(1, len(df_sorted)+1)

        # Wyświetlenie tabel wyników: pokazujemy tylko końcową wagę (z['waga'])
        st.markdown("<h4 style='font-size:18px'>📊 Ranking końcowy (wszyscy zawodnicy)</h4>", unsafe_allow_html=True)
        st.dataframe(df_sorted[["miejsce_ogolne","imie","sektor","stanowisko","waga","miejsce_w_sektorze"]], hide_index=True)

        st.markdown("<h4 style='font-size:18px'>📌 Podsumowanie sektorów</h4>", unsafe_allow_html=True)
        for sektor, grupa in df_sorted.groupby("sektor"):
            st.write(f"**Sektor {sektor}**")
            tabela = grupa.sort_values(by="waga", ascending=False)[["imie","stanowisko","waga","miejsce_w_sektorze","miejsce_ogolne"]]
            st.dataframe(tabela, hide_index=True)

        st.info("ℹ️ Na telefonie po kliknięciu przycisku Pobierz PDF może pojawić się komunikat przeglądarki. Potwierdź go, aby pobrać plik.")
        pdf_bytes = generuj_pdf_reportlab(df_sorted, S.get("nazwa_zawodow", ""))
        st.download_button(
            label="💾 Pobierz wyniki jako PDF",
            data=pdf_bytes,
            file_name="wyniki_zawodow.pdf",
            mime="application/pdf"
        )

# --- Stopka ---
st.markdown(
    "<h1 style='font-size:14px; text-align:center'>© Wojciech Mierzejewski 2026</h1>",
    unsafe_allow_html=True
)

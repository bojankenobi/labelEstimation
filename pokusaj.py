import streamlit as st
import math
import pandas as pd
import datetime
import numpy as np
from supabase import create_client, Client # Dodato za Supabase
import os # Dodato za proveru secrets

# --- Konstante ---
# ... (Konstante ostaju iste) ...
PITCH = 3.175; GAP_MIN = 2.5; GAP_MAX = 4.0; Z_MIN = 70; Z_MAX = 140
SIRINA_CILINDRA_UKUPNA = 200; SIRINA_RADNA = 190; RAZMAK_SIRINA = 5
OTPAD_SIRINA = 10; MAX_SIRINA_MATERIJALA = 200
DUZINA_SKART_OSNOVA = 50.0; DUZINA_SKART_PO_BOJI = 50.0
VREME_PRIPREME_PO_BOJI_ILI_OSNOVA = 30; VREME_RASPREME_MIN = 30
BRZINA_MASINE_DEFAULT = 30; BRZINA_MASINE_MIN = 10; BRZINA_MASINE_MAX = 120
GRAMA_BOJE_PO_M2 = 3.0; GRAMA_LAKA_PO_M2 = 4.0
CENA_BOJE_PO_KG_DEFAULT = 2350.0; CENA_LAKA_PO_KG_DEFAULT = 1800.0
CENA_RADA_MASINE_PO_SATU_DEFAULT = 3000.0
CENA_ALATA_POLUROTACIONI_DEFAULT = 6000.0; CENA_ALATA_ROTACIONI_DEFAULT = 8000.0
KOEFICIJENT_ZARADE_DEFAULT = 0.20; CENA_KLISEA_PO_BOJI_DEFAULT = 2000.0
DEFAULT_MATERIJALI_CENE = {"Papir (hrom)": 39.95, "Plastika (PPW)": 54.05, "Termopapir": 49.35}

# --- Supabase Podešavanja ---
SUPABASE_TABLE_NAME = "kalkulacije" # Ime vaše tabele u Supabase

# --- Funkcija za inicijalizaciju Supabase klijenta ---
@st.cache_resource # Keširaj konekciju
def init_supabase_client():
    """Inicijalizuje i vraća Supabase klijenta koristeći st.secrets."""
    try:
        # Proveri da li su secrets podešeni
        if "supabase" in st.secrets and "url" in st.secrets["supabase"] and "anon_key" in st.secrets["supabase"]:
            url: str = st.secrets["supabase"]["url"]
            key: str = st.secrets["supabase"]["anon_key"]
            # Proveri da li su vrednosti zaista prisutne
            if not url or not key:
                 st.error("Supabase URL ili Ključ nedostaju u Streamlit Secrets.")
                 return None
            st.success("Supabase secrets pronađeni. Inicijalizujem klijenta...")
            return create_client(url, key)
        else:
            st.error("Supabase konfiguracija nije pronađena u Streamlit Secrets. Proverite `secrets.toml` ili podešavanja na Streamlit Cloud.")
            # Fallback na env variable ako secrets ne postoje (manje preporučljivo za deploy)
            # url = os.environ.get("SUPABASE_URL")
            # key = os.environ.get("SUPABASE_ANON_KEY")
            # if url and key:
            #     st.warning("Koristim Supabase kredencijale iz environment varijabli (fallback).")
            #     return create_client(url, key)
            # else:
            #     st.error("Supabase URL/Ključ nisu pronađeni ni u secrets ni u env varijablama.")
            return None
    except Exception as e:
        st.error(f"Greška pri inicijalizaciji Supabase klijenta: {e}")
        return None

# Inicijalizuj Supabase klijenta
supabase: Client = init_supabase_client()

# --- Inicijalizacija Session State ---
# ... (Ostatak inicijalizacije session state ostaje isti) ...
if 'materijali_cene' not in st.session_state: st.session_state.materijali_cene = DEFAULT_MATERIJALI_CENE.copy()
if 'cena_boje_po_kg' not in st.session_state: st.session_state.cena_boje_po_kg = CENA_BOJE_PO_KG_DEFAULT
if 'cena_laka_po_kg' not in st.session_state: st.session_state.cena_laka_po_kg = CENA_LAKA_PO_KG_DEFAULT
if 'cena_rada_masine_po_satu' not in st.session_state: st.session_state.cena_rada_masine_po_satu = CENA_RADA_MASINE_PO_SATU_DEFAULT
if 'cena_alata_polurotacioni' not in st.session_state: st.session_state.cena_alata_polurotacioni = CENA_ALATA_POLUROTACIONI_DEFAULT
if 'cena_alata_rotacioni' not in st.session_state: st.session_state.cena_alata_rotacioni = CENA_ALATA_ROTACIONI_DEFAULT
if 'postojeci_alat_info' not in st.session_state: st.session_state.postojeci_alat_info = ""
if 'cena_klisea_po_boji' not in st.session_state: st.session_state.cena_klisea_po_boji = CENA_KLISEA_PO_BOJI_DEFAULT

# Inicijalizacija za poslednji ID iz Supabase
if 'last_saved_id' not in st.session_state:
    st.session_state.last_saved_id = 0
    if supabase:
        try:
            # Dovući najveći 'Kalkulacija_Broj' iz baze
            response = supabase.table(SUPABASE_TABLE_NAME)\
                             .select("Kalkulacija_Broj")\
                             .order("Kalkulacija_Broj", desc=True)\
                             .limit(1)\
                             .execute()
            if response.data:
                # Proveri da li je Kalkulacija_Broj None pre konverzije
                max_id_val = response.data[0].get("Kalkulacija_Broj")
                if max_id_val is not None:
                    st.session_state.last_saved_id = int(max_id_val)
                else:
                    st.session_state.last_saved_id = 0 # Ako je null u bazi, počni od 0
            st.info(f"Poslednji ID kalkulacije u bazi: {st.session_state.last_saved_id}")
        except Exception as e:
            st.warning(f"Nije moguće pročitati poslednji ID iz Supabase: {e}. Počinje se od 0.")
            st.session_state.last_saved_id = 0

# --- Funkcije Kalkulacija ---
# ... (sve funkcije kalkulacija ostaju iste: pronadji_specifikacije_cilindra, itd.) ...
def pronadji_specifikacije_cilindra(sirina_sablona_W):
    validna_resenja = []; message = ""
    if sirina_sablona_W <= 0: return None, [], "Greška: Širina šablona mora biti > 0."
    for z in range(Z_MIN, Z_MAX + 1):
        obim_C = z * PITCH
        if (sirina_sablona_W + GAP_MIN) <= 1e-9: continue
        n_max_moguce = math.floor(obim_C / (sirina_sablona_W + GAP_MIN))
        for n in range(1, n_max_moguce + 1):
            if n == 0: continue
            razmak_G_obim = (obim_C / n) - sirina_sablona_W
            tolerancija = 1e-9
            if (GAP_MIN - tolerancija) <= razmak_G_obim <= (GAP_MAX + tolerancija):
                validna_resenja.append({"broj_zuba_Z": z, "obim_mm": obim_C, "broj_sablona_N_obim": n, "razmak_G_obim_mm": razmak_G_obim})
    if not validna_resenja:
        message = f"Nije pronađen cilindar ({Z_MIN}-{Z_MAX} zuba) za W={sirina_sablona_W:.3f}mm sa G={GAP_MIN:.1f}-{GAP_MAX:.1f}mm."
        return None, [], message
    validna_resenja.sort(key=lambda x: (x["broj_zuba_Z"], -x["broj_sablona_N_obim"]))
    return validna_resenja[0], validna_resenja, "Proračun za obim OK."

def izracunaj_broj_po_sirini(visina_sablona_H, sirina_radna, razmak_sirina):
    if visina_sablona_H <= 0: return 0
    if visina_sablona_H > sirina_radna: return 0
    if visina_sablona_H <= sirina_radna and (visina_sablona_H * 2 + razmak_sirina) > sirina_radna: return 1
    denominator = visina_sablona_H + razmak_sirina
    if denominator <= 1e-9: return 0
    return int(math.floor((sirina_radna + razmak_sirina) / denominator))

def izracunaj_sirinu_materijala(broj_po_sirini_y, visina_sablona_H, razmak_sirina, otpad_sirina):
    if broj_po_sirini_y <= 0: return 0
    sirina_sablona_ukupno = broj_po_sirini_y * visina_sablona_H
    sirina_razmaka_ukupno = max(0, broj_po_sirini_y - 1) * razmak_sirina
    return sirina_sablona_ukupno + sirina_razmaka_ukupno + otpad_sirina

def format_time(total_minutes):
    if total_minutes is None or not isinstance(total_minutes, (int, float)) or total_minutes < 0:
         return "N/A" # Vrati N/A ako je None, nije broj ili je negativan
    total_minutes = round(total_minutes)
    if total_minutes == 0: return "0 min"
    if total_minutes < 60: return f"{int(total_minutes)} min"
    hours, minutes = divmod(total_minutes, 60)
    if minutes == 0: return f"{int(hours)} h"
    return f"{int(hours)} h {int(minutes)} min"

# --- Funkcija za upis reda u Supabase ---
def save_calculation_to_supabase(supabase_client: Client, data_dict: dict):
    """Upisuje jedan red podataka (kao rečnik) u Supabase tabelu."""
    if not supabase_client:
        st.error("Nije moguće sačuvati, nema konekcije sa Supabase.")
        return False, None # Vrati False i None za ID
    try:
        # Ukloni None vrednosti da ne bi slao null tamo gde Supabase možda ne očekuje
        # ili da bi koristio default vrednosti iz baze ako postoje
        # data_to_insert = {k: v for k, v in data_dict.items() if v is not None}
        # Oprez: Ako kolona u Supabase *jeste* nullable, slanje None je u redu.
        # Za sada šaljemo sve kako jeste.
        response = supabase_client.table(SUPABASE_TABLE_NAME).insert(data_dict).execute()

        # Provera da li je upis uspeo (Supabase obično vraća podatke ako uspe)
        if response.data:
             saved_id = data_dict.get("Kalkulacija_Broj", "Nepoznat") # Uzmi ID koji smo mi dodelili
             return True, saved_id
        else:
            # Ako nema 'data', verovatno je došlo do greške koju API nije prijavio kao exception
            st.error(f"Supabase upis nije uspeo. Odgovor: {response}")
            # Pokušaj da izvučeš grešku ako postoji u odgovoru
            if hasattr(response, 'error') and response.error:
                 st.error(f"Detalji greške: {response.error}")
            return False, None

    except Exception as e:
        st.error(f"Neočekivana greška prilikom upisa u Supabase: {e}")
        # Detaljniji ispis greške ako je API greška
        if hasattr(e, 'message'):
            st.error(f"Detalji API greške: {e.message}")
        return False, None


# --- Funkcija za pretragu Supabase-a ---
@st.cache_data(ttl=60) # Keširaj rezultate pretrage na 60 sekundi
def search_supabase(_supabase_client: Client, search_term: str, search_columns: list):
    """Pretražuje Supabase tabelu i vraća rezultate kao DataFrame."""
    if not _supabase_client:
        st.warning("Nije moguće pretražiti, nema konekcije sa Supabase.")
        return pd.DataFrame() # Vrati prazan DataFrame

    search_term_pattern = f"%{search_term}%" # Obrazac za ILIKE (case-insensitive)

    try:
        # Kreiraj .or() filter string za pretragu više kolona
        # Format: "column1.ilike.%term%,column2.ilike.%term%,..."
        # Filtriraj kolone koje nisu tipa 'text' za ilike pretragu,
        # ili konvertuj search_term u broj ako je moguće za numeričke kolone.
        # Za jednostavnost, pretražujemo samo tekstualne kolone sa ILIKE.
        # Možete dodati složeniju logiku za pretragu brojeva ako je potrebno.
        text_search_parts = []
        numeric_search_parts = []

        # Definiši koje kolone su numeričke da probaš direktno poređenje
        numeric_cols_in_db = ["Sirina_W", "Visina_H", "Tiraz", "Broj_Boja", "Zuba_Z"] # Dodaj po potrebi

        for col in search_columns:
             # ILIKE radi samo na tekstualnim tipovima u Postgres-u
             # Za brojeve bismo koristili eq, gt, lt itd.
             # Najjednostavnije je za sada pretraživati samo glavna tekstualna polja
             if col not in numeric_cols_in_db:
                  text_search_parts.append(f"{col}.ilike.{search_term_pattern}")

             # Opciono: Ako je unos broj, probaj i numeričke kolone
             # if search_term.replace('.','',1).isdigit() and col in numeric_cols_in_db:
             #    try:
             #        num_val = float(search_term)
             #        # Koristi 'eq' za tačno poklapanje broja
             #        # Možda nije idealno za dimenzije, ali za ID/Tiraž može biti korisno
             #        numeric_search_parts.append(f"{col}.eq.{num_val}")
             #    except ValueError:
             #        pass # Nije validan broj

        # Spoji sve delove filtera
        filter_parts = text_search_parts # + numeric_search_parts # Za sada samo tekst
        if not filter_parts:
             st.warning("Nema definisanih validnih kolona za tekstualnu pretragu.")
             return pd.DataFrame()

        or_filter = ",".join(filter_parts)

        # Izvrši upit
        response = _supabase_client.table(SUPABASE_TABLE_NAME)\
                                  .select("*")\
                                  .or_(or_filter)\
                                  .order("created_at", desc=True) # Sortiraj po datumu kreiranja
                                  .execute()

        if response.data:
            # Konvertuj rezultat u DataFrame
            df = pd.DataFrame(response.data)
            # Opciono: Preuredi kolone ili preimenuj za bolji prikaz
            # df = df[['Kalkulacija_Broj', 'Klijent', 'Proizvod', ...]] # Izaberi redosled
            return df
        else:
            # Nema rezultata ili greška (koju .execute() nije uhvatio kao exception)
            if hasattr(response, 'error') and response.error:
                 st.error(f"Greška prilikom pretrage Supabase: {response.error}")
            return pd.DataFrame() # Vrati prazan DataFrame

    except Exception as e:
        st.error(f"Neočekivana greška prilikom pretrage Supabase: {e}")
        if hasattr(e, 'message'):
            st.error(f"Detalji API greške: {e.message}")
        return pd.DataFrame() # Vrati prazan DataFrame u slučaju greške


# --- Streamlit Aplikacija ---
st.set_page_config(page_title="Kalkulacija Štampe", layout="wide")
st.title("📊 Kalkulator Troškova Štampe Etiketa (Supabase)") # Dodato u naslov

# Provera Supabase konekcije na vrhu
if not supabase:
    st.error("❌ KRITIČNO: Neuspešna konekcija sa Supabase bazom podataka. Proverite podešavanja (secrets) i status Supabase projekta.")
    # Možete zaustaviti izvršavanje ostatka aplikacije ako je baza neophodna
    st.stop()
else:
    st.success("✅ Uspešno povezan sa Supabase.")


# --- Input Polja ---
col_info1, col_info2 = st.columns(2)
with col_info1: client_name = st.text_input("Ime Klijenta:")
with col_info2: product_name = st.text_input("Naziv Proizvoda/Etikete:")
st.markdown("---")
st.markdown("Unesite parametre štampe. Rezultati se mogu sačuvati u Supabase bazu.")

# --- Sidebar ---
# ... (Sidebar kod ostaje potpuno isti kao u prethodnoj verziji) ...
st.sidebar.header("Parametri Unosa")
sirina_W_input = st.sidebar.number_input("Širina šablona (po obimu, mm):", 0.1, value=76.0, step=0.1, format="%.3f")
visina_H_input = st.sidebar.number_input("Visina šablona (po širini cil., mm):", 0.1, value=76.0, step=0.1, format="%.3f")
tiraz_input = st.sidebar.number_input("Željeni Tiraž (komada):", 1, value=100000, step=1000, format="%d")

st.sidebar.markdown("---"); st.sidebar.subheader("Podešavanje Boja, Laka i Klišea") # Promenjen naslov
is_blanko = st.sidebar.checkbox("Blanko Šablon (bez boje)", value=False, help="Bez troška boje i klišea.")
broj_boja_input = st.sidebar.number_input("Broj Boja:", 1, 8, value=1, step=1, format="%d", disabled=is_blanko)
is_uv_lak_input = st.sidebar.checkbox("UV Lak", value=False, help=f"Dodaje trošak UV laka ({GRAMA_LAKA_PO_M2}g/m²).")
trenutna_cena_boje = st.session_state.cena_boje_po_kg; cena_boje_kg_input = st.sidebar.number_input("Cena boje (RSD/kg):", 0.0, value=trenutna_cena_boje, step=10.0, format="%.2f", help=f"Def: {CENA_BOJE_PO_KG_DEFAULT:.2f}")
if cena_boje_kg_input != trenutna_cena_boje: st.session_state.cena_boje_po_kg = cena_boje_kg_input
trenutna_cena_laka = st.session_state.cena_laka_po_kg; cena_laka_kg_input = st.sidebar.number_input("Cena UV laka (RSD/kg):", 0.0, value=trenutna_cena_laka, step=10.0, format="%.2f", help=f"Def: {CENA_LAKA_PO_KG_DEFAULT:.2f}")
if cena_laka_kg_input != trenutna_cena_laka: st.session_state.cena_laka_po_kg = cena_laka_kg_input
trenutna_cena_klisea = st.session_state.cena_klisea_po_boji
cena_klisea_input = st.sidebar.number_input("Cena klišea po boji (RSD):", 0.0, value=trenutna_cena_klisea, step=50.0, format="%.2f", help=f"Jednokratni trošak po boji štampe. Def: {CENA_KLISEA_PO_BOJI_DEFAULT:.2f}")
if cena_klisea_input != trenutna_cena_klisea: st.session_state.cena_klisea_po_boji = cena_klisea_input

st.sidebar.markdown("---"); st.sidebar.subheader("Mašina")
brzina_masine_m_min = st.sidebar.slider("Prosečna brzina mašine (m/min):", BRZINA_MASINE_MIN, BRZINA_MASINE_MAX, BRZINA_MASINE_DEFAULT, 5)
trenutna_cena_rada = st.session_state.cena_rada_masine_po_satu; cena_rada_h_input = st.sidebar.number_input("Cena rada mašine (RSD/h):", 0.0, value=trenutna_cena_rada, step=50.0, format="%.2f", help=f"Def: {CENA_RADA_MASINE_PO_SATU_DEFAULT:.2f}")
if cena_rada_h_input != trenutna_cena_rada: st.session_state.cena_rada_masine_po_satu = cena_rada_h_input

st.sidebar.markdown("---"); st.sidebar.subheader("Alat za Isecanje")
tip_alata_options_keys = ["Nijedan", "Polurotacioni", "Rotacioni"]; izabrani_alat_kljuc = st.sidebar.radio("Izaberite tip alata:", options=tip_alata_options_keys, index=0, key="tip_alata_radio")
postojeci_alat_info_input = "" # Privremena promenljiva za unos
if izabrani_alat_kljuc == "Nijedan":
    postojeci_alat_info_input = st.sidebar.text_input("Broj/Naziv postojećeg alata:", value=st.session_state.get('postojeci_alat_info', ''), help="Unesite oznaku alata koji već imate.")
    st.session_state.postojeci_alat_info = postojeci_alat_info_input # Ažuriraj stanje
else:
    # Resetuj info ako je izabran drugi tip alata
    st.session_state.postojeci_alat_info = ""

trenutna_cena_polu = st.session_state.cena_alata_polurotacioni; cena_alata_polu_input = st.sidebar.number_input("Cena polurotacionog alata (RSD):", 0.0, value=trenutna_cena_polu, step=100.0, format="%.2f", help=f"Def: {CENA_ALATA_POLUROTACIONI_DEFAULT:.2f}")
if cena_alata_polu_input != trenutna_cena_polu: st.session_state.cena_alata_polurotacioni = cena_alata_polu_input
trenutna_cena_rot = st.session_state.cena_alata_rotacioni; cena_alata_rot_input = st.sidebar.number_input("Cena rotacionog alata (RSD):", 0.0, value=trenutna_cena_rot, step=100.0, format="%.2f", help=f"Def: {CENA_ALATA_ROTACIONI_DEFAULT:.2f}")
if cena_alata_rot_input != trenutna_cena_rot: st.session_state.cena_alata_rotacioni = cena_alata_rot_input

st.sidebar.markdown("---"); st.sidebar.subheader("Materijal")
lista_materijala = list(st.session_state.materijali_cene.keys()); izabrani_materijal = st.sidebar.selectbox("Izaberite vrstu materijala:", options=lista_materijala, index=0)
trenutna_cena_materijala = st.session_state.materijali_cene.get(izabrani_materijal, 0.0); material_price_label_formatted = f"Cena za '{izabrani_materijal}' (RSD/m²):"
cena_po_m2_input = st.sidebar.number_input(material_price_label_formatted, 0.0, value=trenutna_cena_materijala, step=0.1, format="%.2f")
if cena_po_m2_input != trenutna_cena_materijala: st.session_state.materijali_cene[izabrani_materijal] = cena_po_m2_input

st.sidebar.markdown("---"); st.sidebar.subheader("Koeficijent Zarade")
koeficijent_zarade_input = st.sidebar.slider("Koeficijent zarade (na cenu materijala):", 0.01, 2.00, KOEFICIJENT_ZARADE_DEFAULT, 0.01, format="%.2f", help=f"Def: {KOEFICIJENT_ZARADE_DEFAULT:.2f}")


# --- Proračun i Prikaz Rezultata ---
inputs_valid = sirina_W_input and visina_H_input and tiraz_input > 0 and brzina_masine_m_min and izabrani_materijal and cena_po_m2_input is not None and cena_rada_h_input is not None and izabrani_alat_kljuc is not None and koeficijent_zarade_input is not None

if inputs_valid:
    # 1. Obim; 2. Širina ('y')
    best_solution_obim, all_solutions_obim, message_obim = pronadji_specifikacije_cilindra(sirina_W_input)
    broj_po_sirini_y = izracunaj_broj_po_sirini(visina_H_input, SIRINA_RADNA, RAZMAK_SIRINA)

    # Provera da li je proračun uspeo pre nego što nastavimo
    if best_solution_obim and broj_po_sirini_y >= 0:
        st.header("📊 Rezultati Kalkulacije")

        # --- Izračunate vrednosti (isto kao pre) ---
        # ... (ceo blok izračunavanja vrednosti ostaje isti kao u prethodnoj verziji) ...
        broj_po_obimu_x = best_solution_obim['broj_sablona_N_obim']
        razmak_G_obim_mm = best_solution_obim['razmak_G_obim_mm']
        ukupno_sablona_po_ciklusu = broj_po_sirini_y * broj_po_obimu_x
        valid_broj_boja_za_calc = 0 if is_blanko else (broj_boja_input if broj_boja_input is not None and broj_boja_input >= 1 else 1)
        sirina_materijala_potrebna_mm = izracunaj_sirinu_materijala(broj_po_sirini_y, visina_H_input, RAZMAK_SIRINA, OTPAD_SIRINA)
        prekoracena_sirina_materijala = sirina_materijala_potrebna_mm > MAX_SIRINA_MATERIJALA

        ukupna_duzina_proizvodnja_m = 0.0; ukupna_kvadratura_proizvodnja_m2 = 0.0; poruka_potrosnja_proizvodnja = ""
        if broj_po_sirini_y > 0 and broj_po_obimu_x > 0 and ukupno_sablona_po_ciklusu > 0:
             duzina_segmenta_mm = sirina_W_input + razmak_G_obim_mm
             broj_ciklusa = math.ceil(tiraz_input / ukupno_sablona_po_ciklusu)
             ukupna_duzina_proizvodnja_m = broj_ciklusa * best_solution_obim['obim_mm'] / 1000.0
             if sirina_materijala_potrebna_mm > 0:
                 ukupna_kvadratura_proizvodnja_m2 = ukupna_duzina_proizvodnja_m * (sirina_materijala_potrebna_mm / 1000.0)
             else: poruka_potrosnja_proizvodnja = "Širina materijala je 0, kvadratura N/A."
        else: poruka_potrosnja_proizvodnja = "Format (x ili y) je 0, potrošnja N/A."

        duzina_skart_m = 0.0; kvadratura_skart_m2 = 0.0; opis_skarta = ""
        broj_boja_za_skart_vreme = 1 if is_blanko else valid_broj_boja_za_calc
        if is_blanko: duzina_skart_m = DUZINA_SKART_OSNOVA; opis_skarta = f"Blanko ({DUZINA_SKART_OSNOVA}m)"
        else: duzina_skart_m = DUZINA_SKART_OSNOVA + (valid_broj_boja_za_calc * DUZINA_SKART_PO_BOJI); opis_skarta = f"{valid_broj_boja_za_calc} boj{'a' if valid_broj_boja_za_calc==1 else 'e'} ({DUZINA_SKART_OSNOVA}+{valid_broj_boja_za_calc}×{DUZINA_SKART_PO_BOJI}m)"
        if sirina_materijala_potrebna_mm > 0: kvadratura_skart_m2 = duzina_skart_m * (sirina_materijala_potrebna_mm / 1000.0)

        ukupna_duzina_final_m = ukupna_duzina_proizvodnja_m + duzina_skart_m
        ukupna_kvadratura_final_m2 = ukupna_kvadratura_proizvodnja_m2 + kvadratura_skart_m2

        vreme_pripreme_min = broj_boja_za_skart_vreme * VREME_PRIPREME_PO_BOJI_ILI_OSNOVA
        vreme_proizvodnje_min = (ukupna_duzina_proizvodnja_m / brzina_masine_m_min) if ukupna_duzina_proizvodnja_m > 0 and brzina_masine_m_min > 0 else 0.0
        vreme_raspreme_min = VREME_RASPREME_MIN; ukupno_vreme_min = vreme_pripreme_min + vreme_proizvodnje_min + vreme_raspreme_min

        cena_boje_rsd = 0.0; potrosnja_boje_kg = 0.0; cena_laka_rsd = 0.0; potrosnja_laka_kg = 0.0
        if not is_blanko and valid_broj_boja_za_calc > 0 and ukupna_kvadratura_proizvodnja_m2 > 0:
             potrosnja_boje_g = ukupna_kvadratura_proizvodnja_m2 * valid_broj_boja_za_calc * GRAMA_BOJE_PO_M2; potrosnja_boje_kg = potrosnja_boje_g / 1000.0; cena_boje_rsd = potrosnja_boje_kg * st.session_state.cena_boje_po_kg
        if is_uv_lak_input and ukupna_kvadratura_proizvodnja_m2 > 0:
             potrosnja_laka_g = ukupna_kvadratura_proizvodnja_m2 * GRAMA_LAKA_PO_M2; potrosnja_laka_kg = potrosnja_laka_g / 1000.0; cena_laka_rsd = potrosnja_laka_kg * st.session_state.cena_laka_po_kg
        ukupna_cena_boja_lak_rsd = cena_boje_rsd + cena_laka_rsd

        ukupna_cena_klisea_rsd = 0.0
        if not is_blanko and valid_broj_boja_za_calc > 0:
             ukupna_cena_klisea_rsd = valid_broj_boja_za_calc * st.session_state.cena_klisea_po_boji

        ukupna_cena_materijala_rsd = 0.0
        if ukupna_kvadratura_final_m2 > 0 and cena_po_m2_input >= 0:
             ukupna_cena_materijala_rsd = ukupna_kvadratura_final_m2 * cena_po_m2_input

        ukupna_cena_rada_masine_rsd = 0.0
        if ukupno_vreme_min > 0 and st.session_state.cena_rada_masine_po_satu >= 0:
             ukupno_vreme_h = ukupno_vreme_min / 60.0; ukupna_cena_rada_masine_rsd = ukupno_vreme_h * st.session_state.cena_rada_masine_po_satu

        ukupna_cena_alata_rsd = 0.0; opis_alata_za_prikaz = "Nije izabran"; alat_info_string = ""
        if izabrani_alat_kljuc == "Polurotacioni":
             ukupna_cena_alata_rsd = st.session_state.cena_alata_polurotacioni; opis_alata_za_prikaz = f"Polurotacioni ({ukupna_cena_alata_rsd:,.2f} RSD)"; alat_info_string = "Polurotacioni"
        elif izabrani_alat_kljuc == "Rotacioni":
             ukupna_cena_alata_rsd = st.session_state.cena_alata_rotacioni; opis_alata_za_prikaz = f"Rotacioni ({ukupna_cena_alata_rsd:,.2f} RSD)"; alat_info_string = "Rotacioni"
        elif izabrani_alat_kljuc == "Nijedan":
             postojeci_alat = st.session_state.postojeci_alat_info; opis_alata_za_prikaz = f"Postojeći: {postojeci_alat}" if postojeci_alat else "Nije izabran"; alat_info_string = f"Postojeći: {postojeci_alat}" if postojeci_alat else "Nema"; ukupna_cena_alata_rsd = 0.0

        ukupni_trosak_proizvodnje_rsd = (ukupna_cena_boja_lak_rsd + ukupna_cena_klisea_rsd + ukupna_cena_materijala_rsd + ukupna_cena_rada_masine_rsd + ukupna_cena_alata_rsd)

        zarada_rsd = 0.0
        if ukupna_cena_materijala_rsd > 0 and koeficijent_zarade_input > 0:
             zarada_rsd = ukupna_cena_materijala_rsd * koeficijent_zarade_input

        ukupna_cena_prodajna_rsd = ukupni_trosak_proizvodnje_rsd + zarada_rsd
        prodajna_cena_po_komadu_rsd = (ukupna_cena_prodajna_rsd / tiraz_input) if tiraz_input > 0 else 0.0


        # --- Prikaz Rezultata (isti kao pre) ---
        # ... (ceo blok `st.subheader`, `st.expander`, `st.metric` ostaje isti) ...
        st.subheader(f"Proračun za: {product_name if product_name else '[Proizvod]'} | Klijent: {client_name if client_name else '[Klijent]'}")
        st.markdown("---")

        with st.expander("Detalji Proračuna (Konfiguracija, Potrošnja, Vreme)"):
            params_dims = f"Š:{sirina_W_input:.2f}×V:{visina_H_input:.2f}mm"; params_qty = f"Tiraž:{tiraz_input:,}"
            params_colors = 'Blanko' if is_blanko else str(valid_broj_boja_za_calc)+'B'; params_varnish = '+L' if is_uv_lak_input else ''
            params_mat = f"Mat:'{izabrani_materijal}'"; params_tool = f"Alat:'{alat_info_string}'"; params_speed = f"Brz:{brzina_masine_m_min}m/min"; params_profit = f"Koef.Zar:{koeficijent_zarade_input:.2f}"
            st.write(f"**Parametri:** {params_dims} | {params_qty} | {params_colors}{params_varnish} | {params_mat} | {params_tool} | {params_speed} | {params_profit}")
            st.markdown("---")

            st.subheader("1. Konfiguracija Cilindra i Šablona"); col1, col2 = st.columns(2);
            with col1: st.metric("Broj Zuba (Z)", f"{best_solution_obim['broj_zuba_Z']}"); st.metric("Obim Cilindra", f"{best_solution_obim['obim_mm']:.3f} mm"); st.metric("Razmak Obim (G)", f"{razmak_G_obim_mm:.3f} mm", help=f"{GAP_MIN:.1f}-{GAP_MAX:.1f} mm")
            with col2: st.metric("Šablona Obim (x)", f"{broj_po_obimu_x}"); st.metric("Šablona Širina (y)", f"{broj_po_sirini_y}", help=f"Na {SIRINA_RADNA}mm"); st.metric("Format (y × x)", f"{broj_po_sirini_y} × {broj_po_obimu_x}", help="/ciklus")

            st.subheader("2. Proračun Širine Materijala");
            if broj_po_sirini_y > 0:
                 mat_col1, mat_col2 = st.columns([2,1]); help_sirina = f"({broj_po_sirini_y}×{visina_H_input:.2f}mm)+({max(0, broj_po_sirini_y-1)}×{RAZMAK_SIRINA}mm)+{OTPAD_SIRINA}mm";
                 with mat_col1: st.metric("Potrebna Širina Materijala", f"{sirina_materijala_potrebna_mm:.2f} mm", help=help_sirina)
                 with mat_col2:
                     if not prekoracena_sirina_materijala: st.success(f"✅ OK (≤ {MAX_SIRINA_MATERIJALA} mm)")
                     else: st.error(f"⚠️ PREKORAČENO! >{MAX_SIRINA_MATERIJALA} mm")
            else: st.warning("y=0, širina materijala N/A.")

            st.subheader(f"3. Potrošnja Materijala za PROIZVODNJU ({tiraz_input:,} kom)");
            if broj_po_sirini_y > 0 and broj_po_obimu_x > 0:
                 pro_col1, pro_col2 = st.columns(2)
                 with pro_col1: st.metric("Dužina (Proizvodnja)", f"{ukupna_duzina_proizvodnja_m:,.2f} m")
                 with pro_col2: st.metric("Kvadratura (Proizvodnja)", f"{ukupna_kvadratura_proizvodnja_m2:,.2f} m²")
                 if poruka_potrosnja_proizvodnja: st.warning(poruka_potrosnja_proizvodnja)
            else: st.warning(poruka_potrosnja_proizvodnja)

            st.subheader(f"4. Potrošnja Materijala za ŠKART (Štelovanje)");
            ska_col1, ska_col2 = st.columns(2);
            with ska_col1: st.metric("Dužina (Škart)", f"{duzina_skart_m:,.2f} m", help=opis_skarta)
            with ska_col2:
                 if sirina_materijala_potrebna_mm > 0: help_kvadratura_skart = f"= {duzina_skart_m:,.2f}m*({sirina_materijala_potrebna_mm:.2f}mm/1000)"; st.metric("Kvadratura (Škart)", f"{kvadratura_skart_m2:,.2f} m²", help=help_kvadratura_skart)
                 else: st.info("Kvadratura Škarta N/A (širina=0)")

            st.subheader(f"5. UKUPNA Predviđena Potrošnja Materijala");
            tot_col1, tot_col2 = st.columns(2);
            with tot_col1: st.metric("UKUPNA Dužina", f"{ukupna_duzina_final_m:,.2f} m", help="Proizvodnja + Škart")
            with tot_col2: st.metric("UKUPNA Kvadratura", f"{ukupna_kvadratura_final_m2:,.2f} m²", help="Proizvodnja + Škart")

            st.subheader("6. Procena Vremena Izrade"); time_col1, time_col2, time_col3, time_col4 = st.columns(4);
            with time_col1: st.metric("Vreme Pripreme", format_time(vreme_pripreme_min), help=f"{broj_boja_za_skart_vreme} × {VREME_PRIPREME_PO_BOJI_ILI_OSNOVA}min")
            with time_col2: st.metric("Vreme Proizvodnje", format_time(vreme_proizvodnje_min), help=f"{ukupna_duzina_proizvodnja_m:,.1f}m / {brzina_masine_m_min}m/min")
            with time_col3: st.metric("Vreme Raspreme", format_time(vreme_raspreme_min), help="Fiksno")
            with time_col4: st.metric("UKUPNO Vreme Rada", format_time(ukupno_vreme_min), help="Σ Priprema+Proizvodnja+Rasprema")

            if len(all_solutions_obim) > 1:
                 st.subheader("Ostala moguća rešenja za Obim Cilindra")
                 st.caption("(Sortirano po Z ↑, zatim po x ↓)")
                 other_solutions_data = [sol for sol in all_solutions_obim if sol != best_solution_obim];
                 if other_solutions_data: df_others = pd.DataFrame(other_solutions_data); df_others = df_others.rename(columns={"broj_zuba_Z": "Z", "obim_mm": "Obim", "broj_sablona_N_obim": "x", "razmak_G_obim_mm": "G Obim"}); df_others['Obim'] = df_others['Obim'].map('{:.3f}'.format); df_others['G Obim'] = df_others['G Obim'].map('{:.3f}'.format); st.dataframe(df_others, use_container_width=True)


        st.markdown("---")

        # --- Prikaz Troškova (isti kao pre) ---
        st.subheader("📊 Kalkulacija Troškova")
        cost_row1_cols = st.columns(4)
        with cost_row1_cols[0]: st.metric("Trošak: Boja + Lak", f"{ukupna_cena_boja_lak_rsd:,.2f} RSD", help=f"Boja:{cena_boje_rsd:,.2f}, Lak:{cena_laka_rsd:,.2f}")
        with cost_row1_cols[1]: st.metric("Trošak: Kliše", f"{ukupna_cena_klisea_rsd:,.2f} RSD", help=f"{valid_broj_boja_za_calc} × {st.session_state.cena_klisea_po_boji:.2f} RSD/boji")
        with cost_row1_cols[2]: st.metric("Trošak: Materijal", f"{ukupna_cena_materijala_rsd:,.2f} RSD", help=f"{ukupna_kvadratura_final_m2:,.2f}m²×{cena_po_m2_input:.2f}RSD/m²")
        with cost_row1_cols[3]: st.metric("Trošak: Alat", f"{ukupna_cena_alata_rsd:,.2f} RSD", help=opis_alata_za_prikaz)

        cost_row2_cols = st.columns(4)
        with cost_row2_cols[0]:
            ukupno_vreme_h_za_help = ukupno_vreme_min / 60.0
            st.metric("Trošak: Rad Mašine", f"{ukupna_cena_rada_masine_rsd:,.2f} RSD", help=f"{format_time(ukupno_vreme_min)}({ukupno_vreme_h_za_help:.2f}h)×{st.session_state.cena_rada_masine_po_satu:.2f}RSD/h")

        st.subheader("💰 Zarada i Finalna Prodajna Cena")
        final_col1, final_col2, final_col3 = st.columns(3)
        with final_col1: st.metric("Ukupan Trošak Proizvodnje", f"{ukupni_trosak_proizvodnje_rsd:,.2f} RSD", help="Σ (Boja/Lak + Kliše + Materijal + Rad + Alat)")
        with final_col2: st.metric("Zarada", f"{zarada_rsd:,.2f} RSD", help=f"({koeficijent_zarade_input:.2f} × Cena Materijala)", delta=f"{koeficijent_zarade_input*100:.0f}%")
        with final_col3: st.metric("UKUPNA CENA (Prodajna)", f"{ukupna_cena_prodajna_rsd:,.2f} RSD", delta=f"{zarada_rsd:,.2f} RSD", help="Trošak Proizvodnje + Zarada")

        st.metric("Prodajna Cena po Komadu", f"{prodajna_cena_po_komadu_rsd:.4f} RSD", help=f"= {ukupna_cena_prodajna_rsd:,.2f} RSD / {tiraz_input:,} kom")

        st.markdown("---")

        # --- Dugme za čuvanje u Supabase ---
        if supabase: # Prikazi dugme samo ako je konekcija uspela
            st.subheader("💾 Čuvanje Kalkulacije u Supabase")
            napomena_save = st.text_area("Dodajte napomenu (opciono):", key="sb_napomena")

            if st.button("Sačuvaj u Supabase Bazu", key="sb_save_button"):
                with st.spinner("Čuvanje u Supabase..."):
                    # Pripremi podatke kao rečnik sa ključevima koji odgovaraju imenima kolona u Supabase
                    st.session_state.last_saved_id += 1
                    new_calc_id = st.session_state.last_saved_id
                    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Helper za sigurnu konverziju u float, vraća None ako ne uspe
                    def safe_float_or_none(value):
                        try: return float(value) if value is not None else None
                        except (ValueError, TypeError): return None
                    # Helper za sigurnu konverziju u int, vraća None ako ne uspe
                    def safe_int_or_none(value):
                        try: return int(value) if value is not None else None
                        except (ValueError, TypeError): return None

                    data_to_save = {
                        "Kalkulacija_Broj": new_calc_id,
                        "Timestamp_Kalkulacije": timestamp_str,
                        "Klijent": client_name if client_name else None,
                        "Proizvod": product_name if product_name else None,
                        "Sirina_W": safe_float_or_none(sirina_W_input),
                        "Visina_H": safe_float_or_none(visina_H_input),
                        "Tiraz": safe_int_or_none(tiraz_input),
                        "Broj_Boja": safe_int_or_none(valid_broj_boja_za_calc),
                        "UV_Lak": is_uv_lak_input, # boolean
                        "Materijal": izabrani_materijal,
                        "Cena_Materijala_m2": safe_float_or_none(cena_po_m2_input),
                        "Alat_Info": alat_info_string,
                        "Cena_Alata": safe_float_or_none(ukupna_cena_alata_rsd) if ukupna_cena_alata_rsd > 0 else None, # Čuvaj samo ako je > 0
                        "Zuba_Z": safe_int_or_none(best_solution_obim.get('broj_zuba_Z')),
                        "Format_XY": f"{broj_po_sirini_y}x{broj_po_obimu_x}",
                        "Sirina_Materijala_mm": safe_float_or_none(sirina_materijala_potrebna_mm),
                        "Ukupna_Kvadratura_m2": safe_float_or_none(ukupna_kvadratura_final_m2),
                        "Ukupno_Vreme_Str": format_time(ukupno_vreme_min),
                        "Cena_Boja_Lak_RSD": safe_float_or_none(ukupna_cena_boja_lak_rsd),
                        "Cena_Klisea_RSD": safe_float_or_none(ukupna_cena_klisea_rsd),
                        "Cena_Materijala_Uk_RSD": safe_float_or_none(ukupna_cena_materijala_rsd),
                        "Cena_Rada_RSD": safe_float_or_none(ukupna_cena_rada_masine_rsd),
                        "Trosak_Proizvodnje_RSD": safe_float_or_none(ukupni_trosak_proizvodnje_rsd),
                        "Zarada_RSD": safe_float_or_none(zarada_rsd),
                        "Prodajna_Cena_RSD": safe_float_or_none(ukupna_cena_prodajna_rsd),
                        "Cena_Po_Komadu_RSD": safe_float_or_none(prodajna_cena_po_komadu_rsd),
                        "Napomena": napomena_save if napomena_save else None
                    }

                    # Filtriraj None vrednosti pre slanja, ako Supabase kolone NISU nullable
                    # data_to_save_filtered = {k: v for k, v in data_to_save.items() if v is not None}
                    # Ako su kolone nullable, šaljemo ceo rečnik
                    data_to_save_filtered = data_to_save

                    # Pozovi funkciju za čuvanje
                    success, saved_id = save_calculation_to_supabase(supabase, data_to_save_filtered)

                    if success:
                        st.success(f"✅ Kalkulacija sa Brojem: {saved_id} uspešno sačuvana u Supabase!")
                        # Opciono: Očisti polja
                    else:
                        # Ako upis ne uspe, smanji ID nazad
                        st.session_state.last_saved_id -= 1
                        st.error("❌ Greška prilikom čuvanja kalkulacije u Supabase.")
        else:
            st.warning("Supabase konekcija nije uspela ili nije inicijalizovana. Čuvanje nije moguće.")


    # --- Poruke ako proračun nije uspeo ---
    elif message_obim:
        error_msg = f"Nije pronađen cilindar ({Z_MIN}-{Z_MAX} zuba) za W={sirina_W_input:.3f}mm sa G={GAP_MIN:.1f}-{GAP_MAX:.1f}mm." if 'Nije pronađen cilindar' in message_obim else f"Greška u proračunu: {message_obim}"
        if "Greška" in message_obim: st.error(f"❌ {error_msg}")
        else: st.warning(f"⚠️ {error_msg}")
    elif broj_po_sirini_y < 0:
         st.error(f"❌ Greška u proračunu broja šablona po širini (y={broj_po_sirini_y}).")

else: # Ako nisu uneti svi potrebni podaci
    st.info("Unesite sve parametre u panelu sa leve strane (minimalno Širina, Visina i Tiraž > 0).")


# --- Pretraga Baze Podataka (Supabase) ---
st.markdown("---")
st.header("🔍 Pretraga Baze Kalkulacija (Supabase)")

if supabase: # Prikazi pretragu samo ako je konekcija uspela
    search_term = st.text_input("Unesite pojam za pretragu (Klijent, Proizvod, Materijal):", key="supabase_search_term")

    # Definišemo kolone koje želimo da pretražujemo (po imenima iz Supabase tabele)
    # Fokusirajmo se na tekstualne za ILIKE
    search_cols_in_supabase = ["Klijent", "Proizvod", "Materijal", "Alat_Info", "Napomena"]
    # Možete dodati i numeričke ako implementirate logiku za njih u search_supabase

    if search_term:
        with st.spinner("Pretražujem Supabase bazu..."):
            search_results_df = search_supabase(supabase, search_term, search_cols_in_supabase)

        st.subheader(f"Rezultati pretrage za: '{search_term}'")
        if not search_results_df.empty:
            # Opciono: Formatiraj prikaz DataFrame-a
            # Možda sakrij 'id' i 'created_at' ili preuredi
            columns_to_show = [col for col in search_results_df.columns if col not in ['id']] # Sakrij Supabase ID
            st.dataframe(search_results_df[columns_to_show], use_container_width=True)
            st.caption(f"Pronađeno {len(search_results_df)} zapisa.")
        else:
            st.info("Nema pronađenih zapisa za uneti pojam.")
    else:
        st.info("Unesite pojam u polje iznad za početak pretrage.")

else:
    st.warning("Supabase konekcija nije uspela. Pretraga nije moguća.")


# --- Prikaz trenutnih podešavanja (Footer) ---
# ... (Footer ostaje isti) ...
st.markdown("---")
settings_str = f"MaxMat={MAX_SIRINA_MATERIJALA}mm | CenaRada={st.session_state.cena_rada_masine_po_satu:.2f}RSD/h | Alati: Polu={st.session_state.cena_alata_polurotacioni:.2f}, Rot={st.session_state.cena_alata_rotacioni:.2f} | Kliše={st.session_state.cena_klisea_po_boji:.2f}RSD/boji"
st.caption(settings_str)

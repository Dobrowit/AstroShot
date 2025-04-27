#!/usr/bin/python3

# pip install Pillow beepy send2trash

import os
import json
import glob
import time
import sys
import platform
import winsound
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont, ImageColor
from PIL.PngImagePlugin import PngInfo
from send2trash import send2trash

MAKE_CLS = True
PROC_IMG = True
FILE_EXT = '*.bmp'
SCALE_DIV = 4
SCALE_ALG = 'HAMMING' # LANCZOS, BILINEAR, BICUBIC, NEAREST, BOX, HAMMING
TXT_MARGIN = 15
TXT_POS = 4
FONT_SIZE = 20
FONT_COLOR = "white"
DRAW_TXT = True
DRAW_BACK = True
BACK_COLOR = "black"
SAVE_FORMAT = 'PNG' # PNG, JPEG
DELETE_SRC = True # bezpieczne usuwanie do kosza
CHECK_INTERVAL = 5  # sekundy pomiędzy sprawdzeniami
FRESHNESS_MINUTES = 15  # ile minut uznać za "świeży" zrzut
PORC_LAST = True # procesuje ostatni zrzut jeśli nie jest starszy niż FRESHNESS_MINUTES
SCREENSHOTS_DIR = os.path.expanduser('~\\Pictures\\Frontier Developments\\Elite Dangerous\\')
LOG_DIR = os.path.expanduser('~\\Saved Games\\Frontier Developments\\Elite Dangerous\\')
STATUS_FILE_PATH = os.path.expanduser('~\\Saved Games\\Frontier Developments\\Elite Dangerous\\Status.json')

if platform.system() != "Windows":
    print("Ten skrypt należy uruchamiać w środowisku Windows!")
    sys.exit(1)

if not os.path.isdir(SCREENSHOTS_DIR):
    print("Nie znaleziono katalogu zrzutów ekranu!")
    sys.exit(1)

if not os.path.isdir(LOG_DIR):
    print("Nie znaleziono katalogu dienników!")
    sys.exit(1)

if not os.path.isfile(STATUS_FILE_PATH):
    print("Nie znaleziono pliku statusu!")
    sys.exit(1)

FLAG_BITS = {
    0: "Docked on a landing pad",
    1: "Landed on planet surface",
    2: "Landing Gear Down",
    3: "Shields Up",
    4: "Supercruise",
    5: "FlightAssist Off",
    6: "Hardpoints Deployed",
    7: "In Wing",
    8: "Lights On",
    9: "Cargo Scoop Deployed",
    10: "Silent Running",
    11: "Scooping Fuel",
    12: "SRV Handbrake",
    13: "SRV using Turret view",
    14: "SRV Turret retracted (close to ship)",
    15: "SRV DriveAssist",
    16: "FSD MassLocked",
    17: "FSD Charging",
    18: "FSD Cooldown",
    19: "Low Fuel (< 25%)",
    20: "Over Heating (> 100%)",
    21: "Has Lat and Long",
    22: "Is In Danger",
    23: "Being Interdicted",
    24: "In MainShip",
    25: "In Fighter",
    26: "In SRV",
    27: "HUD in Analysis mode",
    28: "Night Vision",
    29: "Altitude from Average radius",
    30: "FSD Jump",
    31: "SRV HighBeam"
}
FLAG2_BITS = {
    0: "On Foot",
    1: "In Taxi or dropship/shuttle",
    2: "In Multicrew (someone else's ship)",
    3: "On Foot In Station",
    4: "On Foot On Planet",
    5: "Aim Down Sight",
    6: "Low Oxygen",
    7: "Low Health",
    8: "Cold",
    9: "Hot",
    10: "Very Cold",
    11: "Very Hot",
    12: "Glide Mode",
    13: "On Foot In Hangar",
    14: "On Foot Social Space",
    15: "On Foot Exterior",
    16: "Breathable Atmosphere",
    17: "Telepresence Multicrew",
    18: "Physical Multicrew",
    19: "FSD hyperdrive charging"
}

def beep():
    """Prosta sygnalizacja dźwiękowa."""
    winsound.Beep(1000, 200)  # częstotliwość 1000Hz przez 200ms

def is_fresh(file_path):
    """Sprawdź czy plik powstał w ciągu ostatnich FRESHNESS_MINUTES"""
    if not file_path:
        return False
    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_time < timedelta(minutes=FRESHNESS_MINUTES)

def find_latest_screenshot():
    """Odnajduje ostatnio zapisany zrzut ekranu."""
    files = glob.glob(os.path.join(SCREENSHOTS_DIR, FILE_EXT))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def find_latest_journal():
    """Znajdź najnowszy plik dziennika."""
    files = glob.glob(os.path.join(LOG_DIR, 'Journal.*.log'))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def read_journal_old(file_path):
    """Czytaj plik Journal linia po linii."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def read_journal(file_path):
    """Czytaj plik Journal linia po linii."""
    events = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Pominięto nieprawidłową linię w pliku {file_path}")
    return events

def read_status_file():
    """Bezpieczna procedura odczytywania pliku Status.json"""
    if not os.path.exists(STATUS_FILE_PATH):
        print(f"Nie znaleziono pliku {STATUS_FILE_PATH}")
        return None
    max_attempts = 3
    attempt_delay = 0.5  # sekundy
    for attempt in range(max_attempts):
        try:
            with open(STATUS_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            if attempt < max_attempts - 1:
                print(f"Błąd dekodowania pliku {STATUS_FILE_PATH}, próba {attempt + 1}/{max_attempts}. Ponawiam...")
                time.sleep(attempt_delay)
            else:
                print(f"Nie udało się odczytać pliku {STATUS_FILE_PATH} po {max_attempts} próbach.")
                return None

def decode_flags(flags, flags2):
    """Dekodowanie poszczególnych bitów we flagach statusu."""
    flags_status = ""
    for bit in range(32):  # Sprawdzamy bity od 0 do 31
        if flags & (1 << bit):  # Jeśli bit jest ustawiony na 1
            flags_status += FLAG_BITS[bit] + " | "
    for bit in range(20):
        if flags2 & (1 << bit):
            flags_status += FLAG2_BITS[bit] + " | "
    if flags_status:
        return flags_status[:-3]  # Usuń ostatni " | "
    return "None"

def extract_location_data(status_data):
    """Pobiera informacje o położeniu z dziennika i statusu."""
    latest_journal = find_latest_journal()
    if not latest_journal:
        print("Nie znaleziono plików Journal!")
        sys.exit(1)
    events = read_journal(latest_journal)
    location = extract_location(events)
    decoded_flags = decode_flags(status_data.get('Flags', 0), status_data.get('Flags2', 0))
    location_data = {
        'LegalState': status_data.get('LegalState'),
        'Latitude': status_data.get('Latitude'),
        'Longitude': status_data.get('Longitude'),
        'Heading': status_data.get('Heading'),
        'Altitude': status_data.get('Altitude'),
        'BodyName': status_data.get('BodyName'),
        'PlanetRadius': status_data.get('PlanetRadius'),
        'Flags': status_data.get('Flags', 0),
        'Flags2': status_data.get('Flags2', 0)
    }
    if status_data.get('Flags2', 0) != 0:
        location_data.update({
            'Oxygen': status_data.get('Oxygen'),
            'Health': status_data.get('Health'),
            'Temperature': status_data.get('Temperature'),
            'Gravity': status_data.get('Gravity')
        })
    location_data.update({
        'StarSystem': location['system'] or None,
        'Station': location['station'] or None,
        'StationType': location['stationType'] or None,
        'Planet': location['planet'] or None,
        'DecFlags': decoded_flags
    })
    return location_data

def extract_location(events):
    """Wyciągnij informacje o pozycji z eventów w dzienniku."""
    location = {
        "system": None,
        "station": None,
        "stationType": None,
        "planet": None
    }
    for event in events:
        if event.get('event') == 'Location':
            location['system'] = event.get('StarSystem')
            location['planet'] = event.get('Body')
        elif event.get('event') == 'Docked':
            location['station'] = event.get('StationName')
            location['stationType'] = event.get('StationType')
        elif event.get('event') == 'Undocked':
            location['station'] = None
            location['stationType'] = None
        elif event.get('event') == 'FSDJump':
            location['system'] = event.get('StarSystem')
            location['planet'] = None
            location['station'] = None
        elif event.get('event') == 'Touchdown':
            location['planet'] = event.get('Body')
    return location

def save_location_json(screenshot_path, location_data):
    """Zapisuje informacje do pliku JSON dla danego zrzutu ekranu."""
    base, _ = os.path.splitext(screenshot_path)
    json_path = base + '.json'
    if os.path.exists(json_path):
        return

    data = {
        "timestamp": datetime.now().isoformat(),
        "StarSystem": location_data['StarSystem'],
        "Planet": location_data['Planet'],
        "Station": location_data['Station'],
        "StationType": location_data['StationType'],
        "BodyName": location_data['BodyName'],
        "PlanetRadius": location_data['PlanetRadius'],
        "Temperature": location_data.get('Temperature'),
        "Gravity": location_data.get('Gravity'),
        "Latitude": location_data['Latitude'],
        "Longitude": location_data['Longitude'],
        "Heading": location_data['Heading'],
        "Altitude": location_data['Altitude'],
        "LegalState": location_data['LegalState'],
        "Oxygen": location_data.get('Oxygen'),
        "Health": location_data.get('Health'),
        "Flags": location_data['Flags'],
        "Flags2": location_data['Flags2'],
        "DecFlags": location_data['DecFlags']
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Zapisano dane lokalizacji do: {os.path.basename(json_path)}")

def print_status_line(pole, status_data):
    if status_data.get(pole) != None:
        print(f"{(12-len(pole))*" "}{pole}: {status_data.get(pole)}")

def display_status(status_data):
    """Wyświetl status na ekranie."""
    try:
        con_width = os.get_terminal_size().columns
    except OSError:
        con_width = 80  # Domyślna szerokość konsoli
    print(con_width*"=")
    print_status_line("StarSystem", status_data)
    print_status_line("Planet", status_data)
    print_status_line("Station", status_data)
    print_status_line("StationType", status_data)
    print_status_line("BodyName", status_data)
    print_status_line("PlanetRadius", status_data)
    print_status_line("Temperature", status_data)
    print_status_line("Gravity", status_data)
    print_status_line("Latitude", status_data)
    print_status_line("Longitude", status_data)
    print_status_line("Heading", status_data)
    print_status_line("Altitude", status_data)
    print_status_line("LegalState", status_data)
    print_status_line("Oxygen", status_data)
    print_status_line("Health", status_data)
    print(f"\nFlags:")
    flagi = "  " + status_data.get('DecFlags')
    flagi = flagi.replace(" | ", "\n  ")
    print(flagi)
    print(con_width*"=")

def overlay_status(location_data):
    timestamp = datetime.now().isoformat()
    dt = datetime.fromisoformat(timestamp)
    dt_utc = dt.astimezone(timezone.utc) # Konwersja na UTC
    dt_utc = dt_utc.replace(year=dt_utc.year + 1286)
    timestamp = dt_utc.strftime("%Y-%m-%d %H:%M")
    star_system = location_data['StarSystem']
    planet = location_data['Planet']
    planet_radius = location_data['PlanetRadius']
    temperature = location_data.get('Temperature')
    gravity = location_data.get('Gravity')
    latitude = location_data['Latitude']
    longitude = location_data['Longitude']
    altitude = location_data['Altitude']
    line = timestamp + "\nSystem: " + star_system.upper() + "\n"
    if planet.startswith(star_system):
        planet = planet[len(star_system):].lstrip()
    if temperature == None:
        line += "Planet: " + planet.upper()
    else:
        line += "Planet: " + planet.upper() + "(Radius: " + planet_radius + " | Temp.: " + temperature + " | Grav.: " + gravity + "\n"
        line += "Lat: " + latitude + " | Lon: " + longitude + " | Alt: " + altitude
    return line

def process_image(screenshot_path, location_data):
    """Zmniejsza obraz, nakłada tekst i zapisuje."""
    try:
        # Otwórz obraz
        img = Image.open(screenshot_path)
                
        # Zmniejsz obraz
        original_size = img.size
        new_size = (original_size[0] // SCALE_DIV, original_size[1] // SCALE_DIV)

        match SCALE_ALG:
            case 'LANCZOS':
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            case 'BILINEAR':
                img = img.resize(new_size, Image.Resampling.BILINEAR)
            case 'BICUBIC':
                img = img.resize(new_size, Image.Resampling.BICUBIC)
            case 'NEAREST':
                img = img.resize(new_size, Image.Resampling.NEAREST)
            case 'BOX':
                img = img.resize(new_size, Image.Resampling.BOX)
            case 'HAMMING':
                img = img.resize(new_size, Image.Resampling.HAMMING)

        if DRAW_TXT:
            text = overlay_status(location_data) # Przygotuj tekst do nałożenia
            draw = ImageDraw.Draw(img) # Utwórz obiekt do rysowania
            # Użyj domyślnej czcionki Pillow lub systemowej
            try:
                font = ImageFont.truetype("arial.ttf", FONT_SIZE)
            except IOError:
                font = ImageFont.load_default()
            
            # Oblicz rozmiar tekstu i pozycję tekstu
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            match TXT_POS:
                case 1:
                    text_position = (TXT_MARGIN, TXT_MARGIN)
                case 2:
                    text_position = (new_size[0] - text_width - TXT_MARGIN, TXT_MARGIN)
                case 3:
                    text_position = (new_size[0] - text_width - TXT_MARGIN, new_size[1] - text_height - (1.5 * TXT_MARGIN))
                case _:
                    text_position = (TXT_MARGIN, new_size[1] - text_height - (1.5 * TXT_MARGIN))

        if DRAW_BACK and DRAW_TXT:
            # Oblicz marginesy dla prostokąta tła
            rect_margin = TXT_MARGIN // 1
            rect_bbox = (
                text_position[0] - rect_margin,
                text_position[1] - rect_margin,
                text_position[0] + text_width + rect_margin,
                text_position[1] + text_height + rect_margin
            )

            # Rysuj półprzezroczysty czarny prostokąt
            rgb = ImageColor.getrgb(BACK_COLOR)
            fill_color = rgb
            draw.rectangle(rect_bbox, fill=fill_color)

        if DRAW_TXT:
            # Nałóż tekst
            draw.text(text_position, text, font=font, fill=FONT_COLOR, stroke_width=1, stroke_fill="black")

        # Przygotuj metadane PNG
        metadata = PngInfo()
        metadata.add_text("Location", str(text))  # Dane lokalizacji

        # Zapisz plik
        base, _ = os.path.splitext(screenshot_path)
        img_path = base + '.' + SAVE_FORMAT.lower()
        if os.path.exists(img_path):
            return
        img.save(img_path, SAVE_FORMAT, optimize=True, pnginfo=metadata)
        if DELETE_SRC: # bezpieczne usuwanie do kosza
            file = base + '.bmp'
            if os.path.exists(file):
                send2trash(file)
        print(f"Zapisano zmniejszony obraz do: {os.path.basename(img_path)}")
    except Exception as e:
        print(f"Błąd przetwarzania obrazu {screenshot_path}: {e}")

def monitor_mode(known_screenshots):
    """Główna pętla monitorowania folderu ze zrzutami ekranu."""
    print(f"Monitoring folderu: {SCREENSHOTS_DIR} (przerwij Ctrl+C)")
    try:
        while True:
#            status_data = read_status_file()
#            if status_data:
#                    location_data = extract_location_data(status_data)
#                    display_status(location_data)
            latest_screenshot = find_latest_screenshot()
            if latest_screenshot and latest_screenshot not in known_screenshots:
                status_data = read_status_file()
                if status_data:
                    location_data = extract_location_data(status_data)
                    display_status(location_data)
                    save_location_json(latest_screenshot, location_data)
                    if PROC_IMG:
                        process_image(latest_screenshot, location_data)
                    beep()
                else:
                    print("Brak pliku Status.json - nie można odczytać lokalizacji.")
                known_screenshots.add(latest_screenshot)
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\nZakończono monitorowanie.")
        sys.exit(0)

def main():
    if MAKE_CLS:
        os.system('cls')
    known_screenshots = set()
    if PORC_LAST:
        latest_screenshot = find_latest_screenshot()
        if latest_screenshot and is_fresh(latest_screenshot):
            print(f"Znaleziono świeży screenshot: {latest_screenshot}")
            known_screenshots.add(latest_screenshot)
            status_data = read_status_file()
            if status_data:
                location_data = extract_location_data(status_data)
                save_location_json(latest_screenshot, location_data)
                if PROC_IMG:
                    process_image(latest_screenshot, location_data)
                beep()
    monitor_mode(known_screenshots)

if __name__ == '__main__':
    main()

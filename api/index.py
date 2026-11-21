
import io
import base64
import random
import secrets
import os
import re
import logging
from html import escape

from flask import Flask, render_template, request, jsonify
import qrcode
import resend


# =========================================================
# APLIKACE
# =========================================================

app = Flask(__name__, template_folder="../templates")

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# V produkci nikdy nezapínat debug režim.
app.config["DEBUG"] = False


# =========================================================
# KONFIGURACE
# =========================================================

REVOLUT_IBAN = os.getenv(
    "REVOLUT_IBAN",
    "LT803250069633761109"
)

REVOLUT_BIC = os.getenv(
    "REVOLUT_BIC",
    "REVOLT21"
)

BENEFICIARY_NAME = os.getenv(
    "PAYMENT_BENEFICIARY",
    "Mystická Svatyně"
)

ADMIN_EMAIL = os.getenv(
    "ADMIN_EMAIL",
    "ruzar7789@gmail.com"
)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

RESEND_FROM = os.getenv(
    "RESEND_FROM",
    "Mystická Svatyně <onboarding@resend.dev>"
)

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


# =========================================================
# SLUŽBY
# =========================================================

SERVICES = {
    "tarot_basic": {
        "title": "Základní výklad Tarotu (3 karty)",
        "price": 25.00,
        "currency": "EUR",
        "description": "Rozbor minulosti, přítomnosti a směřování v blízké budoucnosti."
    },
    "tarot_full": {
        "title": "Kompletní roční horoskop a Tarot",
        "price": 75.00,
        "currency": "EUR",
        "description": "Detailní vhled do 12 měsíců: financí, vztahů, zdraví a kariéry."
    },
    "ritual_love": {
        "title": "Mistrovský rituál harmonizace vztahu",
        "price": 150.00,
        "currency": "EUR",
        "description": "Hluboká energetická očista a posílení poutek s partnerem."
    },
    "ritual_protection": {
        "title": "Velký rituál osobní a majetkové ochrany",
        "price": 250.00,
        "currency": "EUR",
        "description": "Odstranění negativních bloků a vytvoření ochranného štítu."
    },
    "consultation_vip": {
        "title": "Osobní VIP konzultace (60 minut)",
        "price": 120.00,
        "currency": "EUR",
        "description": "Individuální setkání nebo online hovor s rozborem situace."
    }
}


# Krátké kódy služeb pro platební reference.
SERVICE_CODES = {
    "tarot_basic": "TB",
    "tarot_full": "TF",
    "ritual_love": "RL",
    "ritual_protection": "RP",
    "consultation_vip": "CV"
}


# =========================================================
# TAROT – 22 KARET VELKÉ ARKÁNY
# =========================================================

TAROT_DECK = [
    {
        "id": "0_fool",
        "name": "0. Blázen",
        "element": "Vzduch",
        "keywords": "Nové začátky, Důvěra, Spontánnost, Nevinnost",
        "meaning": "Dnes je den pro nový začátek. Nebojte se udělat krok do neznáma a věřte, že vás vesmír podrží.",
        "meaning_reversed": "Pozor na unáhlená rozhodnutí a naivitu. Než skočíte, raději se dvakrát rozhlédněte.",
        "question": "Co vám brání udělat prvotní krok ke svému snu?"
    },
    {
        "id": "1_magician",
        "name": "I. Magik",
        "element": "Vzduch",
        "keywords": "Manifestace, Síla vůle, Schopnosti, Akce",
        "meaning": "Máte k dispozici všechny nástroje a zdroje, které potřebujete k úspěchu. Čas proměnit záměr v realitu.",
        "meaning_reversed": "Možná pochybujete o svých schopnostech nebo tříštíte pozornost. Zaměřte se na to podstatné.",
        "question": "Jaký svůj skrytý talent můžete dnes plně využít?"
    },
    {
        "id": "2_high_priestess",
        "name": "II. Velekněžka",
        "element": "Voda",
        "keywords": "Intuice, Vnitřní hlas, Tajemství, Podvědomí",
        "meaning": "Naslouchejte svému vnitřnímu hlasu a snové symbolice. Odpovědi se skrývají v tichu vašeho nitra.",
        "meaning_reversed": "Přehlížíte varovné signály své intuice. Zastavte se a nenechte se přehlušit okolním hlukem.",
        "question": "Co vám tichý vnitřní hlas říká, ale vy ho stále přehlížíte?"
    },
    {
        "id": "3_empress",
        "name": "III. Císařovna",
        "element": "Země",
        "keywords": "Hojnost, Tvořivost, Péče, Příroda",
        "meaning": "Přichází období růstu, kreativity a plodnosti. Dopřejte si péči a vnímejte krásu kolem sebe.",
        "meaning_reversed": "Pociťujete kreativní blok nebo zanedbáváte své potřeby na úkor druhých. Doplňte své zdroje.",
        "question": "Jakým způsobem dnes můžete projevit lásku a péči sami k sobě?"
    },
    {
        "id": "4_emperor",
        "name": "IV. Císař",
        "element": "Oheň",
        "keywords": "Struktura, Autorita, Stabilita, Hranice",
        "meaning": "Je čas vnést do života řád, nastavit jasné hranice a převzít plnou zodpovědnost za své směřování.",
        "meaning_reversed": "Pozor na přehnanou tvrdost, kontrolu nebo naopak chaos a nedostatek sebekázně.",
        "question": "Kde ve svém životě potřebujete nastavit pevnější hranice?"
    },
    {
        "id": "5_hierophant",
        "name": "V. Velekněz",
        "element": "Země",
        "keywords": "Tradice, Moudrost, Učení, Duchovní vedení",
        "meaning": "Hledejte moudrost v ověřených hodnotách nebo požádejte o radu zkušeného mentora.",
        "meaning_reversed": "Možná je čas zpochybnit stará dogmata a najít si svou vlastní, osobitou cestu.",
        "question": "Kterému přesvědčení věříte jen proto, že vám to říkali druzí?"
    },
    {
        "id": "6_lovers",
        "name": "VI. Milenci",
        "element": "Vzduch",
        "keywords": "Láska, Volba, Harmonie, Hodnoty",
        "meaning": "Karta přináší harmonii do vztahů a signalizuje důležité rozhodnutí založené na hodnotách srdce.",
        "meaning_reversed": "Vnitřní rozpor nebo neuspořádané vztahy. Je potřeba vyjasnit si, co doopravdy chcete.",
        "question": "Jste v souladu se svými hlavními životními hodnotami?"
    },
    {
        "id": "7_chariot",
        "name": "VII. Vůz",
        "element": "Voda",
        "keywords": "Triumf, Odhodlání, Pohyb, Kontrola",
        "meaning": "Soustřeďte se na cíl a držte opratě pevně v rukou. Vaše odhodlání vás dovede k vítězství.",
        "meaning_reversed": "Ztráta kontroly nebo bezhlavý tlak na pilu. Zpomalte a přehodnoťte směr.",
        "question": "Kam směřujete svou energii a je to správný směr?"
    },
    {
        "id": "8_strength",
        "name": "VIII. Síla",
        "element": "Oheň",
        "keywords": "Trpělivost, Vnitřní síla, Soucit, Odvaha",
        "meaning": "Skutečná síla vychází z jemnosti, trpělivosti a ovládnutí vlastních stínů a emocí.",
        "meaning_reversed": "Pochybnosti o sobě samém nebo vyčerpání. Nezapomínejte být k sobě laskaví.",
        "question": "Jakou výzvu můžete dnes překonat s klidem a vlídností?"
    },
    {
        "id": "9_hermit",
        "name": "IX. Poustevník",
        "element": "Země",
        "keywords": "Sebereflexe, Samota, Vnitřní světlo, Hledání",
        "meaning": "Dopřejte si čas o samotě. Ve ztišení objevíte světlo, které vám posvítí na další cestu.",
        "meaning_reversed": "Přílišná izolace od světa nebo pocit osamění. Nebojte se požádat o pomoc.",
        "question": "Co objevíte, když na chvíli vypnete veškerý okolní hluk?"
    },
    {
        "id": "10_wheel",
        "name": "X. Kolo Štěstěny",
        "element": "Oheň",
        "keywords": "Osud, Změna, Cykly, Příležitost",
        "meaning": "Život je v neustálém pohybu. Přijměte změnu jako příležitost, osud se obrací ve váš prospěch.",
        "meaning_reversed": "Odpor vůči změnám. Snaha udržet věci, které už dosloužily, situaci jen komplikuje.",
        "question": "Jakému cyklu ve svém životě se stále bráníte?"
    },
    {
        "id": "11_justice",
        "name": "XI. Spravedlnost",
        "element": "Vzduch",
        "keywords": "Pravda, Rovnováha, Příčina a následek, Jasnost",
        "meaning": "Čeká vás spravedlivé vyúštění situace. Jednejte v souladu s pravdou a převezměte odpovědnost.",
        "meaning_reversed": "Nespravedlnost, neupřímnost nebo odmítání přiznat si vlastní chybu.",
        "question": "Jste k sobě i k druhým v tuto chvíli zcela upřímní?"
    },
    {
        "id": "12_hanged_man",
        "name": "XII. Viselec",
        "element": "Voda",
        "keywords": "Nová perspektiva, Zastavení, Odevzdání, Oběť",
        "meaning": "Někdy je nejlepším krokem zastavit se a podívat se na situaci z úplně nového úhlu pohledu.",
        "meaning_reversed": "Zbytečné otálení, pocit oběti nebo neschopnost nechat věci volně plynout.",
        "question": "Jaký nový úhel pohledu vám může pomoci vyřešit současnou situaci?"
    },
    {
        "id": "13_death",
        "name": "XIII. Smrt",
        "element": "Voda",
        "keywords": "Transformace, Konec, Nový začátek, Propuštění",
        "meaning": "Něco starého končí, aby uvolnilo místo novému. Přijměte přirozený proces transformace.",
        "meaning_reversed": "Strach z opuštění minulosti. Držení se starých vzorců brání příchodu nového.",
        "question": "Čeho je potřeba se konečně vzdát, abyste se mohli posunout dál?"
    },
    {
        "id": "14_temperance",
        "name": "XIV. Mírnost",
        "element": "Oheň",
        "keywords": "Rovnováha, Trpělivost, Harmonie, Mír",
        "meaning": "Hledejte střední cestu a rovnováhu. Trpělivost a jemné propojování protikladů přinese klid.",
        "meaning_reversed": "Extrémy, nevyrovnanost nebo nedostatek trpělivosti. Zpomalte a vyrovnejte své síly.",
        "question": "V jaké oblasti svého života zacházíte do zbytečného extrému?"
    },
    {
        "id": "15_devil",
        "name": "XV. Ďábel",
        "element": "Země",
        "keywords": "Pouta, Iluze, Pokušení, Stín",
        "meaning": "Poznejte své nezdravé závislosti a omezující přesvědčení. Klíč ke svobodě držíte ve svých rukou.",
        "meaning_reversed": "Osvobození se z toxického prostředí nebo zlom v překonání zlozvyku.",
        "question": "Jaká iluze nebo nezdravý návyk vás vnitřně svazuje?"
    },
    {
        "id": "16_tower",
        "name": "XVI. Věž",
        "element": "Oheň",
        "keywords": "Náhlá změna, Blesk, Osvobození, Procitnutí",
        "meaning": "Zhroucení falešných jistot otevírá cestu k pravdě. Změna může být náhlá, ale očistná.",
        "meaning_reversed": "Odsouvání nevyhnutelné změny nebo strach z prolomení starých struktur.",
        "question": "Jaká nefunkční jistota ve vašem životě potřebuje přestavbu?"
    },
    {
        "id": "17_star",
        "name": "XVII. Hvězda",
        "element": "Vzduch",
        "keywords": "Naděje, Inspirace, Léčení, Jasnost",
        "meaning": "Po bouři přichází klid a naděje. Věřte v budoucnost, jste pod ochranou vyšších sil.",
        "meaning_reversed": "Ztráta víry nebo malomyslnost. Nezapomínejte, že po nejtemnější noci vždy svítá.",
        "question": "Co vám dodává největší pocit naděje a klidu?"
    },
    {
        "id": "18_moon",
        "name": "XVIII. Luna",
        "element": "Voda",
        "keywords": "Iluze, Sny, Nejistota, Intuice",
        "meaning": "Věci nemusí být takové, jak se zdají. Procházejte mlhou s důvěrou ve svůj vnitřní kompas.",
        "meaning_reversed": "Rozptýlení iluzí, překonání strachu a vyjasnění zamotané situace.",
        "question": "Jaký skrytý strach vám brání vidět situaci jasně?"
    },
    {
        "id": "19_sun",
        "name": "XIX. Slunce",
        "element": "Oheň",
        "keywords": "Radost, Úspěch, Vitalita, Jasnost",
        "meaning": "Ozařuje vás pozitivní energie. Čeká vás období radosti, úspěchu a životní vitality.",
        "meaning_reversed": "Dočasné přehlížení pozitivních věcí. Slunce stále svítí, i když je za mraky.",
        "question": "Za co můžete být v tomto okamžiku nejvíce vděční?"
    },
    {
        "id": "20_judgement",
        "name": "XX. Poslední soud",
        "element": "Oheň",
        "keywords": "Procitnutí, Volání, Znovuzrození, Jasnost",
        "meaning": "Přichází moment jasného nahlédnutí a odpoutání se od minulosti. Vyslyšte své vyšší volání.",
        "meaning_reversed": "Pochybnosti o sobě, sebekritika nebo odmítání uzavřít starou kapitolu.",
        "question": "K jaké nové fázi života vás vaše nitro právě teď volá?"
    },
    {
        "id": "21_world",
        "name": "XXI. Svět",
        "element": "Země",
        "keywords": "Dokončení, Integrace, Naplnění, Celistvost",
        "meaning": "Dosáhli jste cíle a uzavřeli důležitou kapitolu. Vychutnejte si pocit celistvosti.",
        "meaning_reversed": "Nedokončené záležitosti. Udělejte poslední krok k uzavření starého cyklu.",
        "question": "Jaký úspěch si zaslouží vaši dnešní oslavu?"
    }
]


# =========================================================
# POMOCNÉ FUNKCE
# =========================================================

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def get_json_data():
    """Bezpečně načte JSON objekt z požadavku."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None

    return data


def validate_email(email):
    """Základní kontrola e-mailové adresy."""
    if not isinstance(email, str):
        return False

    email = email.strip()

    if len(email) > 254:
        return False

    return bool(EMAIL_PATTERN.fullmatch(email))


def get_payment_reference(service_key):
    """
    Vytvoří referenci ve tvaru MS-TB-123456.

    Reference se neukládá do databáze.
    Je určena pro ruční spárování platby.
    """
    service_code = SERVICE_CODES[service_key]
    number = secrets.randbelow(900000) + 100000

    return f"MS-{service_code}-{number}"


def normalize_payment_reference(reference, service_key):
    """
    Přijme buď plnou referenci MS-TB-123456,
    nebo samotný šestimístný kód ze staršího frontendu.
    """
    if not isinstance(reference, str):
        return None

    reference = reference.strip().upper()

    if re.fullmatch(r"\d{6}", reference):
        reference = (
            f"MS-{SERVICE_CODES[service_key]}-{reference}"
        )

    expected_prefix = f"MS-{SERVICE_CODES[service_key]}-"

    if not reference.startswith(expected_prefix):
        return None

    if not re.fullmatch(
        rf"MS-{SERVICE_CODES[service_key]}-\d{{6}}",
        reference
    ):
        return None

    return reference


def create_epc_payload(service, payment_reference):
    """
    Vytvoří EPC SEPA QR payload.

    Reference je vložena do nestrukturované
    remittance zprávy (max. 140 znaků).
    """
    amount = service["price"]

    payload = "\n".join([
        "BCD",
        "002",
        "1",
        "SCT",
        REVOLUT_BIC,
        BENEFICIARY_NAME,
        REVOLUT_IBAN,
        f"EUR{amount:.2f}",
        "",
        "",
        payment_reference,
        ""
    ])

    # EPC payload má limit 331 bajtů.
    if len(payload.encode("utf-8")) > 331:
        raise ValueError("EPC QR payload překračuje povolenou délku.")

    return payload


def create_qr_image(payload):
    """Vygeneruje QR kód s vysokým kontrastem."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4
    )

    qr.add_data(payload)
    qr.make(fit=True)

    # Černá na bílé pro co nejlepší čitelnost
    # v bankovních aplikacích.
    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    return base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")


def safe_html_text(value):
    """Escapuje uživatelský text před vložením do HTML."""
    return escape(str(value), quote=True)


# =========================================================
# BEZPEČNOSTNÍ HLAVIČKY
# =========================================================

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    return response


# =========================================================
# CHYBOVÉ ODPOVĚDI
# =========================================================

@app.errorhandler(413)
def request_too_large(error):
    return jsonify({
        "status": "error",
        "message": "Odeslaná data jsou příliš velká."
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    logger.exception("Interní chyba aplikace.")

    return jsonify({
        "status": "error",
        "message": "Na serveru došlo k chybě. Zkuste to prosím později."
    }), 500


# =========================================================
# HLAVNÍ STRÁNKA
# =========================================================

@app.route("/")
def home():
    return render_template(
        "index.html",
        services=SERVICES
    )


# =========================================================
# TAROT – VÝBĚR KARTY
# =========================================================

@app.route("/api/draw-card", methods=["GET"])
def draw_card():
    card = random.choice(TAROT_DECK)

    is_reversed = random.random() < 0.20

    card_name = (
        f"{card['name']} (Obrácená)"
        if is_reversed
        else card["name"]
    )

    meaning = (
        card["meaning_reversed"]
        if is_reversed
        else card["meaning"]
    )

    return jsonify({
        "id": card["id"],
        "name": card_name,
        "element": card["element"],
        "keywords": card["keywords"],
        "meaning": meaning,
        "question": card["question"],
        "is_reversed": is_reversed
    })


# =========================================================
# GENEROVÁNÍ PLATEBNÍHO QR
# =========================================================

@app.route("/api/generate-qr", methods=["POST"])
def generate_qr():
    data = get_json_data()

    if data is None:
        return jsonify({
            "status": "error",
            "message": "Neplatná data požadavku."
        }), 400

    service_id = data.get("service_id", "tarot_basic")

    if not isinstance(service_id, str):
        return jsonify({
            "status": "error",
            "message": "Neplatný výběr služby."
        }), 400

    service = SERVICES.get(service_id)

    if service is None:
        return jsonify({
            "status": "error",
            "message": "Vybraná služba neexistuje."
        }), 400

    try:
        payment_reference = get_payment_reference(service_id)

        payload = create_epc_payload(
            service,
            payment_reference
        )

        qr_base64 = create_qr_image(payload)

        # Samotný šestimístný kód kvůli kompatibilitě
        # se starší verzí frontendu.
        short_reference = payment_reference[-6:]

        return jsonify({
            "status": "success",
            "qr_image": f"data:image/png;base64,{qr_base64}",
            "title": service["title"],
            "price": f"{service['price']:.2f} EUR",
            "iban": REVOLUT_IBAN,
            "bic": REVOLUT_BIC,
            "vs": short_reference,
            "payment_reference": payment_reference,
            "service_id": service_id
        })

    except Exception:
        logger.exception("Chyba při generování QR.")

        return jsonify({
            "status": "error",
            "message": "QR kód se nepodařilo vytvořit."
        }), 500


# =========================================================
# REZERVACE A E-MAIL
# =========================================================

@app.route("/api/reserve", methods=["POST"])
def reserve():
    data = get_json_data()

    if data is None:
        return jsonify({
            "status": "error",
            "message": "Neplatná data požadavku."
        }), 400

    email = data.get("email", "")
    service_key = data.get("service", "tarot_basic")
    note = data.get("note", "")
    payment_reference = data.get("payment_reference", "")

    # -----------------------------------------------------
    # VALIDACE E-MAILU
    # -----------------------------------------------------

    if not isinstance(email, str):
        return jsonify({
            "status": "error",
            "message": "Zadejte platnou e-mailovou adresu."
        }), 400

    email = email.strip()

    if not validate_email(email):
        return jsonify({
            "status": "error",
            "message": "Zadejte platnou e-mailovou adresu."
        }), 400

    # -----------------------------------------------------
    # VALIDACE SLUŽBY
    # -----------------------------------------------------

    if not isinstance(service_key, str):
        return jsonify({
            "status": "error",
            "message": "Neplatná služba."
        }), 400

    service_info = SERVICES.get(service_key)

    if service_info is None:
        return jsonify({
            "status": "error",
            "message": "Vybraná služba neexistuje."
        }), 400

    # -----------------------------------------------------
    # VALIDACE POZNÁMKY
    # -----------------------------------------------------

    if not isinstance(note, str):
        return jsonify({
            "status": "error",
            "message": "Neplatná poznámka."
        }), 400

    note = note.strip()

    if len(note) > 3000:
        return jsonify({
            "status": "error",
            "message": "Poznámka je příliš dlouhá."
        }), 400

    # -----------------------------------------------------
    # VALIDACE PLATEBNÍ REFERENCE
    # -----------------------------------------------------

    payment_reference = normalize_payment_reference(
        payment_reference,
        service_key
    )

    if payment_reference is None:
        return jsonify({
            "status": "error",
            "message": (
                "Chybí platná platební reference. "
                "Vygenerujte prosím nový QR kód."
            )
        }), 400

    # -----------------------------------------------------
    # KONTROLA RESEND
    # -----------------------------------------------------

    if not RESEND_API_KEY:
        logger.error("Chybí RESEND_API_KEY.")

        return jsonify({
            "status": "error",
            "message": (
                "Odesílání objednávek není momentálně "
                "nastaveno. Zkuste to později."
            )
        }), 503

    # -----------------------------------------------------
    # PŘÍPRAVA OBJEDNÁVKY
    # -----------------------------------------------------

    service_title = service_info["title"]
    price = f"{service_info['price']:.2f} EUR"

    # Číslo objednávky je stejné jako platební reference.
    # Bez databáze se nikam trvale neukládá.
    reference_number = payment_reference

    safe_email = safe_html_text(email)
    safe_title = safe_html_text(service_title)
    safe_price = safe_html_text(price)
    safe_reference = safe_html_text(reference_number)

    safe_note = safe_html_text(note) if note else "Bez poznámky"
    safe_note = safe_note.replace("\n", "<br>")

    admin_html = f"""
    <div style="
        font-family: Arial, sans-serif;
        padding: 24px;
        background-color: #0a0512;
        color: #f3e8ff;
        border: 1px solid #d4af37;
        border-radius: 12px;
    ">
        <h2 style="color: #d4af37;">
            Nová objednávka
        </h2>

        <p>
            <strong>Číslo objednávky:</strong>
            {safe_reference}
        </p>

        <p>
            <strong>Vybraná služba:</strong>
            {safe_title}
        </p>

        <p>
            <strong>Cena:</strong>
            {safe_price}
        </p>

        <p>
            <strong>E-mail klienta:</strong>
            {safe_email}
        </p>

        <p>
            <strong>Platební reference:</strong>
            {safe_reference}
        </p>

        <p>
            <strong>Poznámka / Dotaz:</strong><br>
            {safe_note}
        </p>

        <hr style="border: 1px solid #d4af37;">

        <p style="color: #e7c96a;">
            Stav objednávky: ČEKÁ NA RUČNÍ OVĚŘENÍ PLATBY
        </p>

        <p>
            Zkontrolujte platbu v Revolutu podle platební reference.
        </p>

        <p>
            Pro odpověď zákazníkovi použijte tlačítko
            Odpovědět ve své e-mailové aplikaci.
        </p>
    </div>
    """

    # -----------------------------------------------------
    # ODESLÁNÍ E-MAILU
    # -----------------------------------------------------

    try:
        resend.Emails.send({
            "from": RESEND_FROM,
            "to": [ADMIN_EMAIL],
            "reply_to": email,
            "subject": (
                f"Nová objednávka {reference_number} - {service_title}"
            ),
            "html": admin_html,
            "text": (
                f"Nová objednávka: {reference_number}\n"
                f"Služba: {service_title}\n"
                f"Cena: {price}\n"
                f"E-mail: {email}\n"
                f"Platební reference: {reference_number}\n"
                f"Poznámka: {note or 'Bez poznámky'}\n\n"
                "Stav: Čeká na ruční ověření platby."
            )
        })

        return jsonify({
            "status": "success",
            "message": (
                f"Objednávka {reference_number} byla přijata. "
                "Čeká na ruční ověření platby. "
                "Potvrzení objednávky obdržíte po kontrole platby."
            ),
            "reference_number": reference_number,
            "payment_status": "pending"
        })

    except Exception:
        logger.exception("Chyba při odesílání objednávky přes Resend.")

        return jsonify({
            "status": "error",
            "message": (
                "Objednávku se nepodařilo odeslat. "
                "Zkuste to prosím později."
            )
        }), 500


# =========================================================
# LOKÁLNÍ SPUŠTĚNÍ
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )

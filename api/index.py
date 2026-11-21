
import io
import base64
import os
import re
import secrets
import logging
from html import escape
from decimal import Decimal

from flask import Flask, render_template, request, jsonify
import qrcode
import resend


# ============================================================
# MYSTICKÁ SVATYNĚ – TAROT & ASTRO
# Backend: Flask / Python
# Bez databáze a bez zákaznických hesel
# ============================================================

app = Flask(__name__, template_folder='../templates')
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

# Původní platební údaje – zachované
REVOLUT_IBAN = "LT803250069633761109"
REVOLUT_BIC = "REVOLT21"
BENEFICIARY_NAME = "Mystická Svatyně"

# Původní administrátorský e-mail – zachovaný
ADMIN_EMAIL = "ruzar7789@gmail.com"

# Odesílatel e-mailů
RESEND_FROM = "Mystická Svatyně <onboarding@resend.dev>"

# Tajný API klíč Resend ponecháváme ve Vercelu
resend.api_key = os.getenv("RESEND_API_KEY", "")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("mysticka_svatyne")


# ============================================================
# JAZYKY
# ============================================================

SUPPORTED_LANGUAGES = ("de", "cs", "en")
DEFAULT_LANGUAGE = "de"

MESSAGES = {
    "de": {
        "invalid_json": "Die Anfrage enthält keine gültigen JSON-Daten.",
        "invalid_service": "Der ausgewählte Dienst ist ungültig.",
        "invalid_email": "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
        "invalid_reference": "Die Zahlungsreferenz hat ein ungültiges Format.",
        "invalid_request": "Die Anfrage ist ungültig.",
        "email_unavailable": "Die Reservierung kann derzeit nicht gesendet werden. Bitte versuchen Sie es später erneut.",
        "email_failed": "Die Reservierung konnte nicht gesendet werden. Bitte versuchen Sie es später erneut.",
        "payment_notice": "Die Zahlung wird erst nach manueller Prüfung des Zahlungseingangs bestätigt.",
        "pending": "Die Zahlung wartet auf manuelle Bestätigung.",
        "reservation_received": "Ihre Anfrage wurde angenommen. Die Zahlung ist noch nicht bestätigt. Wir prüfen den Zahlungseingang manuell. Der Termin wird individuell vereinbart."
    },
    "cs": {
        "invalid_json": "Požadavek musí obsahovat platná JSON data.",
        "invalid_service": "Vybraná služba není platná.",
        "invalid_email": "Zadejte platnou e-mailovou adresu.",
        "invalid_reference": "Reference platby nemá platný formát.",
        "invalid_request": "Požadavek není platný.",
        "email_unavailable": "Rezervaci nyní nelze odeslat. Zkuste to prosím později.",
        "email_failed": "Odeslání rezervace se nezdařilo. Zkuste to prosím později.",
        "payment_notice": "Platba bude potvrzena až po ruční kontrole připsání peněz.",
        "pending": "Platba čeká na ruční potvrzení.",
        "reservation_received": "Vaše poptávka byla přijata. Platba zatím není potvrzena. Připsání peněz ověříme ručně. Termín bude domluven individuálně."
    },
    "en": {
        "invalid_json": "The request must contain valid JSON data.",
        "invalid_service": "The selected service is invalid.",
        "invalid_email": "Please enter a valid email address.",
        "invalid_reference": "The payment reference has an invalid format.",
        "invalid_request": "The request is invalid.",
        "email_unavailable": "The reservation cannot be sent right now. Please try again later.",
        "email_failed": "The reservation could not be sent. Please try again later.",
        "payment_notice": "Payment will only be confirmed after manual verification of the incoming transfer.",
        "pending": "Payment is awaiting manual confirmation.",
        "reservation_received": "Your request has been received. Payment is not yet confirmed. We will manually verify the incoming transfer. The appointment will be arranged individually."
    }
}


def get_language(value=None):
    if isinstance(value, str):
        value = value.lower().strip()
    return value if value in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def message(key, language=None):
    language = get_language(language)
    return MESSAGES[language].get(key, MESSAGES[DEFAULT_LANGUAGE].get(key, key))


# ============================================================
# SLUŽBY – PŮVODNÍ ID A CENY ZACHOVÁNY
# ============================================================

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


# ============================================================
# TAROT – VŠECH 22 KARET
# ============================================================

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
        "meaning": "Čeká vás spravedlivé vyústění situace. Jednejte v souladu s pravdou a převezměte odpovědnost.",
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


# ============================================================
# POMOCNÉ FUNKCE
# ============================================================

EMAIL_RE = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")


def _json_body():
    if not request.is_json:
        return None

    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else None


def _clean_text(value, *, max_length, field_name, required=False):
    if value is None:
        value = ""

    if not isinstance(value, str):
        raise ValueError(f"Pole {field_name} musí být text.")

    value = value.strip()

    if required and not value:
        raise ValueError(f"Vyplňte pole {field_name}.")

    if len(value) > max_length:
        raise ValueError(
            f"Pole {field_name} je příliš dlouhé "
            f"(maximum {max_length} znaků)."
        )

    return value


def _valid_email(value):
    return bool(EMAIL_RE.fullmatch(value)) and len(value) <= 254


def _valid_service(service_id):
    return isinstance(service_id, str) and service_id in SERVICES


def _make_reference(prefix="MS"):
    return f"{prefix}-{secrets.token_hex(4).upper()}"


def _no_cache(response):
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    return response


# ============================================================
# BEZPEČNOSTNÍ HLAVIČKY
# ============================================================

@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault(
        "Referrer-Policy",
        "strict-origin-when-cross-origin"
    )
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()"
    )
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({
        "status": "error",
        "message": "Požadavek je příliš velký."
    }), 413


# ============================================================
# HLAVNÍ STRÁNKA
# ============================================================

@app.route("/")
def home():
    language = get_language(request.args.get("lang"))

    return render_template(
        "index.html",
        services=SERVICES,
        language=language
    )


# ============================================================
# TAROT – NÁHODNÁ KARTA
# GET /api/draw-card?lang=de
# ============================================================

@app.route("/api/draw-card", methods=["GET"])
def draw_card():
    language = get_language(request.args.get("lang"))

    card = secrets.choice(TAROT_DECK)
    is_reversed = secrets.randbelow(100) < 20

    card_name = card["name"]

    if is_reversed:
        if language == "de":
            card_name += " (Umgekehrt)"
        elif language == "en":
            card_name += " (Reversed)"
        else:
            card_name += " (Obrácená)"

    meaning = (
        card["meaning_reversed"]
        if is_reversed
        else card["meaning"]
    )

    response = jsonify({
        "id": card["id"],
        "name": card_name,
        "element": card["element"],
        "keywords": card["keywords"],
        "meaning": meaning,
        "question": card["question"],
        "is_reversed": is_reversed,
        "language": language
    })

    return _no_cache(response)


# ============================================================
# GENEROVÁNÍ SEPA QR KÓDU
# POST /api/generate-qr
# ============================================================

@app.route("/api/generate-qr", methods=["POST"])
def generate_qr():
    data = _json_body()

    if data is None:
        language = DEFAULT_LANGUAGE
        return jsonify({
            "status": "error",
            "message": message("invalid_json", language)
        }), 400

    language = get_language(data.get("lang"))

    service_id = data.get("service_id", "tarot_basic")

    if not _valid_service(service_id):
        return jsonify({
            "status": "error",
            "message": message("invalid_service", language)
        }), 400

    service = SERVICES[service_id]

    amount = Decimal(
        str(service["price"])
    ).quantize(Decimal("0.01"))

    payment_reference = _make_reference("MS")

    payment_message = (
        f"{service['title'][:25]} Ref:{payment_reference}"
    )

    # EPC / SEPA QR formát
    sepa_string = (
        "BCD\n"
        "002\n"
        "1\n"
        "SCT\n"
        f"{REVOLUT_BIC}\n"
        f"{BENEFICIARY_NAME}\n"
        f"{REVOLUT_IBAN}\n"
        f"EUR{amount:.2f}\n"
        "\n"
        "\n"
        f"{payment_message}"
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4
    )

    qr.add_data(sepa_string)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="#160d24",
        back_color="#ffffff"
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    qr_b64 = base64.b64encode(
        buf.getvalue()
    ).decode("ascii")

    response = jsonify({
        "status": "success",
        "qr_image": f"data:image/png;base64,{qr_b64}",
        "title": service["title"],
        "price": f"{amount:.2f} EUR",
        "iban": REVOLUT_IBAN,
        "bic": REVOLUT_BIC,
        "vs": payment_reference,
        "payment_reference": payment_reference,
        "service_id": service_id,
        "payment_status": "pending_manual_confirmation",
        "payment_notice": message("payment_notice", language)
    })

    return _no_cache(response)


# ============================================================
# REZERVACE A ODESLÁNÍ E-MAILU PŘES RESEND
# POST /api/reserve
# ============================================================

@app.route("/api/reserve", methods=["POST"])
def reserve():
    data = _json_body()

    if data is None:
        return jsonify({
            "status": "error",
            "message": message("invalid_json")
        }), 400

    language = get_language(data.get("lang"))

    try:
        email = _clean_text(
            data.get("email"),
            max_length=254,
            field_name="e-mail",
            required=True
        )

        service_key = data.get("service", "tarot_basic")

        note = _clean_text(
            data.get("note"),
            max_length=2000,
            field_name="poznámka"
        )

        payment_reference = _clean_text(
            data.get("payment_reference"),
            max_length=32,
            field_name="reference platby"
        )

    except ValueError as exc:
        return jsonify({
            "status": "error",
            "message": str(exc)
        }), 400

    if not _valid_email(email):
        return jsonify({
            "status": "error",
            "message": message("invalid_email", language)
        }), 400

    if not _valid_service(service_key):
        return jsonify({
            "status": "error",
            "message": message("invalid_service", language)
        }), 400

    if payment_reference and not re.fullmatch(
        r"MS-[A-F0-9]{8}",
        payment_reference
    ):
        return jsonify({
            "status": "error",
            "message": message("invalid_reference", language)
        }), 400

    service_info = SERVICES[service_key]

    service_title = service_info["title"]

    price = (
        f"{Decimal(str(service_info['price'])).quantize(Decimal('0.01')):.2f} EUR"
    )

    reservation_reference = _make_reference("RES")

    payment_line = (
        payment_reference
        if payment_reference
        else "Zatím nebyla předána – spárování platby je nutné ověřit ručně."
    )

    # Bezpečné escapování zákaznických údajů pro HTML e-mail
    safe_email = escape(email)
    safe_note = escape(note) if note else "Bez poznámky"
    safe_service_title = escape(service_title)
    safe_price = escape(price)
    safe_reservation_reference = escape(reservation_reference)
    safe_payment_line = escape(payment_line)

    admin_html = f"""
    <div style="
        font-family:Arial,sans-serif;
        padding:24px;
        background:#10091b;
        color:#f3e8ff;
    ">
        <h2 style="color:#d4af37;">
            Nová objednávka {safe_reservation_reference}
        </h2>

        <p>
            <strong>Služba:</strong>
            {safe_service_title}
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
            <strong>Reference platby:</strong>
            {safe_payment_line}
        </p>

        <p>
            <strong>Poznámka / záměr:</strong><br>
            {safe_note}
        </p>

        <hr style="border:0;border-top:1px solid #d4af37;">

        <p style="color:#f0c96b;">
            <strong>
                Stav: čeká na ruční kontrolu platby.
            </strong>
        </p>

        <p>
            Ověřte připsání částky na Revolutu před potvrzením
            objednávky zákazníkovi.
        </p>
    </div>
    """

    if not resend.api_key:
        logger.error(
            "RESEND_API_KEY není nastaven; "
            "objednávku nelze e-mailem předat administrátorovi."
        )

        return jsonify({
            "status": "error",
            "message": message("email_unavailable", language)
        }), 503

    try:
        resend.Emails.send({
            "from": RESEND_FROM,
            "to": [ADMIN_EMAIL],
            "reply_to": email,
            "subject": (
                f"Nová objednávka {reservation_reference} – {service_title}"
            ),
            "html": admin_html
        })

    except Exception:
        logger.exception(
            "Odeslání objednávky přes Resend selhalo."
        )

        return jsonify({
            "status": "error",
            "message": message("email_failed", language)
        }), 502

    response = jsonify({
        "status": "success",
        "reference": reservation_reference,
        "payment_reference": payment_reference or None,
        "payment_status": "pending_manual_confirmation",
        "message": message("reservation_received", language)
    })

    return _no_cache(response)


# ============================================================
# SPUŠTĚNÍ APLIKACE
# ============================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )

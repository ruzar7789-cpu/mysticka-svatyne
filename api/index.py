
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


app = Flask(__name__, template_folder="../templates")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

# ---------------------------------------------------------
# KONFIGURACE PLATEB A E-MAILU
# ---------------------------------------------------------

REVOLUT_IBAN = os.getenv(
    "REVOLUT_IBAN",
    "LT803250069633761109"
).replace(" ", "").upper()

REVOLUT_BIC = os.getenv(
    "REVOLUT_BIC",
    "REVOLT21"
).replace(" ", "").upper()

BENEFICIARY_NAME = os.getenv(
    "PAYMENT_BENEFICIARY_NAME",
    "Mystická Svatyně"
)

ADMIN_EMAIL = os.getenv(
    "ADMIN_EMAIL",
    "ruzar7789@gmail.com"
).strip()

RESEND_FROM = os.getenv(
    "RESEND_FROM",
    "Mystická Svatyně <onboarding@resend.dev>"
).strip()

resend.api_key = os.getenv("RESEND_API_KEY", "")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("mysticka_svatyne")


# ---------------------------------------------------------
# JAZYKY
# ---------------------------------------------------------

SUPPORTED_LANGUAGES = ("de", "cs", "en")


def get_language(value):
    if not isinstance(value, str):
        return "de"

    value = value.lower().strip()

    if value not in SUPPORTED_LANGUAGES:
        return "de"

    return value


MESSAGES = {
    "de": {
        "invalid_json": "Die Anfrage enthält keine gültigen JSON-Daten.",
        "invalid_service": "Der ausgewählte Dienst ist ungültig.",
        "invalid_email": "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
        "reservation_error": "Die Anfrage konnte momentan nicht gesendet werden. Bitte versuchen Sie es später erneut.",
        "send_error": "Das Senden der Anfrage ist fehlgeschlagen. Bitte versuchen Sie es später erneut.",
        "payment_notice": "Die Zahlung wird erst nach manueller Prüfung des Zahlungseingangs bestätigt.",
        "too_large": "Die Anfrage ist zu groß.",
        "reservation_success": "Ihre Anfrage wurde angenommen. Die Zahlung ist noch nicht bestätigt. Wir prüfen den Zahlungseingang manuell. Der Termin wird individuell vereinbart.",
        "reversed": " (Umgekehrt)"
    },
    "cs": {
        "invalid_json": "Požadavek musí obsahovat platná JSON data.",
        "invalid_service": "Vybraná služba není platná.",
        "invalid_email": "Zadejte platnou e-mailovou adresu.",
        "reservation_error": "Rezervaci nyní nelze odeslat. Zkuste to prosím později.",
        "send_error": "Odeslání rezervace se nezdařilo. Zkuste to prosím později.",
        "payment_notice": "Platba bude potvrzena až po ruční kontrole připsání peněz.",
        "too_large": "Požadavek je příliš velký.",
        "reservation_success": "Vaše poptávka byla přijata. Platba zatím není potvrzena. Připsání peněz ověříme ručně. Termín bude domluven individuálně.",
        "reversed": " (Obrácená)"
    },
    "en": {
        "invalid_json": "The request must contain valid JSON data.",
        "invalid_service": "The selected service is invalid.",
        "invalid_email": "Please enter a valid email address.",
        "reservation_error": "Your request cannot be sent right now. Please try again later.",
        "send_error": "The request could not be sent. Please try again later.",
        "payment_notice": "Payment will only be confirmed after we manually verify that the money has arrived.",
        "too_large": "The request is too large.",
        "reservation_success": "Your request has been received. Payment has not yet been confirmed. We will manually verify the incoming payment. The appointment will be arranged individually.",
        "reversed": " (Reversed)"
    }
}


# ---------------------------------------------------------
# SLUŽBY A CENY
# ID A CENY ZŮSTÁVAJÍ ZACHOVÁNY
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# TAROT – PŮVODNÍ ČESKÝ OBSAH VŠECH 22 KARET
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# NĚMECKÉ A ANGLICKÉ PŘEKLADY TAROTU
# Struktura: název, živel, klíčová slova,
# přímý význam, obrácený význam, otázka
# ---------------------------------------------------------

TAROT_TRANSLATIONS = {
    "de": {
        "0_fool": (
            "0. Der Narr", "Luft",
            "Neuanfang, Vertrauen, Spontaneität, Unschuld",
            "Heute ist ein Tag für einen Neuanfang. Wagen Sie den Schritt ins Unbekannte und vertrauen Sie darauf, dass das Universum Sie unterstützt.",
            "Hüten Sie sich vor übereilten Entscheidungen und Naivität. Schauen Sie sich lieber zweimal um, bevor Sie springen.",
            "Was hält Sie davon ab, den ersten Schritt in Richtung Ihres Traums zu machen?"
        ),
        "1_magician": (
            "I. Der Magier", "Luft",
            "Manifestation, Willenskraft, Fähigkeiten, Handlung",
            "Sie verfügen über alle Werkzeuge und Ressourcen, die Sie für Ihren Erfolg benötigen. Jetzt ist es an der Zeit, Ihre Absicht in die Realität umzusetzen.",
            "Vielleicht zweifeln Sie an Ihren Fähigkeiten oder verlieren sich in zu vielen Dingen. Konzentrieren Sie sich auf das Wesentliche.",
            "Welches verborgene Talent können Sie heute voll einsetzen?"
        ),
        "2_high_priestess": (
            "II. Die Hohepriesterin", "Wasser",
            "Intuition, Innere Stimme, Geheimnisse, Unterbewusstsein",
            "Hören Sie auf Ihre innere Stimme und die Symbolik Ihrer Träume. Die Antworten liegen in der Stille Ihres Inneren.",
            "Sie überhören möglicherweise die Warnsignale Ihrer Intuition. Halten Sie inne und lassen Sie sich nicht vom Lärm der Außenwelt übertönen.",
            "Was sagt Ihnen Ihre innere Stimme, das Sie bisher überhören?"
        ),
        "3_empress": (
            "III. Die Herrscherin", "Erde",
            "Fülle, Kreativität, Fürsorge, Natur",
            "Eine Zeit des Wachstums, der Kreativität und Fruchtbarkeit beginnt. Gönnen Sie sich Fürsorge und nehmen Sie die Schönheit um sich herum wahr.",
            "Vielleicht erleben Sie eine kreative Blockade oder vernachlässigen Ihre eigenen Bedürfnisse zugunsten anderer. Stärken Sie Ihre Kraftquellen.",
            "Wie können Sie sich heute selbst Liebe und Fürsorge schenken?"
        ),
        "4_emperor": (
            "IV. Der Herrscher", "Feuer",
            "Struktur, Autorität, Stabilität, Grenzen",
            "Es ist Zeit, Ordnung in Ihr Leben zu bringen, klare Grenzen zu setzen und die volle Verantwortung für Ihren Weg zu übernehmen.",
            "Achten Sie auf übermäßige Härte und Kontrolle oder auf Chaos und mangelnde Selbstdisziplin.",
            "Wo in Ihrem Leben sollten Sie klarere Grenzen setzen?"
        ),
        "5_hierophant": (
            "V. Der Hierophant", "Erde",
            "Tradition, Weisheit, Lernen, Spirituelle Führung",
            "Suchen Sie Weisheit in bewährten Werten oder bitten Sie einen erfahrenen Mentor um Rat.",
            "Vielleicht ist es an der Zeit, alte Dogmen zu hinterfragen und Ihren eigenen Weg zu finden.",
            "An welche Überzeugung glauben Sie nur, weil andere sie Ihnen vermittelt haben?"
        ),
        "6_lovers": (
            "VI. Die Liebenden", "Luft",
            "Liebe, Entscheidung, Harmonie, Werte",
            "Diese Karte bringt Harmonie in Beziehungen und weist auf eine wichtige Entscheidung hin, die auf den Werten Ihres Herzens beruht.",
            "Ein innerer Konflikt oder unausgeglichene Beziehungen können Sie beschäftigen. Werden Sie sich darüber klar, was Sie wirklich wollen.",
            "Leben Sie im Einklang mit Ihren wichtigsten Lebenswerten?"
        ),
        "7_chariot": (
            "VII. Der Wagen", "Wasser",
            "Triumph, Entschlossenheit, Bewegung, Kontrolle",
            "Konzentrieren Sie sich auf Ihr Ziel und behalten Sie die Zügel fest in der Hand. Ihre Entschlossenheit führt Sie zum Erfolg.",
            "Vielleicht verlieren Sie die Kontrolle oder setzen sich selbst zu sehr unter Druck. Verlangsamen Sie das Tempo und überdenken Sie Ihre Richtung.",
            "Wohin lenken Sie Ihre Energie, und ist es die richtige Richtung?"
        ),
        "8_strength": (
            "VIII. Die Kraft", "Feuer",
            "Geduld, Innere Stärke, Mitgefühl, Mut",
            "Wahre Stärke entsteht aus Sanftheit, Geduld und dem bewussten Umgang mit den eigenen Schatten und Gefühlen.",
            "Möglicherweise zweifeln Sie an sich selbst oder fühlen sich erschöpft. Seien Sie freundlich zu sich.",
            "Welche Herausforderung können Sie heute mit Ruhe und Freundlichkeit meistern?"
        ),
        "9_hermit": (
            "IX. Der Eremit", "Erde",
            "Selbstreflexion, Einsamkeit, Inneres Licht, Suche",
            "Nehmen Sie sich Zeit für sich selbst. In der Stille entdecken Sie das Licht, das Ihnen den weiteren Weg weist.",
            "Vielleicht ziehen Sie sich zu sehr zurück oder fühlen sich einsam. Scheuen Sie sich nicht, um Hilfe zu bitten.",
            "Was können Sie entdecken, wenn Sie den Lärm der Außenwelt für einen Moment ausschalten?"
        ),
        "10_wheel": (
            "X. Das Rad des Schicksals", "Feuer",
            "Schicksal, Veränderung, Zyklen, Gelegenheit",
            "Das Leben ist ständig in Bewegung. Nehmen Sie Veränderungen als Chance an. Das Schicksal kann sich zu Ihren Gunsten wenden.",
            "Widerstand gegen Veränderungen und das Festhalten an Dingen, deren Zeit vorbei ist, erschweren die Situation.",
            "Gegen welchen Lebenszyklus wehren Sie sich immer noch?"
        ),
        "11_justice": (
            "XI. Die Gerechtigkeit", "Luft",
            "Wahrheit, Gleichgewicht, Ursache und Wirkung, Klarheit",
            "Eine faire Lösung Ihrer Situation steht bevor. Handeln Sie wahrhaftig und übernehmen Sie Verantwortung.",
            "Ungerechtigkeit, Unehrlichkeit oder die Weigerung, eigene Fehler einzugestehen, können eine Rolle spielen.",
            "Sind Sie im Moment zu sich selbst und zu anderen vollkommen ehrlich?"
        ),
        "12_hanged_man": (
            "XII. Der Gehängte", "Wasser",
            "Neue Perspektive, Stillstand, Hingabe, Opfer",
            "Manchmal ist es der beste Schritt, innezuhalten und eine Situation aus einem völlig neuen Blickwinkel zu betrachten.",
            "Unnötiges Aufschieben, das Gefühl, ein Opfer zu sein, oder die Unfähigkeit loszulassen, halten Sie zurück.",
            "Welche neue Perspektive könnte Ihnen helfen, Ihre aktuelle Situation zu lösen?"
        ),
        "13_death": (
            "XIII. Der Tod", "Wasser",
            "Transformation, Ende, Neuanfang, Loslassen",
            "Etwas Altes geht zu Ende und macht Platz für Neues. Nehmen Sie den natürlichen Prozess der Veränderung an.",
            "Die Angst, die Vergangenheit loszulassen, und das Festhalten an alten Mustern verhindern den Neubeginn.",
            "Was müssen Sie endlich loslassen, um weitergehen zu können?"
        ),
        "14_temperance": (
            "XIV. Die Mäßigkeit", "Feuer",
            "Gleichgewicht, Geduld, Harmonie, Frieden",
            "Suchen Sie den Mittelweg und das Gleichgewicht. Geduld und das Verbinden von Gegensätzen bringen Ruhe.",
            "Extreme, Unausgeglichenheit oder mangelnde Geduld können Sie belasten. Verlangsamen Sie sich und finden Sie Ihre Balance.",
            "In welchem Lebensbereich neigen Sie zu unnötigen Extremen?"
        ),
        "15_devil": (
            "XV. Der Teufel", "Erde",
            "Fesseln, Illusionen, Versuchung, Schatten",
            "Erkennen Sie ungesunde Abhängigkeiten und einschränkende Überzeugungen. Den Schlüssel zur Freiheit halten Sie selbst in der Hand.",
            "Sie können sich aus einem toxischen Umfeld befreien oder einen wichtigen Schritt zur Überwindung einer schlechten Gewohnheit machen.",
            "Welche Illusion oder ungesunde Gewohnheit hält Sie innerlich gefangen?"
        ),
        "16_tower": (
            "XVI. Der Turm", "Feuer",
            "Plötzliche Veränderung, Blitz, Befreiung, Erwachen",
            "Der Zusammenbruch falscher Sicherheiten öffnet den Weg zur Wahrheit. Eine Veränderung kann plötzlich, aber reinigend sein.",
            "Das Aufschieben einer unvermeidlichen Veränderung oder die Angst, alte Strukturen aufzubrechen, hält Sie zurück.",
            "Welche nicht mehr funktionierende Sicherheit in Ihrem Leben muss erneuert werden?"
        ),
        "17_star": (
            "XVII. Der Stern", "Luft",
            "Hoffnung, Inspiration, Heilung, Klarheit",
            "Nach dem Sturm kehren Ruhe und Hoffnung zurück. Vertrauen Sie auf die Zukunft und auf die Kräfte, die Sie begleiten.",
            "Vielleicht verlieren Sie den Glauben oder fühlen sich entmutigt. Denken Sie daran: Auch nach der dunkelsten Nacht wird es wieder hell.",
            "Was schenkt Ihnen das stärkste Gefühl von Hoffnung und Ruhe?"
        ),
        "18_moon": (
            "XVIII. Der Mond", "Wasser",
            "Illusionen, Träume, Unsicherheit, Intuition",
            "Die Dinge sind möglicherweise nicht so, wie sie scheinen. Gehen Sie durch den Nebel und vertrauen Sie Ihrem inneren Kompass.",
            "Illusionen können sich auflösen, Ängste überwunden und verworrene Situationen geklärt werden.",
            "Welche verborgene Angst hindert Sie daran, die Situation klar zu sehen?"
        ),
        "19_sun": (
            "XIX. Die Sonne", "Feuer",
            "Freude, Erfolg, Vitalität, Klarheit",
            "Positive Energie begleitet Sie. Eine Zeit der Freude, des Erfolgs und der Lebenskraft erwartet Sie.",
            "Vielleicht übersehen Sie vorübergehend das Positive. Die Sonne scheint weiterhin, auch wenn Wolken sie verdecken.",
            "Wofür können Sie in diesem Augenblick besonders dankbar sein?"
        ),
        "20_judgement": (
            "XX. Das Gericht", "Feuer",
            "Erwachen, Ruf, Wiedergeburt, Klarheit",
            "Ein Moment klarer Erkenntnis und der Befreiung von der Vergangenheit steht bevor. Hören Sie auf Ihren inneren Ruf.",
            "Selbstzweifel, übermäßige Selbstkritik oder die Weigerung, ein altes Kapitel abzuschließen, können Sie zurückhalten.",
            "In welche neue Lebensphase ruft Sie Ihr Inneres gerade?"
        ),
        "21_world": (
            "XXI. Die Welt", "Erde",
            "Vollendung, Integration, Erfüllung, Ganzheit",
            "Sie haben Ihr Ziel erreicht und ein wichtiges Kapitel abgeschlossen. Genießen Sie das Gefühl der Ganzheit.",
            "Unerledigte Angelegenheiten sind noch offen. Machen Sie den letzten Schritt, um den alten Zyklus abzuschließen.",
            "Welchen Erfolg dürfen Sie heute feiern?"
        )
    },

    "en": {
        "0_fool": (
            "0. The Fool", "Air",
            "New beginnings, Trust, Spontaneity, Innocence",
            "Today is a day for a new beginning. Do not be afraid to step into the unknown and trust that the universe will support you.",
            "Beware of rushed decisions and naivety. Look twice before you leap.",
            "What is stopping you from taking the first step toward your dream?"
        ),
        "1_magician": (
            "I. The Magician", "Air",
            "Manifestation, Willpower, Skills, Action",
            "You have all the tools and resources you need to succeed. It is time to turn your intention into reality.",
            "You may be doubting your abilities or scattering your attention. Focus on what truly matters.",
            "Which hidden talent can you fully use today?"
        ),
        "2_high_priestess": (
            "II. The High Priestess", "Water",
            "Intuition, Inner voice, Mystery, Subconscious",
            "Listen to your inner voice and the symbolism of your dreams. The answers are hidden in the silence within you.",
            "You may be ignoring warning signs from your intuition. Pause and do not let the noise around you drown it out.",
            "What is your quiet inner voice telling you that you keep overlooking?"
        ),
        "3_empress": (
            "III. The Empress", "Earth",
            "Abundance, Creativity, Care, Nature",
            "A period of growth, creativity and fertility is approaching. Take care of yourself and notice the beauty around you.",
            "You may be experiencing a creative block or neglecting your own needs for the sake of others. Restore your energy.",
            "How can you show love and care to yourself today?"
        ),
        "4_emperor": (
            "IV. The Emperor", "Fire",
            "Structure, Authority, Stability, Boundaries",
            "It is time to bring order into your life, set clear boundaries and take full responsibility for your direction.",
            "Beware of excessive rigidity and control, or the opposite: chaos and a lack of self-discipline.",
            "Where in your life do you need to establish stronger boundaries?"
        ),
        "5_hierophant": (
            "V. The Hierophant", "Earth",
            "Tradition, Wisdom, Learning, Spiritual guidance",
            "Seek wisdom in established values or ask an experienced mentor for advice.",
            "It may be time to question old doctrines and find your own individual path.",
            "Which belief do you hold only because others taught it to you?"
        ),
        "6_lovers": (
            "VI. The Lovers", "Air",
            "Love, Choice, Harmony, Values",
            "This card brings harmony to relationships and signals an important decision guided by the values of your heart.",
            "Inner conflict or unbalanced relationships may be present. Clarify what you truly want.",
            "Are you aligned with your most important life values?"
        ),
        "7_chariot": (
            "VII. The Chariot", "Water",
            "Triumph, Determination, Movement, Control",
            "Focus on your goal and keep the reins firmly in your hands. Your determination can lead you to victory.",
            "You may be losing control or pushing yourself too hard. Slow down and reconsider your direction.",
            "Where are you directing your energy, and is it the right direction?"
        ),
        "8_strength": (
            "VIII. Strength", "Fire",
            "Patience, Inner strength, Compassion, Courage",
            "True strength comes from gentleness, patience and mastering your own shadows and emotions.",
            "You may be doubting yourself or feeling exhausted. Remember to be kind to yourself.",
            "Which challenge can you overcome today with calmness and kindness?"
        ),
        "9_hermit": (
            "IX. The Hermit", "Earth",
            "Self-reflection, Solitude, Inner light, Searching",
            "Give yourself time alone. In stillness, you may discover the light that guides your next steps.",
            "You may be isolating yourself too much or feeling lonely. Do not be afraid to ask for help.",
            "What might you discover if you switch off the noise around you for a moment?"
        ),
        "10_wheel": (
            "X. Wheel of Fortune", "Fire",
            "Destiny, Change, Cycles, Opportunity",
            "Life is constantly moving. Accept change as an opportunity; fate may be turning in your favor.",
            "Resisting change and holding on to things whose time has passed only makes the situation harder.",
            "Which cycle in your life are you still resisting?"
        ),
        "11_justice": (
            "XI. Justice", "Air",
            "Truth, Balance, Cause and effect, Clarity",
            "A fair outcome is approaching. Act in accordance with the truth and take responsibility.",
            "Injustice, dishonesty or refusing to admit your own mistake may be present.",
            "Are you being completely honest with yourself and others right now?"
        ),
        "12_hanged_man": (
            "XII. The Hanged Man", "Water",
            "New perspective, Pause, Surrender, Sacrifice",
            "Sometimes the best step is to pause and look at the situation from a completely new point of view.",
            "Unnecessary delays, a sense of victimhood or an inability to let things flow freely may be holding you back.",
            "What new perspective could help you resolve your current situation?"
        ),
        "13_death": (
            "XIII. Death", "Water",
            "Transformation, Ending, New beginning, Release",
            "Something old is ending to make room for something new. Accept the natural process of transformation.",
            "Fear of leaving the past behind and holding on to old patterns can prevent new beginnings.",
            "What do you finally need to let go of so you can move forward?"
        ),
        "14_temperance": (
            "XIV. Temperance", "Fire",
            "Balance, Patience, Harmony, Peace",
            "Seek the middle path and balance. Patience and the gentle blending of opposites will bring calm.",
            "Extremes, imbalance or a lack of patience may be affecting you. Slow down and restore your balance.",
            "In which area of your life are you going to unnecessary extremes?"
        ),
        "15_devil": (
            "XV. The Devil", "Earth",
            "Bonds, Illusions, Temptation, Shadow",
            "Recognize unhealthy dependencies and limiting beliefs. The key to freedom is in your own hands.",
            "You may be freeing yourself from a toxic environment or making a breakthrough in overcoming a bad habit.",
            "Which illusion or unhealthy habit is holding you back inside?"
        ),
        "16_tower": (
            "XVI. The Tower", "Fire",
            "Sudden change, Lightning, Liberation, Awakening",
            "The collapse of false certainties opens the way to truth. Change may be sudden, but it can also be cleansing.",
            "Putting off an inevitable change or fearing the breakdown of old structures may be holding you back.",
            "Which false certainty in your life needs to be rebuilt?"
        ),
        "17_star": (
            "XVII. The Star", "Air",
            "Hope, Inspiration, Healing, Clarity",
            "Calm and hope return after the storm. Trust in the future and in the higher forces supporting you.",
            "You may be losing faith or feeling discouraged. Remember that even the darkest night gives way to dawn.",
            "What gives you the greatest feeling of hope and peace?"
        ),
        "18_moon": (
            "XVIII. The Moon", "Water",
            "Illusions, Dreams, Uncertainty, Intuition",
            "Things may not be as they appear. Move through the mist while trusting your inner compass.",
            "Illusions may be clearing, fears may be overcome and a confusing situation may become clearer.",
            "What hidden fear is preventing you from seeing the situation clearly?"
        ),
        "19_sun": (
            "XIX. The Sun", "Fire",
            "Joy, Success, Vitality, Clarity",
            "Positive energy surrounds you. A period of joy, success and vitality lies ahead.",
            "You may temporarily overlook the positive things. The sun is still shining, even when hidden behind clouds.",
            "What can you be most grateful for at this moment?"
        ),
        "20_judgement": (
            "XX. Judgement", "Fire",
            "Awakening, Calling, Rebirth, Clarity",
            "A moment of clear realization and release from the past is approaching. Listen to your higher calling.",
            "Self-doubt, self-criticism or refusing to close an old chapter may be holding you back.",
            "Toward which new phase of life is your inner self calling you now?"
        ),
        "21_world": (
            "XXI. The World", "Earth",
            "Completion, Integration, Fulfilment, Wholeness",
            "You have reached your goal and completed an important chapter. Enjoy the feeling of wholeness.",
            "Some matters remain unfinished. Take the final step toward closing the old cycle.",
            "Which achievement deserves to be celebrated today?"
        )
    }
}


def get_translated_card(card, language, is_reversed):
    """
    Vrátí kartu v požadovaném jazyce.
    Čeština používá původní obsah TAROT_DECK.
    """
    result = dict(card)

    if language in ("de", "en"):
        translation = TAROT_TRANSLATIONS.get(language, {}).get(card["id"])

        if translation:
            (
                name,
                element,
                keywords,
                meaning,
                meaning_reversed,
                question
            ) = translation

            result["name"] = name
            result["element"] = element
            result["keywords"] = keywords
            result["meaning"] = meaning
            result["meaning_reversed"] = meaning_reversed
            result["question"] = question

    if is_reversed:
        result["name"] += MESSAGES[language]["reversed"]
        result["meaning"] = result["meaning_reversed"]

    return result


# ---------------------------------------------------------
# VALIDACE A POMOCNÉ FUNKCE
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# BEZPEČNOSTNÍ HLAVIČKY
# ---------------------------------------------------------

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
    language = get_language(request.args.get("lang", "de"))

    return jsonify({
        "status": "error",
        "message": MESSAGES[language]["too_large"]
    }), 413


# ---------------------------------------------------------
# HLAVNÍ STRÁNKA
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template(
        "index.html",
        services=SERVICES
    )


# ---------------------------------------------------------
# DENNÍ TAROTOVÁ KARTA
# GET /api/draw-card?lang=de
# GET /api/draw-card?lang=cs
# GET /api/draw-card?lang=en
# ---------------------------------------------------------

@app.route("/api/draw-card", methods=["GET"])
def draw_card():
    language = get_language(request.args.get("lang", "de"))

    card = secrets.choice(TAROT_DECK)
    is_reversed = secrets.randbelow(100) < 20

    translated_card = get_translated_card(
        card,
        language,
        is_reversed
    )

    response = jsonify({
        "id": translated_card["id"],
        "name": translated_card["name"],
        "element": translated_card["element"],
        "keywords": translated_card["keywords"],
        "meaning": translated_card["meaning"],
        "question": translated_card["question"],
        "is_reversed": is_reversed,
        "language": language
    })

    return _no_cache(response)


# ---------------------------------------------------------
# GENEROVÁNÍ SEPA / REVOLUT QR KÓDU
# ---------------------------------------------------------

@app.route("/api/generate-qr", methods=["POST"])
def generate_qr():
    data = _json_body()
    language = get_language(
        (data or {}).get("lang", request.args.get("lang", "de"))
    )

    if data is None:
        return jsonify({
            "status": "error",
            "message": MESSAGES[language]["invalid_json"]
        }), 400

    service_id = data.get("service_id", "tarot_basic")

    if not _valid_service(service_id):
        return jsonify({
            "status": "error",
            "message": MESSAGES[language]["invalid_service"]
        }), 400

    service = SERVICES[service_id]

    amount = Decimal(
        str(service["price"])
    ).quantize(Decimal("0.01"))

    message = service["title"][:35]
    payment_reference = _make_reference("MS")

    # EPC / SEPA QR.
    # QR kód pouze připraví platební příkaz.
    # Platba se musí následně ověřit ručně v Revolutu.

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
        f"{message} Ref:{payment_reference}"
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

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    response = jsonify({
        "status": "success",
        "qr_image": f"data:image/png;base64,{qr_base64}",
        "title": service["title"],
        "price": f"{amount:.2f} EUR",
        "iban": REVOLUT_IBAN,
        "bic": REVOLUT_BIC,
        "vs": payment_reference,
        "payment_reference": payment_reference,
        "service_id": service_id,
        "payment_status": "pending_manual_confirmation",
        "payment_notice": MESSAGES[language]["payment_notice"]
    })

    return _no_cache(response)


# ---------------------------------------------------------
# REZERVACE A ODESLÁNÍ E-MAILU PŘES RESEND
# ---------------------------------------------------------

@app.route("/api/reserve", methods=["POST"])
def reserve():
    data = _json_body()
    language = get_language(
        (data or {}).get("lang", request.args.get("lang", "de"))
    )

    if data is None:
        return jsonify({
            "status": "error",
            "message": MESSAGES[language]["invalid_json"]
        }), 400

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
            "message": MESSAGES[language]["invalid_email"]
        }), 400

    if not _valid_service(service_key):
        return jsonify({
            "status": "error",
            "message": MESSAGES[language]["invalid_service"]
        }), 400

    if payment_reference and not re.fullmatch(
        r"MS-[A-F0-9]{8}",
        payment_reference
    ):
        return jsonify({
            "status": "error",
            "message": "Reference platby nemá platný formát."
        }), 400

    service_info = SERVICES[service_key]

    service_title = service_info["title"]

    price = (
        f"{Decimal(str(service_info['price'])).quantize(Decimal('0.01')):.2f} EUR"
    )

    reservation_reference = _make_reference("RES")

    payment_line = (
        payment_reference
        or "Zatím nebyla předána – spárování platby je nutné ověřit ručně."
    )

    # Ochrana HTML e-mailu před vložením nebezpečného obsahu.
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
            Ověřte připsání částky na Revolutu
            před potvrzením objednávky zákazníkovi.
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
            "message": MESSAGES[language]["reservation_error"]
        }), 503

    try:
        resend.Emails.send({
            "from": RESEND_FROM,
            "to": [ADMIN_EMAIL],
            "reply_to": email,
            "subject": (
                f"Nová objednávka {reservation_reference} – "
                f"{service_title}"
            ),
            "html": admin_html
        })

    except Exception:
        logger.exception(
            "Odeslání objednávky přes Resend selhalo."
        )

        return jsonify({
            "status": "error",
            "message": MESSAGES[language]["send_error"]
        }), 502

    response = jsonify({
        "status": "success",
        "reference": reservation_reference,
        "payment_reference": payment_reference or None,
        "payment_status": "pending_manual_confirmation",
        "message": (
            f"Poptávka {reservation_reference} byla přijata. "
            "Platba zatím není potvrzena; objednávku ověříme "
            "ručně po připsání peněz. "
            "Termín bude domluven individuálně."
        )
    })

    return _no_cache(response)


# ---------------------------------------------------------
# LOKÁLNÍ SPUŠTĚNÍ
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )

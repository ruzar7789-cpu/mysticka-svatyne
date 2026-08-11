import io
import base64
import random
import os
from flask import Flask, render_template, request, jsonify
import qrcode
import resend

app = Flask(__name__, template_folder='../templates')

REVOLUT_IBAN = "LT803250069633761109"
REVOLUT_BIC = "REVOLT21"
ADMIN_EMAIL = "ruzar7789@gmail.com"

resend.api_key = os.getenv("RESEND_API_KEY", "")

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

@app.route('/')
def home():
    return render_template('index.html', services=SERVICES)

@app.route('/api/draw-card', methods=['GET'])
def draw_card():
    card = random.choice(TAROT_DECK)
    is_reversed = random.random() < 0.20  # 20% šance na obrácenou kartu

    card_name = f"{card['name']} (Obrácená)" if is_reversed else card['name']
    meaning = card['meaning_reversed'] if is_reversed else card['meaning']

    return jsonify({
        "id": card["id"],
        "name": card_name,
        "element": card["element"],
        "keywords": card["keywords"],
        "meaning": meaning,
        "question": card["question"],
        "is_reversed": is_reversed
    })

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    data = request.json or {}
    service_id = data.get('service_id', 'tarot_basic')
    service = SERVICES.get(service_id, SERVICES['tarot_basic'])

    amount = service['price']
    message = service['title'][:35]
    vs = str(random.randint(100000, 999999))

    # SEPA EPC QR řetězec včetně BIC kódu
    sepa_string = (
        f"BCD\n002\n1\nSCT\n"
        f"{REVOLUT_BIC}\n"
        f"Mystická Svatyně\n"
        f"{REVOLUT_IBAN}\n"
        f"EUR{amount:.2f}\n\n\n"
        f"{message} Ref:{vs}"
    )

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(sepa_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#d4af37", back_color="#0a0512")

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return jsonify({
        "qr_image": f"data:image/png;base64,{qr_b64}",
        "title": service['title'],
        "price": f"{amount:.2f} EUR",
        "iban": REVOLUT_IBAN,
        "bic": REVOLUT_BIC,
        "vs": vs
    })

@app.route('/api/reserve', methods=['POST'])
def reserve():
    data = request.json or {}
    email = data.get('email', '').strip()
    service_key = data.get('service', 'tarot_basic')
    note = data.get('note', '').strip()

    service_info = SERVICES.get(service_key, SERVICES['tarot_basic'])
    service_title = service_info['title']
    price = f"{service_info['price']} EUR"
    reference_number = f"RES-{random.randint(1000, 9999)}"

    admin_html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #0a0512; color: #f3e8ff;">
        <h2 style="color: #d4af37;">Nová objednávka č. {reference_number}</h2>
        <p><strong>Vybraná služba:</strong> {service_title} ({price})</p>
        <p><strong>E-mail klienta:</strong> {email}</p>
        <p><strong>Poznámka / Dotaz:</strong> {note if note else 'Bez poznámky'}</p>
        <hr style="border: 1px solid #d4af37;">
        <p><em>Pro odpověď zákazníkovi stačí kliknout na "Odpovědět" ve vaší e-mailové aplikaci.</em></p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": "Mystická Svatyně <onboarding@resend.dev>",
            "to": ADMIN_EMAIL,
            "reply_to": email if email else ADMIN_EMAIL,
            "subject": f"Nová objednávka {reference_number} - {service_title}",
            "html": admin_html
        })

        return jsonify({
            "status": "success",
            "message": f"Rezervace č. {reference_number} byla úspěšně odeslána! Potvrzení bylo doručeno na váš e-mail."
        })

    except Exception as e:
        print(f"Resend chyba: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Chyba při odesílání e-mailu: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
    

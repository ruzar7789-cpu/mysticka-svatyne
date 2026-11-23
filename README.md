# Mystická Svatyně — Tarot & Astro

Prémiový vícejazyčný web pro tarot, astrologii a symbolickou duchovní inspiraci.

## Technologie

- Python + Flask (serverless funkce na Vercelu)
- HTML, CSS a vanilla JavaScript
- Tarotový balíček Velké arkány
- SEPA QR platební příkazy
- E-mailové předávání objednávek přes Resend
- Potvrzení přijetí objednávky zákazníkovi v jazyce DE/CS/EN
- Volba digitálního doručení e-mailem nebo individuální domluvy termínu
- Jazyky: němčina (výchozí), čeština a angličtina

## Architektura a soukromí

Aplikace nepoužívá databázi ani zákaznické účty/hesla. Denní karta a volba jazyka se ukládají pouze v prohlížeči návštěvníka. Objednávkový formulář odešle údaje administrátorovi e-mailem.

SEPA QR pouze připravuje bankovní příkaz. Odeslání formuláře ani zobrazení QR kódu neznamená, že byla platba přijata. Připsání platby je nutné ověřit ručně.

## Proměnné prostředí

Nastavte je v chráněných proměnných Vercelu (Production, Preview podle potřeby), nikoli ve zdrojovém kódu:

- `REVOLUT_IBAN` — IBAN příjemce
- `REVOLUT_BIC` — BIC/SWIFT příjemce
- `PAYMENT_BENEFICIARY_NAME` — jméno příjemce
- `ADMIN_EMAIL` — e-mail pro nové objednávky
- `RESEND_API_KEY` — API klíč Resend
- `RESEND_FROM` — ověřená odesílací adresa/doména v Resend
- `LOG_LEVEL` — volitelně, výchozí `INFO`

Ukázka je v souboru `.env.example`. Skutečný soubor `.env` se nesmí commitovat.

## Lokální spuštění

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python api/index.py
```

Na Windows aktivujte prostředí příkazem `.venv\\Scripts\\activate`.

## API

- `GET /` — web
- `GET /api/draw-card?lang=de|cs|en` — denní tarotová karta
- `POST /api/generate-qr` — vytvoření SEPA QR
- `POST /api/reserve` — předání objednávky administrátorovi a potvrzení zákazníkovi

## Objednávka a doručení

Zákazník zvolí digitální doručení e-mailem nebo osobní službu s individuální domluvou termínu. Preferovaný čas může uvést ve formuláři. Objednávka se předá administrátorovi a zákazník dostane potvrzení v jazyce DE/CS/EN. Platba zůstává ručně ověřovaná; potvrzovací e-mail není potvrzením platby ani termínu. Po ověření platby provozovatel ručně odešle hotový digitální výstup, případně domluví osobní službu. Aplikace nadále nepoužívá databázi ani zákaznické účty.

## Před ostrým spuštěním

1. Nastavit a ověřit všechny platební a e-mailové proměnné.
2. Ověřit SEPA QR ve více bankovních aplikacích a potvrdit příjemce, IBAN, BIC, měnu i částku.
3. Otestovat objednávku v DE/CS/EN včetně doručení e-mailu.
4. Doplnit skutečnou identitu provozovatele, adresu, kontaktní údaje a právně zkontrolované Impressum, zásady ochrany osobních údajů, obchodní podmínky a informace o odstoupení/reklamacích podle konkrétního obchodního modelu.
5. Připojit vlastní doménu a ověřit DNS/HTTPS.
6. Provést závěrečný bezpečnostní, přístupnostní a mobilní test.

Právní identifikační údaje provozovatele nejsou v repozitáři domýšleny ani nahrazovány smyšlenými údaji.

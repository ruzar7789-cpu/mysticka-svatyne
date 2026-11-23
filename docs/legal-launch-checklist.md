# Legal and production-readiness handoff — Mystická Svatyně

Status: preparation only. This document is not a legal notice and must not be published as a substitute for reviewed legal texts.

## Operator information supplied by the owner

- Business form: sole proprietor (OSVČ / Einzelunternehmen)
- Registration country: Germany
- Target markets: Germany and Czechia
- Business designation as supplied: "ice cards a vertirieb" (spelling and legal/trade-name status not verified)
- Address as supplied: "Hauptstraße 20, Pethau, Zittau" (postal code and exact postal formatting missing)
- Public contact email: ruzar7789@gmail.com
- Telephone: not supplied

## Mandatory identity checks before publishing the Impressum

1. Obtain the proprietor's full first and last legal name. For a non-registered sole proprietorship, a trade name does not replace the proprietor's name.
2. Confirm the exact registered business/trade designation and spelling.
3. Obtain the full service address including postal code and confirm that it is a serviceable physical address.
4. Confirm whether a business telephone number is available; do not invent one.
5. Confirm whether the operator has a VAT ID (USt-IdNr.), Wirtschafts-Identifikationsnummer, or commercial-register entry. Publish only identifiers that actually exist and are legally required.
6. Confirm whether the operator is subject to a professional regulator or special authorization. Do not list a regulator unless applicable.

## Repository facts observed on feat/celestial-premium-launch

- The application is a Flask serverless site with a static HTML/CSS/JavaScript frontend.
- Supported UI languages are German, Czech, and English.
- There is no application database or customer login/account flow in the reviewed code.
- The browser stores the daily tarot card in localStorage, keyed by language and date. The reviewed code does not show a consent-management platform or analytics integration.
- The booking form sends the customer's email address, selected service, free-text note, payment reference, and language to POST /api/reserve.
- The backend sends the booking details by email through Resend to the configured administrative recipient. The customer email is used as reply-to. The code does not persist bookings to an application database.
- The SEPA QR endpoint uses configured bank details and a service price. The QR is only a payment instruction; payment is manually verified.
- The application uses Vercel hosting. Actual Vercel log retention/settings and the Resend account region, data-processing agreement, retention, and transfer terms have not been verified from this repository.
- The repository's .env.example contains empty placeholders. The code reads bank and mail settings from environment variables. The actual encrypted Vercel environment values have not been verified.
- The current frontend still contains a combined placeholder "Terms & Privacy" modal with incomplete provider and privacy statements. It is not a complete Impressum, privacy notice, terms, or withdrawal notice.

## Legal content still to prepare and review

- German Impressum with verified proprietor identity, full address, contact details, and only applicable registration/tax/regulatory details.
- German Datenschutzerklärung describing the actual hosting, request handling, email delivery through Resend, data categories, purposes, legal bases, recipients/processors, international transfers where relevant, retention, data-subject rights, and supervisory-authority complaint rights.
- AGB/service terms reflecting the actual services, booking/contract formation, prices, payment, scheduling, delivery, complaints, and cancellation.
- Consumer withdrawal information and model withdrawal form where required. The flow must be checked against the exact service and contract-formation process; any request to start during the withdrawal period and any acknowledgment of loss of withdrawal rights must be implemented only where legally appropriate.
- Czech-language versions and any mandatory Czech-market consumer information for sales directed to Czech consumers.

## Technical follow-up before production

- Replace the combined placeholder modal with separate, permanently accessible pages/links for Impressum, Datenschutz, AGB, and Widerruf.
- Add an explicit customer-facing order summary and clarify when a binding contract is formed. The current interface should not imply that sending the enquiry confirms payment or a booked appointment.
- Review the email payload and minimize free-text personal data; add appropriate retention/deletion procedures.
- Verify Resend's data-processing terms and the configured sender domain; verify Vercel's hosting/privacy settings and log retention.
- Verify payment recipient, SEPA QR payload, and the production environment variables without exposing credentials in Git.
- Test the complete DE/CS/EN customer journey and obtain qualified legal review before enabling production sales.

## Open owner confirmations

- Full legal first and last name of the sole proprietor.
- Exact spelling and status of "ice cards a vertirieb" (trade name or registered business name).
- Postal code and confirmation of the full address.
- Whether VAT ID / Wirtschafts-ID / register entry exists.
- Whether a public business telephone should be added.
- Whether the legal operator of Mystická Svatyně is the same sole proprietor/business named above.
- Whether tarot readings are delivered immediately as digital content, later by email, or through scheduled live consultations; and whether rituals are performed remotely or in person.

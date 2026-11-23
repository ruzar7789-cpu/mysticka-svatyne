import base64
import unittest
from unittest.mock import patch

from api import index as site


class MystickaSvatyneTests(unittest.TestCase):
    def setUp(self):
        site.app.config.update(TESTING=True)
        self.client = site.app.test_client()

    def test_homepage_renders_premium_site(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mystická Svatyně".encode("utf-8"), response.data)
        self.assertIn(b"id=\"knihovna\"", response.data)
        self.assertIn(b'id="faq"', response.data)
        self.assertIn(b'href="#rezervace" data-i18n="contact"', response.data)
        self.assertNotIn(b"ruzar7789@gmail.com", response.data)

    def test_daily_card_respects_requested_language(self):
        response = self.client.get("/api/draw-card?lang=cs")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["language"], "cs")
        self.assertTrue(payload["name"])
        self.assertTrue(payload["meaning"])

    def test_sepa_qr_is_generated_from_configured_test_details(self):
        with patch.object(site, "REVOLUT_IBAN", "DE89370400440532013000"), \
             patch.object(site, "REVOLUT_BIC", "COBADEFFXXX"), \
             patch.object(site, "BENEFICIARY_NAME", "Test Empfaenger"):
            response = self.client.post(
                "/api/generate-qr",
                json={"service_id": "tarot_basic", "lang": "cs"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["service_id"], "tarot_basic")
        self.assertEqual(payload["payment_status"], "pending_manual_confirmation")
        self.assertTrue(payload["qr_image"].startswith("data:image/png;base64,"))
        base64.b64decode(payload["qr_image"].split(",", 1)[1], validate=True)

    def test_qr_is_disabled_when_bank_details_are_missing(self):
        with patch.object(site, "REVOLUT_IBAN", ""), \
             patch.object(site, "REVOLUT_BIC", ""):
            response = self.client.post(
                "/api/generate-qr",
                json={"service_id": "tarot_basic", "lang": "cs"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Platební údaje", response.get_json()["message"])

    def test_invalid_service_is_rejected(self):
        response = self.client.post(
            "/api/generate-qr",
            json={"service_id": "not-a-service", "lang": "cs"},
        )
        self.assertEqual(response.status_code, 400)

    def test_reservation_requires_email_configuration(self):
        with patch.object(site, "ADMIN_EMAIL", ""), \
             patch.object(site, "RESEND_FROM", ""), \
             patch.object(site.resend, "api_key", ""):
            response = self.client.post(
                "/api/reserve",
                json={
                    "email": "customer@example.com",
                    "service": "tarot_basic",
                    "note": "",
                    "payment_reference": "MS-A1B2C3D4",
                    "lang": "cs",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("rezervaci", response.get_json()["message"].lower())


if __name__ == "__main__":
    unittest.main()

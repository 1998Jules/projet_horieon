from django.test import SimpleTestCase


class AccueilTests(SimpleTestCase):
    def test_la_racine_redirige_vers_le_geoportail(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/geoportail/", fetch_redirect_response=False)

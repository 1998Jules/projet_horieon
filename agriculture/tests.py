import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token

from .models import CropCalendar

CALENDAR = {
    "name": "Maïs", "crop_type": "CEREAL", "duration_days": 90,
    "sowing_start": 4, "sowing_end": 5, "weeding_start": 5, "weeding_end": 6,
    "harvest_start": 7, "harvest_end": 8,
}


class CropCalendarPermissionsTests(TestCase):
    """Le calendrier cultural se lit librement mais ne se modifie que par un administrateur."""

    def setUp(self):
        self.admin = User.objects.create_user("admin", password="x", is_staff=True)
        self.farmer = User.objects.create_user("paysan", password="x")
        self.admin_token = Token.objects.create(user=self.admin).key
        self.farmer_token = Token.objects.create(user=self.farmer).key
        self.item = CropCalendar.objects.create(**CALENDAR)

    def post(self, url, data=None, token=None):
        headers = {"HTTP_AUTHORIZATION": f"Token {token}"} if token else {}
        return self.client.post(url, data=json.dumps(data or {}), content_type="application/json", **headers)

    def test_lecture_publique(self):
        response = self.client.get("/agriculture/api/crop-calendar/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_ajout_refuse_sans_authentification(self):
        response = self.post("/agriculture/api/crop-calendar/add/", CALENDAR)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(CropCalendar.objects.count(), 1)

    def test_ajout_refuse_a_un_utilisateur_non_administrateur(self):
        response = self.post("/agriculture/api/crop-calendar/add/", CALENDAR, token=self.farmer_token)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CropCalendar.objects.count(), 1)

    def test_ajout_par_un_administrateur(self):
        response = self.post("/agriculture/api/crop-calendar/add/", CALENDAR, token=self.admin_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CropCalendar.objects.count(), 2)

    def test_ajout_avec_champ_manquant(self):
        response = self.post("/agriculture/api/crop-calendar/add/", {"name": "Riz"}, token=self.admin_token)
        self.assertEqual(response.status_code, 400)

    def test_modification_refusee_sans_authentification(self):
        response = self.post(f"/agriculture/api/crop-calendar/update/{self.item.pk}/", {"name": "Piraté"})
        self.assertEqual(response.status_code, 401)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "Maïs")

    def test_modification_d_une_culture_inexistante(self):
        response = self.post("/agriculture/api/crop-calendar/update/999999/", {"name": "X"}, token=self.admin_token)
        self.assertEqual(response.status_code, 404)

    def test_suppression_refusee_a_un_utilisateur_non_administrateur(self):
        response = self.post(f"/agriculture/api/crop-calendar/delete/{self.item.pk}/", token=self.farmer_token)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(CropCalendar.objects.filter(pk=self.item.pk).exists())

    def test_suppression_par_un_administrateur(self):
        response = self.post(f"/agriculture/api/crop-calendar/delete/{self.item.pk}/", token=self.admin_token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CropCalendar.objects.filter(pk=self.item.pk).exists())


class SessionCsrfTests(TestCase):
    """Les vues d'API sont exemptées de CSRF : la session ne suffit pas pour écrire."""

    def setUp(self):
        self.user = User.objects.create_user("paysan", password="x")

    def test_ecriture_refusee_avec_la_seule_session(self):
        self.client.force_login(self.user)
        response = self.client.post("/agriculture/api/champs/create/", data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_lecture_acceptee_avec_la_session(self):
        self.client.force_login(self.user)
        response = self.client.get("/agriculture/api/alerts/")
        self.assertEqual(response.status_code, 200)

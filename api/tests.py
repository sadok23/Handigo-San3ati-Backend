from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import User, Client, Ouvrier, Demande, Commande, Portefeuille, Admin

class Sana3tiAPITests(APITestCase):
    def setUp(self):
        # Admin User
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpassword')

        # Client User
        self.client_user = User.objects.create_user(username='clientuser', email='client@example.com', password='clientpassword', role='client')
        self.client_obj = Client.objects.create(user=self.client_user)

        # Ouvrier User
        self.ouvrier_user = User.objects.create_user(username='ouvrieruser', email='ouvrier@example.com', password='ouvrierpassword', role='ouvrier')
        self.portefeuille = Portefeuille.objects.create()
        self.ouvrier = Ouvrier.objects.create(user=self.ouvrier_user, portefeuille=self.portefeuille, rib='12345')

    def test_create_user_unauthenticated(self):
        """
        Ensure anyone can create a new user (register).
        """
        url = reverse('user-list')
        data = {'username': 'newuser', 'email': 'new@example.com', 'password': 'newpassword', 'role': 'client'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 4) # 3 from setUp + 1 new
        self.assertEqual(User.objects.get(username='newuser').email, 'new@example.com')

    def test_create_demande_authenticated(self):
        """
        Ensure an authenticated client can create a demande.
        """
        self.client.force_authenticate(user=self.client_user)
        # The action is on the ClientViewSet, which is detail=True, so we need the client's pk
        url = reverse('client-create-demande', kwargs={'pk': self.client_obj.pk})
        data = {
            'categorie': 'Plomberie',
            'description': 'Fuite d\'eau',
            'adresse': '123 rue de Paris',
            'prix': 50.0,
            'modePaiement': 'cash',
            'dateHeure': '2025-10-02T15:00:00Z'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Demande.objects.count(), 1)
        self.assertEqual(Demande.objects.get().categorie, 'Plomberie')

    def test_ouvrier_repond_demande(self):
        """
        Ensure an authenticated ouvrier can accept a demande, creating a commande.
        """
        demande = Demande.objects.create(client=self.client_obj, categorie='Plomberie', description='Fuite d\'eau', adresse='123 rue de Paris', prix=50.0, modePaiement='cash', dateHeure='2025-10-02T15:00:00Z')
        self.client.force_authenticate(user=self.ouvrier_user)
        url = reverse('ouvrier-repondre-demande', kwargs={'pk': self.ouvrier.pk})
        data = {'demande_id': demande.pk, 'reponse': 'acceptee'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Commande.objects.count(), 1)
        self.assertEqual(Commande.objects.get().ouvrier, self.ouvrier)
        demande.refresh_from_db()
        self.assertEqual(demande.statut, 'acceptee')

    def test_portefeuille_update_and_commission(self):
        """
        Ensure ouvrier's portefeuille is updated correctly with 15% commission after a commande is completed.
        """
        demande = Demande.objects.create(client=self.client_obj, categorie='Plomberie', description='Fuite d\'eau', adresse='123 rue de Paris', prix=100.0, modePaiement='enLigne', dateHeure='2025-10-02T15:00:00Z')
        commande = Commande.objects.create(demande=demande, ouvrier=self.ouvrier)

        self.client.force_authenticate(user=self.ouvrier_user)
        url = reverse('commande-update-etat', kwargs={'pk': commande.pk})
        data = {'etat': 'terminee'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.portefeuille.refresh_from_db()
        self.assertEqual(self.portefeuille.soldeDisponible, 85.0) # 100 - 15%
        self.assertEqual(self.portefeuille.totalGagne, 85.0)

        self.ouvrier.refresh_from_db()
        self.assertEqual(self.ouvrier.nbMissions, 1)
        self.assertEqual(self.ouvrier.tauxSucces, 100.0)

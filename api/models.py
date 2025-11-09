from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('client', 'Client'),
        ('ouvrier', 'Ouvrier'),
        ('admin', 'Admin'),
    )
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    tel = models.CharField(max_length=20)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    USERNAME_FIELD = 'email' # Use email as the unique identifier for authentication
    REQUIRED_FIELDS = ['nom', 'prenom', 'tel', 'role'] # Removed 'username' from REQUIRED_FIELDS

    def __str__(self):
        return self.email # Represent user by email

class Photo(models.Model):
    image = models.ImageField(upload_to='photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo {self.id}"

class Portefeuille(models.Model):
    soldeDisponible = models.FloatField(default=0.0)
    totalGagne = models.FloatField(default=0.0)

    def __str__(self):
        return f"Portefeuille de {self.ouvrier.user.username}"

class Client(models.Model):
    THEME_CHOICES = (
        ('dark', 'Dark'),
        ('light', 'Light'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    position = models.CharField(max_length=255, blank=True, null=True)
    notification = models.BooleanField(default=True)
    fcm_token = models.CharField(max_length=512, blank=True, null=True)  # store device FCM token

    def __str__(self):
        return self.user.username

class Ouvrier(models.Model):
    THEME_CHOICES = (
        ('dark', 'Dark'),
        ('light', 'Light'),
    )
    CATEGORIE_CHOICES = (
        ('plombier', 'Plombier'),
        ('electricite', 'Electricité'),
        ('menage', 'Ménage'),
        ('jardinage', 'Jardinage'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ouvrier_profile')
    rib = models.CharField(max_length=50)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    notification = models.BooleanField(default=True)
    fcm_token = models.CharField(max_length=512, blank=True, null=True)  # store device FCM token
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES, default='plombier')
    galerie = models.ManyToManyField(Photo, blank=True)
    description = models.TextField(blank=True, null=True)
    enLigne = models.BooleanField(default=False)
    nbMissions = models.IntegerField(default=0)
    tauxSucces = models.FloatField(default=0.0)
    portefeuille = models.OneToOneField(Portefeuille, on_delete=models.CASCADE, related_name='ouvrier')

    def __str__(self):
        return self.user.username

class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')

    def __str__(self):
        return self.user.username

class Demande(models.Model):
    MODE_PAIEMENT_CHOICES = (
        ('cash', 'Cash'),
        ('enLigne', 'En Ligne'),
    )
    STATUT_CHOICES = (
        ('enAttente', 'En Attente'),
        ('confirmee', 'Confirmée'),
        ('enRoute', 'En Route'),
        ('enCours', 'En Cours'),
        ('terminee', 'Terminée'),
        ('failed', 'Failed'),
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='demandes')
    categorie = models.CharField(max_length=255)
    description = models.TextField()
    photos = models.ManyToManyField(Photo, blank=True)
    adresse = models.CharField(max_length=255)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    dateHeure = models.DateTimeField()
    prix = models.FloatField()
    modePaiement = models.CharField(max_length=10, choices=MODE_PAIEMENT_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='enAttente')

    def __str__(self):
        return f"Demande de {self.client.user.username} - {self.categorie}"

class Commande(models.Model):
    ETAT_CHOICES = (
        ('enAttente', 'En Attente'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
        ('enNegociation', 'En Négociation'),
        ('confirmee', 'Confirmée'),
    )
    demande = models.OneToOneField(Demande, on_delete=models.CASCADE, related_name='commande')
    ouvrier = models.ForeignKey(Ouvrier, on_delete=models.CASCADE, related_name='commandes')
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default='enAttente')
    prix = models.FloatField(default=0.0)
    prix_negocie = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Commande {self.id} - {self.demande.categorie}"

class Avis(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='avis_donnes')
    ouvrier = models.ForeignKey(Ouvrier, on_delete=models.CASCADE, related_name='avis_recus')
    note = models.IntegerField()
    commentaire = models.TextField()

    def __str__(self):
        return f"Avis de {self.client.user.username} pour {self.ouvrier.user.username}"

class Signalement(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='signalements')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='signalements')
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Signalement pour la commande {self.commande.id}"

class Post(models.Model):
    ouvrier = models.ForeignKey(Ouvrier, on_delete=models.CASCADE, related_name='posts')
    text = models.TextField(blank=True, null=True)
    photos = models.ManyToManyField(Photo, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post by {self.ouvrier.user.username} at {self.created_at}"

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"Like by {self.user.username} on post {self.post.id}"

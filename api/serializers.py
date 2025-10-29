from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import (
    User, Client, Ouvrier, Admin, Demande, Commande,
    Avis, Portefeuille, Signalement, Photo
)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        # The default TokenObtainPairSerializer expects a 'username' field.
        # We are overriding it to use 'email' as the username field.
        # So, we need to ensure 'email' is passed in attrs and then map it to 'username'.
        attrs['username'] = attrs.get(self.username_field)
        return super().validate(attrs)

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'nom', 'prenom', 'email', 'photo', 'tel', 'role', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        print(f"UserSerializer validated_data: {validated_data}") # Debug print
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password is not None:
            user.set_password(password)
            user.save()
        print(f"User '{user.username}' created with hashed password: {user.password}") # Debug print
        return user

class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Client
        fields = '__all__'

class ClientRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Client
        fields = '__all__'

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer().create(user_data)
        client = Client.objects.create(user=user, **validated_data)
        return client

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user')
        user = instance.user

        instance.theme = validated_data.get('theme', instance.theme)
        instance.position = validated_data.get('position', instance.position)
        instance.notification = validated_data.get('notification', instance.notification)
        instance.save()

        user.username = user_data.get('username', user.username)
        user.nom = user_data.get('nom', user.nom)
        user.prenom = user_data.get('prenom', user.prenom)
        user.email = user_data.get('email', user.email)
        user.photo = user_data.get('photo', user.photo)
        user.tel = user_data.get('tel', user.tel)
        user.role = user_data.get('role', user.role)
        user.save()

        return instance

class PortefeuilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portefeuille
        fields = '__all__'

class OuvrierRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    portefeuille = PortefeuilleSerializer(required=False) # Portefeuille is created automatically

    class Meta:
        model = Ouvrier
        fields = '__all__'

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        portefeuille_data = validated_data.pop('portefeuille', {})

        user_data['role'] = 'ouvrier'
        user = UserSerializer().create(user_data)

        portefeuille = Portefeuille.objects.create(**portefeuille_data)

        ouvrier = Ouvrier.objects.create(user=user, portefeuille=portefeuille, **validated_data)
        return ouvrier

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user')
        portefeuille_data = validated_data.pop('portefeuille', {})
        user = instance.user
        portefeuille = instance.portefeuille

        instance.rib = validated_data.get('rib', instance.rib)
        instance.latitude = validated_data.get('latitude', instance.latitude)
        instance.longitude = validated_data.get('longitude', instance.longitude)
        instance.notification = validated_data.get('notification', instance.notification)
        instance.theme = validated_data.get('theme', instance.theme)
        instance.categorie = validated_data.get('categorie', instance.categorie) # Add this line
        instance.description = validated_data.get('description', instance.description)
        instance.enLigne = validated_data.get('enLigne', instance.enLigne)
        instance.nbMissions = validated_data.get('nbMissions', instance.nbMissions)
        instance.tauxSucces = validated_data.get('tauxSucces', instance.tauxSucces)
        instance.save()

        user.username = user_data.get('username', user.username)
        user.nom = user_data.get('nom', user.nom)
        user.prenom = user_data.get('prenom', user.prenom)
        user.email = user_data.get('email', user.email)
        user.photo = user_data.get('photo', user.photo)
        user.tel = user_data.get('tel', user.tel)
        user.role = user_data.get('role', user.role)
        user.save()

        portefeuille.soldeDisponible = portefeuille_data.get('soldeDisponible', portefeuille.soldeDisponible)
        portefeuille.totalGagne = portefeuille_data.get('totalGagne', portefeuille.totalGagne)
        portefeuille.save()

        return instance

class OuvrierSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    galerie = PhotoSerializer(many=True, read_only=True)
    portefeuille = PortefeuilleSerializer()
    class Meta:
        model = Ouvrier
        fields = '__all__'

class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    class Meta:
        model = Admin
        fields = '__all__'

class DemandeSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    # ouvrier_assigne = OuvrierSerializer(read_only=True) # This field is not directly on Demande model
    commande_count = serializers.SerializerMethodField()
    has_current_ouvrier_commande = serializers.SerializerMethodField()

    class Meta:
        model = Demande
        fields = ('id', 'client', 'categorie', 'description', 'photos', 'adresse', 'latitude', 'longitude', 'dateHeure', 'prix', 'modePaiement', 'statut', 'commande_count', 'has_current_ouvrier_commande')

    def get_commande_count(self, obj):
        return 1 if hasattr(obj, 'commande') else 0

    def get_has_current_ouvrier_commande(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(request.user, 'ouvrier_profile'):
            ouvrier = request.user.ouvrier_profile
            return Commande.objects.filter(demande=obj, ouvrier=ouvrier).exists()
        return False

class CommandeSerializer(serializers.ModelSerializer):
    demande = DemandeSerializer()
    ouvrier = OuvrierSerializer(read_only=True) # Ouvrier is already known from the authenticated user
    class Meta:
        model = Commande
        fields = '__all__'

class AvisSerializer(serializers.ModelSerializer):
    client = ClientSerializer()
    ouvrier = OuvrierSerializer()
    class Meta:
        model = Avis
        fields = '__all__'

class SignalementSerializer(serializers.ModelSerializer):
    commande = CommandeSerializer()
    client = ClientSerializer()
    class Meta:
        model = Signalement
        fields = '__all__'

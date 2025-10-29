from rest_framework import viewsets, status, serializers # Import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken # Import RefreshToken
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt # Import csrf_exempt
from django.utils.decorators import method_decorator # Import method_decorator
from .models import (
    User, Client, Ouvrier, Admin, Demande, Commande,
    Avis, Portefeuille, Signalement, Photo
)
from django.db import models # Import models for aggregation
from .serializers import (
    UserSerializer, ClientSerializer, OuvrierSerializer, AdminSerializer,
    DemandeSerializer, CommandeSerializer, AvisSerializer,
    PortefeuilleSerializer, SignalementSerializer, PhotoSerializer,
    ClientRegistrationSerializer, OuvrierRegistrationSerializer, CustomTokenObtainPairSerializer
)
import requests
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging
import os

# Global variables to hold the initialized Firebase apps
firebase_client_app = None
firebase_ouvrier_app = None
firebase_default_app = None # Add a global for the default app

def initialize_firebase_apps():
    global firebase_client_app, firebase_ouvrier_app, firebase_default_app

    # Path to your service account key files
    client_key_path = os.path.join(settings.BASE_DIR, 'firebase-client-key.json')
    ouvrier_key_path = os.path.join(settings.BASE_DIR, 'firebase-ouvrier-key.json')

    # Initialize default app if not already initialized
    if not firebase_default_app:
        try:
            # Attempt to get the default app; if it doesn't exist, a ValueError is raised
            firebase_default_app = firebase_admin.get_app()
            print("Firebase default app already initialized.")
        except ValueError:
            # If no default app, initialize one using the client credentials
            try:
                cred_default = credentials.Certificate(client_key_path)
                firebase_default_app = firebase_admin.initialize_app(cred_default)
                print("Firebase default app initialized successfully.")
            except Exception as e:
                print(f"Error initializing Firebase default app: {e}")

    # Initialize client app if not already initialized
    if not firebase_client_app:
        try:
            firebase_client_app = firebase_admin.get_app(name='client')
            print("Firebase client app already initialized.")
        except ValueError:
            try:
                cred_client = credentials.Certificate(client_key_path)
                firebase_client_app = firebase_admin.initialize_app(cred_client, name='client')
                print("Firebase client app initialized successfully.")
            except Exception as e:
                print(f"Error initializing Firebase client app: {e}")

    # Initialize ouvrier app if not already initialized
    if not firebase_ouvrier_app:
        try:
            firebase_ouvrier_app = firebase_admin.get_app(name='ouvrier')
            print("Firebase ouvrier app already initialized.")
        except ValueError:
            try:
                cred_ouvrier = credentials.Certificate(ouvrier_key_path)
                firebase_ouvrier_app = firebase_admin.initialize_app(cred_ouvrier, name='ouvrier')
                print("Firebase ouvrier app initialized successfully.")
            except Exception as e:
                print(f"Error initializing Firebase ouvrier app: {e}")

def send_fcm_notification(user_type, token, title, body, data=None):
    """
    Sends a FCM notification to a specific device token using the appropriate Firebase project.
    """
    initialize_firebase_apps()  # Ensure apps are initialized

    app = None
    if user_type == "client":
        app = firebase_client_app
    elif user_type == "ouvrier":
        app = firebase_ouvrier_app
    else:
        print(f"Invalid user_type: {user_type}")
        return

    if not app:
        print(f"Firebase app for user_type '{user_type}' is not initialized.")
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
        data=data if data else {},
    )

    try:
        response = messaging.send(message, app=app) # Use the specific app
        print(f"Successfully sent message: {response}")
    except Exception as e:
        print(f"Error sending FCM message: {e}")


from fcm_django.models import FCMDevice # Import FCMDevice
from firebase_admin.messaging import Message, Notification

def send_notification(user_id, payload):
    initialize_firebase_apps() # Ensure Firebase apps are initialized before sending notifications
    print(f"send_notification: preparing to send to user_id={user_id} payload={payload}")
    try:
        user = User.objects.get(id=user_id)
        devices = FCMDevice.objects.filter(user=user, active=True)

        if devices.exists():
            notification_type = payload.get('type')
            title = "Nouvelle Notification"
            body = "Vous avez reçu une nouvelle notification."

            # Customize title and body based on notification type
            if notification_type == 'new_demand':
                title = "Nouvelle demande de service"
                categorie = payload.get('demand', {}).get('categorie', 'N/A')
                body = f"Une nouvelle demande dans la catégorie '{categorie}' est disponible."
            elif notification_type == 'negotiation_proposal':
                title = "Proposition de négociation"
                body = "Un ouvrier a proposé un nouveau prix pour votre demande."
            elif notification_type == 'demand_accepted':
                title = "Demande acceptée"
                body = "Un ouvrier a accepté votre demande de service."
            elif notification_type == 'demand_refused':
                title = "Demande refusée"
                body = "Un ouvrier a refusé votre demande de service."
            elif notification_type == 'command_confirmed':
                title = "Demande confirmée"
                body = "Votre demande a été confirmée et une commande a été créée."
            elif notification_type == 'command_status_update':
                title = "Mise à jour de votre commande"
                etat = payload.get('command', {}).get('etat', 'N/A')
                body = f"Le statut de votre commande est maintenant : {etat}."
            
            # For test notifications, use provided title/body or defaults
            if notification_type == 'test_notification':
                title = payload.get('title', title)
                body = payload.get('body', body)

            data_payload = {'type': notification_type}
            if 'demand' in payload and payload.get('demand'):
                data_payload['demand_id'] = str(payload['demand'].get('id', ''))
            if 'command' in payload and payload.get('command'):
                data_payload['command_id'] = str(payload['command'].get('id', ''))

            message = Message(
                notification=Notification(title=title, body=body),
                data=data_payload,
            )
            devices.send_message(message)
            print(f"send_notification: FCM sent to {devices.count()} devices for user_id={user_id} with payload={data_payload}")

        else:
            print(f"send_notification: No active FCM devices found for user_id={user_id}")

    except User.DoesNotExist:
        print(f"send_notification: User with id={user_id} does not exist.")
    except Exception as e:
        print(f"send_notification: error sending FCM for user_id={user_id}: {e}")

def manage_fcm_device(user, token, deactivate=False):
    """Helper function to create, update, or deactivate an FCMDevice for a user."""
    if not token and not deactivate:
        return # Nothing to do if no token and not deactivating

    try:
        device = FCMDevice.objects.get(
            registration_id=token,
            user=user,
        )
        if deactivate:
            device.active = False
            device.save()
            print(f"Deactivated FCMDevice for user {user.id}, token {token}")
        else: # Update or create
            if device.active is False: # If it was deactivated, reactivate
                device.active = True
                device.save()
                print(f"Reactivated FCMDevice for user {user.id}, token {token}")
            # If already active and token matches, no change needed here.
            # The client.fcm_token update is handled separately.
    except FCMDevice.DoesNotExist:
        if not deactivate: # Only create if not deactivating
            device = FCMDevice.objects.create(
                registration_id=token,
                user=user,
                active=True,
                type='android' # Default type, can be adjusted if needed
            )
            print(f"Created new FCMDevice for user {user.id}, token {token}")
    except Exception as e:
        print(f"Error managing FCMDevice: {e}")

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return []
        elif self.action == 'retrieve':
            return [IsAuthenticated()]
        return [IsAdminUser()]

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def create_demande(self, request, pk=None):
        client = self.get_object()
        serializer = DemandeSerializer(data=request.data)
        if serializer.is_valid():
            demande = serializer.save(client=client)

            # Handle photo upload if present
            if 'photos' in request.FILES:
                photo_files = request.FILES.getlist('photos')
                for photo_file in photo_files:
                    photo_instance = Photo.objects.create(image=photo_file)
                    demande.photos.add(photo_instance)
                print(f"{len(photo_files)} photos saved for demande {demande.id}")

            # Notify ouvriers with the same category.
            # Previously this filtered by enLigne=True which could miss connected workers
            # (their enLigne flag may not always be updated). Send to all ouvriers in the category.
            ouvriers = Ouvrier.objects.filter(categorie=demande.categorie)
            print(f"create_demande: found {ouvriers.count()} ouvriers in category={demande.categorie}")
            
            # Re-serialize the demande object to include the photos in the response
            demande_data = DemandeSerializer(demande).data

            for ouvrier in ouvriers:
                if ouvrier.fcm_token:
                    print(f"create_demande: sending to ouvrier.user.id={ouvrier.user.id} with token={ouvrier.fcm_token}")
                    send_fcm_notification(
                        user_type="ouvrier",
                        token=ouvrier.fcm_token,
                        title="Nouvelle demande",
                        body=f"Une nouvelle demande dans la catégorie '{demande.categorie}' est disponible.",
                        data={"type": "new_demand", "demande_id": str(demande.id)}
                    )
            return Response(demande_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_fcm_token(self, request, pk=None):
        # Allow client to save/update their FCM device token
        client = self.get_object()
        token = request.data.get('fcm_token')
        if token is None:
            return Response({'error': 'fcm_token is required'}, status=status.HTTP_400_BAD_REQUEST)
        client.fcm_token = token
        client.save()

        # Add logic to create/update FCMDevice
        try:
            # Try to get an existing device for this user and token
            device = FCMDevice.objects.get(
                registration_id=token,
                user=client.user, # Assuming client.user links to the User model
                active=True
            )
            print(f"FCMDevice already exists for user {client.user.id}, token {token}")
        except FCMDevice.DoesNotExist:
            # If not found, create a new one
            device = FCMDevice.objects.create(
                registration_id=token,
                user=client.user,
                active=True,
                type='android' # Default type, can be adjusted if needed
            )
            print(f"Created new FCMDevice for user {client.user.id}, token {token}")
        except Exception as e:
            print(f"Error managing FCMDevice: {e}")
            # Optionally return an error response if device management fails
            # return Response({'error': 'Failed to manage FCM device'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'status': 'token updated'})

    @action(detail=True, methods=['post'])
    def clear_fcm_token(self, request, pk=None):
        """Clears the FCM token for the authenticated client on logout."""
        client = self.get_object()
        user = client.user

        # Clear the fcm_token field on the Client model
        client.fcm_token = None
        client.save()

        # Deactivate the FCMDevice associated with this user
        FCMDevice.objects.filter(user=user, active=True).update(active=False)
        print(f"Cleared FCM token and deactivated FCMDevices for client {client.id}")

        return Response({'status': 'FCM token cleared'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def confirmer_commande(self, request, pk=None):
        client = self.get_object()
        commande_id = request.data.get('commande_id')
        try:
            commande = Commande.objects.get(id=commande_id, demande__client=client)
            if commande.etat in ['acceptee', 'enNegociation']:
                commande.etat = 'confirmee'
                commande.save()
                
                # Update the related Demande status
                demande = commande.demande
                demande.statut = 'confirmee'
                demande.save()

                commande_data = CommandeSerializer(commande).data
                send_notification(commande.ouvrier.user.id, {'type': 'command_confirmed', 'command': commande_data})
                return Response({'status': 'commande confirmée'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'La commande ne peut pas être confirmée'}, status=status.HTTP_400_BAD_REQUEST)
        except Commande.DoesNotExist:
            return Response({'error': 'Commande non trouvée'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def signaler_probleme(self, request, pk=None):
        client = self.get_object()
        serializer = SignalementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(client=client)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OuvrierViewSet(viewsets.ModelViewSet):
    queryset = Ouvrier.objects.all()
    serializer_class = OuvrierSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def repondre_demande(self, request, pk=None):
        ouvrier = self.get_object()
        demande_id = request.data.get('demande_id')
        reponse = request.data.get('reponse')  # 'acceptee', 'refusee', 'enNegociation'
        
        try:
            demande = Demande.objects.get(id=demande_id)
        except Demande.DoesNotExist:
            return Response({'error': 'Demande not found'}, status=status.HTTP_404_NOT_FOUND)

        # Create a Commande with the response as its state
        commande, created = Commande.objects.get_or_create(
            demande=demande,
            ouvrier=ouvrier,
            defaults={'etat': reponse}
        )
        
        # If the commande already existed, update its state
        if not created:
            commande.etat = reponse
            commande.save()

        notification_type = ''
        if reponse == 'enNegociation':
            prix_negocie = request.data.get('prix_negocie')
            commande.prix_negocie = prix_negocie
            notification_type = 'negotiation_proposal'

        elif reponse == 'acceptee':
            commande.prix = demande.prix
            notification_type = 'demand_accepted'

        elif reponse == 'refusee':
            notification_type = 'demand_refused'

        commande.save()
        
        # Send notification to the client
        demande_data = DemandeSerializer(demande).data
        send_notification(demande.client.user.id, {'type': notification_type, 'demand': demande_data})

        return Response({'status': 'réponse envoyée'})

    @action(detail=True, methods=['post'])
    def update_fcm_token(self, request, pk=None):
        ouvrier = self.get_object()
        token = request.data.get('fcm_token')
        if token is None:
            return Response({'error': 'fcm_token is required'}, status=status.HTTP_400_BAD_REQUEST)
        ouvrier.fcm_token = token
        ouvrier.save()

        # Add logic to create/update FCMDevice
        try:
            # Try to get an existing device for this user and token
            device = FCMDevice.objects.get(
                registration_id=token,
                user=ouvrier.user, # Assuming ouvrier.user links to the User model
                active=True
            )
            print(f"FCMDevice already exists for user {ouvrier.user.id}, token {token}")
        except FCMDevice.DoesNotExist:
            # If not found, create a new one
            device = FCMDevice.objects.create(
                registration_id=token,
                user=ouvrier.user,
                active=True,
                type='android' # Default type, can be adjusted if needed
            )
            print(f"Created new FCMDevice for user {ouvrier.user.id}, token {token}")
        except Exception as e:
            print(f"Error managing FCMDevice: {e}")
            # Optionally return an error response if device management fails
            # return Response({'error': 'Failed to manage FCM device'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'status': 'token updated'})

        # Add logic to create/update FCMDevice
        try:
            # Try to get an existing device for this user and token
            device = FCMDevice.objects.get(
                registration_id=token,
                user=ouvrier.user, # Assuming ouvrier.user links to the User model
                active=True
            )
            print(f"FCMDevice already exists for user {ouvrier.user.id}, token {token}")
        except FCMDevice.DoesNotExist:
            # If not found, create a new one
            device = FCMDevice.objects.create(
                registration_id=token,
                user=ouvrier.user,
                active=True,
                type='android' # Default type, can be adjusted if needed
            )
            print(f"Created new FCMDevice for user {ouvrier.user.id}, token {token}")
        except Exception as e:
            print(f"Error managing FCMDevice: {e}")
            # Optionally return an error response if device management fails
            # return Response({'error': 'Failed to manage FCM device'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'status': 'token updated'})

    @action(detail=True, methods=['post'])
    def clear_fcm_token(self, request, pk=None):
        """Clears the FCM token for the authenticated ouvrier on logout."""
        ouvrier = self.get_object()
        user = ouvrier.user

        # Clear the fcm_token field on the Ouvrier model
        ouvrier.fcm_token = None
        ouvrier.save()

        # Deactivate the FCMDevice associated with this user
        FCMDevice.objects.filter(user=user, active=True).update(active=False)
        print(f"Cleared FCM token and deactivated FCMDevices for ouvrier {ouvrier.id}")

        return Response({'status': 'FCM token cleared'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        ouvrier = self.get_object()
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        ouvrier.latitude = latitude
        ouvrier.longitude = longitude
        ouvrier.save()
        return Response({'status': 'position mise à jour'})

    @action(detail=True, methods=['get'])
    def my_missions(self, request, pk=None):
        """
        Returns all commands for the authenticated ouvrier,
        including associated demands and client details.
        """
        if not hasattr(request.user, 'ouvrier_profile'):
            return Response({'error': 'User is not an ouvrier'}, status=status.HTTP_403_FORBIDDEN)

        ouvrier = request.user.ouvrier_profile
        
        # Security check: Ensure the requested ouvrier ID matches the authenticated ouvrier's ID
        if str(ouvrier.id) != str(pk):
            return Response({'error': 'You are not authorized to view these missions'}, status=status.HTTP_403_FORBIDDEN)

        commands = Commande.objects.filter(ouvrier=ouvrier).order_by('-demande__dateHeure')
        try:
            serializer = CommandeSerializer(commands, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TypeError as e:
            print(f"TypeError during serialization in my_missions: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': f'Serialization error: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print(f"Unexpected error during serialization in my_missions: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def update_demande_status(self, request, pk=None):
        """
        Updates the status of a Demande associated with a Commande.
        Requires 'demande_id' and 'new_status' in the request data.
        """
        ouvrier = self.get_object()
        demande_id = request.data.get('demande_id')
        new_status = request.data.get('new_status')

        if not demande_id or not new_status:
            return Response({'error': 'demande_id and new_status are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Ensure the command exists and belongs to this ouvrier
            commande = Commande.objects.get(demande__id=demande_id, ouvrier=ouvrier)
            demande = commande.demande

            # Validate new_status against allowed choices
            if new_status not in [choice[0] for choice in Demande.STATUT_CHOICES]:
                return Response({'error': f'Invalid status: {new_status}'}, status=status.HTTP_400_BAD_REQUEST)

            demande.statut = new_status
            demande.save()

            # Send notification to the client about the status update
            demande_data = DemandeSerializer(demande).data
            send_notification(demande.client.user.id, {'type': 'command_status_update', 'command': CommandeSerializer(commande).data})

            return Response({'status': f'Demande {demande_id} status updated to {new_status}'}, status=status.HTTP_200_OK)
        except Commande.DoesNotExist:
            return Response({'error': 'Commande or Demande not found for this ouvrier'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def financial_summary(self, request, pk=None):
        """
        Returns financial statistics and recent confirmed demands for an ouvrier.
        """
        ouvrier = self.get_object()

        # 1. Solde disponible
        solde_disponible = ouvrier.portefeuille.soldeDisponible

        # 2. Sum of prices for Demandes with status 'terminee' (total earned from completed missions)
        total_earned_completed_demands = Demande.objects.filter(
            commande__ouvrier=ouvrier,
            statut='terminee'
        ).aggregate(total=models.Sum('prix'))['total'] or 0.0

        # 3. Sum of prices for Demandes with status 'confirmee', 'enRoute', 'enCours'
        total_active_demands = Demande.objects.filter(
            commande__ouvrier=ouvrier,
            statut__in=['confirmee', 'enRoute', 'enCours']
        ).aggregate(total=models.Sum('prix'))['total'] or 0.0

        # 4. Sum of prices for last month
        one_month_ago = datetime.datetime.now() - timedelta(days=30)
        total_last_month = Demande.objects.filter(
            commande__ouvrier=ouvrier,
            statut='terminee',
            dateHeure__gte=one_month_ago
        ).aggregate(total=models.Sum('prix'))['total'] or 0.0

        # 5. Average daily balance (simplified: total earned / number of days ouvrier has been active)
        # This assumes 'date_joined' on User model or a similar field on Ouvrier.
        # For simplicity, let's use a fixed period or total earned / total days in service.
        # A more accurate average would require tracking daily balances.
        # For now, let's calculate average daily earnings from completed missions.
        first_mission_date = Demande.objects.filter(
            commande__ouvrier=ouvrier,
            statut='terminee'
        ).aggregate(min_date=models.Min('dateHeure'))['min_date']

        average_daily_earnings = 0.0
        if first_mission_date:
            days_active = (datetime.datetime.now().date() - first_mission_date.date()).days + 1
            if days_active > 0:
                average_daily_earnings = total_earned_completed_demands / days_active

        # 6. All commands with etat 'confirmee'
        all_confirmed_commands = Commande.objects.filter(
            ouvrier=ouvrier,
            etat='confirmee'
        ).order_by('-demande__dateHeure')

        all_confirmed_commands_serializer = CommandeSerializer(all_confirmed_commands, many=True)

        return Response({
            'solde_disponible': solde_disponible,
            'total_earned_completed_demands': total_earned_completed_demands,
            'total_active_demands': total_active_demands,
            'total_last_month': total_last_month,
            'average_daily_earnings': average_daily_earnings,
            'all_confirmed_commands': all_confirmed_commands_serializer.data,
        }, status=status.HTTP_200_OK)

class AdminViewSet(viewsets.ModelViewSet):
    queryset = Admin.objects.all()
    serializer_class = AdminSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def gerer_utilisateurs(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def gerer_transactions(self, request):
        portefeuilles = Portefeuille.objects.all()
        serializer = PortefeuilleSerializer(portefeuilles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def traiter_signalements(self, request):
        signalements = Signalement.objects.all()
        serializer = SignalementSerializer(signalements, many=True)
        return Response(serializer.data)

import datetime
from datetime import timedelta # Import timedelta

class DemandeViewSet(viewsets.ModelViewSet):
    queryset = Demande.objects.all()
    serializer_class = DemandeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def update_expired_demandes(self, request):
        now = datetime.datetime.now()
        updated_demandes = []
        
        # Filter for 'enAttente' demands where dateHeure is in the past
        expired_demandes = Demande.objects.filter(
            statut='enAttente',
            dateHeure__lt=now
        )

        for demande in expired_demandes:
            demande.statut = 'failed'
            demande.save()
            updated_demandes.append(DemandeSerializer(demande).data)
            print(f"Demande {demande.id} status updated to 'failed' due to expiration.")

        if updated_demandes:
            return Response({
                'status': 'Expired demandes updated to failed',
                'updated_count': len(updated_demandes),
                'updated_demandes': updated_demandes
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'No expired demandes found to update',
                'updated_count': 0
            }, status=status.HTTP_200_OK)

class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role'):
            if user.role == 'admin':
                return Commande.objects.all()
            
            if user.role == 'client':
                return Commande.objects.filter(demande__client__user=user).exclude(etat='refusee')
            
            if user.role == 'ouvrier':
                return Commande.objects.filter(ouvrier__user=user)
        
        # Fallback for superuser or other cases
        if user.is_staff:
            return Commande.objects.all()
            
        return Commande.objects.none()

    @action(detail=True, methods=['post'])
    def update_etat(self, request, pk=None):
        commande = self.get_object()
        etat = request.data.get('etat')
        commande.etat = etat
        commande.save()
        commande_data = CommandeSerializer(commande).data
        send_notification(commande.demande.client.user.id, {'type': 'command_status_update', 'command': commande_data})
        if etat == 'terminee':
            # Logique de paiement et de mise à jour du portefeuille
            montant = commande.demande.prix
            commission = montant * 0.15
            gain = montant - commission
            portefeuille = commande.ouvrier.portefeuille
            portefeuille.soldeDisponible += gain
            portefeuille.totalGagne += gain
            portefeuille.save()

            # Mise à jour des statistiques de l'ouvrier
            ouvrier = commande.ouvrier
            ouvrier.nbMissions += 1
            commandes_terminees = Commande.objects.filter(ouvrier=ouvrier, etat='terminee').count()
            ouvrier.tauxSucces = (commandes_terminees / ouvrier.nbMissions) * 100
            ouvrier.save()

        return Response({'status': 'état mis à jour'})

class AvisViewSet(viewsets.ModelViewSet):
    queryset = Avis.objects.all()
    serializer_class = AvisSerializer
    permission_classes = [IsAuthenticated]

class PortefeuilleViewSet(viewsets.ModelViewSet):
    queryset = Portefeuille.objects.all()
    serializer_class = PortefeuilleSerializer
    permission_classes = [IsAuthenticated]

class SignalementViewSet(viewsets.ModelViewSet):
    queryset = Signalement.objects.all()
    serializer_class = SignalementSerializer
    permission_classes = [IsAuthenticated]

class PhotoViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    permission_classes = [IsAuthenticated]


class TestNotificationView(APIView):
    """Simple test endpoint to send a notification to a user_id (for manual testing).
    POST payload: { "user_id": <id>, "title": "...", "body": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        title = request.data.get('title', 'Test Notification')
        body = request.data.get('body', '')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        payload = {'title': title, 'body': body, 'type': 'test_notification'}
        try:
            send_notification(user_id, payload)
            return Response({'status': 'sent'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication # Import necessary authentication classes

# ... (rest of the file)

@method_decorator(csrf_exempt, name='dispatch') # Apply csrf_exempt to all methods in the ViewSet
class ClientRegistrationViewSet(viewsets.ViewSet):
    serializer_class = ClientRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = [] # Explicitly disable authentication for registration

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            client = serializer.save()
            # Manually generate token for the newly registered user
            # Manually generate token for the newly registered user
            refresh = RefreshToken.for_user(client.user)
            return Response({
                'user': serializer.data,
                'token': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class ClientLoginView(APIView):
    permission_classes = [] # Allow any user to access this view

    def post(self, request, *args, **kwargs):
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e: # Catch specific validation error
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e: # Catch other unexpected errors
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        email = request.data.get('email')
        fcm_token = request.data.get('fcm_token') # Get FCM token from request

        try:
            user = User.objects.get(email=email)
            client = Client.objects.get(user=user)

            if fcm_token: # If token is provided
                client.fcm_token = fcm_token # Update client's fcm_token field
                client.save()
                manage_fcm_device(user, fcm_token) # Call helper function

            client_serializer = ClientSerializer(client)
            return Response({
                'client': client_serializer.data, # Match frontend expectation
                'token': str(validated_data['access']),
                'refresh': str(validated_data['refresh']),
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Client.DoesNotExist:
            return Response({'detail': 'Client profile not found.'}, status=status.HTTP_404_NOT_FOUND)

@method_decorator(csrf_exempt, name='dispatch')
class OuvrierRegistrationViewSet(viewsets.ViewSet):
    serializer_class = OuvrierRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            ouvrier = serializer.save()
            refresh = RefreshToken.for_user(ouvrier.user)
            return Response({
                'user': serializer.data,
                'token': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class OuvrierLoginView(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        email = request.data.get('email')
        fcm_token = request.data.get('fcm_token') # Get FCM token from request

        try:
            user = User.objects.get(email=email)
            ouvrier = Ouvrier.objects.get(user=user)

            if fcm_token: # If token is provided
                ouvrier.fcm_token = fcm_token # Update ouvrier's fcm_token field
                ouvrier.save()
                manage_fcm_device(user, fcm_token) # Call helper function

            ouvrier_serializer = OuvrierSerializer(ouvrier)
            return Response({
                'ouvrier': ouvrier_serializer.data,
                'token': str(validated_data['access']),
                'refresh': str(validated_data['refresh']),
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Ouvrier.DoesNotExist:
            return Response({'detail': 'Ouvrier profile not found.'}, status=status.HTTP_404_NOT_FOUND)

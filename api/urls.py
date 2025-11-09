from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, ClientViewSet, OuvrierViewSet, AdminViewSet,
    DemandeViewSet, CommandeViewSet, AvisViewSet,
    PortefeuilleViewSet, SignalementViewSet, PhotoViewSet,
    ClientRegistrationViewSet, ClientLoginView,
    OuvrierRegistrationViewSet, OuvrierLoginView,
    PostViewSet, LikeViewSet
)
from .serializers import CustomTokenObtainPairSerializer # Import custom serializer
from .views import TestNotificationView
from rest_framework_simplejwt.views import TokenObtainPairView # Import TokenObtainPairView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'register-client', ClientRegistrationViewSet, basename='register-client')
router.register(r'clients', ClientViewSet)
router.register(r'register-ouvrier', OuvrierRegistrationViewSet, basename='register-ouvrier')
router.register(r'ouvriers', OuvrierViewSet)
router.register(r'admins', AdminViewSet)
router.register(r'demandes', DemandeViewSet)
router.register(r'commandes', CommandeViewSet)
router.register(r'avis', AvisViewSet)
router.register(r'portefeuilles', PortefeuilleViewSet)
router.register(r'signalements', SignalementViewSet)
router.register(r'photos', PhotoViewSet)
router.register(r'posts', PostViewSet, basename='post')
router.register(r'likes', LikeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(serializer_class=CustomTokenObtainPairSerializer), name='token_obtain_pair'), # Use custom serializer
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('client-login/', ClientLoginView.as_view(), name='client_login'),
    path('ouvrier-login/', OuvrierLoginView.as_view(), name='ouvrier_login'),
    path('test_send_notification/', TestNotificationView.as_view(), name='test_send_notification'),
    path('demandes/update_expired_demandes/', DemandeViewSet.as_view({'post': 'update_expired_demandes'}), name='update_expired_demandes'),
    path('ouvriers/<int:pk>/my_missions/', OuvrierViewSet.as_view({'get': 'my_missions'}), name='ouvrier-my-missions'),
    path('ouvriers/<int:pk>/update_demande_status/', OuvrierViewSet.as_view({'post': 'update_demande_status'}), name='ouvrier-update-demande-status'),
]

from django.contrib import admin

# Register your models here.

from .models import User, Client, Ouvrier, Admin, Demande, Commande, Avis, Portefeuille, Signalement, Photo

admin.site.register(User)
admin.site.register(Client)
admin.site.register(Ouvrier)
admin.site.register(Admin)
admin.site.register(Demande)
admin.site.register(Commande)
admin.site.register(Avis)
admin.site.register(Portefeuille)
admin.site.register(Signalement)
admin.site.register(Photo)
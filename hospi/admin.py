from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Patient)
admin.site.register(Triage)
admin.site.register(Consultation)
admin.site.register(RendezVous)
admin.site.register(Hospitalisation)
admin.site.register(ExamenLab)
admin.site.register(Imagerie)
admin.site.register(Medicament)
admin.site.register(Prescription)
admin.site.register(Facture)
admin.site.register(Batiment)
admin.site.register(Niveau)
admin.site.register(Chambre)
admin.site.register(Lit)
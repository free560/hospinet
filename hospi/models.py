from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.conf import settings
import uuid

class Hopital(models.Model):
    nom = models.CharField(max_length=255, unique=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrateur'),
        ('MEDECIN', 'Médecin'),
        ('INFIRMIER', 'Infirmier'),
        ('LABO', 'Laborantin'),
        ('CAISSIER', 'Caissier'),
        ('ACCUEIL', 'Accueil'),
        ('PHARMACIEN', 'Pharmacien'),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)

    hopital = models.ForeignKey(
        Hopital,
        on_delete=models.CASCADE,
        related_name="utilisateurs",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.nom} {self.prenom} ({self.role})"

#Enregistrement de contruictiont d'un hopital
class Batiment(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE, related_name='batiments')
    nom = models.CharField(max_length=100)
    type_batiment = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.nom} - {self.hopital.nom}"


class Niveau(models.Model):
    numero = models.IntegerField()
    batiment = models.ForeignKey(Batiment, on_delete=models.CASCADE, related_name='niveaux')

    def __str__(self):
        return f"Niveau {self.numero} - {self.batiment.nom}"

class Chambre(models.Model):
    TYPE_CHOICES = [
        ('Simple', 'Simple'),
        ('Double', 'Double'),
        ('ICU', 'ICU'),
        ('Maternité', 'Maternité'),
        ('Bureau', 'Bureau'),
    ]

    CATEGORIE_CHOICES = [
        ('Prive', 'Privé'),
        ('Semi-prive', 'Semi-privé'),
        ('Public', 'Public'),
    ]

    STATUT_CHOICES = [
        ('libre', 'Libre'),
        ('occupe', 'Occupée'),
        ('maintenance', 'Maintenance'),
    ]

    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='chambres')
    numero = models.CharField(max_length=50)
    capacite = models.PositiveIntegerField(default=1)
    type_chambre = models.CharField(max_length=50, choices=TYPE_CHOICES)
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='libre')

    def __str__(self):
        return f"Chambre {self.numero}"

 
# Lit (optionnel, pour suivi précis des patients)
class Lit(models.Model):
    STATUT_CHOICES = [
        ('libre', 'Libre'),
        ('occupe', 'Occupé'),
        ('desinfecte', 'Désinfecté'),
    ]
    code = models.CharField(max_length=50)
    chambre = models.ForeignKey(Chambre, on_delete=models.CASCADE, related_name='lits')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='libre')   # libre, occupé, désinfecté

    def __str__(self):
        return f"Lit {self.code} - {self.chambre.numero}"


class Patient(models.Model):
    SEXE_CHOICES = (
        ('H', 'Homme'),
        ('F', 'Femme'),
    )

    # Champs de base (compatibles avec vos vues)
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE, related_name='patients')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES)
    date_naissance = models.DateField()
    adresse = models.CharField(max_length=255, blank=True)
    contact = models.CharField(max_length=20, blank=True)
    numero_patient = models.CharField(max_length=20, unique=True)
    
    # Champs pour compatibilité avec vos vues
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom} {self.prenom} - {self.numero_patient}"

    def save(self, *args, **kwargs):
        # Génération automatique du numéro patient si vide
        if not self.numero_patient:
            dernier_patient = Patient.objects.order_by('-id').first()
            if dernier_patient and dernier_patient.numero_patient:
                try:
                    dernier_num = int(dernier_patient.numero_patient.replace("PAT", ""))
                    nouveau_num = dernier_num + 1
                except ValueError:
                    nouveau_num = 1
            else:
                nouveau_num = 1
            self.numero_patient = f"PAT{nouveau_num:06d}"
        
        super().save(*args, **kwargs)


class Triage(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    personnel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,limit_choices_to={'role__in': ['INFIRMIER', 'ACCUEIL']})
    symptomes = models.TextField()
    tension = models.CharField(max_length=20, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    pouls = models.IntegerField(null=True, blank=True)
    niveau_urgence = models.CharField(
        max_length=20,
        choices=(
            ('CRITIQUE', 'Critique'),
            ('URGENT', 'Urgent'),
            ('MODERE', 'Modéré'),
            ('FAIBLE', 'Faible'),
        ),
        default='MODERE'
    )

    # Champs pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Triage {self.patient} - {self.niveau_urgence}"


class Consultation(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    triage = models.ForeignKey(Triage, on_delete=models.SET_NULL, null=True, blank=True)

    medecin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': 'MEDECIN'}
    )

    motif = models.TextField()
    diagnostic = models.TextField(blank=True)
    traitement_prescrit = models.TextField(blank=True)
    
    # Champs pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consultation {self.id} - {self.patient}"


class RendezVous(models.Model):
    STATUS = (
        ('CONFIRME', 'Confirmé'),
        ('ANNULE', 'Annulé'),
        ('EN_ATTENTE', 'En attente'),
        ('PLANIFIE', 'Planifié'),  # Ajouté pour compatibilité
        ('TERMINE', 'Terminé'),    # Ajouté pour compatibilité
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    personnel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_rdv = models.DateField()
    heure_rdv = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS, default='EN_ATTENTE')
    
    # Champ pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RDV {self.patient} - {self.date}"


class Hospitalisation(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    chambre = models.ForeignKey(Chambre, on_delete=models.CASCADE)
    lit = models.ForeignKey(Lit, on_delete=models.SET_NULL, null=True, blank=True)
    observation = models.TextField(blank=True)
    
    # Champs supplémentaires pour compatibilité
    date_entree = models.DateField(auto_now_add=True)
    date_sortie = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Champ pour le médecin référent (compatible avec vos vues améliorées)
    medecin_referent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'MEDECIN'}
    )

    def __str__(self):
        return f"Hosp {self.patient} Chambre {self.chambre}"


class ExamenLab(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    laborantin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': 'LABO'}
    )
    type_examen = models.CharField(max_length=100)
    resultat = models.TextField(blank=True)
    
    # Champs pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lab {self.type_examen} - {self.patient}"


# IMAGERIE MÉDICALE - VERSION COMPATIBLE
class Imagerie(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    type_image = models.CharField(max_length=100)
    resultat = models.TextField(blank=True)
    image_fichier = models.FileField(upload_to="imagerie/", blank=True, null=True)
    
    # Champs pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)
    date_imagerie = models.DateTimeField(auto_now_add=True)  # Alias

    def __str__(self):
        return f"Imagerie {self.type_image} - {self.patient}"



class Medicament(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.FloatField()
    
    # Champ pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom


class Prescription(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE)
    medicament = models.ForeignKey(Medicament, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField()
    
    # Champ pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantite} x {self.medicament.nom}"

class Facture(models.Model):
    hopital = models.ForeignKey(Hopital, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    montant = models.FloatField()
    type_service = models.CharField(max_length=100)
    statut = models.CharField(
        max_length=20, 
        default="IMPAYE",
        choices=(
            ('PAYE', 'Payé'),      # Compatible avec vos vues
            ('IMPAYE', 'Impayé'),  # Compatible avec vos vues
            ('PARTIEL', 'Partiellement payé'),
        )
    )
    
    # Champs pour compatibilité
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Facture {self.id} - {self.patient}"
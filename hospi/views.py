from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from .decorators import role_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model
import secrets
import string
from .models import *

User = get_user_model()


def register_hopital(request):
    if request.method == "POST":
        # Données Hôpital
        nom_hopital = request.POST.get('nom_hopital')
        adresse = request.POST.get('adresse')
        telephone = request.POST.get('telephone')

        # Données Admin
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        email = request.POST.get('email_hopital')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        #verification du mode passe
        if password != password2:
            messages.error(request, "Les mots de passe ne correspondent pas")
            return redirect("register")

        # Vérifications simples
        if not all([nom_hopital, email, password]):
            messages.error(request, "Tous les champs obligatoires doivent être remplis.")
            return redirect('register_hopital')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect('register_hopital')

        # Création Hôpital
        hopital = Hopital.objects.create(
            nom=nom_hopital,
            adresse=adresse,
            telephone=telephone
        )

        # Création Admin
        admin_user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            nom=nom,
            prenom=prenom,
            role='ADMIN',
            hopital=hopital,
            is_staff=True,
            is_superuser=False
        )

        messages.success(request, "Hôpital et administrateur créés avec succès.")
        return redirect('login')

    return render(request, 'hospi/auth/register_hopital.html')


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Validation basique
        if not email or not password:
            messages.error(request, "Veuillez remplir tous les champs")
            return redirect("login")

        user = authenticate(email=email, password=password)

        if user:
            login(request, user)
            
            # Redirection selon le rôle
            if user.role == "ADMIN":
                messages.success(request, f"Bienvenue Administrateur {user.nom} {user.prenom}")
            elif user.role == "MEDECIN":
                messages.success(request, f"Bienvenue Docteur {user.nom} {user.prenom}")
            else:
                messages.success(request, f"Bienvenue {user.nom} {user.prenom}")
                
            return redirect("dashboard")

        messages.error(request, "Email ou mot de passe incorrect")
        return redirect("login")

    return render(request, "hospi/auth/login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès")
    return redirect("login")

# DASHBOARD AMÉLIORÉ SELON LE RÔLE
@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.role == "ADMIN":
        context["users"] = User.objects.all()
        context["total_patients"] = Patient.objects.count()
        context["total_consultations"] = Consultation.objects.count()
        context["total_factures"] = Facture.objects.count()
        context["factures_payees"] = Facture.objects.filter(statut="PAYE").count()
        context["factures_impayees"] = Facture.objects.filter(statut="IMPAYE").count()
        context["hospitalisations"] = Hospitalisation.objects.count()

    elif user.role == "MEDECIN":
        context["consultations"] = Consultation.objects.filter(medecin=user)
        context["rdvs"] = RendezVous.objects.filter(personnel=user)
        context["patients_du_jour"] = Patient.objects.filter(
            consultation__medecin=user,
            consultation__created_at__date=timezone.now().date()
        ).distinct().count()

    elif user.role in ["INFIRMIER", "ACCEUIL"]:
        context["triages"] = Triage.objects.all()[:10]  # Limite à 10
        context["patients_sans_triage"] = Patient.objects.filter(triage=None).count()
        context["niveau_urgence"] = Triage.objects.values('niveau_urgence').annotate(count=Count('niveau_urgence'))

    elif user.role == "LABO":
        context["examens"] = ExamenLab.objects.filter(laborantin=user)
        context["examens_attente"] = ExamenLab.objects.filter(laborantin=user, resultat="").count()
        context["types_examens"] = ExamenLab.objects.values('type_examen').annotate(count=Count('type_examen'))

    elif user.role == "CAISSIER":
        context["factures"] = Facture.objects.all()
        context["total_montant"] = Facture.objects.aggregate(total=Sum('montant'))['total'] or 0
        context["montant_paye"] = Facture.objects.filter(statut="PAYE").aggregate(total=Sum('montant'))['total'] or 0

    return render(request, "hospi/dashboard/index.html", context)

# GESTION UTILISATEURS PAR L'ADMIN AMÉLIORÉE
@login_required
@role_required("ADMIN")
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, "hospi/user/list.html", {"users": users})


@login_required
@role_required("ADMIN")
def user_create(request):
    if request.method == "POST":
        try:
            role = request.POST.get("role")
            nom = request.POST.get("nom")
            prenom = request.POST.get("prenom")
            
            if not role or not nom or not prenom:
                messages.error(request, "Tous les champs sont obligatoires")
                return redirect("user_create")
            
            # Génération d'email unique
            email_unique = False
            attempts = 0
            
            while not email_unique and attempts < 10:
                code_unique = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
                role_code = role[0].lower()
                email = f"hospinet{code_unique}{role_code}@hospinet.com"
                
                if not User.objects.filter(email=email).exists():
                    email_unique = True
                    break
                attempts += 1
            
            if not email_unique:
                messages.error(request, "Impossible de générer un email unique")
                return redirect("user_create")
            
            # Mot de passe par défaut sécurisé
            default_password = secrets.token_urlsafe(12)
            
            # Création de l'utilisateur
            user = User.objects.create_user(
                email=email,
                password=default_password,
                role=role,
                nom=nom.upper(),
                prenom=prenom
            )
            
            messages.success(request, f"Utilisateur créé : {email} / Mot de passe initial : {default_password}")
            logger.info(f"Utilisateur créé : {email} par {request.user.email}")
            return redirect("user_list")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    return render(request, "hospi/user/create.html")


@login_required
@role_required("ADMIN")
def user_update(request, id):
    user = get_object_or_404(User, id=id)
    
    # Empêcher la modification de l'admin principal
    if user.email == "admin@hospinet.com" and request.user != user:
        messages.error(request, "Impossible de modifier l'administrateur principal")
        return redirect("user_list")
    
    if request.method == "POST":
        try:
            user.email = request.POST.get("email")
            password = request.POST.get("password")
            if password:
                user.set_password(password)
            user.role = request.POST.get("role")
            user.nom = request.POST.get("nom").upper()
            user.prenom = request.POST.get("prenom")
            user.save()
            
            messages.success(request, "Utilisateur mis à jour")
            logger.info(f"Utilisateur mis à jour : {user.email} par {request.user.email}")
            return redirect("user_list")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/user/update.html", {"user": user})


@login_required
@role_required("ADMIN")
def user_delete(request, id):
    user = get_object_or_404(User, id=id)
    
    # Empêcher la suppression de l'admin principal
    if user.email == "admin@hospinet.com":
        messages.error(request, "Impossible de supprimer l'administrateur principal")
        return redirect("user_list")
    
    # Empêcher l'utilisateur de se supprimer lui-même
    if user == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte")
        return redirect("user_list")
    
    if request.method == "POST":
        try:
            user_email = user.email
            user.delete()
            messages.success(request, "Utilisateur supprimé")
            logger.info(f"Utilisateur supprimé : {user_email} par {request.user.email}")
            return redirect("user_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/user/delete.html", {"user": user})


'''
# PATIENT – CRUD AMÉLIORÉ
@login_required
def patient_list(request):
    patients = Patient.objects.all().order_by('-created_at')
    return render(request, "hospi/patient/list.html", {"patients": patients})


@login_required
def patient_create(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Génération automatique du numéro patient si non fourni
                numero_patient = request.POST.get("numero_patient")
                if not numero_patient:
                    dernier_patient = Patient.objects.order_by('-id').first()
                    if dernier_patient and dernier_patient.numero_patient:
                        dernier_num = int(dernier_patient.numero_patient.replace("PAT", ""))
                        numero_patient = f"PAT{dernier_num + 1:06d}"
                    else:
                        numero_patient = "PAT000001"

                Patient.objects.create(
                    nom=request.POST.get("nom").upper(),
                    prenom=request.POST.get("prenom"),
                    sexe=request.POST.get("sexe"),
                    date_naissance=request.POST.get("date_naissance"),
                    adresse=request.POST.get("adresse"),
                    contact=request.POST.get("contact"),
                    numero_patient=numero_patient
                )

            messages.success(request, "Patient enregistré avec succès")
            return redirect("patient_list")

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement: {str(e)}")
            return redirect("patient_create")

    return render(request, "hospi/patient/create.html")


@login_required
def patient_detail(request, id):
    patient = get_object_or_404(Patient, id=id)
    triages = Triage.objects.filter(patient=patient).order_by('-created_at')
    consultations = Consultation.objects.filter(patient=patient).order_by('-created_at')
    examens = ExamenLab.objects.filter(patient=patient).order_by('-created_at')
    hospitalisations = Hospitalisation.objects.filter(patient=patient).order_by('-created_at')
    factures = Facture.objects.filter(patient=patient).order_by('-created_at')

    context = {
        "patient": patient,
        "triages": triages,
        "consultations": consultations,
        "examens": examens,
        "hospitalisations": hospitalisations,
        "factures": factures
    }
    return render(request, "hospi/patient/detail.html", context)


@login_required
def patient_edit(request, id):
    patient = get_object_or_404(Patient, id=id)
    
    if request.method == "POST":
        try:
            patient.nom = request.POST.get("nom").upper()
            patient.prenom = request.POST.get("prenom")
            patient.sexe = request.POST.get("sexe")
            patient.date_naissance = request.POST.get("date_naissance")
            patient.adresse = request.POST.get("adresse")
            patient.contact = request.POST.get("contact")
            
            # Vérification du numéro patient unique
            nouveau_numero = request.POST.get("numero_patient")
            if nouveau_numero != patient.numero_patient:
                if Patient.objects.filter(numero_patient=nouveau_numero).exists():
                    messages.error(request, "Ce numéro patient existe déjà")
                    return render(request, "hospi/patient/edit.html", {"patient": patient})
                patient.numero_patient = nouveau_numero
            
            patient.save()
            messages.success(request, "Patient mis à jour avec succès")
            return redirect("patient_detail", id=patient.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/patient/edit.html", {"patient": patient})


@login_required
def patient_delete(request, id):
    patient = get_object_or_404(Patient, id=id)
    
    if request.method == "POST":
        try:
            patient.delete()
            messages.success(request, "Patient supprimé avec succès")
            return redirect("patient_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/patient/delete.html", {"patient": patient})

# TRIAGE / PRÉCONSULTATION AMÉLIORÉ
@login_required
def triage_create(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Vérifier si un triage existe déjà pour ce patient
    triage_existant = Triage.objects.filter(patient=patient).first()
    if triage_existant:
        messages.warning(request, "Un triage existe déjà pour ce patient")
        return redirect("patient_detail", id=patient_id)

    if request.method == "POST":
        try:
            Triage.objects.create(
                patient=patient,
                personnel=request.user,
                symptomes=request.POST.get("symptomes"),
                tension=request.POST.get("tension"),
                temperature=request.POST.get("temperature"),
                pouls=request.POST.get("pouls"),
                niveau_urgence=request.POST.get("niveau_urgence")
            )

            messages.success(request, "Triage enregistré avec succès")
            return redirect("patient_detail", id=patient_id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement: {str(e)}")
    
    return render(request, "hospi/triage/create.html", {"patient": patient})

# CONSULTATION MÉDICALE AMÉLIORÉE
@login_required
def consultation_list(request):
    user = request.user
    
    if user.role == "MEDECIN":
        consultations = Consultation.objects.filter(medecin=user).order_by('-created_at')
    else:
        consultations = Consultation.objects.all().order_by('-created_at')

    return render(request, "hospi/consultation/list.html", {"consultations": consultations})


@login_required
def consultation_create(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == "POST":
        try:
            triage_id = request.POST.get("triage_id")
            triage = get_object_or_404(Triage, id=triage_id) if triage_id else None

            consultation = Consultation.objects.create(
                patient=patient,
                triage=triage,
                medecin=request.user,
                motif=request.POST.get("motif"),
                diagnostic=request.POST.get("diagnostic"),
                traitement_prescrit=request.POST.get("traitement_prescrit")
            )
            
            messages.success(request, "Consultation créée avec succès")
            return redirect("consultation_detail", id=consultation.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    triages = Triage.objects.filter(patient=patient)
    context = {"patient": patient, "triages": triages}
    return render(request, "hospi/consultation/create.html", context)


@login_required
def consultation_detail(request, id):
    consultation = get_object_or_404(Consultation, id=id)
    prescriptions = Prescription.objects.filter(consultation=consultation)
    
    context = {
        "consultation": consultation,
        "prescriptions": prescriptions
    }
    return render(request, "hospi/consultation/detail.html", context)


@login_required
def consultation_edit(request, id):
    consultation = get_object_or_404(Consultation, id=id)
    
    # Vérification des permissions
    if request.user != consultation.medecin and request.user.role != "ADMIN":
        messages.error(request, "Vous ne pouvez pas modifier cette consultation")
        return redirect("consultation_detail", id=id)
    
    if request.method == "POST":
        try:
            consultation.motif = request.POST.get("motif")
            consultation.diagnostic = request.POST.get("diagnostic")
            consultation.traitement_prescrit = request.POST.get("traitement_prescrit")
            consultation.save()
            
            messages.success(request, "Consultation mise à jour avec succès")
            return redirect("consultation_detail", id=consultation.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/consultation/edit.html", {"consultation": consultation})


@login_required
def consultation_delete(request, id):
    consultation = get_object_or_404(Consultation, id=id)
    
    # Vérification des permissions
    if request.user.role != "ADMIN":
        messages.error(request, "Seul l'administrateur peut supprimer une consultation")
        return redirect("consultation_detail", id=id)
    
    if request.method == "POST":
        try:
            consultation.delete()
            messages.success(request, "Consultation supprimée avec succès")
            return redirect("consultation_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/consultation/delete.html", {"consultation": consultation})

# RENDEZ-VOUS AMÉLIORÉS
@login_required
def rdv_list(request):
    user = request.user
    
    if user.role in ["MEDECIN", "INFIRMIER"]:
        rdvs = RendezVous.objects.filter(personnel=user).order_by('date', 'heure')
    else:
        rdvs = RendezVous.objects.all().order_by('date', 'heure')
    
    return render(request, "hospi/rdv/list.html", {"rdvs": rdvs})


@login_required
def rdv_create(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == "POST":
        try:
            RendezVous.objects.create(
                patient=patient,
                personnel=request.user,
                date=request.POST.get("date"),
                heure=request.POST.get("heure"),
                status=request.POST.get("status", "PLANIFIE")
            )
            messages.success(request, "Rendez-vous créé avec succès")
            return redirect("patient_detail", id=patient_id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    return render(request, "hospi/rdv/create.html", {"patient": patient})


@login_required
def rdv_edit(request, id):
    rdv = get_object_or_404(RendezVous, id=id)
    
    if request.method == "POST":
        try:
            rdv.date = request.POST.get("date")
            rdv.heure = request.POST.get("heure")
            rdv.status = request.POST.get("status")
            rdv.save()
            
            messages.success(request, "Rendez-vous mis à jour avec succès")
            return redirect("rdv_list")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/rdv/edit.html", {"rdv": rdv})


@login_required
def rdv_delete(request, id):
    rdv = get_object_or_404(RendezVous, id=id)
    
    if request.method == "POST":
        try:
            rdv.delete()
            messages.success(request, "Rendez-vous supprimé avec succès")
            return redirect("rdv_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/rdv/delete.html", {"rdv": rdv})

# EXAMENS DE LABORATOIRE AMÉLIORÉS
@login_required
@role_required("LABO", "MEDECIN", "ADMIN")
def examen_list(request):
    user = request.user
    
    if user.role == "LABO":
        examens = ExamenLab.objects.filter(laborantin=user).order_by('-created_at')
    else:
        examens = ExamenLab.objects.all().order_by('-created_at')
    
    return render(request, "hospi/labo/list.html", {"examens": examens})


@login_required
@role_required("LABO", "MEDECIN")
def examen_create(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == "POST":
        try:
            ExamenLab.objects.create(
                patient=patient,
                laborantin=request.user,
                type_examen=request.POST.get("type_examen"),
                resultat=request.POST.get("resultat")
            )
            messages.success(request, "Examen de laboratoire enregistré")
            return redirect("patient_detail", id=patient_id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement: {str(e)}")
    
    return render(request, "hospi/labo/create.html", {"patient": patient})


@login_required
@role_required("LABO", "MEDECIN", "ADMIN")
def examen_detail(request, id):
    examen = get_object_or_404(ExamenLab, id=id)
    return render(request, "hospi/labo/detail.html", {"examen": examen})


@login_required
@role_required("LABO", "ADMIN")
def examen_edit(request, id):
    examen = get_object_or_404(ExamenLab, id=id)
    
    if request.method == "POST":
        try:
            examen.type_examen = request.POST.get("type_examen")
            examen.resultat = request.POST.get("resultat")
            examen.save()
            
            messages.success(request, "Examen mis à jour avec succès")
            return redirect("examen_detail", id=examen.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/labo/edit.html", {"examen": examen})


@login_required
@role_required("LABO", "ADMIN")
def examen_delete(request, id):
    examen = get_object_or_404(ExamenLab, id=id)
    
    if request.method == "POST":
        try:
            examen.delete()
            messages.success(request, "Examen supprimé avec succès")
            return redirect("examen_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/labo/delete.html", {"examen": examen})


# IMAGERIE MÉDICALE AMÉLIORÉE
@login_required
@role_required("MEDECIN", "LABO", "ADMIN")
def imagerie_list(request):
    imageries = Imagerie.objects.all().order_by('-created_at')
    return render(request, "imagerie/list.html", {"imageries": imageries})


@login_required
@role_required("MEDECIN", "LABO")
def imagerie_create(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == "POST":
        try:
            fichier = request.FILES.get("image_fichier")
            
            if not fichier:
                messages.error(request, "Veuillez sélectionner un fichier")
                return render(request, "imagerie/create.html", {"patient": patient})
            
            # Vérification du type de fichier
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if fichier.content_type not in allowed_types:
                messages.error(request, "Type de fichier non autorisé")
                return render(request, "hospi/imagerie/create.html", {"patient": patient})
            
            Imagerie.objects.create(
                patient=patient,
                type_image=request.POST.get("type_image"),
                resultat=request.POST.get("resultat"),
                image_fichier=fichier
            )
            messages.success(request, "Imagerie enregistrée")
            return redirect("patient_detail", id=patient_id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement: {str(e)}")
    
    return render(request, "hospi/imagerie/create.html", {"patient": patient})


@login_required
@role_required("MEDECIN", "LABO", "ADMIN")
def imagerie_detail(request, id):
    image = get_object_or_404(Imagerie, id=id)
    return render(request, "hospi/imagerie/detail.html", {"image": image})


@login_required
@role_required("MEDECIN", "LABO", "ADMIN")
def imagerie_edit(request, id):
    imagerie = get_object_or_404(Imagerie, id=id)
    
    if request.method == "POST":
        try:
            imagerie.type_image = request.POST.get("type_image")
            imagerie.resultat = request.POST.get("resultat")
            
            if 'image_fichier' in request.FILES:
                fichier = request.FILES.get("image_fichier")
                allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
                if fichier.content_type in allowed_types:
                    imagerie.image_fichier = fichier
            
            imagerie.save()
            messages.success(request, "Imagerie mise à jour avec succès")
            return redirect("imagerie_detail", id=imagerie.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/imagerie/edit.html", {"imagerie": imagerie})


@login_required
@role_required("ADMIN")
def imagerie_delete(request, id):
    imagerie = get_object_or_404(Imagerie, id=id)
    
    if request.method == "POST":
        try:
            imagerie.delete()
            messages.success(request, "Imagerie supprimée avec succès")
            return redirect("imagerie_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/imagerie/delete.html", {"imagerie": imagerie})

# PHARMACIE – MÉDICAMENTS AMÉLIORÉS
@login_required
@role_required("PHARMACIEN", "MEDECIN", "ADMIN", "INFIRMIER")
def medicament_list(request):
    medicaments = Medicament.objects.all().order_by('nom')
    return render(request, "hospi/pharmacie/medicament_list.html", {"medicaments": medicaments})


@login_required
@role_required("PHARMACIEN", "ADMIN")
def medicament_create(request):
    if request.method == "POST":
        try:
            Medicament.objects.create(
                nom=request.POST.get("nom").upper(),
                quantite=int(request.POST.get("quantite", 0)),
                prix_unitaire=float(request.POST.get("prix_unitaire", 0))
            )
            messages.success(request, "Médicament ajouté")
            return redirect("medicament_list")
            
        except ValueError:
            messages.error(request, "Veuillez entrer des valeurs numériques valides")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'ajout: {str(e)}")
    
    return render(request, "hospi/pharmacie/medicament_create.html")


@login_required
@role_required("PHARMACIEN", "ADMIN")
def medicament_update(request, id):
    medicament = get_object_or_404(Medicament, id=id)
    
    if request.method == "POST":
        try:
            medicament.nom = request.POST.get("nom").upper()
            medicament.quantite = int(request.POST.get("quantite", 0))
            medicament.prix_unitaire = float(request.POST.get("prix_unitaire", 0))
            medicament.save()
            
            messages.success(request, "Médicament mis à jour")
            return redirect("medicament_list")
            
        except ValueError:
            messages.error(request, "Veuillez entrer des valeurs numériques valides")
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/pharmacie/medicament_update.html", {"medicament": medicament})


@login_required
@role_required("PHARMACIEN", "ADMIN")
def medicament_delete(request, id):
    medicament = get_object_or_404(Medicament, id=id)
    
    if request.method == "POST":
        try:
            medicament.delete()
            messages.success(request, "Médicament supprimé")
            return redirect("medicament_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/pharmacie/medicament_delete.html", {"medicament": medicament})

@login_required
@role_required("PHARMACIEN", "MEDECIN", "ADMIN")
def prescription_list(request):
    prescriptions = Prescription.objects.all().order_by('-created_at')
    return render(request, "hospi/pharmacie/prescription_list.html", {"prescriptions": prescriptions})


@login_required
@role_required("MEDECIN")
def prescription_create(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    medicaments = Medicament.objects.filter(quantite__gt=0)  # Uniquement les médicaments disponibles
    
    if request.method == "POST":
        try:
            medicament_id = request.POST.get("medicament_id")
            medicament = get_object_or_404(Medicament, id=medicament_id)
            quantite = int(request.POST.get("quantite", 1))
            
            # Vérifier la disponibilité
            if quantite > medicament.quantite:
                messages.error(request, f"Stock insuffisant. Disponible: {medicament.quantite}")
                return render(request, "pharmacie/prescription_create.html", {
                    "consultation": consultation,
                    "medicaments": medicaments
                })
            
            Prescription.objects.create(
                consultation=consultation,
                medicament=medicament,
                quantite=quantite
            )
            
            # Mettre à jour le stock
            medicament.quantite -= quantite
            medicament.save()
            
            messages.success(request, "Prescription ajoutée avec succès")
            return redirect("consultation_detail", id=consultation_id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de l'ajout: {str(e)}")
    
    return render(request, "hospi/pharmacie/prescription_create.html", {
        "consultation": consultation,
        "medicaments": medicaments
    })


@login_required
@role_required("PHARMACIEN", "MEDECIN", "ADMIN")
def prescription_edit(request, id):
    prescription = get_object_or_404(Prescription, id=id)
    medicaments = Medicament.objects.all()
    
    if request.method == "POST":
        try:
            ancien_medicament = prescription.medicament
            ancienne_quantite = prescription.quantite
            
            nouveau_medicament_id = request.POST.get("medicament_id")
            nouveau_medicament = get_object_or_404(Medicament, id=nouveau_medicament_id)
            nouvelle_quantite = int(request.POST.get("quantite", 1))
            
            # Logique de gestion de stock
            if ancien_medicament != nouveau_medicament:
                # Restituer l'ancien stock
                ancien_medicament.quantite += ancienne_quantite
                ancien_medicament.save()
                
                # Vérifier le nouveau stock
                if nouvelle_quantite > nouveau_medicament.quantite:
                    messages.error(request, "Stock insuffisant")
                    return render(request, "hospi/pharmacie/prescription_edit.html", {
                        "prescription": prescription,
                        "medicaments": medicaments
                    })
                
                # Déduire du nouveau stock
                nouveau_medicament.quantite -= nouvelle_quantite
                nouveau_medicament.save()
                
                prescription.medicament = nouveau_medicament
            else:
                # Même médicament, ajuster la quantité
                difference = nouvelle_quantite - ancienne_quantite
                if difference > ancien_medicament.quantite:
                    messages.error(request, "Stock insuffisant")
                    return render(request, "pharmacie/prescription_edit.html", {
                        "prescription": prescription,
                        "medicaments": medicaments
                    })
                
                ancien_medicament.quantite -= difference
                ancien_medicament.save()
            
            prescription.quantite = nouvelle_quantite
            prescription.save()
            
            messages.success(request, "Prescription mise à jour avec succès")
            return redirect("prescription_list")
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/pharmacie/prescription_edit.html", {
        "prescription": prescription,
        "medicaments": medicaments
    })


@login_required
@role_required("PHARMACIEN", "MEDECIN", "ADMIN")
def prescription_delete(request, id):
    prescription = get_object_or_404(Prescription, id=id)
    
    if request.method == "POST":
        try:
            # Restituer le stock
            medicament = prescription.medicament
            medicament.quantite += prescription.quantite
            medicament.save()
            
            prescription.delete()
            messages.success(request, "Prescription supprimée avec succès")
            return redirect("prescription_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/pharmacie/prescription_delete.html", {"prescription": prescription})

# FACTURATION AMÉLIORÉE
@login_required
@role_required("CAISSIER", "ADMIN")
def facture_list(request):
    factures = Facture.objects.all().order_by('-created_at')
    return render(request, "hospi/facture/list.html", {"factures": factures})


@login_required
@role_required("CAISSIER", "ADMIN")
def facture_create(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == "POST":
        try:
            Facture.objects.create(
                patient=patient,
                montant=float(request.POST.get("montant", 0)),
                type_service=request.POST.get("type_service"),
                statut=request.POST.get("statut", "IMPAYE")
            )
            messages.success(request, "Facture créée")
            return redirect("patient_detail", id=patient_id)
            
        except ValueError:
            messages.error(request, "Veuillez entrer un montant valide")
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    return render(request, "hospi/facture/create.html", {"patient": patient})


@login_required
@role_required("CAISSIER", "ADMIN")
def facture_detail(request, id):
    facture = get_object_or_404(Facture, id=id)
    return render(request, "hospi/facture/detail.html", {"facture": facture})


@login_required
@role_required("CAISSIER", "ADMIN")
def facture_edit(request, id):
    facture = get_object_or_404(Facture, id=id)
    
    if request.method == "POST":
        try:
            facture.montant = float(request.POST.get("montant", 0))
            facture.type_service = request.POST.get("type_service")
            facture.statut = request.POST.get("statut")
            facture.save()
            
            messages.success(request, "Facture mise à jour avec succès")
            return redirect("facture_detail", id=facture.id)
            
        except ValueError:
            messages.error(request, "Veuillez entrer un montant valide")
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/facture/edit.html", {"facture": facture})


@login_required
@role_required("CAISSIER", "ADMIN")
def facture_delete(request, id):
    facture = get_object_or_404(Facture, id=id)
    
    if request.method == "POST":
        try:
            facture.delete()
            messages.success(request, "Facture supprimée avec succès")
            return redirect("facture_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/facture/delete.html", {"facture": facture})

# HOSPITALISATION AMÉLIORÉE
@login_required
@role_required("MEDECIN", "INFIRMIER", "ADMIN")
def hospitalisation_list(request):
    hospitalisations = Hospitalisation.objects.all().order_by('-created_at')
    return render(request, "hospi/hospitalisation/list.html", {"hospitalisations": hospitalisations})


@login_required
@role_required("MEDECIN")
def hospitalisation_create(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Vérifier si le patient est déjà hospitalisé
    hospitalisation_existante = Hospitalisation.objects.filter(
        patient=patient,
        date_sortie__isnull=True
    ).exists()
    
    if hospitalisation_existante:
        messages.warning(request, "Ce patient est déjà hospitalisé")
        return redirect("patient_detail", id=patient_id)
    
    if request.method == "POST":
        try:
            Hospitalisation.objects.create(
                patient=patient,
                chambre=request.POST.get("chambre"),
                lit=request.POST.get("lit"),
                observation=request.POST.get("observation"),
                medecin_referent=request.user
            )
            messages.success(request, "Hospitalisation créée")
            return redirect("patient_detail", id=patient_id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    return render(request, "hospi/hospitalisation/create.html", {"patient": patient})


@login_required
@role_required("MEDECIN", "INFIRMIER", "ADMIN")
def hospitalisation_detail(request, id):
    hospitalisation = get_object_or_404(Hospitalisation, id=id)
    return render(request, "hospi/hospitalisation/detail.html", {"hospitalisation": hospitalisation})


@login_required
@role_required("MEDECIN")
def hospitalisation_edit(request, id):
    hospitalisation = get_object_or_404(Hospitalisation, id=id)
    
    if request.method == "POST":
        try:
            hospitalisation.chambre = request.POST.get("chambre")
            hospitalisation.lit = request.POST.get("lit")
            hospitalisation.observation = request.POST.get("observation")
            
            # Gestion de la date de sortie
            if request.POST.get("date_sortie"):
                hospitalisation.date_sortie = request.POST.get("date_sortie")
            
            hospitalisation.save()
            messages.success(request, "Hospitalisation mise à jour avec succès")
            return redirect("hospitalisation_detail", id=hospitalisation.id)
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    return render(request, "hospi/hospitalisation/edit.html", {"hospitalisation": hospitalisation})


@login_required
@role_required("MEDECIN", "ADMIN")
def hospitalisation_delete(request, id):
    hospitalisation = get_object_or_404(Hospitalisation, id=id)
    
    if request.method == "POST":
        try:
            hospitalisation.delete()
            messages.success(request, "Hospitalisation supprimée avec succès")
            return redirect("hospitalisation_list")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return render(request, "hospi/hospitalisation/delete.html", {"hospitalisation": hospitalisation})


'''

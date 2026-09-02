from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    # AUTHENTIFICATION
    path('', views.login_view, name='login'),
    path('register-hopital/', views.register_hopital, name='register_hopital'),
    path('logout/', views.logout_view, name='logout'),
    # DASHBOARD
    path('dashboard/', views.dashboard, name='dashboard'),
    # GESTION UTILISATEURS (ADMIN)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:id>/update/', views.user_update, name='user_update'),
    path('users/<int:id>/delete/', views.user_delete, name='user_delete'),
 
    # PATIENTS
    #path('patients/', views.patient_list, name='patient_list'),
    #path('patients/create/', views.patient_create, name='patient_create'),
    #path('patients/<int:id>/', views.patient_detail, name='patient_detail'),
    #path('patients/<int:id>/edit/', views.patient_edit, name='patient_edit'),
    #path('patients/<int:id>/delete/', views.patient_delete, name='patient_delete'),
    # TRIAGE
    #path('patients/<int:patient_id>/triage/create/', views.triage_create, name='triage_create'),
    # CONSULTATIONS
    #path('consultations/', views.consultation_list, name='consultation_list'),
    #path('patients/<int:patient_id>/consultation/create/', views.consultation_create, name='consultation_create'),
    #path('consultations/<int:id>/', views.consultation_detail, name='consultation_detail'),
    #path('consultations/<int:id>/edit/', views.consultation_edit, name='consultation_edit'),
    #path('consultations/<int:id>/delete/', views.consultation_delete, name='consultation_delete'),
    # RENDEZ-VOUS
    #path('rdv/', views.rdv_list, name='rdv_list'),
    #path('patients/<int:patient_id>/rdv/create/', views.rdv_create, name='rdv_create'),
    #path('rdv/<int:id>/edit/', views.rdv_edit, name='rdv_edit'),
    #path('rdv/<int:id>/delete/', views.rdv_delete, name='rdv_delete'),
    # EXAMENS LABORATOIRE
    #path('examens/', views.examen_list, name='examen_list'),
    #path('patients/<int:patient_id>/examen/create/', views.examen_create, name='examen_create'),
    #path('examens/<int:id>/', views.examen_detail, name='examen_detail'),
    #path('examens/<int:id>/edit/', views.examen_edit, name='examen_edit'),
    #path('examens/<int:id>/delete/', views.examen_delete, name='examen_delete'),
 
    # IMAGERIE MÉDICALE
    #path('imagerie/', views.imagerie_list, name='imagerie_list'),
    #path('patients/<int:patient_id>/imagerie/create/', views.imagerie_create, name='imagerie_create'),
    #path('imagerie/<int:id>/', views.imagerie_detail, name='imagerie_detail'),
    #path('imagerie/<int:id>/edit/', views.imagerie_edit, name='imagerie_edit'),
    #path('imagerie/<int:id>/delete/', views.imagerie_delete, name='imagerie_delete'),

    # PHARMACIE - MÉDICAMENTS
    #path('medicaments/', views.medicament_list, name='medicament_list'),
    #path('medicaments/create/', views.medicament_create, name='medicament_create'),
    #path('medicaments/<int:id>/update/', views.medicament_update, name='medicament_update'),
    #path('medicaments/<int:id>/delete/', views.medicament_delete, name='medicament_delete'),

    # PHARMACIE - PRESCRIPTIONS
    #path('prescriptions/', views.prescription_list, name='prescription_list'),
    #path('consultations/<int:consultation_id>/prescription/create/', views.prescription_create, name='prescription_create'),
    #path('prescriptions/<int:id>/edit/', views.prescription_edit, name='prescription_edit'),
    #('prescriptions/<int:id>/delete/', views.prescription_delete, name='prescription_delete'),
    
    # FACTURATION
    #path('factures/', views.facture_list, name='facture_list'),
    #path('patients/<int:patient_id>/facture/create/', views.facture_create, name='facture_create'),
    #path('factures/<int:id>/', views.facture_detail, name='facture_detail'),
    #path('factures/<int:id>/edit/', views.facture_edit, name='facture_edit'),
    #path('factures/<int:id>/delete/', views.facture_delete, name='facture_delete'),
    
    # HOSPITALISATION
    #path('hospitalisations/', views.hospitalisation_list, name='hospitalisation_list'),
    #path('patients/<int:patient_id>/hospitalisation/create/', views.hospitalisation_create, name='hospitalisation_create'),
    #path('hospitalisations/<int:id>/', views.hospitalisation_detail, name='hospitalisation_detail'),
    #path('hospitalisations/<int:id>/edit/', views.hospitalisation_edit, name='hospitalisation_edit'),
    #path('hospitalisations/<int:id>/delete/', views.hospitalisation_delete, name='hospitalisation_delete'),

    # GESTION UTILISATEURS (ADMIN)
    #path('users/', views.user_list, name='user_list'),
    #path('users/create/', views.user_create, name='user_create'),
    #path('users/<int:id>/update/', views.user_update, name='user_update'),
    #path('users/<int:id>/delete/', views.user_delete, name='user_delete'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
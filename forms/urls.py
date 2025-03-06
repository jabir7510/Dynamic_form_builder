from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dasboard  ', views.DashboardView.as_view(), name='dashboard'),
    
    # Combined form-related URLs:
    path('create_form/', views.FormAPIView.as_view(), name='create_form'),
    path('list_forms/', views.FormAPIView.as_view(), name='list_forms'),
    path('forms/<int:form_id>/', views.FormAPIView.as_view(), name='form_detail'),
    path('update_form/<int:form_id>/', views.FormAPIView.as_view(), name='update_form'),
    path('delete_form/<int:form_id>/', views.FormAPIView.as_view(), name='delete_form'),  
    
    path('forms/public/<uuid:unique_id>/', views.PublicFormView.as_view(), name='public_form'),  #for filling the form

    path('api/forms/<int:form_id>/fields/', views.FormFieldAPIView.as_view(), name='form_fields_api')  #for adding fields for the form
]

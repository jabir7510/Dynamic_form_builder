import json
from urllib import request
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.views import View
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from .models import Form, FormField, FormResponse, FormResponseField
from .forms import RegistrationForm, LoginForm
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework import status

class UserRegisterView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'register.html', {'form': form})
    
    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please log in.")
            return redirect('login')
        return render(request, 'register.html', {'form': form})

class UserLoginView(View):
    def get(self, request):
        form = LoginForm()
        return render(request, 'login.html', {'form': form})
    
    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid credentials")
        return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')

# --------- Form Management Views ---------

@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        return render(request, 'dashboard.html')


@method_decorator(login_required, name='dispatch')
class FormAPIView(APIView):
    """
    Combined API and view for Form operations.
    
    URL behavior is determined by:
      - The HTTP method (GET, POST, PUT, DELETE)
      - The URL name (using request.resolver_match.url_name) and provided parameters
    
    Expected URL names:
      • 'create_form'      : GET renders create_form.html, POST creates a new form.
      • 'list_forms'       : GET renders list_forms.html (listing all forms for the user).
      • 'form_detail'      : GET renders form_detail.html for a given form_id.
      • 'update_form'      : PUT updates the form details.
      • 'delete_form'      : POST (or DELETE) deletes the form.
      • 'public_form'      : GET renders public_form.html for a given unique_id.
    """
    
    def get(self, request, form_id=None, unique_id=None):
        url_name = request.resolver_match.url_name
        if url_name == 'create_form':
            return render(request, 'create_form.html')
        elif url_name == 'list_forms':
            forms = Form.objects.filter(user=request.user).order_by('-created_at')
            return render(request, 'list_forms.html', {'forms': forms})
        elif url_name == 'form_detail' and form_id:
            form = get_object_or_404(Form, id=form_id, user=request.user)
            return render(request, 'form_detail.html', {'form': form})
        elif url_name == 'update_form' and form_id:
            form = get_object_or_404(Form, id=form_id, user=request.user)
            fields = form.fields.all().order_by('order')
            form_data = {
                'title': form.title,
                'description': form.description,
                'fields': fields
            }
            return render(request, 'edit_form.html', {'form_data': form_data})
    
        elif url_name == 'public_form' and unique_id:
            form = get_object_or_404(Form, unique_id=unique_id)
            
            # Check if form is private and user is not authenticated
            if form.visibility == 'private' and not request.user.is_authenticated:
                # Redirect to login page with next parameter to return after login
                return redirect(f'/login/?next=/form/{unique_id}/')
                
            return render(request, 'public_form.html', {'form': form})

        else:
            return Response({"error": "Invalid GET request"}, status=400)
    
    def post(self, request, form_id=None, unique_id=None):
        url_name = request.resolver_match.url_name
        if url_name == 'create_form':
            # Create a new form record.
            title = request.POST.get('title', 'Untitled Form')
            description = request.POST.get('description', '')
            visibility = request.POST.get('visibility', 'public')

            form_obj = Form.objects.create(user=request.user, title=title, description=description, visibility=visibility)
            return JsonResponse({'form_id': form_obj.id, 'unique_id': str(form_obj.unique_id)}, status=201)
        
        elif url_name == 'delete_form' and form_id:
            # Delete via POST (you can also use the DELETE method if preferred).
            form = get_object_or_404(Form, id=form_id, user=request.user)
            form.delete()
            messages.success(request, "Form deleted successfully.")
            return redirect('list_forms')
        else:
            return Response({"error": "Invalid POST request"}, status=400)
    
    def put(self, request, form_id=None):
        if form_id:
            form = get_object_or_404(Form, id=form_id, user=request.user)
            title = request.data.get('title', form.title)
            description = request.data.get('description', form.description)
            form.title = title
            form.description = description
            form.save()
            return JsonResponse({'status': 'success', 'form_id': form.id})
        return Response({'error': 'Form ID required for update'}, status=400)
    
    def delete(self, request, form_id=None, unique_id=None):
        # Delete an existing form. The form_id must be provided.
        if form_id:
            form = get_object_or_404(Form, id=form_id, user=request.user)
            form.delete()
            return JsonResponse({'status': 'success', 'message': 'Form deleted successfully.'})
        return Response({'error': 'Form ID required for deletion.'}, status=400)

# --------- API for Dynamic Form Fields ---------

@method_decorator(login_required, name='dispatch')
class FormFieldAPIView(APIView):
    parser_classes = [JSONParser]

    def get(self, request, form_id):
        form_obj = get_object_or_404(Form, id=form_id, user=request.user)
        fields = form_obj.fields.all().order_by('order')
        data = [{
            'id': field.id,
            'label': field.label,
            'field_type': field.field_type,
            'order': field.order,
            'options': field.options.split(',') if field.options else []
        } for field in fields]
        return JsonResponse(data, safe=False)

    def post(self, request, form_id):
        """Add multiple fields dynamically."""
        form_obj = get_object_or_404(Form, id=form_id, user=request.user)
        try:
         
            data = request.data 
            fields_data = data.get('fields', [])

            if not fields_data:
                return HttpResponseBadRequest("No fields provided")

            created_fields = []
            for field in fields_data:
                label = field.get('label', 'Untitled Question')
                field_type = field.get('field_type')
                options = ','.join(field.get('options', [])) if field.get('options') else ''
                order = field.get('order', 0)

                if not field_type:
                    continue

                field_obj = FormField.objects.create(
                    form=form_obj, label=label, field_type=field_type, options=options, order=order
                )
                created_fields.append({
                    'id': field_obj.id,
                    'label': field_obj.label,
                    'field_type': field_obj.field_type,
                    'order': field_obj.order,
                    'options': field_obj.options.split(',') if field_obj.options else []
                })

            return JsonResponse({'fields': created_fields}, status=201)
        except Exception as e:
            return HttpResponseBadRequest(str(e))
        

class PublicFormView(View):
    def dispatch(self, request, *args, **kwargs):
        self.form = get_object_or_404(Form, unique_id=kwargs.get('unique_id'))
        if self.form.visibility == 'private' and not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this form.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, unique_id):
        # Check if the authenticated user is the form creator
        if request.user.is_authenticated and self.form.user == request.user:
            messages.error(request, "You cannot fill your own form.")
            return redirect('dashboard')
        
        fields = self.form.fields.all().order_by('order')
        return render(request, 'public_form.html', {'form': self.form, 'fields': fields})

    def post(self, request, unique_id):
        # Check if the authenticated user is the form creator
        if request.user.is_authenticated and self.form.user == request.user:
            messages.error(request, "You cannot fill your own form.")
            return redirect('dashboard')
        
        fields = self.form.fields.all().order_by('order')
        submitted_by_email = self.get_submitter_email(request)
        form_response = self.create_form_response(submitted_by_email)
        self.save_field_responses(request, form_response, fields)
        messages.success(request, "Form submitted successfully!")
        return redirect('public_form', unique_id=unique_id)

    def get_submitter_email(self, request):
        if self.form.visibility == 'private' and request.user.is_authenticated:
            return request.user.email
        return ""

    def create_form_response(self, submitted_by_email):
        return FormResponse.objects.create(
            form=self.form,
            submitted_by_email=submitted_by_email
        )

    def save_field_responses(self, request, form_response, fields):
        for field in fields:
            if field.field_type == 'multiple_choice':
                self.save_multiple_choice_responses(request, form_response, field)
            else:
                self.save_single_value_response(request, form_response, field)

    def save_multiple_choice_responses(self, request, form_response, field):
        selected_values = request.POST.getlist(f'field_{field.id}')
        for value in selected_values:
            if value:
                FormResponseField.objects.create(
                    response=form_response,
                    form_field=field,
                    value=value
                )

    def save_single_value_response(self, request, form_response, field):
        if field.field_type == 'file_upload' and f'field_{field.id}' in request.FILES:
            uploaded_file = request.FILES[f'field_{field.id}']
            FormResponseField.objects.create(
                response=form_response,
                form_field=field,
                uploaded_file=uploaded_file  # Store the file
            )
        else:
            field_value = request.POST.get(f'field_{field.id}', '')
            if field_value:
                FormResponseField.objects.create(
                    response=form_response,
                    form_field=field,
                    value=field_value
                )


    
# --------- Form Response Views ---------

@method_decorator(login_required, name='dispatch')
class ListResponsesView(View):
    def get(self, request):
        forms = Form.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'list_responses.html', {'forms': forms})

@method_decorator(login_required, name='dispatch')
class FormResponsesView(View):
    def get(self, request, form_id):
        form = get_object_or_404(Form, id=form_id, user=request.user)
        responses = FormResponse.objects.filter(form=form).order_by('-created_at')
        
        response_data = []
        for response in responses:
            fields = FormResponseField.objects.filter(response=response)
            field_values = {}
            for field in fields:
                label = field.form_field.label
                if field.form_field.field_type == 'multiple_choice':
                    if label not in field_values:
                        field_values[label] = []
                    field_values[label].append(field.value)
                elif field.form_field.field_type == 'file_upload' and field.uploaded_file:
                    field_values[label] = field.uploaded_file.url  # Use URL for file
                else:
                    field_values[label] = field.value
            response_data.append({
                'id': response.id,
                'created_at': response.created_at,
                'fields': field_values,
                'submitted_by_email': response.submitted_by_email,
            })
        
        form_fields = FormField.objects.filter(form=form).order_by('order')
        
        return render(request, 'form_responses.html', {
            'form': form,
            'responses': response_data,
            'form_fields': form_fields
        })
from django.db import models
from django.contrib.auth.models import User
import uuid, json

class Form(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),    # Anyone can access
        ('private', 'Private'),  # Only logged-in users can access
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_by_email = models.EmailField(blank=True, null=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # For shareable link
    visibility = models.CharField(
        max_length=7,
        choices=VISIBILITY_CHOICES,
        default='public',
    )
    
    def __str__(self):
        return self.title

class FormField(models.Model):
    FIELD_TYPES = [
        ('short_text', 'Short Answer'),
        ('paragraph', 'Paragraph'),
        ('multiple_choice', 'Multiple Choice'),
        ('checkboxes', 'Checkboxes'),
        ('dropdown', 'Dropdown'),
        ('date', 'Date'),
        ('time', 'Time'),
        ('file_upload', 'File Upload'),
        ('rating', 'Rating')
    ]

    form = models.ForeignKey(Form, related_name="fields", on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50, choices=FIELD_TYPES)
    options = models.TextField(blank=True, null=True)  # For multiple choices
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()})"
    
    def get_options_list(self):
        """Returns the options as a Python list"""
        if not self.options:
            return []
        try:
            return json.loads(self.options)
        except json.JSONDecodeError:
            return self.options.split(',') 
        
class FormResponse(models.Model):
    form = models.ForeignKey(Form, related_name="responses", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_by_email = models.EmailField(blank=True, null=True)  # Add this field

class FormResponseField(models.Model):
    response = models.ForeignKey(FormResponse, related_name="fields", on_delete=models.CASCADE)
    form_field = models.ForeignKey(FormField, on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)  # Stores the response value

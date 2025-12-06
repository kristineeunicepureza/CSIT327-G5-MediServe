from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import Medicine, MedicineBatch


class MedicineForm(forms.ModelForm):
    """Form for editing medicine details (not including batch info)"""

    class Meta:
        model = Medicine
        fields = ['name', 'brand', 'category', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter medicine name',
                'required': True,
            }),
            'brand': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter brand name',
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter category',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Enter description',
                'rows': 3,
            }),
        }

    def clean_name(self):
        """Validate medicine name is not empty"""
        name = self.cleaned_data.get('name')
        if not name or name.strip() == '':
            raise ValidationError("Medicine name cannot be empty.")
        return name.strip()


class MedicineBatchEditForm(forms.ModelForm):
    """Form for editing batch details"""

    class Meta:
        model = MedicineBatch
        fields = ['expiry_date', 'date_received', 'quantity_received', 'quantity_available']
        widgets = {
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True,
            }),
            'date_received': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True,
            }),
            'quantity_received': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 1,
                'required': True,
            }),
            'quantity_available': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 0,
                'required': True,
            }),
        }

    def clean_date_received(self):
        """Validate date_received is not in the future"""
        date_received = self.cleaned_data.get('date_received')
        if date_received and date_received > date.today():
            raise ValidationError("Date received cannot be in the future.")
        return date_received

    def clean_expiry_date(self):
        """Validate expiry_date is in the future"""
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date <= date.today():
            raise ValidationError("Expiry date must be in the future.")
        return expiry_date

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        date_received = cleaned_data.get('date_received')
        expiry_date = cleaned_data.get('expiry_date')
        quantity_received = cleaned_data.get('quantity_received')
        quantity_available = cleaned_data.get('quantity_available')

        if date_received and expiry_date:
            if expiry_date <= date_received:
                raise ValidationError(
                    "Expiry date must be after the date received."
                )

        if quantity_received and quantity_available:
            if quantity_available > quantity_received:
                raise ValidationError(
                    "Available quantity cannot exceed received quantity."
                )

        return cleaned_data
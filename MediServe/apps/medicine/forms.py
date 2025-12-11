from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import Medicine, MedicineBatch


def validate_no_antibiotics(value):
    """Validate that the value doesn't contain 'antibiotic'"""
    if value and 'antibiotic' in value.lower():
        raise ValidationError(
            'Antibiotics cannot be added to the system. '
            'These require prescription and in-person consultation at the health center.'
        )


class MedicineForm(forms.ModelForm):
    """Form for editing medicine details (not including batch info)"""

    class Meta:
        model = Medicine
        fields = ['name', 'brand', 'category', 'description', 'prescription_type', 'order_limit']
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
                'placeholder': 'Enter category (e.g., Vitamins, Pain Relief)',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Enter description',
                'rows': 3,
            }),
            'prescription_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'order_limit': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def clean_name(self):
        """Validate medicine name - no antibiotics, not empty"""
        name = self.cleaned_data.get('name')

        if not name or name.strip() == '':
            raise ValidationError("Medicine name cannot be empty.")

        name = name.strip()

        # Check for antibiotic
        if 'antibiotic' in name.lower():
            raise ValidationError(
                "❌ Antibiotics cannot be added to the system. "
                "These require prescription and in-person consultation at the health center."
            )

        return name

    def clean_category(self):
        """Validate category - no antibiotics"""
        category = self.cleaned_data.get('category')

        if category:
            category = category.strip()

            if 'antibiotic' in category.lower():
                raise ValidationError(
                    "❌ Antibiotic category is not allowed. "
                    "Please use a different category."
                )

        return category

    def clean_description(self):
        """Validate description - no antibiotics"""
        description = self.cleaned_data.get('description')

        if description:
            description = description.strip()

            if 'antibiotic' in description.lower():
                raise ValidationError(
                    "❌ Please remove references to antibiotics from the description."
                )

        return description

    def clean_brand(self):
        """Validate brand - no antibiotics"""
        brand = self.cleaned_data.get('brand')

        if brand:
            brand = brand.strip()

            if 'antibiotic' in brand.lower():
                raise ValidationError(
                    "❌ Brand name cannot contain references to antibiotics."
                )

        return brand


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


class MedicineStockForm(forms.Form):
    """Form for adding new medicine stock (inline form in medicine_stock.html)"""

    medicine_name = forms.CharField(
        max_length=255,
        required=True,
        validators=[validate_no_antibiotics],
        widget=forms.TextInput(attrs={
            'placeholder': 'Medicine Name',
            'class': 'form-input'
        }),
        help_text='Note: Antibiotics are not allowed'
    )

    brand = forms.CharField(
        max_length=255,
        required=False,
        validators=[validate_no_antibiotics],
        widget=forms.TextInput(attrs={
            'placeholder': 'Brand (optional)',
            'class': 'form-input'
        })
    )

    category = forms.CharField(
        max_length=255,
        required=False,
        validators=[validate_no_antibiotics],
        widget=forms.TextInput(attrs={
            'placeholder': 'Category (e.g., Vitamins, Pain Relief)',
            'class': 'form-input'
        }),
        help_text='Antibiotic category is not allowed'
    )

    description = forms.CharField(
        required=False,
        validators=[validate_no_antibiotics],
        widget=forms.Textarea(attrs={
            'placeholder': 'Description',
            'class': 'form-textarea',
            'rows': 2
        })
    )

    prescription_type = forms.ChoiceField(
        choices=Medicine.PRESCRIPTION_TYPE_CHOICES,
        initial='non_prescription',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    order_limit = forms.ChoiceField(
        choices=Medicine.ORDER_LIMIT_CHOICES,
        initial='1_week',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    expiry_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input'
        })
    )

    date_received = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input'
        })
    )

    quantity = forms.IntegerField(
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Quantity',
            'class': 'form-input',
            'min': '1'
        })
    )

    def clean_expiry_date(self):
        """Validate expiry date is in the future"""
        expiry_date = self.cleaned_data.get('expiry_date')
        if expiry_date and expiry_date <= date.today():
            raise ValidationError("Expiry date must be in the future.")
        return expiry_date

    def clean_date_received(self):
        """Validate date received is not in the future"""
        date_received = self.cleaned_data.get('date_received')
        if date_received and date_received > date.today():
            raise ValidationError("Date received cannot be in the future.")
        return date_received

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        expiry_date = cleaned_data.get('expiry_date')
        date_received = cleaned_data.get('date_received')

        if expiry_date and date_received:
            if expiry_date <= date_received:
                raise ValidationError(
                    "Expiry date must be after the date received."
                )

        return cleaned_data
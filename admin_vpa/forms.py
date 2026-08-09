from django import forms
from django.contrib.auth.models import User, Group, Permission

class UsuarioForm(forms.ModelForm):
    # Campo para seleccionar permisos individuales
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by('content_type__app_label', 'name'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Permisos Específicos"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'user_permissions']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control shadow-none'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control shadow-none'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control shadow-none'}),
            'email': forms.EmailInput(attrs={'class': 'form-control shadow-none'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
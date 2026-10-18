from django import forms
from django.contrib.auth.models import User, Group, Permission

class UsuarioForm(forms.ModelForm):
    nueva_password = forms.CharField(
        label="Nueva Contraseña (Opcional)",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dejar en blanco para mantener la contraseña actual...'
        }),
        help_text="Si está creando un usuario y lo deja en blanco, se asignará 'Emvepro2026*' por defecto."
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'groups': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'user_permissions': forms.SelectMultiple(attrs={'class': 'form-select', ' size': '8'}),
        }

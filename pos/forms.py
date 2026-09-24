from django import forms
from core.models import User


class AdminUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"})
    )

    class Meta:
        model = User
        fields = ("username", "role", "is_active")
        widgets = {
            "username": forms.TextInput(attrs={"class": "input", "autocomplete": "off"}),
            "role": forms.Select(attrs={"class": "input"}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("El usuario es obligatorio.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1") or ""
        p2 = cleaned.get("password2") or ""
        # Waiters/kitchen: simple passwords are fine (non-technical staff,
        # frequent shift changes). Admin handles money and users, so we
        # require a slightly higher minimum.
        min_len = 8 if cleaned.get("role") == User.Role.ADMIN else 4
        if p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if len(p1) < min_len:
            self.add_error("password1", f"La contraseña debe tener al menos {min_len} caracteres.")
        return cleaned

    def save(self, commit=True):
        u = super().save(commit=False)
        u.set_password(self.cleaned_data["password1"])
        if commit:
            u.save()
        return u


class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "role", "is_active")
        widgets = {
            "username": forms.TextInput(attrs={"class": "input", "autocomplete": "off"}),
            "role": forms.Select(attrs={"class": "input"}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("El usuario es obligatorio.")
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username


class AdminUserPasswordForm(forms.Form):
    password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"})
    )

    def __init__(self, *args, target_role=None, **kwargs):
        # The view passes the role of the user being reset, so clean()
        # knows which minimum length to enforce.
        self.target_role = target_role
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1") or ""
        p2 = cleaned.get("password2") or ""
        min_len = 8 if self.target_role == User.Role.ADMIN else 4
        if p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if len(p1) < min_len:
            self.add_error("password1", f"La contraseña debe tener al menos {min_len} caracteres.")
        return cleaned

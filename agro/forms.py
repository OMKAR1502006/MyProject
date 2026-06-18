from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import FarmerProfile


class FarmerRegistrationForm(UserCreationForm):
    """Registration with farmer-specific fields."""

    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=False, label='Full name')
    phone = forms.CharField(max_length=15, required=False, label='Mobile number')
    village = forms.CharField(max_length=100, required=False)
    district = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    primary_crop = forms.CharField(max_length=80, required=False, label='Main crop')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        if commit:
            user.save()
            FarmerProfile.objects.create(
                user=user,
                phone=self.cleaned_data.get('phone', ''),
                village=self.cleaned_data.get('village', ''),
                district=self.cleaned_data.get('district', ''),
                state=self.cleaned_data.get('state', ''),
                primary_crop=self.cleaned_data.get('primary_crop', ''),
            )
        return user


class FarmerProfileForm(forms.ModelForm):
    """Edit farmer profile."""

    first_name = forms.CharField(max_length=50, required=False, label='Full name')
    email = forms.EmailField(required=False)

    class Meta:
        model = FarmerProfile
        fields = (
            'phone', 'village', 'district', 'state',
            'primary_crop', 'farm_size_acres', 'preferred_language',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['preferred_language'].widget = forms.Select(
            choices=getattr(settings, 'LANGUAGES', [('en', 'English')])
        )
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.email = self.cleaned_data.get('email', user.email)
        if commit:
            user.save()
            profile.save()
        return profile

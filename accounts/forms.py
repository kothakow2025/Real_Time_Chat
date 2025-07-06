from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from crispy_forms.bootstrap import FormActions
from . import models

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    profile_picture = forms.ImageField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists in the database
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError('This email address is already registered. Please use a different email or try logging in.')
        return email
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'username',
            'email',
            'profile_picture',
            'password1',
            'password2',
            FormActions(
                Submit('submit', 'Sign Up', css_class='btn btn-primary btn-block')
            )
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create or update profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            if self.cleaned_data['profile_picture']:
                profile.profile_picture = self.cleaned_data['profile_picture']
                profile.save()
        
        return user

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists for another user
            existing_user = User.objects.filter(email=email).exclude(id=self.instance.id).first()
            if existing_user:
                raise forms.ValidationError('This email address is already registered by another user. Please use a different email.')
        return email
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'username',
            'email',
            FormActions(
                Submit('submit', 'Update Profile', css_class='btn btn-primary')
            )
        )

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio', 'show_online_status']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'profile_picture',
            FormActions(
                Submit('submit', 'Update Picture', css_class='btn btn-success')
            )
        )

class FriendRequestForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Get users who are not friends and haven't received/sent requests
            from .models import FriendRequest
            
            # Exclude current user
            users = User.objects.exclude(id=self.user.id)
            
            # Exclude users with existing friend requests
            existing_requests = FriendRequest.objects.filter(
                models.Q(from_user=self.user) | models.Q(to_user=self.user)
            ).values_list('from_user_id', 'to_user_id')
            
            excluded_ids = set()
            for from_id, to_id in existing_requests:
                excluded_ids.add(from_id)
                excluded_ids.add(to_id)
            
            users = users.exclude(id__in=excluded_ids)
            
            self.fields['to_user'] = forms.ModelChoiceField(
                queryset=users,
                empty_label="Select a user to send friend request",
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'to_user',
            FormActions(
                Submit('submit', 'Send Friend Request', css_class='btn btn-primary')
            )
        )
#!/usr/bin/env python
"""
Test script for email uniqueness validation
"""
import os
import sys
import django
import uuid

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kothakow.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.forms import SignUpForm, UserUpdateForm

def test_signup_email_validation():
    """Test email uniqueness validation in SignUpForm"""
    print("Testing SignUpForm email validation...")
    
    # Generate unique usernames
    unique_id = str(uuid.uuid4())[:8]
    
    # Create a test user with an email
    test_user = User.objects.create_user(
        username=f'testuser1_{unique_id}',
        email='test@example.com',
        password='testpass123'
    )
    print(f"Created user: {test_user.username} with email: {test_user.email}")
    
    # Test 1: Try to create another user with the same email
    form_data = {
        'username': f'testuser2_{unique_id}',
        'email': 'test@example.com',  # Same email as existing user
        'first_name': 'Test',
        'last_name': 'User',
        'password1': 'testpass123',
        'password2': 'testpass123'
    }
    
    form = SignUpForm(data=form_data)
    is_valid = form.is_valid()
    print(f"Form valid with duplicate email: {is_valid}")
    
    if not is_valid:
        print("Errors:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
    
    # Test 2: Try to create a user with a different email
    form_data2 = {
        'username': f'testuser3_{unique_id}',
        'email': 'new@example.com',  # Different email
        'first_name': 'New',
        'last_name': 'User',
        'password1': 'testpass123',
        'password2': 'testpass123'
    }
    
    form2 = SignUpForm(data=form_data2)
    is_valid2 = form2.is_valid()
    print(f"Form valid with unique email: {is_valid2}")
    
    if not is_valid2:
        print("Errors:")
        for field, errors in form2.errors.items():
            print(f"  {field}: {errors}")
    
    # Clean up
    test_user.delete()
    print("SignUpForm email validation test completed!\n")

def test_profile_update_email_validation():
    """Test email uniqueness validation in UserUpdateForm"""
    print("Testing UserUpdateForm email validation...")
    
    # Generate unique usernames
    unique_id = str(uuid.uuid4())[:8]
    
    # Create two test users with different emails
    user1 = User.objects.create_user(
        username=f'updateuser1_{unique_id}',
        email='update1@example.com',
        password='testpass123'
    )
    
    user2 = User.objects.create_user(
        username=f'updateuser2_{unique_id}',
        email='update2@example.com',
        password='testpass123'
    )
    
    print(f"Created users: {user1.username} ({user1.email}) and {user2.username} ({user2.email})")
    
    # Test 1: Try to update user2 with user1's email
    form_data = {
        'username': f'updateuser2_{unique_id}',
        'email': 'update1@example.com',  # Same email as user1
        'first_name': 'Update',
        'last_name': 'User'
    }
    
    form = UserUpdateForm(data=form_data, instance=user2)
    is_valid = form.is_valid()
    print(f"Form valid with duplicate email: {is_valid}")
    
    if not is_valid:
        print("Errors:")
        for field, errors in form.errors.items():
            print(f"  {field}: {errors}")
    
    # Test 2: Try to update user2 with a unique email
    form_data2 = {
        'username': f'updateuser2_{unique_id}',
        'email': 'update3@example.com',  # Unique email
        'first_name': 'Update',
        'last_name': 'User'
    }
    
    form2 = UserUpdateForm(data=form_data2, instance=user2)
    is_valid2 = form2.is_valid()
    print(f"Form valid with unique email: {is_valid2}")
    
    if not is_valid2:
        print("Errors:")
        for field, errors in form2.errors.items():
            print(f"  {field}: {errors}")
    
    # Test 3: Try to update user2 with their own email (should be valid)
    form_data3 = {
        'username': f'updateuser2_{unique_id}',
        'email': 'update2@example.com',  # Same email as user2
        'first_name': 'Update',
        'last_name': 'User'
    }
    
    form3 = UserUpdateForm(data=form_data3, instance=user2)
    is_valid3 = form3.is_valid()
    print(f"Form valid with own email: {is_valid3}")
    
    if not is_valid3:
        print("Errors:")
        for field, errors in form3.errors.items():
            print(f"  {field}: {errors}")
    
    # Clean up
    user1.delete()
    user2.delete()
    print("UserUpdateForm email validation test completed!\n")

if __name__ == '__main__':
    test_signup_email_validation()
    test_profile_update_email_validation()
    print("All email validation tests completed!") 
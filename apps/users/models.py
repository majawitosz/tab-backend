from django.db import models
from django.contrib.auth.models import User

# Add a token field to the User model (simplified for this example)
User.add_to_class('auth_token', models.CharField(max_length=100, null=True, blank=True))
"""
URL configuration for tab_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from apps.users.api import api as users_api
from apps.dania.api import api as dishes_api

urlpatterns = [
    path('admin/', admin.site.urls),
    # wszystkie endpoints związane z auth
    path('api/users/', users_api.urls),
    # wszystkie endpoints związane z daniami
    path('api/dania/', dishes_api.urls),
]


"""This contains all of the URL mappings for the Home application. The
`urlpatterns` list routes URLs to views. For more information please see:

https://docs.djangoproject.com/en/2.1/topics/http/urls/
"""

from ghostwriter.home.views import dashboard, profile, management, upload_avatar
from django.urls import path

app_name = "home"

# URLs for the basic views
urlpatterns = [
     path('', dashboard, name='dashboard'),
     path('profile/', profile, name='profile'),
     path('management/', management, name='management'),
     path('profile/avatar', upload_avatar,
          name='upload_avatar')
]

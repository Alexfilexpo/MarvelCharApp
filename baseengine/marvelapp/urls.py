from django.urls import path

from .views import *

urlpatterns = [
    path('', SearchForm.as_view(), name='search_form_url'),
]

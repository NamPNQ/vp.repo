from django.conf.urls import patterns, url, include
from django.contrib import admin
import views

urlpatterns = patterns('',
    url(r'^modules/', views.dispatchModuleCalls, name='dispatchModuleCalls'),
    )


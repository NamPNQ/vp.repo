from django.conf.urls import patterns, url, include

import views


urlpatterns = patterns('',
    url(r'^$', views.DashboardView.as_view(), name='dashboard-home'),
    url(r'^login/$', views.loginView, name='dashboard-login'),
    url(r'^logout/$', views.logoutDashboard, name='dashboard-logout'),
    url(r'^clients/$', views.clientListView, name='client-list'),
    url(r'^clients/add/$', views.clientRegView, name='add-client'),
    url(r'^clients/(?P<client_id>\d+)/$', views.clientEditView, name='view-client'),
    url(r'^tokens/$', views.tokenListView, name='token-list'),
    url(r'^api-records/$', views.apiRecordsView, name='dashboard-api-records'),
    url(r'^stats/$', views.statsView, name='dashboard-stats'),
    url(r'^materials/$', views.materialsView, name='dashboard-materials'),
    url(r'^oasis/$', views.oasis_view, name='dashboard-oasis'),
    url(r'^persons/$', views.persons_view, name='dashboard-persons'),
    url(r'^render/(?P<mid>[0-9a-z]+)(/(?P<version>\d+))?/?$', views.renderMaterialView, name='render-materials'),
)

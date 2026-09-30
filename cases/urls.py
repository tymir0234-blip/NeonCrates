from django.urls import path

from cases import views

urlpatterns = [
    path('', views.home, name='home'),
    path('case/<slug:slug>/', views.case_detail, name='case'),
    path('api/open/<slug:slug>/', views.api_open, name='api_open'),
    path('inventory/', views.inventory, name='inventory'),
    path('profile/', views.profile_page, name='profile'),
    path('top/', views.top_drops, name='top'),
    path('upgrade/', views.upgrade, name='upgrade'),
    path('api/upgrade/preview/', views.api_upgrade_preview, name='api_upgrade_preview'),
    path('api/upgrade/roll/', views.api_upgrade_roll, name='api_upgrade_roll'),
    path('contract/', views.contract, name='contract'),
    path('giveaway/', views.giveaways, name='giveaways'),
    path('giveaway/<int:pk>/enter/', views.giveaway_enter, name='giveaway_enter'),
    path('giveaway/<int:pk>/pick/', views.giveaway_pick, name='giveaway_pick'),
    path('tournaments/', views.tournaments, name='tournaments'),
    path('faq/', views.faq, name='faq'),
    path('support/', views.support, name='support'),
    path('rules/<slug:kind>/', views.rule, name='rule'),
]

app_name = 'cases'
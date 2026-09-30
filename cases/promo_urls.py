from django.urls import path

from cases import views

urlpatterns = [
    path('', views.promo_redeem, name='redeem'),
]

app_name = 'promo'
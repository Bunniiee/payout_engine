from django.http import HttpResponse
from django.urls import path, include


def health(request):
    return HttpResponse('ok', content_type='text/plain')


urlpatterns = [
    path('health/', health),
    path('api/v1/', include('payouts.urls')),
]

from django.urls import path,include
from . import views
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('', views.home, name='home'),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/register/', include('dj_rest_auth.registration.urls')),
    path('experiments/', csrf_exempt(views.ExperimentAPIView.as_view()), name='experiments'),
    path('experiment-results/<int:experiment_id>/', csrf_exempt(views.ExperimentResultsAPIView.as_view()), name='experiment-results'),
    path('experiment-recommend-structures/<int:experiment_id>/', csrf_exempt(views.ExperimentRecommendStructuresAPIView.as_view()), name='experiment-recommend-structures'),
    path('generate-presigned-url', csrf_exempt(views.PresignUploadView.as_view()), name='generate-presigned-url'),
    path('experiment-gyration-radius/<int:experiment_id>/', csrf_exempt(views.ExperimentGyrationRadiusAPIView.as_view()), name='experiment-gyration-radius'),
    path('experiment-rmsd/<int:experiment_id>/', csrf_exempt(views.ExperimentRMSDAPIView.as_view()), name='experiment-rmsd'),
    path('experiment-cmd-output/<int:experiment_id>/', csrf_exempt(views.ExperimentCMDOutput.as_view()), name='experiment-rmsd'),


]


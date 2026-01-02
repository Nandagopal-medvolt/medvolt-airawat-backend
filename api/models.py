from django.db import models
from django.contrib.auth.models import User
# Create your models here.




class Experiment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    pdb_file_url = models.CharField()
    results_folder_s3_url = models.CharField(null=True, blank=True)
    simulation_time = models.IntegerField(help_text="Simulation time in nanoseconds")
    smile=models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    batch_job_id=models.CharField(max_length=100, null=True, blank=True)

    batch_status = models.CharField(max_length=50, null=True, blank=True)
    batch_status_reason = models.TextField(null=True, blank=True)
    batch_created_at = models.DateTimeField(null=True, blank=True)
    batch_started_at = models.DateTimeField(null=True, blank=True)
    batch_stopped_at = models.DateTimeField(null=True, blank=True)
    batch_status_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
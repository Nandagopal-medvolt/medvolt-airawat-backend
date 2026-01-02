from api.models import Experiment
from rest_framework import serializers

class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = [ 'name', 'id','description', 'pdb_file_url', 'simulation_time']
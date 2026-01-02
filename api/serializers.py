from api.models import Experiment
from rest_framework import serializers
from .aws_clients import get_batch_client

class ExperimentSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Experiment
        fields = ['name', 'id', 'description', 'simulation_time', 'status','smile']
    
    def get_status(self, obj):
        if not obj.batch_status:
            return None
        
        return {
            'status': obj.batch_status,
            'status_reason': obj.batch_status_reason or None,
            'created_at': self._format_datetime(obj.batch_created_at),
            'started_at': self._format_datetime(obj.batch_started_at),
            'stopped_at': self._format_datetime(obj.batch_stopped_at),
        }
    
    def _format_datetime(self, dt):
        if not dt:
            return None
        return dt.strftime("%b %d, %Y %I:%M %p %Z")
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from api.models import Experiment
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from api.serializers import ExperimentSerializer
from rest_framework.response import Response
from api.utils import get_result_urls,get_recommended_structures_with_viz,fetch_gyration_radius,fetch_cmd_output
from .aws_clients import get_batch_client,get_s3_client
import uuid
from django.conf import settings
import json
import base64
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone


def home(request):
    return JsonResponse({"message": "Welcome to the API Home Page"})

class PresignUploadView(APIView):
    def post(self, request):
        s3 = get_s3_client()

        key = f"airawat-backend/cmd/inputs/{uuid.uuid4()}.pdb"

        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
                "ContentType": "chemical/x-pdb",
            },
            ExpiresIn=3600,
        )

        return Response({
            "upload_url": url,
            "s3_key": key
        })
    

class ExperimentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        experiments = Experiment.objects.filter(user=request.user)
        
        self._update_batch_statuses(experiments)
        
        experiments = Experiment.objects.filter(user=request.user)
        
        serializer = ExperimentSerializer(experiments, many=True)
        return Response(serializer.data)
    
    def _update_batch_statuses(self, experiments):
        experiments_to_update = [
            exp for exp in experiments 
            if exp.batch_job_id and self._should_update_status(exp)
        ]
        
        if not experiments_to_update:
            return
        
        batch_job_ids = [exp.batch_job_id for exp in experiments_to_update]
        
        try:
            batch_client = get_batch_client()
            response = batch_client.describe_jobs(jobs=batch_job_ids)
            
            jobs_map = {job['jobId']: job for job in response['jobs']}
            
            for exp in experiments_to_update:
                job = jobs_map.get(exp.batch_job_id)
                if job:
                    self._update_experiment_status(exp, job)
                    
        except Exception as e:
            print(f"Error fetching batch statuses: {e}")
    
    def _should_update_status(self, experiment):
        if not experiment.batch_status:
            return True
        
        terminal_states = ['SUCCEEDED', 'FAILED']
        if experiment.batch_status in terminal_states:
            return False
        
        if experiment.batch_status_updated_at:
            time_since_update = timezone.now() - experiment.batch_status_updated_at
            return time_since_update.total_seconds() > 30
        
        return True
    
    def _update_experiment_status(self, experiment, job_data):
        experiment.batch_status = job_data['status']
        experiment.batch_status_reason = job_data.get('statusReason', '')
        
        if job_data.get('createdAt'):
            experiment.batch_created_at = self._convert_timestamp(job_data['createdAt'])
        if job_data.get('startedAt'):
            experiment.batch_started_at = self._convert_timestamp(job_data['startedAt'])
        if job_data.get('stoppedAt'):
            experiment.batch_stopped_at = self._convert_timestamp(job_data['stoppedAt'])
        
        experiment.batch_status_updated_at = timezone.now()
        experiment.save(update_fields=[
            'batch_status', 
            'batch_status_reason',
            'batch_created_at',
            'batch_started_at',
            'batch_stopped_at',
            'batch_status_updated_at'
        ])
    
    def _convert_timestamp(self, timestamp_ms):
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=dt_timezone.utc)        
    

        # payload = {
        #     "simulation_time": "50",
        #     "s3_bucket": "medvolt-cmd-standalone-test",
        #     "s3_input_pdb_file_key": "cmd/complex_Mv_17030.pdb",
        #     "s3_output_path": "airawat/traj_analysis/run1",
        #     "smile": "C[N+]1(C)C2CCC1CC(O(C(=O)C(O)c1ccccc1)C2))"
        # }

    def post(self, request):
        user=request.user
        experiment=Experiment.objects.create(user=user,smile=request.data.get('smile',''),description=request.data.get('description',''),name=request.data.get('name',''),pdb_file_url=request.data.get('pdb_file_url',''),simulation_time=request.data.get('simulation_time',''))

        batch = get_batch_client()
        experiment.results_folder_s3_url= f"s3://medvolt-cmd-standalone-test/airawat/traj_analysis/exp_{experiment.id}"
        experiment.save(update_fields=["results_folder_s3_url"])

        payload = {
            "simulation_time": experiment.simulation_time,
            "s3_bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "s3_input_pdb_file_key": experiment.pdb_file_url,
            "s3_output_path": f"airawat/traj_analysis/exp_{experiment.id}",
            "smile": experiment.smile,
        }
        base64_payload = base64.b64encode(json.dumps(payload).encode()).decode()

        response = batch.submit_job(
            jobName=f"cmd-exp-{experiment.id}",
            jobQueue="cmd-t4-queue",
            jobDefinition="cmd-standalone-airawat-job-definition:1",
            containerOverrides={
                "command": [
                   base64_payload
                ]
            }
        )

        experiment.batch_job_id = response["jobId"]
        experiment.save(update_fields=["batch_job_id"])

        return Response(
            {
                "experiment_id": experiment.id,
                "batch_job_id": response["jobId"],
            },
            status=201,
        )
        

class ExperimentResultsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, experiment_id):
        try:
            experiment = Experiment.objects.get(id=experiment_id, user=request.user)
            results_folder_s3_url = experiment.results_folder_s3_url
            result_urls = get_result_urls(results_folder_s3_url)
            return Response(result_urls)

        except Experiment.DoesNotExist:
            return Response({"error": "Experiment not found"}, status=404)

class ExperimentRecommendStructuresAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, experiment_id):
        try:
            experiment = Experiment.objects.get(id=experiment_id, user=request.user)
            results_folder_s3_url = experiment.results_folder_s3_url  + "/recommended_structures/"
            result_urls = get_recommended_structures_with_viz(results_folder_s3_url)
            return Response(result_urls)

        except Experiment.DoesNotExist:
            return Response({"error": "Experiment not found"}, status=404)


class ExperimentGyrationRadiusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, experiment_id):
        try:
            experiment = Experiment.objects.get(id=experiment_id, user=request.user)
            results_folder_s3_url = experiment.results_folder_s3_url  + "/gyrate.csv"
            result = fetch_gyration_radius(results_folder_s3_url)
            return Response(result)

        except Experiment.DoesNotExist:
            return Response({"error": "Experiment not found"}, status=404)
        

class ExperimentRMSDAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, experiment_id):
        try:
            experiment = Experiment.objects.get(id=experiment_id, user=request.user)
            results_folder_s3_url = experiment.results_folder_s3_url  + "/rmsd.csv"
            result = fetch_gyration_radius(results_folder_s3_url)
            return Response(result)

        except Experiment.DoesNotExist:
            return Response({"error": "Experiment not found"}, status=404)
        

class ExperimentCMDOutput(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, experiment_id):
        try:
            experiment = Experiment.objects.get(id=experiment_id, user=request.user)
            results_folder_s3_url = experiment.results_folder_s3_url  + "/output.csv"
            result = fetch_cmd_output(results_folder_s3_url)
            return Response(result)

        except Experiment.DoesNotExist:
            return Response({"error": "Experiment not found"}, status=404)
        

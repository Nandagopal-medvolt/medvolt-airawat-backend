from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from api.models import Experiment
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from api.serializers import ExperimentSerializer
from rest_framework.response import Response
from api.utils import get_result_urls,get_recommended_structures_with_viz
from .aws_clients import get_batch_client,get_s3_client
import uuid
from django.conf import settings
import json
import base64
# Create your views here.



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
        experiments= Experiment.objects.filter(user=request.user)
        serializer= ExperimentSerializer(experiments, many=True)
        return Response(serializer.data)
        
    

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

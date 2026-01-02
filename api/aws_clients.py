# aws_clients.py
import boto3
from django.conf import settings
from botocore.config import Config

_session = None
_s3_client = None
_batch_client = None


def get_aws_session():
    global _session
    if _session is None:
        _session = boto3.session.Session(
            region_name=settings.AWS_REGION_NAME
        )
    return _session


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = get_aws_session().client(
            "s3",
            config=Config(
                max_pool_connections=50,
                retries={"max_attempts": 5},
            ),
        )
    return _s3_client


def get_batch_client():
    global _batch_client
    if _batch_client is None:
        _batch_client = get_aws_session().client(
            "batch",
            config=Config(
                retries={"max_attempts": 3},
            ),
        )
    return _batch_client

from urllib.parse import urlparse
from .aws_clients import get_s3_client
from django.conf import settings


def parse_s3_uri(s3_uri: str):
   
    parsed = urlparse(s3_uri)

    if parsed.scheme != "s3":
        raise ValueError("Invalid S3 URI. Expected format: s3://bucket/key")

    bucket = parsed.netloc
    key = parsed.path.lstrip("/")

    if not bucket or not key:
        raise ValueError("Invalid S3 URI. Bucket or key missing")

    return bucket, key

def get_result_urls(s3_uri, expires=3600):
    s3 = get_s3_client()
    bucket, prefix = parse_s3_uri(s3_uri)

    paginator = s3.get_paginator("list_objects_v2")
    results = []

    for page in paginator.paginate(
        Bucket=bucket,
        Prefix=prefix,
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            results.append({
                "key": key,
                "url": s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": bucket,
                        "Key": key,
                    },
                    ExpiresIn=expires,
                ),
            })

    return results


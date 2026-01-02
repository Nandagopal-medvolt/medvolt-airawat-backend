from urllib.parse import urlparse
from .aws_clients import get_s3_client
from django.conf import settings
import py3Dmol

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
    
    report_files = {
        "analysis_summary.txt",
        "simulation_recommendations.txt",
        "model_selection_report.txt"
    }
    
    visualization_files = {
        "cvs_projections.png",
        "cvs_timeseries.png",
        "free_energy_surface.png",
        "metastable_states.png",
        "model_performance_metrics.png",
        "training_validation_curves.png"
    }
    
    results = {
        "reports": [],
        "visualizations": [],
        "recommended_structures": []
    }
    
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            filename = key.split("/")[-1]
            
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires,
            )
            
            item = {"key": key, "url": url}
            
            if filename in report_files:
                results["reports"].append(item)
            elif filename in visualization_files:
                results["visualizations"].append(item)
            elif "recommended_structures/" in key and key.endswith(".pdb"):
                results["recommended_structures"].append(item)
    
    return results


def get_recommended_structures_with_viz(s3_uri, expires=3600):
    s3 = get_s3_client()
    bucket, prefix = parse_s3_uri(s3_uri)
    paginator = s3.get_paginator("list_objects_v2")
    
    recommended_structures = []
    
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            
            if "recommended_structures/" in key and key.endswith(".pdb"):
                url = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=expires,
                )
                
                try:
                    response = s3.get_object(Bucket=bucket, Key=key)
                    pdb_data = response['Body'].read().decode('utf-8')
                    
                    html_content = generate_pdb_visualization(pdb_data)
                    
                    recommended_structures.append({
                        "key": key,
                        "filename": key.split("/")[-1],
                        "url": url,
                        "visualization_html": html_content
                    })
                    
                except Exception as e:
                    recommended_structures.append({
                        "key": key,
                        "filename": key.split("/")[-1],
                        "url": url,
                        "visualization_html": None,
                        "error": str(e)
                    })
    
    return recommended_structures


def generate_pdb_visualization(pdb_data):
    lines = pdb_data.splitlines()
    atom_lines = [line for line in lines if line.startswith("ATOM")]
    hetatm_lines = [line for line in lines if line.startswith("HETATM")]
    other_lines = [
        line
        for line in lines
        if not (line.startswith("ATOM") or line.startswith("HETATM"))
    ]
    ordered_lines = atom_lines + hetatm_lines + other_lines
    ordered_data = "\n".join(ordered_lines)
    
    view = py3Dmol.view(width=800, height=600)
    view.addModel(ordered_data, "pdb")
    
    view.setStyle(
        {"model": 0, "and": [{"atom": "C", "invert": True}]},
        {"cartoon": {"color": "spectrum"}},
    )
    
    view.setStyle(
        {"model": 0, "and": [{"hetflag": True}]},
        {"stick": {"colorscheme": "greenCarbon"}},
    )
    
    view.zoomTo()
    
    return view._make_html()
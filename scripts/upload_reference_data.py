"""Upload bundled reference JSON data to the deployed Augury data bucket."""

from __future__ import annotations

import argparse
from pathlib import Path

import boto3


def upload_tree(client, bucket: str, root: Path, prefix: str) -> int:
    count = 0
    for path in root.rglob("*.json"):
        key = f"{prefix}/{path.relative_to(root).as_posix()}"
        client.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": "application/json"})
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", default="simplifynext-dev")
    parser.add_argument("--profile", default="simplifynext")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    cloudformation = session.client("cloudformation")
    outputs = {
        item["OutputKey"]: item["OutputValue"]
        for item in cloudformation.describe_stacks(StackName=args.stack)["Stacks"][0].get("Outputs", [])
    }
    bucket = outputs["DataBucketName"]
    s3 = session.client("s3")
    root = args.project_root / "data"
    uploaded = 0
    uploaded += upload_tree(s3, bucket, root / "founder_briefs", "founder_briefs")
    uploaded += upload_tree(s3, bucket, root / "example_profiles", "example_profiles")
    uploaded += upload_tree(s3, bucket, root / "benchmark_priors", "benchmark_priors")
    print(f"Uploaded {uploaded} reference JSON files to s3://{bucket}/")


if __name__ == "__main__":
    main()

"""Create/update CloudFront hosting and upload the static frontend files."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", default="simplifynext-frontend")
    parser.add_argument("--profile", default="simplifynext")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    cloudformation = session.client("cloudformation")
    template = (args.project_root / "frontend-template.yaml").read_text(encoding="utf-8")
    stack_changed = False
    try:
        cloudformation.describe_stacks(StackName=args.stack)
        try:
            cloudformation.update_stack(
                StackName=args.stack,
                TemplateBody=template,
                Capabilities=["CAPABILITY_IAM"],
            )
            stack_changed = True
        except ClientError as exc:
            if "No updates are to be performed" not in str(exc):
                raise
        waiter = cloudformation.get_waiter("stack_update_complete") if stack_changed else None
    except ClientError as exc:
        if "does not exist" not in str(exc):
            raise
        cloudformation.create_stack(
            StackName=args.stack,
            TemplateBody=template,
            Capabilities=["CAPABILITY_IAM"],
        )
        stack_changed = True
        waiter = cloudformation.get_waiter("stack_create_complete")
    if waiter:
        waiter.wait(StackName=args.stack, WaiterConfig={"Delay": 15, "MaxAttempts": 80})

    stack = cloudformation.describe_stacks(StackName=args.stack)["Stacks"][0]
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stack.get("Outputs", [])}
    bucket = outputs["FrontendBucketName"]
    distribution_id = outputs["CloudFrontDistributionId"]
    s3 = session.client("s3")
    content_types = {
        ".html": "text/html",
        ".js": "application/javascript",
        ".css": "text/css",
        ".json": "application/json",
    }
    files = ["index.html", "app.js", "styles.css"]
    fixture = args.project_root / "fixtures" / "content_package.fixture.json"
    if fixture.exists():
        files.append("fixtures/content_package.fixture.json")
    for name in files:
        path = args.project_root / name
        s3.upload_file(
            str(path),
            bucket,
            name,
            ExtraArgs={"ContentType": content_types[path.suffix]},
        )
    session.client("cloudfront").create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(time.time()),
        },
    )
    print(f"Frontend URL: {outputs['FrontendUrl']}")
    print(f"Frontend bucket: {bucket}")


if __name__ == "__main__":
    main()

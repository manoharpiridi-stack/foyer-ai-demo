"""Build the Docker image, push it to ECR and deploy it as a Lambda function with Terraform."""

import os
import subprocess
import time
from pathlib import Path

from dotenv import dotenv_values, find_dotenv

ROOT = Path(__file__).resolve().parent.parent
TERRAFORM = ROOT / "terraform"


def run(cmd: list[str], **kwargs):
    print("\n$", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)


def terraform_output(name: str) -> str:
    result = subprocess.run(["terraform", "output", "-raw", name], cwd=TERRAFORM, check=True, capture_output=True, text=True)
    return result.stdout.strip()


if __name__ == "__main__":
    # Terraform reads TF_VAR_* environment variables, so the key never has to be written to a .tfvars file.
    # A separate dict keeps the name's lowercase on Windows, where os.environ upper-cases it.
    key = dotenv_values(find_dotenv(usecwd=True))["OPENAI_API_KEY"].strip()
    tf_env = {**os.environ, "TF_VAR_openai_api_key": key}
    tag = time.strftime("%Y%m%d-%H%M%S")
    tf_vars = ["-var", f"image_tag={tag}"]

    run(["terraform", "init", "-input=false"], cwd=TERRAFORM)

    # 1. The image registry must exist before an image can be pushed to it.
    run(["terraform", "apply", "-auto-approve", "-target=aws_ecr_repository.app", *tf_vars], cwd=TERRAFORM, env=tf_env)
    repository = terraform_output("ecr_repository_url")  # <account>.dkr.ecr.<region>.amazonaws.com/foyer-ai-demo
    region = repository.split(".")[3]

    # 2. Build for Lambda's CPU (amd64) and push. --provenance=false: Lambda rejects multi-manifest images.
    password = subprocess.run(["aws", "ecr", "get-login-password", "--region", region], check=True, capture_output=True, text=True).stdout
    run(["docker", "login", "--username", "AWS", "--password-stdin", repository.split("/")[0]], input=password, text=True)
    run(["docker", "build", "--platform", "linux/amd64", "--provenance=false", "-t", f"{repository}:{tag}", str(ROOT)])
    run(["docker", "push", f"{repository}:{tag}"])

    # 3. Create or update everything else; the Lambda now points at the new image.
    run(["terraform", "apply", "-auto-approve", *tf_vars], cwd=TERRAFORM, env=tf_env)
    print(f"\nDeployed image {tag}\nApp URL: {terraform_output('app_url')}")

#!/bin/zsh

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1   # change if needed
aws ecr get-login-password --region $REGION \
| docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

TAG=$(date +%Y%m%d%H%M)   # timestamp tag
docker buildx build \
  --platform linux/amd64 \
  -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/preppr:$TAG \
  -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/preppr:latest \
  --push .
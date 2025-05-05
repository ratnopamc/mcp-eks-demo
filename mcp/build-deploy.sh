#!/bin/bash

# Exit on any error
set -e

# Configuration
ECR_REPOSITORY="mcp-server-py"
IMAGE_TAG="latest"
DEPLOYMENT_NAME="mcp-server-py"
NAMESPACE="default"

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
AWS_REGION=$(aws configure get region)
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-west-2"  # Default region
fi

echo "Using AWS Account ID: $AWS_ACCOUNT_ID and Region: $AWS_REGION"

# Log in to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repository if it doesn't exist
echo "Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION || \
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# Build and tag the Docker image
echo "Building Docker image..."
docker build --platform linux/amd64 -t $ECR_REPOSITORY:$IMAGE_TAG .

# Tag the image for ECR
ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
echo "Tagging image as: $ECR_IMAGE_URI"
docker tag $ECR_REPOSITORY:$IMAGE_TAG $ECR_IMAGE_URI

# Push the image to ECR
echo "Pushing image to ECR..."
docker push $ECR_IMAGE_URI

# Update the Kubernetes deployment
echo "Updating Kubernetes deployment..."

# Create a temporary deployment file with the correct image
cat > mcp-deploy-resolved.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $DEPLOYMENT_NAME
  namespace: $NAMESPACE
spec:
  replicas: 2
  selector:
    matchLabels:
      app: $DEPLOYMENT_NAME
  template:
    metadata:
      labels:
        app: $DEPLOYMENT_NAME
    spec:
      containers:
      - name: $DEPLOYMENT_NAME
        image: $ECR_IMAGE_URI
        ports:
        - containerPort: 8000
        env:
        - name: PORT
          value: "8000"
        - name: LOG_LEVEL
          value: "INFO"
        - name: HTTPX_TIMEOUT
          value: "5"
        - name: OPENWEATHER_API_KEY
          valueFrom:
            secretKeyRef:
              name: openweather-api
              key: API_KEY
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: $DEPLOYMENT_NAME-service
  namespace: $NAMESPACE
spec:
  selector:
    app: $DEPLOYMENT_NAME
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: $DEPLOYMENT_NAME-ingress
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: $DEPLOYMENT_NAME-service
            port:
              number: 80
EOF

# Apply the deployment
echo "Applying Kubernetes deployment..."
kubectl apply -f mcp-deploy-resolved.yaml

# Clean up the temporary file
rm mcp-deploy-resolved.yaml

echo "Deployment completed successfully!"
echo "To check the status of your deployment, run:"
echo "kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME"
echo "To get the ALB URL, run:"
echo "kubectl get ingress $DEPLOYMENT_NAME-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"

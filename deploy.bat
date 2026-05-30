@echo off
echo === Research Agent - Full Deployment ===

echo.
echo [1/5] Creating Kind cluster...
kind create cluster --name research-agent --config kind-config.yaml
if %ERRORLEVEL% NEQ 0 (
    echo Cluster may already exist, continuing...
)

echo.
echo [2/5] Building Docker image...
docker build -t research-agent:latest .

echo.
echo [3/5] Loading image into Kind...
kind load docker-image research-agent:latest --name research-agent

echo.
echo [4/5] Applying K8s manifests...
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

echo.
echo [5/5] Waiting for pod to be ready...
kubectl wait --for=condition=ready pod -l app=research-agent --timeout=120s

echo.
echo === Deployment Complete ===
echo Access the Research Agent at: http://localhost:8080
echo.
echo To check status: kubectl get pods -l app=research-agent
echo To view logs:    kubectl logs -l app=research-agent -f

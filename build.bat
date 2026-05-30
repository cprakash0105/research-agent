@echo off
echo === Building Research Agent Docker Image ===
docker build -t research-agent:latest .

echo === Loading Image into Kind Cluster ===
kind load docker-image research-agent:latest --name research-agent

echo === Done ===
echo Image loaded into Kind cluster successfully.

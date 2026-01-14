#!/bin/bash
# TokenMachine deployment script

set -e

echo "TokenMachine Deployment Script"
echo "=============================="

cd infra/docker
docker compose up -d

echo "Waiting for services to be ready..."
sleep 10

echo "Checking service status..."
docker compose ps

echo "Deployment complete!"
echo "API: http://localhost:8000"
echo "Web UI: http://localhost:8080"
echo "Grafana: http://localhost:3001"

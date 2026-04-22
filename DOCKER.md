# NeuralBook Docker Deployment

Complete Docker deployment guide for NeuralBook platform.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start the API server
docker-compose up -d api

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

Server runs at: `http://localhost:8000`

### Using Docker Directly

```bash
# Build image
docker build -t neuralbook:latest .

# Run container
docker run -d \
  --name neuralbook-api \
  -p 8000:8000 \
  -v neuralbook_data:/data \
  neuralbook:latest

# Test API
curl http://localhost:8000/health

# View logs
docker logs -f neuralbook-api

# Stop container
docker stop neuralbook-api
```

## Configuration

### Environment Variables

```bash
NEURALBOOK_HOST=0.0.0.0           # Server bind address
NEURALBOOK_PORT=8000               # Server port
NEURALBOOK_STORE_PATH=/data/store.json  # Data store location
PYTHONUNBUFFERED=1                 # Real-time logging
```

### Docker Compose Override

Create `docker-compose.override.yml`:

```yaml
services:
  api:
    environment:
      NEURALBOOK_PORT: 9000
    ports:
      - "9000:8000"
    volumes:
      - ./custom_data:/data
```

## Development Mode

### Interactive Development Container

```bash
# Start dev container
docker-compose run --rm dev bash

# Inside container:
# $ python examples/01_hello_world.py
# $ python -m pytest tests/ -v
# $ python examples/02_api_server.py
```

### Hot Reload Development

```bash
docker-compose up -d dev
docker-compose exec dev python examples/02_api_server.py --host 0.0.0.0 --port 8000
```

## Data Persistence

### Named Volume

```bash
# Create persistent volume
docker volume create neuralbook_data

# Run with volume
docker run -d \
  --name neuralbook-api \
  -p 8000:8000 \
  -v neuralbook_data:/data \
  neuralbook:latest

# Inspect volume
docker volume inspect neuralbook_data

# Backup volume
docker run --rm \
  -v neuralbook_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/neuralbook-data.tar.gz -C /data .

# Restore volume
docker run --rm \
  -v neuralbook_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/neuralbook-data.tar.gz -C /data
```

### Bind Mount

```bash
# Use local directory
docker run -d \
  --name neuralbook-api \
  -p 8000:8000 \
  -v $(pwd)/neuralbook_data:/data \
  neuralbook:latest
```

## Health Checks

The Docker image includes health checks:

```bash
# Manual health check
curl http://localhost:8000/health

# Docker healthcheck status
docker ps | grep neuralbook

# View healthcheck logs
docker inspect --format='{{json .State.Health}}' neuralbook-api | jq
```

## Production Deployment

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy service
docker service create \
  --name neuralbook-api \
  --publish 8000:8000 \
  --mount type=volume,source=neuralbook_data,target=/data \
  --restart-condition on-failure \
  neuralbook:latest

# View service status
docker service ps neuralbook-api

# Update service
docker service update \
  --image neuralbook:1.0.1 \
  neuralbook-api
```

### Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neuralbook-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: neuralbook-api
  template:
    metadata:
      labels:
        app: neuralbook-api
    spec:
      containers:
      - name: api
        image: neuralbook/neuralbook:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEURALBOOK_HOST
          value: "0.0.0.0"
        - name: NEURALBOOK_PORT
          value: "8000"
        volumeMounts:
        - name: data
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 2
          periodSeconds: 10
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: neuralbook-data

---
apiVersion: v1
kind: Service
metadata:
  name: neuralbook-api
spec:
  type: LoadBalancer
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: neuralbook-api

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: neuralbook-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
```

Deploy to Kubernetes:

```bash
kubectl apply -f deployment.yaml
kubectl get pods
kubectl logs -f deployment/neuralbook-api
```

## Networking

### Expose API

```bash
# Port mapping
docker run -d -p 8000:8000 neuralbook:latest

# Custom port
docker run -d -p 9000:8000 neuralbook:latest

# All interfaces
docker run -d -p 0.0.0.0:8000:8000 neuralbook:latest
```

### Multiple Instances

```bash
# Start multiple containers
for i in {1..3}; do
  docker run -d \
    --name neuralbook-api-$i \
    -p $((8000 + i)):8000 \
    neuralbook:latest
done

# Access via:
# http://localhost:8001
# http://localhost:8002
# http://localhost:8003
```

## Performance Tuning

### Resource Limits

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: 512M
        reservations:
          cpus: "0.5"
          memory: 256M
```

### Caching Strategy

```bash
# Multi-stage build reduces image size
docker build --target builder -t neuralbook:builder .
docker build -t neuralbook:optimized .

# Check image size
docker images neuralbook

# Use slim base image
# FROM python:3.13-slim (used in Dockerfile)
```

## Troubleshooting

### Container won't start

```bash
# View logs
docker logs neuralbook-api

# Inspect container
docker inspect neuralbook-api

# Run with interactive shell
docker run -it neuralbook:latest bash
```

### Health check failing

```bash
# Manual test
docker exec neuralbook-api curl http://localhost:8000/health

# Check endpoint
docker exec neuralbook-api python -c "
import requests
resp = requests.get('http://localhost:8000/health')
print(resp.json())
"
```

### Data persistence issues

```bash
# Check volume mount
docker inspect neuralbook-api | grep Mounts

# Verify data exists
docker exec neuralbook-api ls -la /data/

# Check file permissions
docker exec neuralbook-api stat /data/store.json
```

### Out of disk space

```bash
# Clean up stopped containers
docker container prune -f

# Remove unused volumes
docker volume prune -f

# Remove unused images
docker image prune -a -f

# Check disk usage
docker system df
```

## Security

### Run as non-root user

```dockerfile
# In Dockerfile
RUN useradd -m -u 1000 neuralbook
USER neuralbook
```

### Secrets management

```bash
# Docker secrets (Swarm)
echo "secret_key_value" | docker secret create neuralbook_key -

# Kubernetes secrets
kubectl create secret generic neuralbook-secrets \
  --from-literal=api-key=secret-value

# Environment file (development only)
docker run --env-file .env neuralbook:latest
```

### Network isolation

```yaml
services:
  api:
    networks:
      - neuralbook
    expose:  # Internal only
      - 8000
    ports:  # External access
      - "8000:8000"

networks:
  neuralbook:
    driver: bridge
```

## Monitoring

### Container metrics

```bash
# CPU and memory
docker stats neuralbook-api

# Network traffic
docker stats --no-stream

# Event logs
docker events --filter 'container=neuralbook-api'
```

### Prometheus metrics

```yaml
# With monitoring
docker run -d \
  --name neuralbook-api \
  -p 8000:8000 \
  -e NEURALBOOK_METRICS=true \
  neuralbook:latest

# Scrape metrics
curl http://localhost:8000/metrics
```

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [NeuralBook Examples](../examples/)
- [NeuralBook Docs](../docs/)

---

**Questions?** See [../README.md](../README.md) or open an issue on GitHub.

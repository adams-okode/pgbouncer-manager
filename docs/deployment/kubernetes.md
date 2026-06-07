# Kubernetes Deployment

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer-manager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pgbouncer-manager
  template:
    metadata:
      labels:
        app: pgbouncer-manager
    spec:
      containers:
      - name: pgbouncer-manager
        image: predicta/pgbouncer-manager:latest
        ports:
        - containerPort: 3000
        env:
        - name: CONFIG_DIR
          value: "/app/config"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
      volumes:
      - name: config
        configMap:
          name: pgbouncer-config
```

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: pgbouncer-manager
spec:
  selector:
    app: pgbouncer-manager
  ports:
  - port: 3000
    targetPort: 3000
```

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pgbouncer-manager
spec:
  rules:
  - host: pgbouncer-manager.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pgbouncer-manager
            port:
              number: 3000
```

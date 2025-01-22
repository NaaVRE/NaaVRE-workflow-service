# NaaVRE-workflow-service

## Running locally

Create conda environment:

```shell
conda env create -f environment.yaml
```

Activate the environment:

```shell
conda activate naavre-workflow-service
```

Run the dev server

```shell
fastapi dev app/main.py
```

## Build Docker image

```shell
docker build . -f docker/Dockerfile -t naavre-workflow-service:dev
```

To run it:

```shell
docker run -p 127.0.0.1:8000:8000 naavre-workflow-service:dev
```

and open http://127.0.0.1:8000/docs

## Deployment

We use Helm for the deployment:

```shell
helm -n naavre-workflow-service upgrade --install --create-namespace naavre-workflow-service ./helm/naavre-workflow-service -f values.yaml
```

`values.yaml` should contain ingress, OAuth2, and other configuration (
checkout [./helm/naavre-workflow-service/values-example.yaml](./helm/naavre-workflow-service/values-example.yaml)).

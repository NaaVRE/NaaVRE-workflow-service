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

# Test on GitHub

The secrets.CONFIG_FILE should have quotes escaped:

```commandline
{  \"vl_configurations\": [    {      \"name\": \"virtual_lab_1\",      \"wf_engine_config\": {        \"name\": \"argo\",        \"api_endpoint\": \"https://naavre-dev.minikube.test/argowf/\",        \"access_token\": \"eyJhbGciOg...\",        \"service_account\": \"executor\",        \"namespace\": \"default\",        \"workdir_storage_size\": \"1Gi\"      }    },    {      \"name\": \"virtual_lab_2\",      \"wf_engine_config\": {        \"name\": \"argo\",        \"api_endpoint\": \"https://my-argo.example.com/argowf/\",        \"access_token\": \"eyJhbGciOg...\",        \"service_account\": \"executor\",        \"namespace\": \"argo\",        \"workdir_storage_size\": \"1Gi\"      }    }  ]}
```

You can run the following command to generate the secrets.CONFIG_FILE:

```shell
tr -d '\n' < configuration.json | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
```
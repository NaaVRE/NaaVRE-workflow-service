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


## Testing
To run the you first need to start a Minikube cluster:

```shell
minikube start --addons=ingress,ingress-dns,metrics-server
```

Then you need to download the test script and make it executable:

```shell
wget https://raw.githubusercontent.com/NaaVRE/NaaVRE-helm/refs/heads/main/scripts/setup-tests.sh
chmod +x setup-tests.sh
```

Finally, you can run the tests:

```shell
./setup-tests.sh -f values-deploy-naavre-workflow-service-minikube-github.yaml -d -n -u -p -v
```

### Adding new tests
To add a new test workflow follow these steps:
1. Start a NaaVRE instance. This can be from the Minikube cluster at https://naavre-dev.minikube.test/vreapp or any other instance.
2. Create a new notebook with the cells that you want to test
3. Containerize the cells 
4. Build the workflow
5. Then in the app/tests/resources/ directory, create a new directory for your workflow
6. Copy the notebook, and workflow to this directory. Make sure they are named `notebook.ipynb` and `wf.naavrewf` respectively.
7. Add a `wf_payload.json`. You can copy it from an existing folder. 
8. If your workflow contains `params`, `secrets` or cron schedule, make sure to update the `wf_payload.json` accordingly.
9. If your tests have specific HTTP return codes should add a file named `responses.json` with the expected response. If this file is not present, the test will expect a 200 status code. Look at app/tests/resources/py_lint/ for an example of this file.

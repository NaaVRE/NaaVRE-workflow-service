# Variables
MINIKUBE_HOST="minikube.local"
AUTH_TOKEN=""
ARGO_TOKEN=""
OIDC_CONFIGURATION_URL="https://$MINIKUBE_HOST/auth/realms/vre/.well-known/openid-configuration"
echo "OIDC_CONFIGURATION_URL=https://$MINIKUBE_HOST/auth/realms/vre/.well-known/openid-configuration" >> $GITHUB_ENV
VERIFY_SSL="False"
echo "VERIFY_SSL=False" >> $GITHUB_ENV
DISABLE_AUTH="False"
echo "DISABLE_AUTH=False" >> $GITHUB_ENV
CONFIG_FILE_URL="minkube_configuration.json"
echo "CONFIG_FILE_URL=NaaVRE-workflow-service/minkube_configuration.json" >> $GITHUB_ENV
SECRETS_CREATOR_API_ENDPOINT="https://$MINIKUBE_HOST/k8s-secret-creator/1.0.0"
echo "SECRETS_CREATOR_API_ENDPOINT=https://$MINIKUBE_HOST/k8s-secret-creator/1.0.0" >> $GITHUB_ENV
SECRETS_CREATOR_API_TOKEN="SECRETS_CREATOR_API_TOKEN"
echo "SECRETS_CREATOR_API_TOKEN=SECRETS_CREATOR_API_TOKEN" >> $GITHUB_ENV

#Get the minikube IP and add it to /etc/hosts if not already present
MINIKUBE_IP=$(minikube ip)
if ! grep -q "$MINIKUBE_IP" /etc/hosts; then
    echo "Adding minikube IP to /etc/hosts"
    echo "$MINIKUBE_IP $MINIKUBE_HOST" | sudo tee -a /etc/hosts > /dev/null
else
    echo "Minikube IP already present in /etc/hosts"
fi

# Test $MINIKUBE_HOST
if ! curl -k https://$MINIKUBE_HOST | grep '<head><title>404 Not Found</title></head>'; then
    echo "Minikube local test failed"
    exit 1
else
    echo "Minikube local test passed"
fi


# Add the third-party Helm repos
helm repo add argo https://argoproj.github.io/argo-helm
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
helm repo add bitnami https://charts.bitnami.com/bitnami


#Install argo workflows from NaaVRE-helm
git clone https://github.com/NaaVRE/NaaVRE-helm.git
cd NaaVRE-helm
git checkout 24-add-testing-against-argo-running-in-minikube
helm dependency update naavre
helm dependency build naavre
context="naavreWorkflowService-minikube-github"
namespace="naavre"
release_name="naavre"
helm template "$release_name" values/ --output-dir values/rendered -f "./values/values-deploy-$context.yaml" && \
helm -n "$namespace" upgrade --create-namespace --install "$release_name" naavre/ $(find values/rendered/values/templates -type f | xargs -I{} echo -n " -f {}")
cd ../


#Get user access token for the workflow service and set the environment variable AUTH_TOKEN
echo "Getting access token for the workflow service"
curl -k -X POST https://$MINIKUBE_HOST/auth/realms/vre/protocol/openid-connect/token   \
  -H "Content-Type: application/x-www-form-urlencoded"   -d "grant_type=password"   \
  -d "client_id=naavre"   -d "username=my-user"   -d "password=USER_PASSWORD"   -d "scope=openid" | jq -r '.access_token' > auth_token.txt
echo "Setting the AUTH_TOKEN environment variable"
AUTH_TOKEN=$(cat auth_token.txt)
echo "AUTH_TOKEN=$(cat auth_token.txt)" >> $GITHUB_ENV


#Get Argo workflow summation token and set it to configuration.json
echo "Getting Argo workflow submission token"
ARGO_TOKEN=`kubectl get secret  argo-vreapi.service-account-token -o=jsonpath='{.data.token}' -n naavre  | base64 --decode`
jq --arg token "$ARGO_TOKEN" '.vl_configurations |= map(if .name == "virtual_lab_1" then .wf_engine_config.access_token = $token else . end)' configuration.json > tmp.json && mv tmp.json minkube_configuration.json



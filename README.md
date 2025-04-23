# Microservice Application Example - DevOps Overview

This project demonstrates a typical microservices architecture deployed to Azure Kubernetes Service (AKS) using Azure Pipelines for Continuous Integration and Continuous Deployment (CI/CD). This README focuses on the DevOps workflow, pipeline configuration, and Kubernetes setup.

## Architecture

The application consists of several microservices:
*   **Frontend:** Vue.js single-page application served via Nginx.
*   **Auth API:** Handles user authentication (Go).
*   **Users API:** Manages user data (Java Spring Boot).
*   **Todos API:** Manages todo items (Node.js Express).
*   **Log Message Processor:** Processes log messages (Python).

These services communicate with each other and potentially external services like Redis (for session/cache, managed via secrets).

![Microservices Architecture Diagram](arch-img/Microservices.png)

## DevOps Workflow: CI/CD with Azure Pipelines & AKS

The core of the DevOps process is defined in `azure-pipelines.yml`. It automates the building, testing (implicitly via build success), and deployment of the microservices to AKS based on changes pushed to the `dev` or `master` branches.

### Prerequisites

To run this pipeline and deploy the application, you need:

1.  **Azure DevOps Project:** Where the repository and pipeline reside.
2.  **Azure Subscription:** Containing the necessary Azure resources.
3.  **Azure Container Registry (ACR):** To store the built Docker images.
4.  **Azure Kubernetes Service (AKS):** The target cluster for deployment.
5.  **Service Connections in Azure DevOps:**
    *   `ACR-Service-Connection` : Connects Azure DevOps to your ACR for pushing images. Requires appropriate permissions .
    *   `aks-prod-microAppProd-prod-pheasant-aks-apps-prod-1745099156012`: Connects Azure DevOps to your AKS cluster for deploying manifests. Requires appropriate permissions.
6.  **Variable Groups in Azure DevOps Library:**
    *   `app-variables-dev`: Contains variables for the `dev` environment.
    *   `app-variables-prod`: Contains variables for the `prod` environment.
    *   **Required Variables in each group:**
        *   `acrName`: The name of your Azure Container Registry (e.g., `myregistry.azurecr.io`).
        *   `redisHostName`: The hostname/address of the Redis instance.
        *   `redisPrimaryKey`: The access key/password for Redis. (Mark as secret)
        *   `jwtSecretValue`: The secret key used for JWT signing/validation. (Mark as secret)

### Azure Pipeline (`azure-pipelines.yml`) Breakdown

The pipeline is structured into two main stages:

**Stage 1: `BuildAndPush` (Build & Push Changed Images)**

*   **Trigger:** Runs on pushes to `dev` or `master` branches *only* if changes occur within the service directories (`auth-api/`, `users-api/`, etc.), `k8s/`, or the pipeline file itself (excluding `.md` files).
*   **Environment Detection:** Determines the target environment (`dev` or `prod`) based on the source branch (`Build.SourceBranchName`). This selects the correct variable group (`app-variables-dev` or `app-variables-prod`).
*   **Matrix Strategy:** Defines a job for each microservice (`AuthApi`, `UsersApi`, etc.) to allow parallel execution and specific configurations.
*   **Change Detection:**
    *   Checks out the full Git history (`fetchDepth: 0`).
    *   Uses `git diff HEAD~1 HEAD -- <service_directory>/` to compare the current commit with its direct parent.
    *   Sets a pipeline variable (`DetectChanges.ShouldBuild`) to `true` or `false` for each service based on whether changes were detected in its specific directory.
*   **Conditional Build & Push:**
    *   The `Docker@2` task runs *only if* the corresponding `DetectChanges.ShouldBuild` variable is `true`.
    *   Builds the Docker image using the `Dockerfile` within the service's directory.
    *   Pushes the image to the specified ACR (`$(acrName)` from the variable group) and tags it with the unique `$(Build.BuildId)`.

**Stage 2: `DeployToAKS` (Deploy Applications to AKS)**

*   **Dependency & Condition:** Runs only after `BuildAndPush` succeeds (or is skipped) and only for `dev` or `master` branches.
*   **Environment Targeting:** Uses an Azure DevOps Environment (`aks-$(environment)`) for deployment tracking and approvals .
*   **Deployment Strategy:** `runOnce` deploys all steps sequentially.
*   **Steps:**
    1.  **Checkout:** Gets the `k8s/` manifests.
    2.  **Replace Tokens:** Uses the `replacetokens@5` task to find placeholders like `#{Build.BuildId}#`, `#{k8sNamespace}#`, `#{acrName}#` in the `.yaml` files within the `k8s/` directory and replaces them with the actual values from pipeline variables (e.g., the current build ID as the image tag, the target namespace like `apps-dev`).
    3.  **Ensure Namespace:** Applies `k8s/namespace.yaml` using `KubernetesManifest@0` to create or update the target Kubernetes namespace (`apps-dev` or `apps-prod`).
    4.  **Create/Update Secrets:** Uses `KubernetesManifest@0` with `action: createSecret` to securely create/update Kubernetes secrets:
        *   `redis-secret`: Stores Redis connection details (`redisHost`, `redisKey`) fetched from the variable group.
        *   `app-secrets`: Stores the JWT secret (`jwtSecret`) fetched from the variable group. `force: true` ensures secrets are updated if they already exist.
    5.  **Apply ConfigMap:** Applies `k8s/app-configmap.yaml` to provide non-sensitive configuration to the applications.
    6.  **Prepare Deployment Flags:** A Bash script reads the `ShouldBuild` output variables from *each* job in the `BuildAndPush` stage. It sets new variables (`DeployAuthApi`, `DeployUsersApi`, etc.) to `true` only for services that were actually rebuilt in the previous stage.
    7.  **Conditional Manifest Application:** Uses `KubernetesManifest@1` tasks with conditions (`condition: eq(variables['Deploy<ServiceName>'], 'true')`). Each task applies the corresponding `deployment.yaml` and `service.yaml` files *only* if that specific service was rebuilt. This prevents unnecessary rollouts for unchanged services.
    8.  **Wait & Verify:** Uses `Kubernetes@1` tasks:
        *   `kubectl wait deployment --all --for=condition=available`: Waits for all deployments in the namespace to report as available (up to a timeout).
        *   `kubectl get deployment`, `kubectl get pods`, `kubectl get svc`: Lists the deployed resources to provide visibility in the pipeline logs.

### Kubernetes Configuration (`k8s/` directory)

This directory contains the Kubernetes manifest files (YAML blueprints) describing the desired state of the application in the cluster.

*   **`namespace.yaml`:** Defines the Kubernetes namespaces (`apps-dev`, `apps-prod`) to isolate environments.
*   **`*-deployment.yaml`:** Defines the Deployment resource for each microservice. It specifies:
    *   The Docker image to use (including the ACR name `#{acrName}#` and image tag `#{Build.BuildId}#` replaced by the pipeline).
    *   The number of replicas (pods).
    *   Environment variables, potentially referencing the ConfigMap (`app-configmap.yaml`) and Secrets (`app-secrets`, `redis-secret`).
    *   Update strategy (e.g., RollingUpdate).
*   **`*-service.yaml`:** Defines the Service resource for each microservice. It provides a stable internal IP address and DNS name for pods within the cluster, allowing services to discover and communicate with each other. For the `frontend`, it might be of type `LoadBalancer`.
*   **`app-configmap.yaml`:** Defines a ConfigMap resource holding non-sensitive configuration data (like API URLs) that can be mounted or injected as environment variables into the pods.

### How to Run

1.  Ensure all prerequisites (Azure resources, Service Connections, Variable Groups with correct variables) are set up.
2.  Import the `azure-pipelines.yml` file into Azure Pipelines within your Azure DevOps project.
3.  Push a change to one of the service directories (e.g., `todos-api/`) on the `dev` branch.
4.  Observe the pipeline run:
    *   The `BuildAndPush` stage should detect the change only in the `todos-api` job.
    *   Only the `todos-api` Docker image should be built and pushed.
    *   The `DeployToAKS` stage should run.
    *   Tokens will be replaced in all manifests.
    *   Namespace, Secrets, and ConfigMap will be applied.
    *   *Only* the `todos-api-deployment.yaml` and `todos-api-service.yaml` manifests should be applied due to the conditional deployment logic.
    *   The pipeline will wait for the `todos-api` deployment to become available.

## Key Concepts & Decisions

*   **Infrastructure as Code (IaC):** Kubernetes manifests (`k8s/*.yaml`) define the desired infrastructure state declaratively.
*   **GitOps (Principles):** The Git repository is the source of truth. Changes merged to `dev`/`master` trigger automated deployments.
*   **Environment Separation:** Using branches (`dev`/`master`), namespaces (`apps-dev`/`apps-prod`), and variable groups to manage different deployment environments.
*   **Efficiency:** Conditional building and deployment based on actual code changes significantly speeds up the pipeline and reduces unnecessary resource churn in AKS, especially for projects with many microservices.
*   **Secrets Management:** Leveraging Azure DevOps Variable Groups (marked as secret) and Kubernetes Secrets ensures sensitive data is not hardcoded in the repository or pipeline definition.
*   **Tokenization:** Using `replacetokens` provides a flexible way to inject dynamic values (like image tags, registry names, namespaces) into Kubernetes manifests at deployment time.
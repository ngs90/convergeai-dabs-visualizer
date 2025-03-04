Databricks Asset Bundle Visualizer

# Requirements


Install PlantUML: `choco install plantuml`
Install Mermaid: `npm install -g @mermaid-js/mermaid-cli`

### How to run 

Generate puml and .png files using PlantUML:
`python "src/dabsVisualizer.py" -i "example/databricks.yml" -o "example/dabs_visualization.png" -t plantuml`

Generate mmd files using Mermaid: 
`python "src/dabsVisualizer.py" -i "example/databricks.yml" -o "example/dabs_visualization.png" -t mermaid`
The .mmd files can be inserted directly into markdown and be rendered on i.e. GitHub.

### PlantUML example (exported as .png): 

<!-- ![image info](./example/dabs_visualization.png) -->

![image info](./example-advanced/figures/dabs_visualization_dev.png)


### Mermaid example (rendered directly in markdown): 
```mermaid 
---
title mlops_stacks (dev mode development)
host https://adb-xxxx.xx.azuredatabricks.net
---
flowchart LR
    %% Custom style definitions
    classDef jobNode fill:#2C3E50,color:#FFFFFF,stroke:#1A5276,stroke-width:2px;
    classDef workflowNode fill:#34495E,color:#ECF0F1,stroke:#2980B9,stroke-width:1px;
    classDef taskNode fill:#5D6D7E,color:#FFFFFF,stroke:#2874A6,stroke-width:1px;
    classDef clusterNode fill:#7F8C8D,color:#FFFFFF,stroke:#566573,stroke-width:1px;
    classDef paramNode fill:#566573,color:#E5E7E9,stroke:#2C3E50,stroke-dasharray:5;

    subgraph dev[" dev Environment "]
    direction TB

    subgraph Jobs
    direction TB
    batch_inference_job("dev-mlops_stacks-batch-inference-job  Notify on_failure: first@company.com, second@company.com"):::jobNode
    subgraph Workflow_batch_inference_job[Workflow]
    direction TB
    batch_inference_job("batch_inference_job (Notebook Task)"):::taskNode
    batch_inference_job_params("Parameters: env, input_table_name, output_table_name, model_name, git_source_info"):::paramNode
    batch_inference_job --> batch_inference_job_params
    end
    cluster_batch_inference_job("Cluster: batch_inference_job_cluster Spark: 13.3.x-cpu-ml-scala2.12 Nodes: m7g.large Runtime: "):::clusterNode
    batch_inference_job --> cluster_batch_inference_job
    batch_inference_job --> Workflow_batch_inference_job
    model_training_job("dev-mlops_stacks-model-training-job "):::jobNode
    subgraph Workflow_model_training_job[Workflow]
    direction TB
    Train("Train (Notebook Task)"):::taskNode
    Train_params("Parameters: env, training_data_path, experiment_name, model_name, git_source_info"):::paramNode
    Train --> Train_params
    ModelValidation("ModelValidation (Notebook Task)"):::taskNode
    ModelValidation_params("Parameters: experiment_name, run_mode, enable_baseline_comparison, validation_input, model_type, targets, custom_metrics_loader_function, validation_thresholds_loader_function, evaluator_config_loader_function, git_source_info"):::paramNode
    ModelValidation --> ModelValidation_params
    ModelDeployment("ModelDeployment (Notebook Task)"):::taskNode
    ModelDeployment_params("Parameters: env, git_source_info"):::paramNode
    ModelDeployment --> ModelDeployment_params
    Train --> ModelValidation
    ModelValidation --> ModelDeployment
    end
    cluster_model_training_job("Cluster: model_training_job_cluster Spark: 13.3.x-cpu-ml-scala2.12 Nodes: Standard_D3_v2 Runtime: "):::clusterNode
    model_training_job --> cluster_model_training_job
    model_training_job --> Workflow_model_training_job
    end
    end
```
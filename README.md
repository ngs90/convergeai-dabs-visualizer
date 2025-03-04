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
    classDef default fill:#f9f,stroke:#333,stroke-width:2px;

    subgraph dev[" "]
    direction LR

    subgraph Jobs
    direction LR
    batch_inference_job["dev-mlops_stacks-batch-inference-job\n\nnotify on_failure: first@company.com, second@company.com"]
    subgraph Workflow_batch_inference_job[Workflow]
    direction LR
    batch_inference_job["batch_inference_job (notebook)"]
    batch_inference_job_params["env\ninput_table_name\noutput_table_name\nmodel_name\ngit_source_info"]
    batch_inference_job --> batch_inference_job_params
    end
    cluster_batch_inference_job["Cluster: batch_inference_job_cluster\n13.3.x-cpu-ml-scala2.12, m7g.large, "]
    batch_inference_job --> cluster_batch_inference_job
    batch_inference_job --> Workflow_batch_inference_job
    model_training_job["dev-mlops_stacks-model-training-job\n"]
    subgraph Workflow_model_training_job[Workflow]
    direction LR
    Train["Train (notebook)"]
    Train_params["env\ntraining_data_path\nexperiment_name\nmodel_name\ngit_source_info"]
    Train --> Train_params
    ModelValidation["ModelValidation (notebook)"]
    ModelValidation_params["experiment_name\nrun_mode\nenable_baseline_comparison\nvalidation_input\nmodel_type\ntargets\ncustom_metrics_loader_function\nvalidation_thresholds_loader_function\nevaluator_config_loader_function\ngit_source_info"]
    ModelValidation --> ModelValidation_params
    ModelDeployment["ModelDeployment (notebook)"]
    ModelDeployment_params["env\ngit_source_info"]
    ModelDeployment --> ModelDeployment_params
    Train --> ModelValidation
    ModelValidation --> ModelDeployment
    end
    cluster_model_training_job["Cluster: model_training_job_cluster\n13.3.x-cpu-ml-scala2.12, Standard_D3_v2, "]
    model_training_job --> cluster_model_training_job
    model_training_job --> Workflow_model_training_job
    end
    end
```
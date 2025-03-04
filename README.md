Databricks Asset Bundle Visualizer

### How to run 

`python "src/dabsVisualizer.py" -i "example/databricks.yml" -o "example/dabs_visualization.png"`

### Example 

![image info](./example/dabs_visualization.png)


# mermaid example 
```mermaid 
---
title: mlops_stacks - dev (mode: development)
---
graph TD
    job_batch_inference_job["dev-mlops_stacks-batch-inference-job\nNotify on_failure: first@company.com, second@company.com"]
    task_batch_inference_job_batch_inference_job["batch_inference_job (notebook)"]
    job_batch_inference_job --> task_batch_inference_job_batch_inference_job
    params_batch_inference_job_batch_inference_job["env\ninput_table_name\noutput_table_name\nmodel_name\ngit_source_info"]
    task_batch_inference_job_batch_inference_job --> params_batch_inference_job_batch_inference_job
    cluster_batch_inference_job["Cluster: batch_inference_job_cluster\n13.3.x-cpu-ml-scala2.12, m7g.large, "]
    job_batch_inference_job --> cluster_batch_inference_job
    job_model_training_job["dev-mlops_stacks-model-training-job"]
    task_model_training_job_Train["Train (notebook)"]
    job_model_training_job --> task_model_training_job_Train
    params_model_training_job_Train["env\ntraining_data_path\nexperiment_name\nmodel_name\ngit_source_info"]
    task_model_training_job_Train --> params_model_training_job_Train
    task_model_training_job_ModelValidation["ModelValidation (notebook)"]
    job_model_training_job --> task_model_training_job_ModelValidation
    task_model_training_job_Train --> task_model_training_job_ModelValidation
    params_model_training_job_ModelValidation["experiment_name\nrun_mode\nenable_baseline_comparison\nvalidation_input\nmodel_type\ntargets\ncustom_metrics_loader_function\nvalidation_thresholds_loader_function\nevaluator_config_loader_function\ngit_source_info"]
    task_model_training_job_ModelValidation --> params_model_training_job_ModelValidation
    task_model_training_job_ModelDeployment["ModelDeployment (notebook)"]
    job_model_training_job --> task_model_training_job_ModelDeployment
    task_model_training_job_ModelValidation --> task_model_training_job_ModelDeployment
    params_model_training_job_ModelDeployment["env\ngit_source_info"]
    task_model_training_job_ModelDeployment --> params_model_training_job_ModelDeployment
    cluster_model_training_job["Cluster: model_training_job_cluster\n13.3.x-cpu-ml-scala2.12, Standard_D3_v2, "]
    job_model_training_job --> cluster_model_training_job
```
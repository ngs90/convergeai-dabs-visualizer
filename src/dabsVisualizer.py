#!/usr/bin/env python3
"""
dabsVisualizer: A CLI tool to generate UML diagrams from Databricks YAML asset bundle definitions.

Changes from the previous version:
- Added support for Mermaid as an alternative diagram generation language
- Added --type parameter to choose between PlantUML and Mermaid diagram generation
- Default diagram type is now Mermaid
"""

import sys
import yaml
import glob
import os
import argparse
import subprocess
import tempfile
import shutil
import json

def load_bundle_yaml(main_yaml_path):
    """
    Loads the main databricks.yml file, extracts the bundle name and targets,
    and then loads all YAML resource files specified in the 'include' list.
    Merges resource definitions into one dictionary (e.g. all_resources["jobs"]).
    
    For resource type "jobs", if the same job key appears in more than one file,
    then its "tasks" and "job_clusters" arrays are merged (with duplicate clusters eliminated).
    """
    with open(main_yaml_path, "r", encoding="utf-8") as f:
        bundle_data = yaml.safe_load(f)
    
    bundle_name = bundle_data.get("bundle", {}).get("name", "unknown_bundle")
    targets = bundle_data.get("targets", {})
    variables = bundle_data.get("variables", {})
    all_resources = {}
    
    main_dir = os.path.dirname(os.path.abspath(main_yaml_path))
    include_patterns = bundle_data.get("include", [])
    
    for pattern in include_patterns:
        pattern_path = os.path.join(main_dir, pattern)
        for resource_file in glob.glob(pattern_path):
            try:
                with open(resource_file, "r", encoding="utf-8") as rf:
                    resource_yaml = yaml.safe_load(rf)
                if not resource_yaml:
                    continue

                resources = resource_yaml.get("resources", {})
                for resource_type, items in resources.items():
                    if resource_type not in all_resources:
                        all_resources[resource_type] = {}
                    for key, value in items.items():
                        # For jobs, merge definitions if key already exists.
                        if resource_type == "jobs" and key in all_resources[resource_type]:
                            existing = all_resources[resource_type][key]
                            # Merge tasks: extend list if tasks exist
                            if "tasks" in value:
                                if "tasks" not in existing:
                                    existing["tasks"] = []
                                existing["tasks"].extend(value["tasks"])
                            # Merge job_clusters: add unique clusters by job_cluster_key
                            if "job_clusters" in value:
                                if "job_clusters" not in existing:
                                    existing["job_clusters"] = []
                                for new_cluster in value["job_clusters"]:
                                    new_key = new_cluster.get("job_cluster_key")
                                    duplicate = False
                                    for existing_cluster in existing["job_clusters"]:
                                        if existing_cluster.get("job_cluster_key") == new_key:
                                            duplicate = True
                                            break
                                    if not duplicate:
                                        existing["job_clusters"].append(new_cluster)
                            # Optionally, merge other fields if needed.
                        else:
                            all_resources[resource_type][key] = value
            except Exception as e:
                print(f"[WARNING] Failed to load {resource_file}: {e}")
    return bundle_name, all_resources, targets, variables

def build_plantuml_for_target(bundle_name, resources, target_name, target_data):
    """
    Builds a PlantUML diagram (as text) for a single environment/target.
    """
    target_mode = target_data.get("mode", "unknown")
    workspace = target_data.get("workspace", {})
    workspace_host = workspace.get("host", "unknown")

    # We'll create a diagram that focuses solely on this environment.
    lines = []
    lines.append("@startuml")
    lines.append("!theme plain")

    # Label with environment details
    target_label = f'{target_name} (mode: {target_mode})\\n(host: {workspace_host})'
    # Top-level package for this environment
    lines.append(f'package "{bundle_name} - {target_label}" {{')

    # If there are jobs, render them
    if "jobs" in resources:
        # A subpackage for all jobs in this environment
        lines.append(f'  package "Jobs" as Jobs_{target_name} {{')
        
        # For each job in the merged resources
        for job_id, job_data in resources["jobs"].items():
            # Build job label with triggers, notifications
            job_name = job_data.get("name", job_id)

            # Trigger info
            trigger_str = ""
            trigger_def = job_data.get("trigger", {})
            if "periodic" in trigger_def:
                interval = trigger_def["periodic"].get("interval", "")
                unit = trigger_def["periodic"].get("unit", "")
                trigger_str = f'\\ntrigger: periodic ({interval} {unit})'

            # Notifications
            email_notifications = job_data.get("email_notifications", {})
            notify_str = ""
            for notif_type, recipients in email_notifications.items():
                notify_str += f'\\nnotify {notif_type}: {", ".join(recipients)}'

            job_label = f'{job_name}{trigger_str}{notify_str}'
            job_alias = f'jobs_{job_id}_{target_name}'
            lines.append(f'    rectangle "{job_label}" as {job_alias}')

            # Workflow subpackage for tasks
            workflow_alias = f'Workflow_{job_id}_{target_name}'
            lines.append(f'    package "Workflow" as {workflow_alias} {{')
            lines.append(f'      {job_alias} --> {workflow_alias} : contains')

            # Show tasks
            tasks = job_data.get("tasks", [])
            for task in tasks:
                task_key = task.get("task_key")
                if not task_key:
                    continue
                task_alias = f'task_{job_id}_{task_key}_{target_name}'
                if "notebook_task" in task:
                    task_label = f'{task_key}\\n(notebook)'
                elif "python_wheel_task" in task:
                    task_label = f'{task_key}\\n(python_wheel)'
                else:
                    task_label = task_key
                lines.append(f'      package "{task_label}" as {task_alias} {{')
                depends_on = task.get("depends_on", [])
                for dep_item in depends_on:
                    dep_key = dep_item.get("task_key")
                    if dep_key:
                        dep_alias = f'task_{job_id}_{dep_key}_{target_name}'
                        lines.append(f'      {dep_alias} --> {task_alias} : depends on')
                
                base_parameters = task.get("notebook_task", {}).get("base_parameters", {})
                if base_parameters:
                    parameter_alias = f'parameters_{task_alias}'
                    param_vals = ""
                    for param, val in base_parameters.items():
                        param_vals += f"{param}\\n"
                    param_vals = param_vals.strip()
                    
                    lines.append(f'        rectangle "{param_vals}" as {param}_{parameter_alias}')
                lines.append("      }") # end Task

            lines.append("    }")  # end Workflow

            # Clusters for this job
            job_clusters = job_data.get("job_clusters", [])
            for cluster in job_clusters:
                cluster_key = cluster.get("job_cluster_key")
                if cluster_key:
                    new_cluster = cluster.get("new_cluster", {})
                    spark_version = new_cluster.get("spark_version", "")
                    node_type_id = new_cluster.get("node_type_id", "")
                    runtime_engine = new_cluster.get("runtime_engine", "")
                    cluster_label = (
                        f'Cluster: {cluster_key}\\n'
                        f'{spark_version}, {node_type_id}, {runtime_engine}'
                    )
                    cluster_alias = f'job_cluster_{job_id}_{cluster_key}_{target_name}'
                    lines.append(f'    rectangle "{cluster_label}" as {cluster_alias}')
                    lines.append(f'    {job_alias} --> {cluster_alias} : uses')

        lines.append("  }")  # end Jobs_{target_name}

    lines.append("}")  # end top-level package for this environment
    lines.append("@enduml")
    return "\n".join(lines)
def build_mermaid_for_target(bundle_name, resources, target_name, target_data):
    """
    Builds a Mermaid diagram (as text) for a single environment/target,
    mimicking the structure of the provided PlantUML diagram.
    """
    target_mode = target_data.get("mode", "unknown")
    workspace = target_data.get("workspace", {})
    workspace_host = workspace.get("host", "unknown")

    # Start the Mermaid diagram
    lines = []
    lines.append("---")
    lines.append(f"title {bundle_name} ({target_name} mode {target_mode})")
    lines.append(f"host {workspace_host}")
    lines.append("---")
    lines.append("flowchart LR")
    lines.append("    classDef default fill:#f9f,stroke:#333,stroke-width:2px;")
    lines.append("")
    
    # Create the main container for the environment
    lines.append(f"    subgraph {target_name}[\" \"]")
    lines.append("    direction LR")
    lines.append("")
    
    # Jobs subgraph
    lines.append("    subgraph Jobs")
    lines.append("    direction LR")
    
    if "jobs" in resources:
        for job_id, job_data in resources["jobs"].items():
            job_name = job_data.get("name", job_id)
            job_id_safe = job_id.replace("-", "_")

            # Trigger and notification information
            trigger_str = ""
            trigger_def = job_data.get("trigger", {})
            if "periodic" in trigger_def:
                interval = trigger_def["periodic"].get("interval", "")
                unit = trigger_def["periodic"].get("unit", "")
                trigger_str = f"trigger: periodic ({interval} {unit})"

            # Notifications
            email_notifications = job_data.get("email_notifications", {})
            notify_str = ""
            for notif_type, recipients in email_notifications.items():
                notify_str += f"\\nnotify {notif_type}: {', '.join(recipients)}"

            # Job node
            job_label = f"{job_name}\\n{trigger_str}{notify_str}"
            lines.append(f'    {job_id_safe}["{job_label}"]')

            # Workflow subgraph
            lines.append(f"    subgraph Workflow_{job_id_safe}[Workflow]")
            lines.append("    direction LR")

            # Tasks
            tasks = job_data.get("tasks", [])
            task_nodes = []
            for task in tasks:
                task_key = task.get("task_key")
                if not task_key:
                    continue
                task_key_safe = task_key.replace("-", "_")

                # Determine task type
                if "notebook_task" in task:
                    task_label = f"{task_key} (notebook)"
                elif "python_wheel_task" in task:
                    task_label = f"{task_key} (python_wheel)"
                else:
                    task_label = task_key

                # Task node
                task_nodes.append(task_key_safe)
                lines.append(f'    {task_key_safe}["{task_label}"]')

                # Base parameters
                base_parameters = task.get("notebook_task", {}).get("base_parameters", {})
                if base_parameters:
                    param_str = "\\n".join(base_parameters.keys())
                    lines.append(f'    {task_key_safe}_params["{param_str}"]')
                    lines.append(f'    {task_key_safe} --> {task_key_safe}_params')

            # Task dependencies
            for task in tasks:
                task_key = task.get("task_key")
                if not task_key:
                    continue
                task_key_safe = task_key.replace("-", "_")
                
                depends_on = task.get("depends_on", [])
                for dep_item in depends_on:
                    dep_key = dep_item.get("task_key")
                    if dep_key:
                        dep_key_safe = dep_key.replace("-", "_")
                        lines.append(f'    {dep_key_safe} --> {task_key_safe}')

            lines.append("    end")  # End Workflow subgraph

            # Job Clusters
            job_clusters = job_data.get("job_clusters", [])
            for cluster in job_clusters:
                cluster_key = cluster.get("job_cluster_key")
                if cluster_key:
                    new_cluster = cluster.get("new_cluster", {})
                    spark_version = new_cluster.get("spark_version", "")
                    node_type_id = new_cluster.get("node_type_id", "")
                    runtime_engine = new_cluster.get("runtime_engine", "")
                    
                    cluster_label = (
                        f"Cluster: {cluster_key}\\n"
                        f"{spark_version}, {node_type_id}, {runtime_engine}"
                    )
                    cluster_id_safe = f"cluster_{job_id_safe}"
                    lines.append(f'    {cluster_id_safe}["{cluster_label}"]')
                    lines.append(f'    {job_id_safe} --> {cluster_id_safe}')

            # Connect job to workflow
            lines.append(f'    {job_id_safe} --> Workflow_{job_id_safe}')

        lines.append("    end")  # End Jobs subgraph
    
    lines.append("    end")  # End target environment subgraph
    
    return "\n".join(lines)

def run_plantuml(puml_content, output_file):
    """
    Writes the PlantUML source to a temporary file and calls the PlantUML CLI
    to render it as a PNG. Captures stdout/stderr for debugging.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".puml") as tmp:
        tmp_name = tmp.name
        tmp.write(puml_content.encode("utf-8"))
    
    try:
        result = subprocess.run(
            ["plantuml", "-tpng", tmp_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("[ERROR] PlantUML execution failed:")
            print("stdout:", result.stdout)
            print("stderr:", result.stderr)
            return

        generated_png = tmp_name.replace(".puml", ".png")
        if os.path.exists(generated_png):
            shutil.move(generated_png, os.path.abspath(output_file))
            print(f"[INFO] PNG generated at: {os.path.abspath(output_file)}")
        else:
            print(f"[ERROR] Expected PNG not found at: {generated_png}")
            print("PlantUML output:")
            print("stdout:", result.stdout)
            print("stderr:", result.stderr)
    except Exception as e:
        print(f"[ERROR] Exception during PlantUML execution: {e}")
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

def run_mermaid(mermaid_content, output_file):
    """
    Uses the Mermaid CLI to convert Mermaid source to PNG.
    Requires mermaid-cli to be installed.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mmd") as tmp:
        tmp_name = tmp.name
        tmp.write(mermaid_content.encode("utf-8"))
        print(tmp_name)
        print(os.path.abspath(output_file))
    
#     try:
    if True:
        result = subprocess.run(
            ["mmdc", "-i", tmp_name, "-o", os.path.abspath(output_file), "-t", "dark"],
            capture_output=True,
            text=True
        )
        if result .returncode != 0:
            print("[ERROR] Mermaid CLI execution failed:")
            print("stdout:", result.stdout)
            print("stderr:", result.stderr)
            return

        print(f"[INFO] PNG generated at: {os.path.abspath(output_file)}")
    # except Exception as e:
    #     print(f"[ERROR] Exception during Mermaid CLI execution: {e}")
    # finally:
    #     if os.path.exists(tmp_name):
    #         os.remove(tmp_name)

def main():
    parser = argparse.ArgumentParser(
        description="Generate UML visualization from Databricks YAML asset bundle definitions. One PNG per environment."
    )
    parser.add_argument(
        "-i", "--input", 
        help="Path to databricks.yml file", 
        default="databricks.yml"
    )
    parser.add_argument(
        "-o", "--output", 
        help="Base name for output files (default: dabs_visualization). Each environment's file will be named <base>_<env>.png/.puml",
        default="figures/dabs_visualization"
    )
    parser.add_argument(
        "-t", "--type", 
        help="Diagram generation type (default: mermaid). Options: mermaid, plantuml",
        default="plantuml",
        choices=["mermaid", "plantuml"]
    )
    args = parser.parse_args()

    # Load YAML data
    bundle_name, resources, targets, variables = load_bundle_yaml(args.input)

    def get_replacements(data, variables):
        replacements = {}
        for k,v in variables.items(): 
            var = v.get('default', None)
            target_var = data.get('variables', {}).get(k, None)
            replacements[r'${var.'+k+r'}'] = target_var if target_var else var
        return replacements 

    def resolve_replacements(data, variables):
        data_str = json.dumps(data)
        for k, v in variables.items():
            data_str = data_str.replace(k, str(v))
        return json.loads(data_str)

    # For each environment/target, build a separate .puml/.mmd and .png
    for target_name, target_data in targets.items():

        replacements = {r'${bundle.target}': target_name}
        replacements['${workspace.current_user.userName}'] = '[CURRENT USER]'
        variables_resolved = resolve_replacements(variables, replacements)
        variable_replacements = get_replacements(target_data, variables_resolved)
        target_data_resolved = resolve_replacements(target_data, variable_replacements | replacements)
        resources_resolved = resolve_replacements(resources, variable_replacements | replacements)

        # Choose diagram generation method based on type
        if args.type == "plantuml":
            diagram_content = build_plantuml_for_target(bundle_name, resources_resolved, target_name, target_data_resolved)
            file_ext = "puml"
            render_func = run_plantuml
        elif args.type == "mermaid":
            diagram_content = build_mermaid_for_target(bundle_name, resources_resolved, target_name, target_data_resolved)
            file_ext = "mmd"
            render_func = run_mermaid

        # Generate source file paths
        source_file = f"{args.output}/source/{target_name}.{file_ext}"
        png_file = f"{args.output}_{target_name}.png"

        # Save the source file
        os.makedirs(os.path.dirname(source_file), exist_ok=True)
        with open(source_file, "w", encoding="utf-8") as f:
            f.write(diagram_content)
        print(f"[INFO] Diagram source saved to: {os.path.abspath(source_file)}")
        
        # Render the diagram
        render_func(diagram_content, png_file)
        print(f"[INFO] Generated diagram for environment '{target_name}': {os.path.abspath(png_file)}")

if __name__ == "__main__":
    main()
"""
Spandak8s CLI - Platform Status Commands

This module provides comprehensive platform monitoring and health checking:
- Kubernetes cluster connectivity and health
- Platform module status (MinIO, Spark, Dremio, etc.)
- Resource utilization across tenants
- Application deployment status
- System diagnostics and troubleshooting

Commands:
- status cluster: Check Kubernetes cluster health and connectivity
- status modules: Display status of all platform modules
- status tenants: Show tenant deployment status and resource usage
- status apps: Check application health across all tenants
- status diagnostics: Run comprehensive system health checks
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from pkg.kubernetes import (
    get_cluster_info,
    validate_kubernetes_access,
    is_cluster_ready,
    check_module_health,
    get_pod_status
)
from pkg.module_detector import detect_running_modules, validate_module_health

console = Console()

@click.group(invoke_without_command=True)
@click.option('--env', '-e', default=None, help='Environment (dev, staging, prod)')
@click.option('--all-envs', '-a', is_flag=True, help='Show status for all environments')
@click.pass_context
def status_group(ctx, env, all_envs):
    """Get status of tenant environments and modules"""
    if ctx.invoked_subcommand is None:
        # If no subcommand is provided, run the main status functionality
        show_status(ctx, env, all_envs)

def show_status(ctx, env, all_envs):
    """Show status of all modules in an environment"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    tenant_name = config.tenant_name
    
    # Determine which environments to check
    environments = []
    if all_envs:
        environments = ['dev', 'staging', 'prod']
    else:
        env = env or config.default_environment
        environments = [env]
    
    try:
        for environment in environments:
            console.print(f"\n🔍 [cyan]Checking status for environment: {environment}[/cyan]")
            
            tenant_namespace = f"{tenant_name}-{environment}"
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task(f"Detecting modules in {tenant_namespace}...", total=None)
                
                # Try API first, fallback to direct cluster detection
                try:
                    status_data = api_client.get_tenant_status(tenant_name, environment)
                    
                    # Extract modules from the API response format
                    modules = {}
                    for env_data in status_data.get('environments', []):
                        if env_data.get('environment') == environment:
                            env_modules = env_data.get('modules', [])
                            for module in env_modules:
                                module_name = module.get('name')
                                if module_name:
                                    modules[module_name] = {
                                        'status': module.get('status', 'unknown'),
                                        'namespace': env_data.get('namespace', tenant_namespace),
                                        'replicas': f"{module.get('ready_replicas', 0)}/{module.get('replicas', 0)}",
                                        'endpoint': 'N/A'  # Will be populated later if needed
                                    }
                            break
                            
                except Exception as e:
                    # Fallback to direct cluster detection
                    console.print(f"[dim]API unavailable ({e}), scanning cluster directly...[/dim]")
                    detected_modules = detect_running_modules(tenant_namespace)
                    modules = {}
                    for module_name, module_info in detected_modules.items():
                        modules[module_name] = {
                            'status': module_info['status'],
                            'namespace': module_info['namespace'],
                            'replicas': f"{module_info['pods']}/{module_info['pods']}",
                            'endpoint': ', '.join(module_info['endpoints'][:2]) if module_info['endpoints'] else 'N/A'
                        }
            
            if not modules:
                console.print(f"📭 [yellow]No modules deployed in {environment} environment[/yellow]")
                continue
            
            # Create status table
            table = Table(title=f"📊 Module Status - {environment.upper()} Environment")
            table.add_column("Module", style="cyan", no_wrap=True)
            table.add_column("Status", style="white")
            table.add_column("Namespace", style="dim")
            table.add_column("Replicas", style="green")
            table.add_column("Endpoint", style="blue")
            
            for module_name, module_info in modules.items():
                status = module_info.get('status', 'unknown')
                
                # Color code the status
                if status == 'running':
                    status_display = "[green]✅ Running[/green]"
                elif status == 'pending':
                    status_display = "[yellow]⏳ Pending[/yellow]"
                elif status == 'failed':
                    status_display = "[red]❌ Failed[/red]"
                else:
                    status_display = f"[dim]❓ {status}[/dim]"
                
                table.add_row(
                    module_name,
                    status_display,
                    module_info.get('namespace', tenant_namespace),
                    str(module_info.get('replicas', 'N/A')),
                    module_info.get('endpoint', 'N/A')
                )
            
            console.print(table)
            
            # Show summary
            total_modules = len(modules)
            running_modules = sum(1 for m in modules.values() if m.get('status') == 'running')
            
            summary_text = f"Total modules: {total_modules} | Running: {running_modules}"
            if running_modules == total_modules:
                summary_text = f"[green]{summary_text} ✅[/green]"
            elif running_modules == 0:
                summary_text = f"[red]{summary_text} ❌[/red]"
            else:
                summary_text = f"[yellow]{summary_text} ⚠️[/yellow]"
            
            console.print(f"\n{summary_text}")
            
    except Exception as e:
        console.print(f"❌ [red]Error getting status: {e}[/red]")

@status_group.command('health')
@click.pass_context
def health_check(ctx):
    """Check health of the Spanda Platform backend"""
    api_client = ctx.obj['api_client']
    
    try:
        console.print("🏥 [cyan]Checking Spanda Platform health...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Connecting to backend...", total=None)
            health_data = api_client.health_check()
        
        # Display health information
        health_text = ""
        
        if 'status' in health_data:
            status = health_data['status']
            if status == 'healthy':
                health_text += "[green]✅ Backend Status: Healthy[/green]\n"
            else:
                health_text += f"[red]❌ Backend Status: {status}[/red]\n"
        
        if 'version' in health_data:
            health_text += f"🏷️  Version: {health_data['version']}\n"
        
        if 'uptime' in health_data:
            health_text += f"⏱️  Uptime: {health_data['uptime']}\n"
        
        if 'database' in health_data:
            db_status = health_data['database']
            if db_status == 'connected':
                health_text += "[green]🗄️  Database: Connected[/green]\n"
            else:
                health_text += f"[red]🗄️  Database: {db_status}[/red]\n"
        
        if 'kubernetes' in health_data:
            k8s_status = health_data['kubernetes']
            if k8s_status == 'connected':
                health_text += "[green]☸️  Kubernetes: Connected[/green]\n"
            else:
                health_text += f"[red]☸️  Kubernetes: {k8s_status}[/red]\n"
        
        console.print(Panel(health_text, title="🏥 Platform Health", border_style="green"))
        
    except Exception as e:
        console.print(f"❌ [red]Error checking health: {e}[/red]")
        console.print("[dim]💡 Make sure the Spanda Platform backend is running[/dim]")

@status_group.command('cluster')
@click.pass_context
def cluster_info(ctx):
    """Show Kubernetes cluster information"""
    try:
        console.print("☸️ [cyan]Checking Kubernetes cluster...[/cyan]")
        
        # Validate cluster access first
        if not validate_kubernetes_access():
            console.print("❌ [red]Cannot access Kubernetes cluster[/red]")
            console.print("[dim]💡 Make sure kubectl is configured and cluster is running[/dim]")
            return
        
        # Check if cluster is ready
        if not is_cluster_ready():
            console.print("⚠️ [yellow]Cluster is not fully ready[/yellow]")
        
        # Get comprehensive cluster information
        cluster_data = get_cluster_info()
        
        if 'current_context' in cluster_data:
            console.print(f"📍 Current Context: [yellow]{cluster_data['current_context']}[/yellow]")
        
        if 'cluster_info' in cluster_data:
            console.print("\n📊 [bold]Cluster Information:[/bold]")
            for line in cluster_data['cluster_info'].split('\n'):
                if line.strip():
                    console.print(f"   {line}")
        
        if 'nodes' in cluster_data:
            table = Table(title="🖥️ Cluster Nodes")
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Roles", style="green")
            table.add_column("Version", style="blue")
            
            for node in cluster_data['nodes']:
                status_color = "green" if node['status'] == "Ready" else "red"
                status_display = f"[{status_color}]{node['status']}[/{status_color}]"
                roles_str = ', '.join(node['roles'])
                
                table.add_row(
                    node['name'],
                    status_display,
                    roles_str,
                    node['version']
                )
            
            console.print(table)
        
        # Show namespace summary for tenant
        config = ctx.obj['config']
        tenant_name = config.tenant_name
        default_env = config.default_environment
        tenant_namespace = f"{tenant_name}-{default_env}"
        
        console.print(f"\n🏷️ [cyan]Checking tenant namespace: {tenant_namespace}[/cyan]")
        pods = get_pod_status(tenant_namespace)
        
        if pods:
            console.print(f"📦 Found {len(pods)} pods in tenant namespace")
            pod_table = Table(title=f"Pods in {tenant_namespace}")
            pod_table.add_column("Name", style="cyan")
            pod_table.add_column("Status", style="white")
            pod_table.add_column("Ready", style="green")
            pod_table.add_column("Restarts", style="yellow")
            
            for pod in pods:
                status = pod['status']
                status_color = "green" if status == "Running" else "yellow" if status == "Pending" else "red"
                status_display = f"[{status_color}]{status}[/{status_color}]"
                
                pod_table.add_row(
                    pod['name'],
                    status_display,
                    pod['ready'],
                    str(pod['restarts'])
                )
            
            console.print(pod_table)
        else:
            console.print(f"📭 [dim]No pods found in {tenant_namespace} namespace[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Error checking cluster: {e}[/red]")

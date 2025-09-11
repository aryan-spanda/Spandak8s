"""
Spandak8s CLI - Module Management Commands

This module provides comprehensive module management capabilities including:
- Listing available platform modules (MinIO, Spark, Dremio, etc.)
- Generating tenant configuration with resource quotas
- Managing module health checks and dependencies
- Displaying module categories and resource tiers

Commands:
- modules list: Show all available platform modules
- modules generate-config: Create tenant configuration with selected modules
- modules list-tiers: Display available resource tiers (Bronze/Standard/Premium)
- modules list-categories: Show module categories
- modules health: Check module health status
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from pkg.module_detector import validate_module_health
from pkg.module_definitions import module_definitions

console = Console()

@click.group()
def modules_group():
    """Manage platform modules (enable, disable, configure)"""
    pass

@modules_group.command('list')
@click.pass_context
def list_modules(ctx):
    """List all available platform modules"""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Fetching available modules...", total=None)
            
            # Try API first, fallback to local definitions
            try:
                api_client = ctx.obj['api_client']
                modules = api_client.list_available_modules()
            except Exception:
                console.print("[dim]API unavailable, using local module definitions...[/dim]")
                modules = module_definitions.list_available_modules()
        
        if not modules:
            console.print("📭 [yellow]No modules available[/yellow]")
            return
        
        table = Table(title="🔧 Available Platform Modules")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Version", style="green")
        table.add_column("Category", style="magenta")
        
        for module in modules:
            table.add_row(
                module.get('name', 'Unknown'),
                module.get('description', 'No description available'),
                module.get('version', 'latest'),
                module.get('category', 'general')
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ [red]Error listing modules: {e}[/red]")

@modules_group.command('enable')
@click.argument('module_name')
@click.option('--env', '-e', default=None, help='Environment (dev, staging, prod)')
@click.option('--config-file', type=click.File('r'), help='YAML config file for advanced settings')
@click.pass_context
def enable_module(ctx, module_name, env, config_file):
    """Enable a platform module for your tenant"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    # Use default environment if not specified
    if env is None:
        env = config.default_environment
    
    tenant_name = config.tenant_name
    
    try:
        # Build module configuration - platform determines resources
        module_config = {
            'environment': env,
            'tenant': tenant_name,
            'module': module_name
        }
        
        # Load additional config from file if provided
        if config_file:
            import yaml
            file_config = yaml.safe_load(config_file)
            module_config.update(file_config)
        
        console.print(f"🚀 [cyan]Enabling module '{module_name}' for tenant '{tenant_name}' in environment '{env}'[/cyan]")
        console.print("📋 [dim]Platform will determine optimal resource allocation based on tenant quotas[/dim]")
        
        if module_config.get('config_file'):
            console.print("📋 [dim]Additional configuration loaded from file[/dim]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Deploying module...", total=None)
            result = api_client.enable_module(tenant_name, env, module_name, module_config)
        
        console.print(f"✅ [green]Successfully enabled '{module_name}'![/green]")
        
        if 'status' in result:
            console.print(f"📊 Status: {result['status']}")
        if 'namespace' in result:
            console.print(f"🏷️  Namespace: {result['namespace']}")
        if 'endpoint' in result:
            console.print(f"🌐 Endpoint: {result['endpoint']}")
            
    except Exception as e:
        console.print(f"❌ [red]Error enabling module '{module_name}': {e}[/red]")

@modules_group.command('disable')
@click.argument('module_name')
@click.option('--env', '-e', default=None, help='Environment (dev, staging, prod)')
@click.option('--force', '-f', is_flag=True, help='Force disable without confirmation')
@click.pass_context
def disable_module(ctx, module_name, env, force):
    """Disable a platform module for your tenant"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    # Use default environment if not specified
    if env is None:
        env = config.default_environment
    
    tenant_name = config.tenant_name
    
    try:
        if not force:
            if not click.confirm(f"Are you sure you want to disable '{module_name}' in '{env}' environment?"):
                console.print("❌ [yellow]Operation cancelled[/yellow]")
                return
        
        console.print(f"🛑 [cyan]Disabling module '{module_name}' for tenant '{tenant_name}' in environment '{env}'[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Removing module...", total=None)
            result = api_client.disable_module(tenant_name, env, module_name)
        
        console.print(f"✅ [green]Successfully disabled '{module_name}'![/green]")
        
        if 'message' in result:
            console.print(f"📄 {result['message']}")
            
    except Exception as e:
        console.print(f"❌ [red]Error disabling module '{module_name}': {e}[/red]")

@modules_group.command('status')
@click.argument('module_name')
@click.option('--env', '-e', default=None, help='Environment (dev, staging, prod)')
@click.pass_context
def module_status(ctx, module_name, env):
    """Get status and configuration of a specific module"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    # Use default environment if not specified
    if env is None:
        env = config.default_environment
    
    tenant_name = config.tenant_name
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Fetching module status...", total=None)
            module_config = api_client.get_module_config(tenant_name, env, module_name)
        
        # Display module status in a nice panel
        status_text = f"[bold cyan]{module_name}[/bold cyan] in [yellow]{env}[/yellow] environment\n\n"
        
        if 'status' in module_config:
            status = module_config['status']
            status_color = "green" if status == "running" else "red" if status == "failed" else "yellow"
            status_text += f"Status: [{status_color}]{status}[/{status_color}]\n"
        
        if 'namespace' in module_config:
            status_text += f"Namespace: {module_config['namespace']}\n"
        
        if 'config' in module_config:
            status_text += "\n[bold]Configuration:[/bold]\n"
            for key, value in module_config['config'].items():
                status_text += f"  • {key}: {value}\n"
        
        console.print(Panel(status_text, title="📊 Module Status", border_style="cyan"))
        
    except Exception as e:
        console.print(f"❌ [red]Error getting status for '{module_name}': {e}[/red]")

@modules_group.command('configure')
@click.argument('module_name')
@click.option('--env', '-e', default=None, help='Environment (dev, staging, prod)')
@click.option('--config-file', type=click.File('r'), help='YAML config file with settings')
@click.option('--scale', type=int, help='Scale replicas (if supported by tenant tier)')
@click.pass_context
def configure_module(ctx, module_name, env, config_file, scale):
    """Update configuration for an existing module (limited by tenant quotas)"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    # Use default environment if not specified
    if env is None:
        env = config.default_environment
    
    tenant_name = config.tenant_name
    
    try:
        # Build update configuration - limited to what tenants can control
        updates = {}
        
        if scale:
            updates['scale'] = scale
        
        # Load configuration from file if provided
        if config_file:
            import yaml
            file_config = yaml.safe_load(config_file)
            updates.update(file_config)
        
        if not updates:
            console.print("❌ [red]No configuration updates specified[/red]")
            console.print("💡 [dim]Use --scale to adjust replicas or --config-file for advanced settings[/dim]")
            return
        
        console.print(f"⚙️ [cyan]Updating configuration for '{module_name}'[/cyan]")
        console.print("📋 [dim]Requested changes (subject to tenant quotas):[/dim]")
        for key, value in updates.items():
            console.print(f"   • {key}: {value}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Updating module configuration...", total=None)
            result = api_client.update_module_config(tenant_name, env, module_name, updates)
        
        console.print(f"✅ [green]Successfully updated '{module_name}' configuration![/green]")
        
        if 'status' in result:
            console.print(f"📊 Status: {result['status']}")
        
        if 'applied_changes' in result:
            console.print("📋 [dim]Applied changes:[/dim]")
            for key, value in result['applied_changes'].items():
                console.print(f"   • {key}: {value}")
        
        if 'rejected_changes' in result:
            console.print("⚠️ [yellow]Changes rejected due to tenant limits:[/yellow]")
            for key, reason in result['rejected_changes'].items():
                console.print(f"   • {key}: {reason}")
            
    except Exception as e:
        console.print(f"❌ [red]Error updating configuration for '{module_name}': {e}[/red]")

@modules_group.command('generate-config')
@click.argument('namespace')
@click.option('--modules', '-m', multiple=True, help='Modules to enable (can be specified multiple times)')
@click.option('--tier', '-t', default='standard', 
              type=click.Choice(['bronze', 'standard', 'premium'], case_sensitive=False),
              help='Resource tier for quota allocation')
@click.option('--storage-class', '-s', default='standard', help='Storage class to use')
@click.option('--output', '-o', type=click.File('w'), help='Output file (default: stdout)')
@click.option('--validate-deps', is_flag=True, default=True, help='Validate module dependencies')
@click.pass_context
def generate_tenant_config(ctx, namespace, modules, tier, storage_class, output, validate_deps):
    """Generate tenant configuration with resource quotas and enabled modules"""
    
    try:
        # Validate module dependencies if requested
        if validate_deps and modules:
            is_valid, missing_deps = module_definitions.validate_dependencies(list(modules))
            if not is_valid:
                console.print("⚠️ [yellow]Dependency validation failed:[/yellow]")
                for dep in missing_deps:
                    console.print(f"   • {dep}")
                if not click.confirm("Continue anyway?"):
                    console.print("❌ [yellow]Operation cancelled[/yellow]")
                    return
        
        # Show configuration summary
        console.print(f"🔧 [cyan]Generating tenant configuration for namespace '{namespace}'[/cyan]")
        console.print(f"📊 Resource Tier: [green]{tier.title()}[/green]")
        console.print(f"💾 Storage Class: [green]{storage_class}[/green]")
        
        if modules:
            console.print(f"📦 Enabled Modules: [green]{', '.join(modules)}[/green]")
        else:
            console.print("📦 [dim]No modules specified - all modules will be disabled[/dim]")
        
        # Generate the configuration
        config = module_definitions.generate_tenant_values(
            namespace=namespace,
            modules=list(modules),
            resource_tier=tier.lower(),
            storage_class=storage_class
        )
        
        # Convert to YAML
        import yaml
        yaml_output = yaml.dump(config, default_flow_style=False, sort_keys=False)
        
        # Output to file or stdout
        if output:
            output.write(yaml_output)
            console.print(f"✅ [green]Configuration written to {output.name}[/green]")
        else:
            console.print("\n" + "="*50)
            console.print(yaml_output)
            console.print("="*50)
        
        # Show resource quota summary
        resource_template = module_definitions.get_resource_template(tier.lower())
        if resource_template:
            console.print(f"\n📊 [cyan]Resource Quota Summary ({tier.title()} Tier):[/cyan]")
            quota = resource_template["resource_quota"]
            console.print(f"   • CPU Requests/Limits: {quota.get('requests.cpu', 'N/A')}")
            console.print(f"   • Memory Requests/Limits: {quota.get('requests.memory', 'N/A')}")
            console.print(f"   • Storage Requests: {quota.get('requests.storage', 'N/A')}")
            console.print(f"   • PVC Limit: {quota.get('persistentvolumeclaims', 'N/A')}")
        
    except Exception as e:
        console.print(f"❌ [red]Error generating configuration: {e}[/red]")

@modules_group.command('list-tiers')
def list_resource_tiers():
    """List available resource quota tiers"""
    try:
        resource_templates = module_definitions.get_resource_templates()
        
        if not resource_templates:
            console.print("📭 [yellow]No resource tiers available[/yellow]")
            return
        
        table = Table(title="💎 Available Resource Tiers")
        table.add_column("Tier", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("CPU", style="green")
        table.add_column("Memory", style="green")
        table.add_column("Storage", style="green")
        table.add_column("PVCs", style="yellow")
        
        for tier_key, tier_data in resource_templates.items():
            quota = tier_data.get("resource_quota", {})
            table.add_row(
                tier_key,
                tier_data.get("name", tier_key.title()),
                quota.get("requests.cpu", "N/A"),
                quota.get("requests.memory", "N/A"), 
                quota.get("requests.storage", "N/A"),
                quota.get("persistentvolumeclaims", "N/A")
            )
        
        console.print(table)
        
        # Show descriptions
        console.print("\n📋 [cyan]Tier Descriptions:[/cyan]")
        for tier_key, tier_data in resource_templates.items():
            desc = tier_data.get("description", "No description available")
            console.print(f"   • [green]{tier_key}[/green]: {desc}")
        
    except Exception as e:
        console.print(f"❌ [red]Error listing resource tiers: {e}[/red]")

@modules_group.command('list-categories')
def list_module_categories():
    """List available module categories"""
    try:
        categories = module_definitions.get_categories()
        
        if not categories:
            console.print("📭 [yellow]No module categories available[/yellow]")
            return
        
        console.print("📂 [cyan]Available Module Categories:[/cyan]\n")
        
        for category_key, category_data in categories.items():
            icon = category_data.get("icon", "📦")
            name = category_data.get("name", category_key.title())
            desc = category_data.get("description", "No description available")
            
            # Get modules in this category
            modules = module_definitions.get_modules_by_category(category_key)
            module_count = len(modules)
            
            console.print(f"{icon} [green]{name}[/green] ({module_count} modules)")
            console.print(f"   {desc}")
            
            if modules:
                module_names = [m.get("display_name", m.get("name", "Unknown")) for m in modules]
                console.print(f"   [dim]Modules: {', '.join(module_names)}[/dim]")
            
            console.print()
        
    except Exception as e:
        console.print(f"❌ [red]Error listing categories: {e}[/red]")

"""
Spandak8s CLI - Module Management Commands

This module provides comprehensive module management capabilities including:
- Listing available p        # Check current deployment status
        console.print("🔍 [dim]Checking current deployment status...[/dim]")
        try:
            current_status = api_client.get_module_deployment_status(tenant_name, module_name, env)
            if current_status.get('deployed', False) and current_status.get('status') == 'running':
                console.print(f"✅ [green]Module '{module_name}' is already running in {env} environment[/green]")
                console.print(f"📊 Status: {current_status.get('status')} ({current_status.get('replicas', {}).get('ready', 0)}/{current_status.get('replicas', {}).get('desired', 0)} replicas)")
                return
        except Exception:
            # Status check failed, continue with deployment
            passules (MinIO, Spark, Dremio, etc.)
- Generating tenant configuration with resource quotas
- Managing module health checks and dependencies
- Displaying module categories and resource tiers

Commands:
- modules lis        table.a        table.add_column("Storage", style="green")
          for category_key, category_modules in categories.items():
            console.print(f"📂 [cyan]{category_key}:[/cyan]")
            
            # Get modules in this category
            for module_name in category_modules:
                module_data = module_definitions.get_module(module_name)
                if module_data:
                    desc = module_data.get('description', 'No description available')
                    version = module_data.get('version', 'latest')
                    console.print(f"   • [green]{module_name}[/green] (v{version}): {desc}")
            console.print()  # Empty line between categories.add_column("PVCs", style="yellow")
        
        for tier_key, tier_data in resource_tiers.items():
            table.add_row(
                tier_key,
                tier_key.title(),
                tier_data.get("cpu", "N/A"),
                tier_data.get("memory", "N/A"), 
                tier_data.get("storage", "N/A"),
                "Unlimited"  # Default PVC limit
            )U", style="green")
        table.add_column("Memory", style="green")
        table.add_column("Storage", style="green")
        table.add_column("PVCs", style="yellow")
        
        for tier_key, tier_data in resource_tiers.items():
            table.add_row(
                tier_key.title(),
                tier_key.title(),
                tier_data.get("cpu", "N/A"),
                tier_data.get("memory", "N/A"),
                tier_data.get("storage", "N/A"),
                "Unlimited"  # Default PVC limit
            )ilable platform modules
- modules generate-config: Create tenant configuration with selected modules
- modules list-tiers: Display available resource tiers (Bronze/Standard/Premium)
- modules list-categories: Show module categories
- modules health: Check module health status
"""

import click
from rich.console import Console
from rich.table import Table
# Panel import removed - not used in current implementation
from rich.progress import Progress, SpinnerColumn, TextColumn

# NOTE: module_definitions is now passed via context from main CLI (no global import)

console = Console()

def _get_module_definitions(ctx):
    """Helper function to get module_definitions from context with error handling"""
    module_definitions = ctx.obj.get('module_definitions')
    if not module_definitions:
        console.print("[red]Error: Module definitions not available. Check API connection.[/red]")
        return None
    return module_definitions

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
            
            # Get module_definitions from context (API-driven)
            module_definitions = ctx.obj.get('module_definitions')
            if not module_definitions:
                console.print("[red]Error: Module definitions not available. Check API connection.[/red]")
                return
                
            modules = module_definitions.list_modules_by_category()
        
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
    
    # Ensure backend is running
    # if not api_client.ensure_backend_running():
    #     return
    
    # Parse tenant and environment from --env parameter
    if env and '-' in env:
        # Environment format: tenant-environment (e.g., langflow-dev)
        tenant_name, parsed_env = env.split('-', 1)
        env = parsed_env
    else:
        # Use default values if not specified
        if env is None:
            env = config.get('defaults.environment', 'dev')
        tenant_name = config.get('tenant.name', 'default')
    
    try:
        # Check if module exists first
        console.print(f"🔍 [dim]Checking module '{module_name}' availability...[/dim]")
        
        # Validate module exists by getting its details
        try:
            module_details = api_client.get_module_details(module_name)
            console.print(f"📦 [cyan]Module: {module_details.get('display_name', module_name)}[/cyan]")
            console.print(f"📝 [dim]{module_details.get('description', 'No description available')}[/dim]")
        except Exception:
            console.print(f"❌ [red]Module '{module_name}' not found in catalog[/red]")
            return
        
        # Check current deployment status
        console.print(f"🔍 [dim]Checking current deployment status...[/dim]")
        try:
            current_status = api_client.get_module_deployment_status(tenant_name, module_name, env)
            if current_status.get('deployed', False) and current_status.get('status') == 'running':
                console.print(f"✅ [green]Module '{module_name}' is already running in {env} environment[/green]")
                console.print(f"📊 Status: {current_status.get('status')} ({current_status.get('replicas', {}).get('ready', 0)}/{current_status.get('replicas', {}).get('desired', 0)} replicas)")
                return
        except Exception:
            # Status check failed, continue with deployment
            pass
        
        # Build module configuration
        module_config = {
            'environment': env,
            'tenant': tenant_name,
            'module': module_name
        }
        
        # Load additional config from file if provided
        if config_file:
            import yaml
            try:
                file_config = yaml.safe_load(config_file)
                module_config.update(file_config)
                console.print("📋 [dim]Additional configuration loaded from file[/dim]")
            except Exception as e:
                console.print(f"⚠️ [yellow]Warning: Could not load config file: {e}[/yellow]")
        
        console.print(f"🚀 [cyan]Enabling module '{module_name}' for tenant '{tenant_name}'[/cyan]")
        console.print(f"🏷️  Environment: [green]{env}[/green]")
        console.print(f" Namespace: [cyan]{tenant_name}-{env}[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Deploying module with Helm...", total=None)
            result = api_client.enable_module(tenant_name, env, module_name, module_config)
        
        console.print(f"✅ [green]Successfully enabled '{module_name}'![/green]")
        
        # Display deployment details
        if 'namespace' in result:
            console.print(f"🏷️  Namespace: [cyan]{result['namespace']}[/cyan]")
        
        if 'deployment' in result and 'release_name' in result['deployment']:
            console.print(f"📦 Helm Release: [cyan]{result['deployment']['release_name']}[/cyan]")
        
        if 'status' in result and result['status'].get('deployed'):
            status_info = result['status']
            console.print(f"📊 Status: [green]{status_info.get('status', 'running')}[/green]")
            
            replicas = status_info.get('replicas', {})
            if replicas:
                console.print(f"🔢 Replicas: {replicas.get('ready', 0)}/{replicas.get('desired', 0)}")
        
        console.print(f"💡 [dim]Check status with: spandak8s modules status {module_name}[/dim]")
            
    except Exception as e:
        console.print(f"❌ [red]Error enabling module '{module_name}': {e}[/red]")
        console.print("💡 [dim]Try checking: spandak8s status cluster[/dim]")

@modules_group.command('disable')
@click.argument('module_name')
@click.option('--env', '-e', default=None, help='Environment (dev, staging, prod)')
@click.option('--force', '-f', is_flag=True, help='Force disable without confirmation')
@click.pass_context
def disable_module(ctx, module_name, env, force):
    """Disable a platform module for your tenant"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    # Ensure backend is running
    # if not api_client.ensure_backend_running():
    #     return
    
    # Parse tenant and environment from --env parameter
    if env and '-' in env:
        # Environment format: tenant-environment (e.g., langflow-dev)
        tenant_name, parsed_env = env.split('-', 1)
        env = parsed_env
    else:
        # Use default values if not specified
        if env is None:
            env = config.get('defaults.environment', 'dev')
        tenant_name = config.get('tenant.name', 'default')
    
    try:
        # Check current deployment status first
        console.print("🔍 [dim]Checking current deployment status...[/dim]")
        try:
            current_status = api_client.get_module_deployment_status(tenant_name, module_name, env)
            if not current_status.get('deployed', False):
                console.print(f"ℹ️ [yellow]Module '{module_name}' is not currently deployed in {env} environment[/yellow]")
                return
        except Exception:
            # Status check failed, continue anyway
            console.print("⚠️ [yellow]Could not check deployment status, proceeding with disable...[/yellow]")
        
        if not force:
            console.print(f"⚠️  [yellow]This will remove '{module_name}' and all its data from '{env}' environment[/yellow]")
            if not click.confirm(f"Are you sure you want to disable '{module_name}'?"):
                console.print("❌ [yellow]Operation cancelled[/yellow]")
                return
        
        console.print(f"🛑 [cyan]Disabling module '{module_name}' for tenant '{tenant_name}'[/cyan]")
        console.print(f"🏷️  Environment: [yellow]{env}[/yellow]")
        console.print(f"🏢 Namespace: [cyan]{tenant_name}-{env}[/cyan]")
        
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
    """Check the deployment status of a specific module"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    # Ensure backend is running
    # if not api_client.ensure_backend_running():
    #     return
    
    # Parse tenant and environment from --env parameter
    if env and '-' in env:
        # Environment format: tenant-environment (e.g., langflow-dev)
        tenant_name, parsed_env = env.split('-', 1)
        env = parsed_env
    else:
        # Use default values if not specified
        if env is None:
            env = config.get('defaults.environment', 'dev')
        tenant_name = config.get('tenant.name', 'default')
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Checking module status...", total=None)
            status = api_client.get_module_deployment_status(tenant_name, module_name, env)
        
        console.print(f"📊 [cyan]Module Status: {module_name}[/cyan]")
        console.print(f"🏢 Tenant: [green]{tenant_name}[/green]")
        console.print(f"🏷️  Environment: [green]{env}[/green]")
        console.print(f"🏗️  Namespace: [cyan]{status.get('namespace', 'unknown')}[/cyan]")
        
        # Status indicator
        deployed = status.get('deployed', False)
        if deployed:
            module_status = status.get('status', 'unknown')
            if module_status == 'running':
                status_display = "[green]✅ Running[/green]"
            elif module_status == 'degraded':
                status_display = "[yellow]⚠️  Degraded[/yellow]"
            elif module_status == 'failed':
                status_display = "[red]❌ Failed[/red]"
            else:
                status_display = f"[dim]❓ {module_status}[/dim]"
        else:
            status_display = "[red]🔴 Not Deployed[/red]"
        
        console.print(f"📈 Status: {status_display}")
        
        # Replica information
        replicas = status.get('replicas', {})
        if replicas and replicas.get('desired', 0) > 0:
            ready = replicas.get('ready', 0)
            desired = replicas.get('desired', 0)
            console.print(f"🔢 Replicas: {ready}/{desired}")
            
            if ready == desired:
                console.print("✅ [green]All replicas are ready[/green]")
            elif ready > 0:
                console.print("⚠️ [yellow]Some replicas are not ready[/yellow]")
            else:
                console.print("❌ [red]No replicas are ready[/red]")
        
        # Last checked time
        if 'last_checked' in status:
            console.print(f"🕐 Last Checked: [dim]{status['last_checked']}[/dim]")
            
    except Exception as e:
        console.print(f"❌ [red]Error checking status for '{module_name}': {e}[/red]")

# Remove duplicate function - already defined above

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
        # Get module definitions from context
        module_definitions = _get_module_definitions(ctx)
        if not module_definitions:
            return
            
        # Validate module dependencies if requested
        if validate_deps and modules:
            validation_result = module_definitions.validate_modules(list(modules))
            if not validation_result.get('valid', True):
                console.print("⚠️ [yellow]Dependency validation failed:[/yellow]")
                for error in validation_result.get('errors', []):
                    console.print(f"   • {error}")
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
        yaml_output = module_definitions.generate_tenant_values(
            tenant_name=namespace,
            modules=list(modules),
            tier=tier.lower()
        )
        
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
@click.pass_context
def list_resource_tiers(ctx):
    """List available resource quota tiers"""
    try:
        # Get module definitions from context
        module_definitions = _get_module_definitions(ctx)
        if not module_definitions:
            return
            
        resource_tiers = module_definitions.get_resource_tiers()
        
        if not resource_tiers:
            console.print("📭 [yellow]No resource tiers available[/yellow]")
            return
        
        table = Table(title="💎 Available Resource Tiers")
        table.add_column("Tier", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("CPU", style="green")
        table.add_column("Memory", style="green")
        table.add_column("Storage", style="green")
        table.add_column("PVCs", style="yellow")
        
        for tier_key, tier_data in resource_tiers.items():
            table.add_row(
                tier_key,
                tier_key.title(),
                tier_data.get("cpu", "N/A"),
                tier_data.get("memory", "N/A"), 
                tier_data.get("storage", "N/A"),
                "Unlimited"  # Default PVC limit
            )
        
        console.print(table)
        
        # Show descriptions
        console.print("\n📋 [cyan]Tier Descriptions:[/cyan]")
        for tier_key, tier_data in resource_tiers.items():
            desc = f"Resource allocation for {tier_key} tier"
            console.print(f"   • [green]{tier_key.title()}[/green]: {desc}")
            console.print(f"     CPU: {tier_data.get('cpu', 'N/A')}, Memory: {tier_data.get('memory', 'N/A')}, Storage: {tier_data.get('storage', 'N/A')}")
        
    except Exception as e:
        console.print(f"❌ [red]Error listing resource tiers: {e}[/red]")

@modules_group.command('list-categories')
@click.pass_context
def list_module_categories(ctx):
    """List available module categories"""
    try:
        # Get module definitions from context
        module_definitions = _get_module_definitions(ctx)
        if not module_definitions:
            return
            
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

"""
Spandak8s CLI - Tenant Management Commands

This module handles tenant lifecycle management including:
- Creating and configuring new tenants
- Managing tenant resource quotas (Bronze/Standard/Premium tiers)
- Deploying tenant applications with proper resource limits
- Monitoring tenant status and health
- Managing tenant namespaces and RBAC

Commands:
- tenants list: Show all configured tenants
- tenants create: Create a new tenant with resource quota
- tenants deploy: Deploy tenant configuration to Kubernetes
- tenants status: Check tenant deployment status
- tenants delete: Remove tenant and cleanup resources
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@click.group()
def tenants_group():
    """Manage tenants and their configurations"""
    pass

@tenants_group.command('list')
@click.pass_context
def list_tenants(ctx):
    """List all tenants"""
    api_client = ctx.obj['api_client']
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Fetching tenants...", total=None)
            tenants = api_client.list_tenants()
        
        if not tenants:
            console.print("📭 [yellow]No tenants found[/yellow]")
            return
        
        table = Table(title="🏢 Platform Tenants")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Status", style="white")
        table.add_column("Environments", style="green")
        table.add_column("Modules", style="blue")
        table.add_column("Created", style="dim")
        
        for tenant in tenants:
            # Get status color
            status = tenant.get('status', 'unknown')
            if status == 'active':
                status_display = "[green]✅ Active[/green]"
            elif status == 'inactive':
                status_display = "[red]❌ Inactive[/red]"
            else:
                status_display = f"[dim]❓ {status}[/dim]"
            
            # Format environments
            environments = tenant.get('environments', [])
            env_display = ', '.join(environments) if environments else 'None'
            
            # Count modules
            module_count = len(tenant.get('modules', []))
            
            table.add_row(
                tenant.get('name', 'Unknown'),
                status_display,
                env_display,
                str(module_count),
                tenant.get('created_at', 'N/A')
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ [red]Error listing tenants: {e}[/red]")

@tenants_group.command('info')
@click.argument('tenant_name', required=False)
@click.pass_context
def tenant_info(ctx, tenant_name):
    """Get detailed information about a tenant"""
    config = ctx.obj['config']
    api_client = ctx.obj['api_client']
    
    # Use current tenant if none specified
    if not tenant_name:
        tenant_name = config.tenant_name
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(f"Fetching info for {tenant_name}...", total=None)
            tenant_data = api_client.get_tenant_info(tenant_name)
        
        # Display tenant information in a panel
        info_text = f"[bold cyan]{tenant_name}[/bold cyan]\n\n"
        
        if 'status' in tenant_data:
            status = tenant_data['status']
            status_color = "green" if status == "active" else "red"
            info_text += f"Status: [{status_color}]{status}[/{status_color}]\n"
        
        if 'description' in tenant_data:
            info_text += f"Description: {tenant_data['description']}\n"
        
        if 'created_at' in tenant_data:
            info_text += f"Created: {tenant_data['created_at']}\n"
        
        if 'resource_quota' in tenant_data:
            quota = tenant_data['resource_quota']
            info_text += "\n[bold]Resource Quotas:[/bold]\n"
            for key, value in quota.items():
                info_text += f"  • {key}: {value}\n"
        
        if 'environments' in tenant_data:
            environments = tenant_data['environments']
            info_text += f"\n[bold]Environments:[/bold] {', '.join(environments)}\n"
        
        if 'modules' in tenant_data:
            modules = tenant_data['modules']
            info_text += f"\n[bold]Active Modules:[/bold] {len(modules)}\n"
            for module in modules:
                env = module.get('environment', 'unknown')
                name = module.get('name', 'unknown')
                status = module.get('status', 'unknown')
                info_text += f"  • {name} ({env}): {status}\n"
        
        console.print(Panel(info_text, title="🏢 Tenant Information", border_style="cyan"))
        
    except Exception as e:
        console.print(f"❌ [red]Error getting tenant info: {e}[/red]")

@tenants_group.command('create')
@click.argument('tenant_name')
@click.option('--description', help='Tenant description')
@click.option('--cpu-quota', default='10', help='CPU quota (default: 10)')
@click.option('--memory-quota', default='20Gi', help='Memory quota (default: 20Gi)')
@click.option('--storage-quota', default='50Gi', help='Storage quota (default: 50Gi)')
@click.option('--environments', default='dev,staging,prod', help='Comma-separated environments (default: dev,staging,prod)')
@click.pass_context
def create_tenant(ctx, tenant_name, description, cpu_quota, memory_quota, storage_quota, environments):
    """Create a new tenant"""
    api_client = ctx.obj['api_client']
    
    try:
        # Parse environments
        env_list = [env.strip() for env in environments.split(',')]
        
        # Build tenant data
        tenant_data = {
            'name': tenant_name,
            'description': description or f'Tenant {tenant_name}',
            'resource_quota': {
                'cpu': cpu_quota,
                'memory': memory_quota,
                'storage': storage_quota
            },
            'environments': env_list
        }
        
        console.print(f"🏗️ [cyan]Creating tenant '{tenant_name}'[/cyan]")
        console.print("📋 [dim]Configuration:[/dim]")
        console.print(f"   • Description: {tenant_data['description']}")
        console.print(f"   • CPU Quota: {cpu_quota}")
        console.print(f"   • Memory Quota: {memory_quota}")
        console.print(f"   • Storage Quota: {storage_quota}")
        console.print(f"   • Environments: {', '.join(env_list)}")
        
        if not click.confirm("\nProceed with tenant creation?"):
            console.print("❌ [yellow]Operation cancelled[/yellow]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Creating tenant...", total=None)
            result = api_client.create_tenant(tenant_data)
        
        console.print(f"✅ [green]Successfully created tenant '{tenant_name}'![/green]")
        
        if 'namespaces' in result:
            console.print("🏷️  Created namespaces:")
            for namespace in result['namespaces']:
                console.print(f"   • {namespace}")
        
        console.print("\n💡 [dim]You can now configure your CLI to use this tenant:[/dim]")
        console.print(f"[yellow]spandak8s config set tenant.name {tenant_name}[/yellow]")
        
    except Exception as e:
        console.print(f"❌ [red]Error creating tenant: {e}[/red]")

@tenants_group.command('switch')
@click.argument('tenant_name')
@click.pass_context
def switch_tenant(ctx, tenant_name):
    """Switch to a different tenant"""
    config = ctx.obj['config']
    
    try:
        # Update configuration
        config.set('tenant.name', tenant_name)
        
        console.print(f"🔄 [green]Switched to tenant '{tenant_name}'[/green]")
        console.print("💡 [dim]All future commands will operate on this tenant[/dim]")
        
    except Exception as e:
        console.print(f"❌ [red]Error switching tenant: {e}[/red]")

@tenants_group.command('current')
@click.pass_context
def current_tenant(ctx):
    """Show current tenant"""
    config = ctx.obj['config']
    tenant_name = config.tenant_name
    
    console.print(f"🏢 Current tenant: [cyan]{tenant_name}[/cyan]")
    
    # Try to get additional info about the tenant
    try:
        api_client = ctx.obj['api_client']
        tenant_data = api_client.get_tenant_info(tenant_name)
        
        if 'status' in tenant_data:
            status = tenant_data['status']
            status_color = "green" if status == "active" else "red"
            console.print(f"📊 Status: [{status_color}]{status}[/{status_color}]")
        
        if 'environments' in tenant_data:
            environments = tenant_data['environments']
            console.print(f"🌍 Environments: {', '.join(environments)}")
            
    except Exception:
        # If we can't get tenant info, just show the name
        pass

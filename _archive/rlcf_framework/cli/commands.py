"""
RLCF CLI Commands

User-facing commands (rlcf-cli) and administrative commands (rlcf-admin).
"""

import click
import asyncio
import yaml
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Import backend modules
from .. import models
from ..database import SessionLocal, engine, Base
from ..config import load_model_config, load_task_config
from .. import seed_data
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================================
# Helper Functions
# ============================================================================

def get_event_loop():
    """Get or create event loop for async operations."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_async(coro):
    """Run async coroutine and return result."""
    loop = get_event_loop()
    return loop.run_until_complete(coro)


async def get_db_session() -> AsyncSession:
    """Get async database session."""
    async with SessionLocal() as session:
        return session


# ============================================================================
# USER-FACING CLI (rlcf-cli)
# ============================================================================

@click.group()
@click.version_option(version='0.1.0', prog_name='rlcf-cli')
def cli():
    """RLCF Command Line Interface - User commands for tasks, users, and feedback."""
    pass


# ----------------------------------------------------------------------------
# Tasks Commands
# ----------------------------------------------------------------------------

@cli.group()
def tasks():
    """Manage RLCF tasks."""
    pass


@tasks.command('create')
@click.argument('yaml_file', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Preview tasks without creating them')
def tasks_create(yaml_file, dry_run):
    """Create tasks from YAML file.

    Example:
        rlcf-cli tasks create tasks.yaml
    """
    try:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)

        tasks_data = data.get('tasks', [])

        if dry_run:
            click.echo(f"[DRY RUN] Would create {len(tasks_data)} tasks:")
            for i, task in enumerate(tasks_data, 1):
                click.echo(f"  {i}. {task.get('task_type', 'Unknown')} - {task.get('input_data', {}).get('question', 'N/A')[:50]}")
            return

        async def create_tasks():
            async with SessionLocal() as db:
                created = []
                for task_data in tasks_data:
                    task = models.LegalTask(
                        task_type=models.TaskType[task_data['task_type']],
                        input_data=task_data.get('input_data', {}),
                        ground_truth_data=task_data.get('ground_truth_data'),
                        status=models.TaskStatus.OPEN
                    )
                    db.add(task)
                    created.append(task)

                await db.commit()

                for task in created:
                    await db.refresh(task)

                return created

        created_tasks = run_async(create_tasks())

        click.echo(f"✅ Created {len(created_tasks)} tasks successfully!")
        for task in created_tasks:
            click.echo(f"  - Task ID: {task.id} ({task.task_type.value})")

    except Exception as e:
        click.echo(f"❌ Error creating tasks: {e}", err=True)
        sys.exit(1)


@tasks.command('list')
@click.option('--status', type=click.Choice(['OPEN', 'BLIND_EVALUATION', 'AGGREGATED', 'CLOSED']), help='Filter by status')
@click.option('--limit', default=20, help='Maximum number of tasks to display')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def tasks_list(status, limit, output_format):
    """List all tasks with optional filtering.

    Example:
        rlcf-cli tasks list --status OPEN --limit 10
    """
    async def fetch_tasks():
        async with SessionLocal() as db:
            query = select(models.LegalTask)

            if status:
                query = query.where(models.LegalTask.status == models.TaskStatus[status])

            query = query.order_by(models.LegalTask.created_at.desc()).limit(limit)

            result = await db.execute(query)
            return result.scalars().all()

    try:
        task_list = run_async(fetch_tasks())

        if output_format == 'json':
            tasks_json = [
                {
                    'id': t.id,
                    'task_type': t.task_type.value,
                    'status': t.status.value,
                    'created_at': t.created_at.isoformat() if t.created_at else None
                }
                for t in task_list
            ]
            click.echo(json.dumps(tasks_json, indent=2))
        else:
            # Table format
            click.echo("\n" + "="*80)
            click.echo(f"{'ID':<6} {'Type':<20} {'Status':<20} {'Created':<20}")
            click.echo("="*80)

            for task in task_list:
                created = task.created_at.strftime('%Y-%m-%d %H:%M') if task.created_at else 'N/A'
                click.echo(f"{task.id:<6} {task.task_type.value:<20} {task.status.value:<20} {created:<20}")

            click.echo("="*80)
            click.echo(f"\nTotal: {len(task_list)} tasks")

    except Exception as e:
        click.echo(f"❌ Error listing tasks: {e}", err=True)
        sys.exit(1)


@tasks.command('export')
@click.argument('task_id', type=int)
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml']), default='json', help='Export format')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
def tasks_export(task_id, output_format, output):
    """Export task details and aggregated results.

    Example:
        rlcf-cli tasks export 123 --format json -o task_123.json
    """
    async def fetch_task_data():
        async with SessionLocal() as db:
            result = await db.execute(
                select(models.LegalTask).where(models.LegalTask.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                return None

            # Fetch feedbacks
            feedbacks_result = await db.execute(
                select(models.Feedback)
                .join(models.Response)
                .where(models.Response.task_id == task_id)
            )
            feedbacks = feedbacks_result.scalars().all()

            return {
                'task': {
                    'id': task.id,
                    'task_type': task.task_type.value,
                    'status': task.status.value,
                    'input_data': task.input_data,
                    'ground_truth_data': task.ground_truth_data,
                    'created_at': task.created_at.isoformat() if task.created_at else None
                },
                'feedbacks': [
                    {
                        'user_id': f.user_id,
                        'feedback_data': f.feedback_data,
                        'submitted_at': f.submitted_at.isoformat() if f.submitted_at else None
                    }
                    for f in feedbacks
                ]
            }

    try:
        data = run_async(fetch_task_data())

        if data is None:
            click.echo(f"❌ Task {task_id} not found", err=True)
            sys.exit(1)

        if output_format == 'yaml':
            output_str = yaml.dump(data, default_flow_style=False)
        else:
            output_str = json.dumps(data, indent=2)

        if output:
            with open(output, 'w') as f:
                f.write(output_str)
            click.echo(f"✅ Exported task {task_id} to {output}")
        else:
            click.echo(output_str)

    except Exception as e:
        click.echo(f"❌ Error exporting task: {e}", err=True)
        sys.exit(1)


# ----------------------------------------------------------------------------
# Users Commands
# ----------------------------------------------------------------------------

@cli.group()
def users():
    """Manage RLCF users."""
    pass


@users.command('create')
@click.argument('username')
@click.option('--authority-score', type=float, default=0.0, help='Initial authority score')
def users_create(username, authority_score):
    """Create a new user.

    Example:
        rlcf-cli users create john_doe --authority-score 0.5
    """
    async def create_user():
        async with SessionLocal() as db:
            user = models.User(
                username=username,
                authority_score=authority_score,
                track_record_score=0.0,
                baseline_credential_score=0.0
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user

    try:
        user = run_async(create_user())
        click.echo(f"✅ Created user: {user.username} (ID: {user.id})")
    except Exception as e:
        click.echo(f"❌ Error creating user: {e}", err=True)
        sys.exit(1)


@users.command('list')
@click.option('--limit', default=50, help='Maximum number of users to display')
@click.option('--sort-by', type=click.Choice(['id', 'username', 'authority_score']), default='id', help='Sort field')
def users_list(limit, sort_by):
    """List all users.

    Example:
        rlcf-cli users list --sort-by authority_score --limit 10
    """
    async def fetch_users():
        async with SessionLocal() as db:
            query = select(models.User)

            if sort_by == 'id':
                query = query.order_by(models.User.id)
            elif sort_by == 'username':
                query = query.order_by(models.User.username)
            elif sort_by == 'authority_score':
                query = query.order_by(models.User.authority_score.desc())

            query = query.limit(limit)

            result = await db.execute(query)
            return result.scalars().all()

    try:
        user_list = run_async(fetch_users())

        click.echo("\n" + "="*80)
        click.echo(f"{'ID':<6} {'Username':<25} {'Authority':<15} {'Track Record':<15}")
        click.echo("="*80)

        for user in user_list:
            click.echo(f"{user.id:<6} {user.username:<25} {user.authority_score:<15.3f} {user.track_record_score:<15.3f}")

        click.echo("="*80)
        click.echo(f"\nTotal: {len(user_list)} users")

    except Exception as e:
        click.echo(f"❌ Error listing users: {e}", err=True)
        sys.exit(1)


# ============================================================================
# ADMIN CLI (rlcf-admin)
# ============================================================================

@click.group()
@click.version_option(version='0.1.0', prog_name='rlcf-admin')
def admin():
    """RLCF Admin CLI - Administrative commands for configuration, database, and server management."""
    pass


# ----------------------------------------------------------------------------
# Config Commands
# ----------------------------------------------------------------------------

@admin.group()
def config():
    """Manage RLCF configuration."""
    pass


@config.command('show')
@click.option('--type', 'config_type', type=click.Choice(['model', 'task', 'all']), default='all', help='Configuration type to show')
def config_show(config_type):
    """Display current configuration.

    Example:
        rlcf-admin config show --type model
    """
    try:
        if config_type in ['model', 'all']:
            model_config = load_model_config()
            click.echo("\n📋 Model Configuration:")
            click.echo("="*60)
            click.echo(yaml.dump(model_config.model_dump(), default_flow_style=False))

        if config_type in ['task', 'all']:
            task_config = load_task_config()
            click.echo("\n📋 Task Configuration:")
            click.echo("="*60)
            click.echo(yaml.dump(task_config.model_dump(), default_flow_style=False))

    except Exception as e:
        click.echo(f"❌ Error loading configuration: {e}", err=True)
        sys.exit(1)


@config.command('validate')
def config_validate():
    """Validate configuration files.

    Example:
        rlcf-admin config validate
    """
    try:
        # Try loading both configs
        model_config = load_model_config()
        task_config = load_task_config()

        click.echo("✅ model_config.yaml: Valid")
        click.echo("✅ task_config.yaml: Valid")
        click.echo("\n✨ All configurations are valid!")

    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {e}", err=True)
        sys.exit(1)


# ----------------------------------------------------------------------------
# Database Commands
# ----------------------------------------------------------------------------

@admin.group()
def db():
    """Database management commands."""
    pass


@db.command('migrate')
def db_migrate():
    """Run database migrations.

    Example:
        rlcf-admin db migrate
    """
    async def run_migrations():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    try:
        click.echo("🔄 Running database migrations...")
        run_async(run_migrations())
        click.echo("✅ Database migrations completed successfully!")
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}", err=True)
        sys.exit(1)


@db.command('seed')
@click.option('--users', default=5, help='Number of demo users to create')
@click.option('--tasks', default=10, help='Number of demo tasks to create')
def db_seed(users, tasks):
    """Seed database with demo data.

    Example:
        rlcf-admin db seed --users 10 --tasks 20
    """
    try:
        click.echo(f"🌱 Seeding database with {users} users and {tasks} tasks...")
        run_async(seed_data.seed_demo_data())
        click.echo("✅ Database seeded successfully!")
    except Exception as e:
        click.echo(f"❌ Seeding failed: {e}", err=True)
        sys.exit(1)


@db.command('reset')
@click.confirmation_option(prompt='⚠️  This will delete ALL data. Are you sure?')
def db_reset():
    """Reset database (delete all data).

    Example:
        rlcf-admin db reset
    """
    async def reset_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    try:
        click.echo("🗑️  Resetting database...")
        run_async(reset_db())
        click.echo("✅ Database reset completed!")
    except Exception as e:
        click.echo(f"❌ Reset failed: {e}", err=True)
        sys.exit(1)


# ----------------------------------------------------------------------------
# Server Commands
# ----------------------------------------------------------------------------

@admin.command('server')
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--port', default=8000, type=int, help='Server port')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def server_start(host, port, reload):
    """Start the RLCF backend server.

    Example:
        rlcf-admin server --host localhost --port 8080 --reload
    """
    import uvicorn

    try:
        click.echo(f"🚀 Starting RLCF server on {host}:{port}")
        if reload:
            click.echo("🔄 Auto-reload enabled (development mode)")

        uvicorn.run(
            "backend.rlcf_framework.main:app",
            host=host,
            port=port,
            reload=reload
        )
    except Exception as e:
        click.echo(f"❌ Server start failed: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Entry Points
# ============================================================================

if __name__ == '__main__':
    cli()

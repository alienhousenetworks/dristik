"""Initial Unified Enterprise Schema

Revision ID: 001_enterprise_schema
Revises: 
Create Date: 2026-10-31 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_enterprise_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False, unique=True),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='enterprise'),
        sa.Column('sso_enabled', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('sso_provider', sa.String(length=50), nullable=True),
        sa.Column('sso_metadata_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # 2. workspaces
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('org_id', 'slug', name='uq_workspaces_org_slug'),
    )
    op.create_index('idx_workspaces_org', 'workspaces', ['org_id'])

    # 3. domains
    op.create_table(
        'domains',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('workspace_id', sa.String(length=64), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('default_scheme', sa.String(length=10), nullable=False, server_default='https'),
        sa.Column('site_type', sa.String(length=50), nullable=False, server_default='b2b_saas'),
        sa.Column('crawl_frequency', sa.String(length=50), nullable=False, server_default='weekly'),
        sa.Column('max_pages', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_domains_workspace', 'domains', ['workspace_id'])
    op.create_index('ix_domains_hostname', 'domains', ['hostname'])

    # 4. audit_runs
    op.create_table(
        'audit_runs',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('domain_id', sa.String(length=64), sa.ForeignKey('domains.id', ondelete='CASCADE'), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('triggered_by', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('stage', sa.String(length=50), nullable=False, server_default='discovery'),
        sa.Column('tier', sa.String(length=50), nullable=True, server_default='enterprise'),
        sa.Column('pages_crawled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overall_score', sa.Integer(), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('evidence_coverage', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_audit_runs_domain', 'audit_runs', ['domain_id'])
    op.create_index('ix_audit_runs_domain_str', 'audit_runs', ['domain'])

    # 5. evidence_nodes
    op.create_table(
        'evidence_nodes',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('audit_run_id', sa.String(length=64), sa.ForeignKey('audit_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('storage_uri', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_evidence_nodes_run', 'evidence_nodes', ['audit_run_id'])
    op.create_index('idx_evidence_nodes_hash', 'evidence_nodes', ['content_hash'])

    # 6. findings
    op.create_table(
        'findings',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('audit_run_id', sa.String(length=64), sa.ForeignKey('audit_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('impact_explanation', sa.Text(), nullable=True),
        sa.Column('remediation_advice', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('suggested_patch', sa.JSON(), nullable=True),
        sa.Column('jira_issue_key', sa.String(length=50), nullable=True),
        sa.Column('github_pr_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='open'),
        sa.Column('remediation_status', sa.String(length=50), nullable=True, server_default='OPEN'),
        sa.Column('confidence', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('evidence_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_findings_run', 'findings', ['audit_run_id'])

    # 7. ai_citations
    op.create_table(
        'ai_citations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('domain_id', sa.String(length=64), sa.ForeignKey('domains.id', ondelete='CASCADE'), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('engine', sa.String(length=50), nullable=False),
        sa.Column('is_cited', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('citation_rank', sa.Integer(), nullable=True),
        sa.Column('cited_url', sa.Text(), nullable=True),
        sa.Column('extracted_snippet', sa.Text(), nullable=True),
        sa.Column('competitor_citations', sa.JSON(), nullable=True),
        sa.Column('queried_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_ai_citations_domain', 'ai_citations', ['domain_id'])

    # 8. enterprise_audit_logs
    op.create_table(
        'enterprise_audit_logs',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_audit_logs_org', 'enterprise_audit_logs', ['org_id'])

    # Supporting application tables: users, integrations
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), server_default='member'),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'integrations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('org_id', sa.String(length=64), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('credentials_encrypted', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('integrations')
    op.drop_table('users')
    op.drop_table('enterprise_audit_logs')
    op.drop_table('ai_citations')
    op.drop_table('findings')
    op.drop_table('evidence_nodes')
    op.drop_table('audit_runs')
    op.drop_table('domains')
    op.drop_table('workspaces')
    op.drop_table('organizations')

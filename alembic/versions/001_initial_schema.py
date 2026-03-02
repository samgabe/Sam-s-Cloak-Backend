"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('master_resume', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create job_applications table
    op.create_table(
        'job_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_title', sa.String(length=255), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('job_description', sa.Text(), nullable=False),
        sa.Column('job_url', sa.String(length=500), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('salary_range', sa.String(length=100), nullable=True),
        sa.Column('remote_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('ai_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('missing_keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_applications_user_id'), 'job_applications', ['user_id'], unique=False)
    op.create_index(op.f('ix_job_applications_status'), 'job_applications', ['status'], unique=False)
    
    # Create tailored_documents table
    op.create_table(
        'tailored_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('job_application_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_application_id'], ['job_applications.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tailored_documents_user_id'), 'tailored_documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_tailored_documents_job_application_id'), 'tailored_documents', ['job_application_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tailored_documents_job_application_id'), table_name='tailored_documents')
    op.drop_index(op.f('ix_tailored_documents_user_id'), table_name='tailored_documents')
    op.drop_table('tailored_documents')
    
    op.drop_index(op.f('ix_job_applications_status'), table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_user_id'), table_name='job_applications')
    op.drop_table('job_applications')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

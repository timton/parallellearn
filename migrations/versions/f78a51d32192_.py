"""empty message

Revision ID: f78a51d32192
Revises: 
Create Date: 2018-06-26 12:04:40.897715

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f78a51d32192'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('projects', 'episode',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('projects', 'season',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.create_unique_constraint(None, 'users', ['email'])
    op.create_unique_constraint(None, 'users', ['username'])
    op.alter_column('versions', 'rating',
               existing_type=postgresql.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.alter_column('versions', 'source',
               existing_type=sa.TEXT(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('versions', 'source',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('versions', 'rating',
               existing_type=postgresql.DOUBLE_PRECISION(precision=53),
               nullable=False)
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_constraint(None, 'users', type_='unique')
    op.alter_column('projects', 'season',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('projects', 'episode',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
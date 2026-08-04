"""initial schema

Revision ID: 1004823f51b2
Revises: 
Create Date: 2026-08-01 15:25:23.582861

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "1004823f51b2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("title", sa.JSON(), nullable=False),
        sa.Column("excerpt", sa.JSON(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("cover_image_url", sa.String(length=1024), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("meta_title", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.String(length=512), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_blog_posts_active_published",
        "blog_posts",
        ["is_active", "published_at"],
        unique=False,
    )
    op.create_index("ix_blog_posts_is_active", "blog_posts", ["is_active"], unique=False)
    op.create_index(
        "ix_blog_posts_published_at", "blog_posts", ["published_at"], unique=False
    )
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=True)

    op.create_table(
        "cv_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.JSON(), nullable=False),
        sa.Column("preview_image_url", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cv_templates_is_active", "cv_templates", ["is_active"], unique=False
    )
    op.create_index("ix_cv_templates_slug", "cv_templates", ["slug"], unique=True)
    op.create_index(
        "ix_cv_templates_sort_order", "cv_templates", ["sort_order"], unique=False
    )

    op.create_table(
        "packages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.JSON(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("max_revisions", sa.Integer(), nullable=False),
        sa.Column("includes_letter", sa.Boolean(), nullable=False),
        sa.Column("includes_linkedin", sa.Boolean(), nullable=False),
        sa.Column("priority_support", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_packages_is_active", "packages", ["is_active"], unique=False)
    op.create_index("ix_packages_price", "packages", ["price"], unique=False)
    op.create_index("ix_packages_slug", "packages", ["slug"], unique=True)
    op.create_index("ix_packages_sort_order", "packages", ["sort_order"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=False)
    op.create_index("idx_users_is_admin", "users", ["is_admin"], unique=False)

    op.create_table(
        "vouchers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "discount_type",
            sa.Enum("PERCENTAGE", "FIXED", name="discount_type"),
            nullable=False,
        ),
        sa.Column("discount_value", sa.Integer(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vouchers_code", "vouchers", ["code"], unique=True)
    op.create_index("ix_vouchers_is_active", "vouchers", ["is_active"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("package_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.String(length=255), nullable=True),
        sa.Column("payment_status", sa.String(length=50), nullable=False),
        sa.Column("voucher_code", sa.String(length=100), nullable=True),
        sa.Column("discount_amount", sa.Integer(), nullable=False),
        sa.Column("cv_data", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_orders_progress_between_0_and_100",
        ),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["cv_templates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_orders_status", "orders", ["status"], unique=False)
    op.create_index("idx_orders_user_id", "orders", ["user_id"], unique=False)
    op.create_index("ix_orders_package_id", "orders", ["package_id"], unique=False)
    op.create_index("ix_orders_payment_id", "orders", ["payment_id"], unique=False)
    op.create_index(
        "ix_orders_payment_status", "orders", ["payment_status"], unique=False
    )
    op.create_index("ix_orders_template_id", "orders", ["template_id"], unique=False)
    op.create_index(
        "ix_orders_user_status", "orders", ["user_id", "status"], unique=False
    )
    op.create_index("ix_orders_voucher_code", "orders", ["voucher_code"], unique=False)

    op.create_table(
        "portfolio_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.JSON(), nullable=False),
        sa.Column("description", sa.JSON(), nullable=True),
        sa.Column("template_id", sa.String(length=36), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=False),
        sa.Column("pdf_url", sa.String(length=1024), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["cv_templates.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_portfolio_items_category", "portfolio_items", ["category"], unique=False
    )
    op.create_index(
        "ix_portfolio_items_is_active", "portfolio_items", ["is_active"], unique=False
    )
    op.create_index(
        "ix_portfolio_items_sort_order",
        "portfolio_items",
        ["sort_order"],
        unique=False,
    )
    op.create_index(
        "ix_portfolio_items_template_id",
        "portfolio_items",
        ["template_id"],
        unique=False,
    )

    op.create_table(
        "files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column(
            "file_type",
            sa.Enum(
                "PHOTO",
                "CERTIFICATE",
                "DIPLOMA",
                "DOCUMENT",
                "RESULT_PDF",
                name="file_type",
            ),
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_files_order_id", "files", ["order_id"], unique=False)
    op.create_index("ix_files_file_type", "files", ["file_type"], unique=False)
    op.create_index("ix_files_order_type", "files", ["order_id", "file_type"], unique=False)

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("old_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("old_progress", sa.Integer(), nullable=True),
        sa.Column("new_progress", sa.Integer(), nullable=False),
        sa.Column("changed_by", sa.String(length=128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_order_history_order_id",
        "order_status_history",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_order_status_history_changed_by",
        "order_status_history",
        ["changed_by"],
        unique=False,
    )
    op.create_index(
        "ix_order_status_history_new_status",
        "order_status_history",
        ["new_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_order_status_history_new_status", table_name="order_status_history")
    op.drop_index("ix_order_status_history_changed_by", table_name="order_status_history")
    op.drop_index("idx_order_history_order_id", table_name="order_status_history")
    op.drop_table("order_status_history")

    op.drop_index("ix_files_order_type", table_name="files")
    op.drop_index("ix_files_file_type", table_name="files")
    op.drop_index("idx_files_order_id", table_name="files")
    op.drop_table("files")

    op.drop_index("ix_portfolio_items_template_id", table_name="portfolio_items")
    op.drop_index("ix_portfolio_items_sort_order", table_name="portfolio_items")
    op.drop_index("ix_portfolio_items_is_active", table_name="portfolio_items")
    op.drop_index("ix_portfolio_items_category", table_name="portfolio_items")
    op.drop_table("portfolio_items")

    op.drop_index("ix_orders_voucher_code", table_name="orders")
    op.drop_index("ix_orders_user_status", table_name="orders")
    op.drop_index("ix_orders_template_id", table_name="orders")
    op.drop_index("ix_orders_payment_status", table_name="orders")
    op.drop_index("ix_orders_payment_id", table_name="orders")
    op.drop_index("ix_orders_package_id", table_name="orders")
    op.drop_index("idx_orders_user_id", table_name="orders")
    op.drop_index("idx_orders_status", table_name="orders")
    op.drop_table("orders")

    op.drop_index("ix_vouchers_is_active", table_name="vouchers")
    op.drop_index("ix_vouchers_code", table_name="vouchers")
    op.drop_table("vouchers")

    op.drop_index("idx_users_is_admin", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_packages_sort_order", table_name="packages")
    op.drop_index("ix_packages_slug", table_name="packages")
    op.drop_index("ix_packages_price", table_name="packages")
    op.drop_index("ix_packages_is_active", table_name="packages")
    op.drop_table("packages")

    op.drop_index("ix_cv_templates_sort_order", table_name="cv_templates")
    op.drop_index("ix_cv_templates_slug", table_name="cv_templates")
    op.drop_index("ix_cv_templates_is_active", table_name="cv_templates")
    op.drop_table("cv_templates")

    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.drop_index("ix_blog_posts_published_at", table_name="blog_posts")
    op.drop_index("ix_blog_posts_is_active", table_name="blog_posts")
    op.drop_index("ix_blog_posts_active_published", table_name="blog_posts")
    op.drop_table("blog_posts")

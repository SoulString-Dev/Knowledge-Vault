"""ORM 模型汇总：alembic autogenerate 与元数据注册入口。"""

from app.models.annotation import Annotation
from app.models.article import Article
from app.models.base import Base
from app.models.job import Job
from app.models.refresh_token import RefreshToken
from app.models.tag import ArticleTag, Tag
from app.models.user import User

__all__ = [
    "Annotation",
    "Article",
    "ArticleTag",
    "Base",
    "Job",
    "RefreshToken",
    "Tag",
    "User",
]

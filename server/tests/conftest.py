"""测试全局环境：在任何 app 模块导入前设置好配置。"""

import os
import tempfile

os.environ.setdefault("SECRET_KEY", "x" * 48)  # ≥32 字节，避免 HS256 密钥长度告警
os.environ.setdefault("LLM_BASE_URL", "http://localhost:9999/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("REGISTER_MODE", "open")
os.environ.setdefault("APP_DATA_DIR", tempfile.mkdtemp(prefix="kb-test-app-data-"))
os.environ.setdefault("EMBEDDING_DIM", "1024")

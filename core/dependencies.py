from fastapi.security import HTTPBearer, APIKeyHeader

# Access Token (Authorization: Bearer <token>)
access_security = HTTPBearer(auto_error=True)

# Refresh Token (X-Refresh-Token: <token>)
refresh_security = APIKeyHeader(name="X-Refresh-Token", auto_error=True)

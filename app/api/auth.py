from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.db import execute_query, execute_write
from app.utils.crypto import verify_password, get_password_hash, create_access_token, decode_access_token
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Schemas Pydantic
class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    must_change_password: bool

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency para validar o token JWT e retornar o username do admin logado.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload["sub"]

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    """
    Realiza o login administrativo verificando as credenciais no SQLite.
    """
    rows = execute_query("SELECT password_hash, must_change_password FROM admin_users WHERE username = ?", (data.username,))
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos."
        )
        
    admin = rows[0]
    if not verify_password(data.password, admin["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos."
        )

    # Gera token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": data.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "must_change_password": bool(admin["must_change_password"])
    }

@router.post("/change-password")
def change_password(data: PasswordChangeRequest, current_user: str = Depends(get_current_admin)):
    """
    Permite alterar a senha administrativa.
    """
    rows = execute_query("SELECT password_hash FROM admin_users WHERE username = ?", (current_user,))
    if not rows:
        raise HTTPException(status_code=404, detail="Administrador não encontrado.")
        
    admin = rows[0]
    if not verify_password(data.old_password, admin["password_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    new_hash = get_password_hash(data.new_password)
    execute_write(
        "UPDATE admin_users SET password_hash = ?, must_change_password = 0, updated_at = datetime('now', 'localtime') WHERE username = ?",
        (new_hash, current_user)
    )
    
    return {"message": "Senha alterada com sucesso."}

@router.get("/me")
def get_me(current_user: str = Depends(get_current_admin)):
    """
    Verifica se o token é válido e retorna o usuário atual.
    """
    rows = execute_query("SELECT username, must_change_password FROM admin_users WHERE username = ?", (current_user,))
    if not rows:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return {"username": rows[0]["username"], "must_change_password": bool(rows[0]["must_change_password"])}

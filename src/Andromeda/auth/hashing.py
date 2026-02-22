from argon2 import PasswordHasher


ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536, # 64 MB
    parallelism=2
)


def hash_secret(unhashed_secret: str) -> str:
    if len(unhashed_secret) != 43:
        raise ValueError(f"unhashed_secret must be 43 characters, got {len(unhashed_secret)}")
    
    return ph.hash(unhashed_secret)


def verify_secret(hashed_secret: str, unhashed_secret: str) -> bool:
    try:
        return ph.verify(hashed_secret, unhashed_secret)
    except Exception:
        return False
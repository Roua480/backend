import pyotp


def create_totp_secret() -> str:
    return pyotp.random_base32()


def make_otpauth_uri(secret: str, email: str, issuer: str = "PolyLab") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


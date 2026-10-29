from pwdlib import PasswordHash
password_hash = PasswordHash.recommended()
hashed = password_hash.hash("1234")
print(hashed)
print(password_hash.verify("1234", hashed))
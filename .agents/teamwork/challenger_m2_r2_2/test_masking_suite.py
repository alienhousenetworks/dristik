import sys
from pathlib import Path

# Ensure backend is on sys.path
backend_path = Path("/Users/sayantande/Downloads/dristik-main/backend")
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.db.session import mask_database_url

def test_mask_database_url_passwords():
    test_passwords = [
        # Multiple @ characters
        "p@ssword",
        "p@ss@word",
        "p@@ss@@w@@rd",
        "@@@@@",
        "@leading",
        "trailing@",
        
        # Quotes
        'p"assword',
        "p'assword",
        "p`assword",
        '"quoted"',
        "'single'",
        '`backtick`',
        'p"a\'s`s',
        '""',
        
        # Colons
        "pass:word",
        "p:a:s:s",
        ":leading_colon",
        "trailing_colon:",
        ":::",
        
        # Slashes
        "pass/word",
        "p//ss",
        "/leading_slash",
        "trailing_slash/",
        "pass%2Fword",
        "pass\\word",
        
        # Combined special chars
        "p@ss:word/123",
        "p@ss/word@123",
        "p\"a:s@s/w'o`r\\d",
        
        # Unicode
        "pässwörd",
        "密码123",
        "пароль123",
        "كلمة_السر",
        "🔑🔓🛡️",
        "сложный_пароль_!@#$%^&*()",
        "日本語パスワード",
        "한국어비밀번호",
        "üñîçødé_tëst",
        "Emoji_🔥_🚀_💻",
        
        # Empty and simple
        "",
        "simplepassword",
        "123456",
        " "
    ]
    
    results = []
    print("=" * 80)
    print("TESTING mask_database_url WITH ADVERSARIAL PASSWORDS")
    print("=" * 80)
    
    for pwd in test_passwords:
        url = f"postgresql://testuser:{pwd}@localhost:5432/dristik_db"
        try:
            masked = mask_database_url(url)
            
            # Check for credential leakage:
            # If pwd is non-trivial, check if significant substring or exact pwd leaked
            leaked = False
            leak_details = []
            
            # Check exact pwd in masked (if length > 0)
            if len(pwd.strip()) > 0 and pwd in masked:
                leaked = True
                leak_details.append(f"exact password '{pwd}' found in output")
            
            # Check if parts of pwd leaked (for passwords with @, :, /)
            for part in [p for p in pwd.replace("@", " ").replace(":", " ").replace("/", " ").split() if len(p) >= 3]:
                if part in masked and part not in ["localhost", "5432", "dristik_db", "testuser", "postgresql"]:
                    leaked = True
                    leak_details.append(f"password fragment '{part}' leaked in output")
                    
            status = "FAIL (LEAK)" if leaked else "PASS"
            results.append((pwd, url, masked, status, leak_details))
            print(f"[{status}] Pwd: {pwd!r}")
            print(f"       Masked: {masked}")
            if leak_details:
                print(f"       Details: {', '.join(leak_details)}")
        except Exception as exc:
            results.append((pwd, url, str(exc), "ERROR", [str(exc)]))
            print(f"[ERROR] Pwd: {pwd!r} -> Exception: {exc}")
            
    print("=" * 80)
    passed = sum(1 for r in results if r[3] == "PASS")
    failed = sum(1 for r in results if r[3] != "PASS")
    print(f"TOTAL: {len(results)} | PASSED: {passed} | FAILED/LEAKED: {failed}")
    print("=" * 80)
    return results

if __name__ == "__main__":
    test_mask_database_url_passwords()

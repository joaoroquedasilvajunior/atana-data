"""rais__generate_pis_salt.py — one-time setup before Sprint 1 ETL.

Generates a 32-byte random salt for PIS/PASEP hashing. Prints it to stdout so
the operator can store it in 1Password and add it to their shell environment.

NEVER commit the salt. NEVER re-generate the salt after the first ETL run
(doing so will produce a different hash space and break the longitudinal panel).

Usage:
    python rais__generate_pis_salt.py

Recommended workflow:
    1. Run this script once on João's machine
    2. Copy the printed salt to 1Password under "Atana — PIS hashing salt"
    3. Add to ~/.zshrc (or equivalent):
         export ATANA_PIS_SALT='<paste here>'
    4. Restart shell or `source ~/.zshrc`
    5. Verify: `echo $ATANA_PIS_SALT | wc -c` should print 65 (64 hex + newline)
    6. Never run this script again. If the salt is ever lost, the entire ETL
       must be re-run from year 2014 onward to rebuild the hash space.
"""

import secrets
import sys
import os


def main():
    if os.environ.get("ATANA_PIS_SALT"):
        print("ATANA_PIS_SALT is already set in your environment.", file=sys.stderr)
        print("Refusing to generate a new one — running this twice would break", file=sys.stderr)
        print("the longitudinal panel. If you really want a new salt, unset", file=sys.stderr)
        print("ATANA_PIS_SALT first AND understand the consequences.", file=sys.stderr)
        sys.exit(1)

    salt = secrets.token_hex(32)  # 32 bytes = 64 hex chars
    print(salt)
    print(file=sys.stderr)
    print("=" * 64, file=sys.stderr)
    print("Salt generated. Next steps:", file=sys.stderr)
    print("  1. Copy the value above to 1Password", file=sys.stderr)
    print("  2. Add to ~/.zshrc:", file=sys.stderr)
    print(f"       export ATANA_PIS_SALT='{salt}'", file=sys.stderr)
    print("  3. Restart shell, then run the ETL", file=sys.stderr)
    print("  4. NEVER run this script again", file=sys.stderr)
    print("=" * 64, file=sys.stderr)


if __name__ == "__main__":
    main()

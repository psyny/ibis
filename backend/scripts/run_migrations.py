import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ALEMBIC_DIR = os.path.join(os.path.dirname(HERE), "ibis")


def main() -> int:
    print("Running Alembic migrations...")
    result = subprocess.run(["alembic", "upgrade", "head"], cwd=ALEMBIC_DIR)
    if result.returncode != 0:
        print("Alembic migrations failed")
        return result.returncode
    print("Alembic migrations completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

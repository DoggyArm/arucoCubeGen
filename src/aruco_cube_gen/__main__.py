from .config import Config
from .generate import generate_all

def main():
    cfg = Config()
    out_dir = generate_all(cfg)
    print(f"Done. Outputs in: {out_dir}")

if __name__ == "__main__":
    main()

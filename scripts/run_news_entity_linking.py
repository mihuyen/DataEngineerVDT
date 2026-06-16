from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.transform.news_entity_linking import run


def main() -> None:
    result = run()
    print("News entity linking completed")
    for key, value in result.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()

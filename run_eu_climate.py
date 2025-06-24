#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now we can import from eu_climate
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            from eu_climate.scripts.demo_web_exports import main
            main()
        elif sys.argv[1] == "main":
            from eu_climate.main import main
            main()
    else:
        print("Usage: python3 run_eu_climate.py [demo|main]")

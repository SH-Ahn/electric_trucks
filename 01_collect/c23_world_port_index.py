"""World Port Index (US NGA Pub. 150): ~3,800 ports with coordinates, harbour size and type.

Ports anchor drayage, the urban-freight segment that electrifies first (China, California,
Rotterdam), and are the main sites for NO2 and health co-benefit analysis.

Source: https://msi.nga.mil/Publications/WPI
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import RAW_DIR  # noqa: E402
from helpers import download  # noqa: E402

URL = "https://msi.nga.mil/api/publications/download?key=16920959/SFH00000/UpdatedPub150.csv&type=view"


def main() -> None:
    p = download(URL, RAW_DIR / "world_port_index" / "world_port_index.csv", source="NGA World Port Index",
                 headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}, overwrite=True)
    print(f"ok {p.name} ({p.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()

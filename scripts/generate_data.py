import argparse
import json
from pathlib import Path

from supplytwin.data import write_sample
from supplytwin.domain import Network, Scenario

parser = argparse.ArgumentParser(description="Generate reproducible synthetic SupplyTwin networks")
parser.add_argument("--seed", type=int, default=17)
parser.add_argument("--scale", type=int, default=1)
parser.add_argument("--output", type=Path, default=Path("data/sample"))
args = parser.parse_args()
write_sample(args.output, args.seed, args.scale)
Path("data/schemas").mkdir(parents=True, exist_ok=True)

for model in [Network, Scenario]:
    Path(f"data/schemas/{model.__name__.lower()}.schema.json").write_text(
        json.dumps(model.model_json_schema(), indent=2)
    )
print(f"Generated seed={args.seed}, scale={args.scale} → {args.output}")

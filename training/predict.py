from __future__ import annotations
import argparse
import json
from nlp.inference import predict

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("query", help="Question text")
    args = parser.parse_args(); print(json.dumps(predict(args.query), ensure_ascii=False, indent=2))

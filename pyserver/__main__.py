#!/usr/bin/env python3
import argparse
import asyncio
import logging


from .server.serve import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="PythonWorkerService (assistant.v1)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(serve(args.host, args.port))


if __name__ == "__main__":
    main()

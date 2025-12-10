
#!/usr/bin/env python3
import argparse
import asyncio
import logging
import signal
import time
from typing import Optional

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

import protobufs.gen.py.protobufs.apis.services.pyserver_api_pb2_grpc as rpc
from .server import PythonWorkerService,TTSQueue

async def serve(host: str, port: int) -> None:
    server = grpc.aio.server()

    # Health service
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=None,
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    # App services
    tts = TTSQueue()
    await tts.start()
    worker = PythonWorkerService(tts)
    rpc.add_PythonWorkerServiceServicer_to_server(worker, server)

    bind_addr = f"{host}:{port}"
    server.add_insecure_port(bind_addr) 
    logging.getLogger("server").info("PythonWorkerService listening on %s", bind_addr)

    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("grpc.health.v1.Health", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("assistant.v1.PythonWorkerService", health_pb2.HealthCheckResponse.SERVING)

    await server.start()

    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_running_loop().add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass  # Windows

    await stop_event.wait()
    logging.getLogger("server").info("Shutting down...")

    # Health: not serving
    health_servicer.set("", health_pb2.HealthCheckResponse.NOT_SERVING)
    health_servicer.set("assistant.v1.PythonWorkerService", health_pb2.HealthCheckResponse.NOT_SERVING)

    await server.stop(grace=None)  # allow in-flight RPCs to finish
    await tts.stop()


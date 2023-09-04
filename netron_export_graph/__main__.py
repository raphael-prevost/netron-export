import argparse
from ._netron_export_graph import export_graph

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("model_path", help="Path to model file (onnx, pt, etc.)")
    argparser.add_argument("--output",
                           "-o",
                           default="./network.png",
                           help="Output file to be written (either svg or png)")
    argparser.add_argument("--timeout", "-t", default=5000, type=int, help="Timeout for requests in ms")
    argparser.add_argument("--port",
                           "-p",
                           default=8487,
                           type=int,
                           help="Port that will be used to serve the Netron app")
    args = argparser.parse_args()

    export_graph(args.model_path, args.output, args.port, args.timeout)

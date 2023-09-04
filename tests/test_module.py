import os
import sys
import runpy
import tempfile
import pytest

import torch

@pytest.mark.parametrize("ext", ["svg", "png"])
def test_main(ext):
    """
    This is a smoke test that does not check for validity of results.
    """
    model = torch.nn.Sequential(torch.nn.Linear(10, 10))
    model.eval()

    with tempfile.TemporaryDirectory() as temp_dir:
        model_path = os.path.join(temp_dir, "model.onnx")
        output_path = os.path.join(temp_dir, f"model.{ext}")
        torch.onnx.export(model, torch.rand(1, 10), model_path)

        sys.argv = ['', "--output", output_path, model_path]
        runpy.run_module("netron_export_graph", run_name="__main__")

        assert os.path.isfile(output_path), f"{output_path} not created"


if __name__ == '__main__':
    pytest.main()

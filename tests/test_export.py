import os
import tempfile
import pytest

import torch

from netron_export_graph import export_graph

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

        export_graph(model_path, output_path, port=8487, timeout=5000)

        assert os.path.isfile(output_path), f"{output_path} not created"


if __name__ == '__main__':
    pytest.main()

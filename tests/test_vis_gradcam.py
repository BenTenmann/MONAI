# Copyright 2020 - 2021 MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import numpy as np
import torch
from parameterized import parameterized

from monai.networks.nets import DenseNet, DenseNet121, SEResNet50
from monai.visualize import GradCAM

# 2D
TEST_CASE_0 = [
    {
        "model": "densenet2d",
        "shape": (2, 1, 48, 64),
        "feature_shape": (2, 1, 1, 2),
        "target_layers": "class_layers.relu",
    },
    (2, 1, 48, 64),
]
# 3D
TEST_CASE_1 = [
    {
        "model": "densenet3d",
        "shape": (2, 1, 6, 6, 6),
        "feature_shape": (2, 1, 2, 2, 2),
        "target_layers": "class_layers.relu",
    },
    (2, 1, 6, 6, 6),
]
# 2D
TEST_CASE_2 = [
    {
        "model": "senet2d",
        "shape": (2, 3, 64, 64),
        "feature_shape": (2, 1, 2, 2),
        "target_layers": "layer4",
    },
    (2, 1, 64, 64),
]

# 3D
TEST_CASE_3 = [
    {
        "model": "senet3d",
        "shape": (2, 3, 8, 8, 48),
        "feature_shape": (2, 1, 1, 1, 2),
        "target_layers": "layer4",
    },
    (2, 1, 8, 8, 48),
]


class TestGradientClassActivationMap(unittest.TestCase):
    @parameterized.expand([TEST_CASE_0, TEST_CASE_1, TEST_CASE_2, TEST_CASE_3])
    def test_shape(self, input_data, expected_shape):
        if input_data["model"] == "densenet2d":
            model = DenseNet121(spatial_dims=2, in_channels=1, out_channels=3)
        if input_data["model"] == "densenet3d":
            model = DenseNet(
                spatial_dims=3, in_channels=1, out_channels=3, init_features=2, growth_rate=2, block_config=(6,)
            )
        if input_data["model"] == "senet2d":
            model = SEResNet50(spatial_dims=2, in_channels=3, num_classes=4)
        if input_data["model"] == "senet3d":
            model = SEResNet50(spatial_dims=3, in_channels=3, num_classes=4)
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()
        cam = GradCAM(nn_module=model, target_layers=input_data["target_layers"])
        image = torch.rand(input_data["shape"], device=device)
        result = cam(x=image, layer_idx=-1)
        np.testing.assert_array_equal(cam.nn_module.class_idx.cpu(), model(image).max(1)[-1].cpu())
        fea_shape = cam.feature_map_size(input_data["shape"], device=device)
        self.assertTupleEqual(fea_shape, input_data["feature_shape"])
        self.assertTupleEqual(result.shape, expected_shape)
        # check result is same whether class_idx=None is used or not
        result2 = cam(x=image, layer_idx=-1, class_idx=model(image).max(1)[-1].cpu())
        torch.testing.assert_allclose(result, result2)

    def test_ill(self):
        model = DenseNet121(spatial_dims=2, in_channels=1, out_channels=3)
        for name, x in model.named_parameters():
            if "features" in name:
                x.requires_grad = False
        cam = GradCAM(nn_module=model, target_layers="class_layers.relu")
        image = torch.rand((2, 1, 48, 64))
        with self.assertRaises(RuntimeError):
            cam(x=image)


if __name__ == "__main__":
    unittest.main()

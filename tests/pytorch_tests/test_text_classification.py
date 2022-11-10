#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: EPL-2.0
#

import os
import pytest
import shutil
import tempfile

from tlt.datasets import dataset_factory
from tlt.models import model_factory


@pytest.mark.pytorch
@pytest.mark.parametrize('model_name,dataset_name',
                         [['bert-base-cased', 'imdb'],
                          ['distilbert-base-uncased', 'imdb']])
def test_pyt_text_classification(model_name, dataset_name):
    """
    Tests basic transfer learning functionality for PyTorch text classification models using a hugging face dataset
    """
    framework = 'pytorch'
    output_dir = tempfile.mkdtemp()

    # Get the dataset
    dataset = dataset_factory.get_dataset('/tmp/data', 'text_classification', framework, dataset_name,
                                          'huggingface', split=["train"], shuffle_files=False)

    # Get the model
    model = model_factory.get_model(model_name, framework)

    # Preprocess the dataset
    dataset.preprocess(model_name, batch_size=32)
    dataset.shuffle_split(train_pct=0.05, val_pct=0.05, seed=10)
    assert dataset._validation_type == 'shuffle_split'

    # Evaluate before training
    pretrained_metrics = model.evaluate(dataset)
    assert len(pretrained_metrics) > 0

    # Train
    model.train(dataset, output_dir=output_dir, epochs=1, do_eval=False)

    # Evaluate
    trained_metrics = model.evaluate(dataset)
    assert trained_metrics[0] <= pretrained_metrics[0]  # loss
    assert trained_metrics[1] >= pretrained_metrics[1]  # accuracy

    # Export the saved model
    model.export(output_dir)
    saved_model_dir = os.path.join(output_dir, model_name)
    assert os.path.isdir(saved_model_dir)
    assert os.path.isfile(os.path.join(saved_model_dir, "pytorch_model.bin"))

    # Reload the saved model
    reload_model = model_factory.get_model(model_name, framework)
    reload_model.load_from_directory(saved_model_dir)

    # Evaluate
    reload_metrics = reload_model.evaluate(dataset)
    assert reload_metrics == trained_metrics

    # Ensure we get 'NotImplementedError' for graph_optimization
    with pytest.raises(NotImplementedError):
        model.optimize_graph(saved_model_dir, os.path.join(saved_model_dir, 'optimized'))

    # Delete the temp output directory
    if os.path.exists(output_dir) and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)

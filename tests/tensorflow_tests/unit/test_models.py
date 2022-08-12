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

import pytest

from unittest.mock import MagicMock, patch

from test_utils import platform_config
from tlt.models import model_factory
from tlt.utils.types import FrameworkType, UseCaseType

try:
    # Do TF specific imports in a try/except to prevent pytest test loading from failing when running in a PyTorch env
    from tlt.models.image_classification.tfhub_image_classification_model import TFHubImageClassificationModel
except ModuleNotFoundError as e:
    TFHubImageClassificationModel = None
    print("WARNING: Unable to import TFHubImageClassificationModel. TensorFlow may not be installed")


try:
    # Do TF specific imports in a try/except to prevent pytest test loading from failing when running in a PyTorch env
    from tlt.models.text_classification.tfhub_text_classification_model import TFHubTextClassificationModel
except ModuleNotFoundError as e:
    TFHubTextClassificationModel = None
    print("WARNING: Unable to import TFHubTextClassificationModel. TensorFlow may not be installed")

from tlt.datasets.image_classification.image_classification_dataset import ImageClassificationDataset
from tlt.datasets.text_classification.text_classification_dataset import TextClassificationDataset


@pytest.mark.tensorflow
@pytest.mark.parametrize('model_name,expected_class,expected_image_size',
                         [['efficientnet_b0', TFHubImageClassificationModel, 224],
                          ['small_bert/bert_en_uncased_L-2_H-128_A-2', TFHubTextClassificationModel, None]])
def test_tfhub_model_load(model_name, expected_class, expected_image_size):
    """
    Checks that a model can be downloaded form TF Hub
    """
    model = model_factory.get_model(model_name, 'tensorflow')
    assert type(model) == expected_class
    if expected_image_size:
        assert model.image_size == expected_image_size


@pytest.mark.tensorflow
@pytest.mark.parametrize('model_name,use_case',
                         [['efficientnet_b0', 'image_classification'],
                          ['small_bert/bert_en_uncased_L-2_H-128_A-2', 'text_classification']])
def test_get_supported_models(model_name, use_case):
    """
    Call get supported models and checks to make sure the dictionary has keys for each use case,
    and checks for a known supported model.
    """
    model_dict = model_factory.get_supported_models()

    # Ensure there are keys for each use case
    for k in UseCaseType:
        assert str(k) in model_dict.keys()

    # Check for a known model
    assert model_name in model_dict[use_case]
    model_info = model_dict[use_case][model_name]
    assert str(FrameworkType.TENSORFLOW) in model_info
    assert 'TFHub' == model_info[str(FrameworkType.TENSORFLOW)]['model_hub']


@pytest.mark.tensorflow
@pytest.mark.parametrize('framework,use_case',
                         [['tensorflow', None],
                          ['pytorch', None],
                          [None, 'image_classification'],
                          [None, 'question_answering'],
                          ['tensorflow', 'image_classification'],
                          ['tensorflow', 'text_classification'],
                          ['pytorch', 'text_classification'],
                          ['pytorch', 'question_answering']])
def test_get_supported_models_with_filter(framework, use_case):
    """
    Tests getting the dictionary of supported models while filtering by framework and/or use case.
    Checks to ensure that keys for the expected use cases are there. If filtering by framework, then the test will
    also check to make sure we only have models for the specified framework.
    """
    model_dict = model_factory.get_supported_models(framework, use_case)

    if use_case is not None:
        # Model dictionary should only have a key for the specified use case
        assert 1 == len(model_dict.keys())
        assert use_case in model_dict
    else:
        # Model dictionary should have keys for every use case
        assert len(UseCaseType) == len(model_dict.keys())
        for k in UseCaseType:
            assert str(k) in model_dict.keys()

    # If filtering by framework, we should not find models from other frameworks
    if framework is not None:
        for use_case_key in model_dict.keys():
            for model_name_key in model_dict[use_case_key].keys():
                assert 1 == len(model_dict[use_case_key][model_name_key].keys())
                assert framework in model_dict[use_case_key][model_name_key]


@pytest.mark.tensorflow
@pytest.mark.parametrize('bad_framework',
                         ['tensorflowers',
                          'python',
                          'torch',
                          'fantastic-potato'])
def test_get_supported_models_bad_framework(bad_framework):
    """
    Ensure that the proper error is raised when a bad framework is passed in
    """
    with pytest.raises(ValueError) as e:
        model_factory.get_supported_models(bad_framework)
        assert "Unsupported framework: {}".format(bad_framework) in str(e)


@pytest.mark.tensorflow
@pytest.mark.parametrize('bad_use_case',
                         ['tensorflow',
                          'imageclassification',
                          'python',
                          'fantastic-potato'])
def test_get_supported_models_bad_use_case(bad_use_case):
    """
    Ensure that the proper error is raised when a bad use case is passed in
    """
    with pytest.raises(ValueError) as e:
        model_factory.get_supported_models(use_case=bad_use_case)
        assert "Unsupported use case: {}".format(bad_use_case) in str(e)


@pytest.mark.tensorflow
@pytest.mark.parametrize('model_name,dataset_type,get_hub_model_patch,class_names',
                         [['efficientnet_b0', ImageClassificationDataset,
                           'tlt.models.image_classification.tfhub_image_classification_model.'
                           'TFHubImageClassificationModel._get_hub_model', ['a', 'b', 'c']],
                          ['small_bert/bert_en_uncased_L-2_H-128_A-2', TextClassificationDataset,
                           'tlt.models.text_classification.tfhub_text_classification_model.'
                           'TFHubTextClassificationModel._get_hub_model', ['a', 'b']]])
def test_tfhub_efficientnet_b0_train(model_name, dataset_type, get_hub_model_patch, class_names):
    """
    Tests calling train on an TFHub model with a mock dataset and mock model and verifies we get back the return
    value from the fit function.
    """
    model = model_factory.get_model(model_name, 'tensorflow')

    with patch(get_hub_model_patch) as mock_get_hub_model:
        mock_dataset = MagicMock()
        mock_dataset.__class__ = dataset_type
        print(type(mock_dataset))

        mock_dataset.class_names = class_names
        mock_model = MagicMock()
        expected_return_value = {"result": True}

        def mock_fit(dataset, epochs, shuffle, callbacks, validation_data=None):
            assert dataset is not None
            assert isinstance(epochs, int)
            assert isinstance(shuffle, bool)
            assert len(callbacks) > 0

            return expected_return_value

        mock_model.fit = mock_fit
        mock_get_hub_model.return_value = mock_model

        return_val = model.train(mock_dataset, output_dir="/tmp/output")
        assert return_val == expected_return_value


@pytest.mark.tensorflow
@pytest.mark.parametrize(
    'cpu_model,enable_auto_mixed_precision,expected_auto_mixed_precision_parameter,tf_version,model_name,dataset_type',
    [['85', None, False, '2.9.0', 'efficientnet_b0', ImageClassificationDataset],
     ['143', None, True, '2.9.0', 'efficientnet_b0', ImageClassificationDataset],
     ['123', None, False, '2.9.0', 'efficientnet_b0', ImageClassificationDataset],
     ['85', True, True, '2.9.0', 'efficientnet_b0', ImageClassificationDataset],
     ['143', True, True, '2.9.0', 'efficientnet_b0', ImageClassificationDataset],
     ['123', True, True, '2.9.0', 'efficientnet_b0', ImageClassificationDataset],
     ['85', True, True, '2.10.0', 'efficientnet_b0', ImageClassificationDataset],
     ['85', None, False, '2.9.0', 'bert_en_wwm_uncased_L-24_H-1024_A-16', TextClassificationDataset],
     ['143', None, True, '2.9.0', 'bert_en_wwm_uncased_L-24_H-1024_A-16', TextClassificationDataset],
     ['123', None, False, '2.9.0', 'bert_en_wwm_uncased_L-24_H-1024_A-16', TextClassificationDataset],
     ['85', True, True, '2.9.0', 'bert_en_wwm_uncased_L-24_H-1024_A-16', TextClassificationDataset],
     ['143', True, True, '2.9.0', 'bert_en_wwm_uncased_L-24_H-1024_A-16', TextClassificationDataset],
     ['123', True, True, '2.9.0', 'bert_en_wwm_uncased_L-24_H-1024_A-16', TextClassificationDataset],
     ['85', True, True, '2.10.0', 'efficientnet_b0', ImageClassificationDataset],
     ['143', True, True, '2.10.0', 'efficientnet_b0', ImageClassificationDataset],
     ['123', True, True, '2.10.0', 'efficientnet_b0', ImageClassificationDataset],
     ['85', False, False, '2.9.1', 'efficientnet_b0', ImageClassificationDataset],
     ['143', False, False, '2.9.1', 'efficientnet_b0', ImageClassificationDataset],
     ['123', False, False, '2.9.1', 'efficientnet_b0', ImageClassificationDataset],
     ['123', False, None, '2.8.0', 'efficientnet_b0', ImageClassificationDataset],
     ['123', None, None, '2.8.0', 'efficientnet_b0', ImageClassificationDataset],
     ['123', True, None, '2.8.0', 'efficientnet_b0', ImageClassificationDataset],
     ['85', None, None, '2.8.0', 'efficientnet_b0', ImageClassificationDataset],
     ['85', True, None, '2.8.0', 'efficientnet_b0', ImageClassificationDataset],
     ['143', None, True, '3.1.0', 'efficientnet_b0', ImageClassificationDataset]])
@patch("tlt.models.tfhub_model.tf.version")
@patch("tlt.models.tfhub_model.tf.config.optimizer.set_experimental_options")
@patch("tlt.utils.platform_util.PlatformUtil._get_cpuset")
@patch("tlt.utils.platform_util.os")
@patch("tlt.utils.platform_util.system_platform")
@patch("tlt.utils.platform_util.subprocess")
def test_tfhub_auto_mixed_precision(mock_subprocess, mock_platform, mock_os, mock_get_cpuset,
                                    mock_set_experimental_options, mock_tf_version, cpu_model,
                                    enable_auto_mixed_precision, expected_auto_mixed_precision_parameter,
                                    tf_version, model_name, dataset_type):
    """
    Verifies that auto mixed precision is enabled by default for SPR (cpu model 85), but disabled by default for other
    CPU types like SKX (cpu model 143).  The default auto mixed precision setting is used when
    enable_auto_mixed_precision=None. Auto mixed precision was enabled for TF 2.9.0 and later, so don't expect the call
    to set the config for earlier TF versions.
    
    If enable_auto_mixed_precision is set to True/False, then that's what should be used, regardless of CPU type.
    """
    mock_get_cpuset.return_value = platform_config.CPUSET
    platform_config.set_mock_system_type(mock_platform)
    platform_config.set_mock_os_access(mock_os)

    # get the lscpu sample output, but replace in the parameterized cpu model id
    lscpu_value = platform_config.LSCPU_OUTPUT
    original_model_value = "Model:                 143\n"  # model test value from the test platform config
    new_model_value = "Model:                 {}\n".format(cpu_model)
    lscpu_value = lscpu_value.replace(original_model_value, new_model_value)
    mock_subprocess.check_output.return_value = lscpu_value

    mock_dataset = MagicMock()
    mock_dataset.__class__ = dataset_type
    mock_dataset.class_names = ['a', 'b']

    mock_tf_version.VERSION = tf_version

    model = model_factory.get_model(model_name, 'tensorflow')
    model._get_hub_model = MagicMock()

    model.train(mock_dataset, output_dir="/tmp/output", enable_auto_mixed_precision=enable_auto_mixed_precision)

    if expected_auto_mixed_precision_parameter is not None:
        expected_parameter = {'auto_mixed_precision_mkl': expected_auto_mixed_precision_parameter}
        mock_set_experimental_options.assert_called_with(expected_parameter)
    else:
        # We expect that the auto mixed prercision config is not called (due to TF version unsupported)
        assert not mock_set_experimental_options.called
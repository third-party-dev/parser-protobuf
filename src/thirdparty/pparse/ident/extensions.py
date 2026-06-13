
# NOTE: Includes information from netron/source/view.js

#['.zip', '.tar', '.tar.gz', '.tgz', '.gz']

typedb = {
    'acuity': {
        'exts': ['.json'],
        'name': 'Acuity ML',
        'maintainer': 'VeriSilicon',
        'purpose': 'Optimizing neural networks for deployment on Vivante Neural Network Processor IP',
        'links': [
            'https://verisilicon.github.io/acuity-models/',
            'https://github.com/VeriSilicon/acuity-models',
        ],
        'notes': [
            'Built on Tensorflow',
            'Conversions: Caffe, Tensorflow, PyTorch, TFLite, DarkNet, ONNX',
        ],
    },
    'armnn': {
        'exts': ['.armnn', '.json'],
        'name': 'Arm NN ML',
        'maintainer': 'ARM Software',
        'purpose': 'Bridge existing neural network frameworks and Arm hardware',
        'links': [
            'https://developer.arm.com/products/processors/machine-learning/arm-nn',
            'https://github.com/ARM-software/armnn',
            'https://www.hackster.io/elham-harirpoush2/accelerated-ml-inference-on-raspberry-pi-0c0d33',
        ],
        'notes': [
            'Built on TensorflowLite, ONNX, .armnn serialization',
            'Inference for ARM Cortex-A CPUs, Arm Mali GPUs, Arm Ethos NPUs'
            'Uses ARM Compute Library (ACL)'
        ],
    },
    'barracuda': {
        'exts': ['.nn'],
        'name': 'Barracuda ML',
        'maintainer': 'Unity Technologies',
        'purpose': 'Lightweight neural network inference library for Unity',
        'links': [
            'https://docs.unity3d.com/Packages/com.unity.barracuda@1.0/manual/index.html',
            'https://github.com/Unity-Technologies/barracuda-release',
            'https://www.mdpi.com/2075-1702/13/3/239',
        ],
        'notes': [
            'Built on ONNX',
            'Supports imports from PyTorch, Tensorflow, Keras'
            'Uses custom JSON model serialization'
        ],
    },
    'bigdl': {
        'exts': ['.model', '.bigdl'],
        'name': 'BigDL ML',
        'maintainer': 'Intel Analytics / Apache Software / OSS',
        'purpose': 'BigDL is a distributed deep learning library for Apache Spark',
        'links': [
            'https://bigdl.readthedocs.io/',
            'https://github.com/intel-analytics/BigDL',
        ],
        'notes': [
            'Built on ONNX',
            'Serializes to PRotobuf, Keras, TensorflowSavedModel, Native BigDL, ONNX',
            'Supports Python and Saala'
        ],
    },
    'caffe': {
        'exts': ['.caffemodel', '.pbtxt', '.prototxt', '.pt', '.txt'],
        'name': 'Caffe ML',
        'maintainer': 'Berkeley Vision and Learning Center (BVLC)',
        'purpose': 'For vision and image processing and Convolutional NNs.',
        'links': [
            'https://caffe.berkeleyvision.org/',
            'https://github.com/BVLC/caffe',
        ],
        'notes': [
            'Serializes to Protobuf, .caffemodel for weights, .prototxt for network config',
        ],
    },
    'caffe2': {
        'exts': ['.pb', '.pbtxt', '.prototxt'],
        'name': 'Caffe2 ML',
        'maintainer': 'Maintained by Facebook AI Research (Meta AI) ... via PyTorch',
        'purpose': 'Scale machine learning models across mobile and edge devices',
        'links': [
            'https://github.com/pytorch/pytorch',
        ],
        'notes': [
            'Fully merged into PyTorch',
            'Serializes to Protobuf, ONNX, PyTorch, Pickle'
        ],
    },
    'cambricon': {
        'exts': ['.cambricon'],
        'name': 'Cambricon (model/accelerator context)',
        'maintainer': 'Cambricon Technologies (company)',
        'purpose': 'Hardware and software for AI inference on Cambricon NPUs (neural processing units).',
        'links': [
            'https://www.cambricon.com',
        ],
        'notes': [
            'Serialization format: Hardware‑specific compiled binaries or proprietary formats for its NPUs (not a common exchange format).',
        ],
    },
    'catboost': {
        'exts': ['.cbm'],
        'name': 'CatBoost ML',
        'maintainer': 'Yandex (Russian technology company)',
        'purpose': 'For prediction tasks and gradient booting',
        'links': [
            'https://catboost.ai/',
            'https://github.com/catboost/catboost',
        ],
        'notes': [
            'Native CatBoot Serialization',
            'Serializes to JSON, Protobuf, ONNX, CoreML, Tensorflow'
        ],
    },
    'circle': {
        'exts': ['.circle'],
        # [], [/^....CIR0/],
        'name': 'Circle ML',
        'maintainer': 'Circle Inc. (Private AI company)',
        'purpose': 'Onprim AI-powered data processing for business intel',
        'links': [
            'https://www.circleinc.ai/',
        ],
        'notes': [
            'Serializes to JSON, Parquet, Protobuf, potential ONNX'
        ],
    },
    'cntk': {
        'exts': ['.model', '.cntk', '.cmf', '.dnn'],
        'name': 'CNTK (Microsoft Cognitive Toolkit) ML',
        'maintainer': 'Microsoft Research',
        'purpose': 'For speech, image, and handwriting recognition, time series prediction',
        'links': [
            'https://docs.microsoft.com/en-us/cognitive-toolkit/',
            'https://github.com/microsoft/CNTK',
        ],
        'notes': [
            'Serializes to native .model, ONNX, Protobuf, TensorFlow, Keras, CoreML',
            'Maintenance mode, superceded by PyTorch and TensorFlow',
            'Supports Python, C++, BrainScript',
        ],
    },
    'coreml': {
        'exts': ['.mlmodel', '.bin', 'manifest.json', 'metadata.json', 'featuredescriptions.json', '.pb', '.pbtxt', '.mil'],
        #['.mlpackage', '.mlmodelc'],
        'name': 'Core ML',
        'maintainer': 'Apple Inc. Core ML Team',
        'purpose': 'Provide efficient ML model deployment on Apple devices across iOS, macOS, watchOS, and tvOS',
        'links': [
            'https://developer.apple.com/machine-learning/core-ml/',
        ],
        'notes': [
            'Serializes to native .mlmodel, protobuf based',
            'Conversion from ONNX, TensorFlow, Caffe, Keras',
        ],
    },
    'darknet': {
        'exts': ['.cfg', '.model', '.txt', '.weights'],
        'name': 'Darknet ML',
        'maintainer': 'Joseph Redmon',
        'purpose': 'C-based NN Framework to support real time object detection.',
        'links': [
            'https://github.com/pjreddie/darknet',
        ],
        'notes': [
            'Not actively maintained since 2020',
            'Successor: AlexeyAB/darknet',
            'Conversions include ONNX, PyTorch, TensorFlow',
            'Natively uses custom .cfg for model arch and .weights for weights',
        ],
    },
    'dl4j': {
        'exts': ['.json', '.bin'],
        'name': 'DL4J ML',
        'maintainer': 'Eclipse Foundation',
        'purpose': 'Java deep learning in JVM and enterprise/big-data environments',
        'links': [
            'https://deeplearning4j.org/',
            'https://github.com/eclipse/deeplearning4j',
        ],
        'notes': [
            'Protobuf based .zip files with binary and JSON',
        ],
    },
    'dlc': {
        'exts': ['.dlc', '.params'],
            #/^model$/]);
        'name': 'DLC (DeepLabCut)',
        'maintainer': 'DeepLabCut developer community',
        'purpose': 'A deep‑learning‑based toolbox for markerless pose estimation (tracking bodyparts / animal / human movement)',
        'links': [
            'https://deeplabcut.github.io/DeepLabCut/README.html',
            'https://github.com/DeepLabCut/DeepLabCut',
        ],
        'notes': [
            'Stores data and project meta in YAML. Uses TensorFlow/PyTorch checkpoints.',
        ],
    },
    # 'dnn': {
    #     'exts': ['.dnn'],
    #     'name': 'Unspecified',
    #     'maintainer': 'Undefined',
    #     'purpose': 'Unknown',
    #     'links': [
    #         '',
    #     ],
    #     'notes': [
    #         '',
    #     ],
    # },
    # TODO: Intel OpenVINO image DNN format?
    'dot': {
        'exts': ['.dot'],
        # [], [/^\s*(\/\*[\s\S]*?\*\/|\/\/.*|#.*)?\s*digraph\s*([A-Za-z][A-Za-z0-9-_]*|".*?")?\s*{/m]);
        'name': 'DOT (GraphViz / Neural network graph export)',
        'maintainer': 'Open source GraphViz community',
        'purpose': 'Describes graph structures (nodes & edges) in text for visualization.',
        'links': [
            'https://graphviz.org',
            'https://github.com/ellson/graphviz',
        ],
        'notes': [
            '',
        ],
    },
    
    # TODO: DMN/PMML DOT?

    # TODO: Try harder.
    'espresso': {
        'exts': ['.espresso.net', '.espresso.shape', '.espresso.weights'],
        # ['.mlmodelc']);
        'name': 'Espresso (ML/format)',
        'maintainer': 'Undefined',
        'purpose': 'Unknown',
        'links': [
            '',
        ],
        'notes': [
            '',
        ],
    },

    'executorch': {
        'exts': ['.pte'],
        # [], [/^....ET12/]
        'name': 'ExecuTorch',
        'maintainer': 'PyTorch community / Meta / Open source',
        'purpose': 'for executing optimized, ahead‑of‑time compiled PyTorch models',
        'links': [
            'https://pytorch.org/executorch/',
            'https://github.com/pytorch/executorch',
        ],
        'notes': [
            'custom AOT binary format (commonly .ptc or .pte) for compiled model code',
        ],
    },
    'flax': {
        'exts': ['.msgpack'],
        'name': 'Flax',
        'maintainer': 'Google / open‑source Flax',
        'purpose': 'built on JAX for research and production deep learning',
        'links': [
            'https://flax.readthedocs.io/',
            'https://github.com/google/flax',
        ],
        'notes': [
            'Checkpoints usually saved via JAX/Flax mechanisms (.msgpack/python dict state, often with Flax serialization utilities); not a universal single file format',
        ],
    },
    'flux': {
        'exts': ['.bson'],
        'name': 'Flux (Julia)',
        'maintainer': 'FluxML community',
        'purpose': 'for the Julia language, supports neural networks/training/inference',
        'links': [
            'https://fluxml.ai/Flux.jl/',
            'https://github.com/FluxML/Flux.jl',
        ],
        'notes': [
            'typically serialized using Julia native formats (e.g., BSON/JSON or custom state/weights);',
        ],
    },
    'gguf': {
        'exts': ['.gguf'],
        # /^[^.]+$/], [], [/^GGUF/]);
        'name': 'GGUF (GGML Unified Format)',
        'maintainer': 'GGML/GGUF ecosystem',
        'purpose': 'binary tensor model format optimized for efficient CPU‑first inference, especially used by local LLMs like llama.cpp',
        'links': [
            'https://github.com/ggerganov/ggml',
        ],
        'notes': [
            'Binary format .gguf containing model weights+metadata optimized for memory‑mapped loading and quantization',
        ],
    },
    'hailo': {
        'exts': ['.hn', '.har', '.metadata.json'],
        'name': 'Hailo',
        'maintainer': 'Hailo (company)',
        'purpose': 'Model deployment & optimization for Hailo AI accelerators on edge devices',
        'links': [
            'https://hailo.ai/',
            'https://github.com/hailo-ai/hailo_model_zoo',
        ],
        'notes': [
            'HEF (Hailo Executable Format) — compiled binary models for Hailo hardware (originating from ONNX/TF/other sources).',
        ],
    },
    'hickle': {
        'exts': ['.h5', '.hkl'],
        'name': 'Hickle',
        'maintainer': 'OSS',
        'purpose': 'HDF5‑based serialization library for Python objects (often used to store ML data/weights).',
        'links': [
            'https://github.com/telegraphic/hickle',
        ],
        'notes': [
            'HDF5 (via a pickle‑like API, compressed & portable).',
        ],
    },
    # 'imgdnn': {
    #     'exts': ['.dnn', 'params', '.json'],
    #     'name': 'Unspecified',
    #     'maintainer': 'Undefined',
    #     'purpose': 'Unknown',
    #     'links': [
    #         '',
    #     ],
    #     'notes': [
    #         '',
    #     ],
    # },
    'kann': {
        'exts': ['.kann', '.bin', '.kgraph'],
        # [], [/^....KaNN/]);
        'name': 'KANN',
        'maintainer': 'Eric Jang / OSS',
        'purpose': 'A minimalist C++ neural network library',
        'links': [
            'https://github.com/ericjang/kann',
        ],
        'notes': [
            'Custom JSON/Text for model definitions',
        ],
    },
    'keras': {
        'exts': ['.h5', '.hd5', '.hdf5', '.keras', '.json', '.cfg', '.model', '.pb', '.pth', '.weights', '.pkl', '.lite', '.tflite', '.ckpt', '.pb', 'model.weights.npz'],
        # /^.*group\d+-shard\d+of\d+(\.bin)?$/], ['.zip'], [/^\x89HDF\r\n\x1A\n/]);
        'name': 'Keras',
        'maintainer': 'Keras community (initially François Chollet)',
        'purpose': 'High‑level neural network API for building and training models.',
        'links': [
            'https://keras.io/',
            'https://github.com/keras‑team/keras',
        ],
        'notes': [
            '.keras (zip archive with JSON config + weights); legacy H5 also supported.',
        ],
    },
    'kmodel': {
        'exts': ['.kmodel'],
        'name': 'Kendryte / Kendryte K210',
        'maintainer': 'Kendryte/Sipeed ecosystem',
        'purpose': 'Neural network model format for Kendryte edge AI chips.',
        'links': [
            'https://github.com/kendryte/nncase',
        ],
        'notes': [
            '.kmodel — binary model optimized for Kendryte NN hardware',
        ],
    },
    'lasagne': {
        'exts': ['.pkl', '.pickle', '.joblib', '.model', '.pkl.z', '.joblib.z'],
        'name': 'Lasagne',
        'maintainer': 'OSS',
        'purpose': 'Lightweight neural network library built on Theano (research/prototyping).',
        'links': [
            'https://lasagne.readthedocs.io/',
            'https://github.com/Lasagne/Lasagne',
        ],
        'notes': [
            'Pickle (Python object serialization for models).',
        ],
    },
    'lightgbm': {
        'exts': ['.txt', '.pkl', '.model'],
        'name': 'LightGBM',
        'maintainer': 'Microsoft/LightGBM contributors',
        'purpose': 'Gradient boosting decision tree framework for tabular ML.',
        'links': [
            'https://lightgbm.readthedocs.io/',
            'https://github.com/microsoft/LightGBM',
        ],
        'notes': [
            'Text/JSON model dump or binary model files via LightGBM API.',
        ],
    },
    'mediapipe': {
        'exts': ['.pbtxt'],
        'name': 'MediaPipe',
        'maintainer': 'Google + open‑source',
        'purpose': 'Cross‑platform perception and multimedia ML pipelines (e.g., face/pose tracking)',
        'links': [
            'https://mediapipe.dev/',
            'https://github.com/google/mediapipe',
        ],
        'notes': [
            'Models often in TensorFlow Lite / custom graph files embedded in MediaPipe pipelines.',
        ],
    },
    'megengine': {
        'exts': ['.tm', '.mge', '.pkl'],
        'name': 'MegEngine',
        'maintainer': 'Megvii (Face++)/open‑source',
        'purpose': 'Deep learning framework for training/inference (Python/C++).',
        'links': [
            'https://www.megengine.org.cn/',
            'https://github.com/MegEngine/MegEngine',
        ],
        'notes': [
            'Framework‑specific checkpoint format (Python pickle JSON + weights) or conversion to standard formats (ONNX).',
        ],
    },
    'mlir': {
        'exts': ['.mlir', '.mlir.txt', '.mlirbc', '.txt'],
        'name': 'MLIR',
        'maintainer': 'LLVM community / Google contributors',
        'purpose': 'Intermediate representation for compiling and optimizing ML models.',
        'links': [
            'https://mlir.llvm.org',
            'https://github.com/llvm/llvm-project',
        ],
        'notes': [
            'Text/binary IR files (.mlir), compiler IR.',
        ],
    },
    'mlnet': {
        'exts': ['.zip', '.mlnet'],
        'name': 'ML.NET',
        'maintainer': 'Microsoft / .NET community.',
        'purpose': '.NET framework for ML training and inference.',
        'links': [
            'https://dotnet.microsoft.com/en-us/apps/machinelearning-ai/ml-dotnet',
            'https://github.com/dotnet/machinelearning',
        ],
        'notes': [
            'Binary .zip models (contains protobuf + metadata).',
        ],
    },
    'mnn': {
        'exts': ['.mnn'],
        'name': 'MNN',
        'maintainer': 'Alibaba',
        'purpose': 'Mobile neural network inference framework.',
        'links': [
            'https://www.mnn.zone',
            'https://github.com/alibaba/MNN',
        ],
        'notes': [
            'Binary .mnn files.',
        ],
    },
    'mslite': {
        'exts': ['.ms', '.bin'],
        # [], [/^....MSL0/, /^....MSL1/, /^....MSL2/]);
        'name': 'MSLite',
        'maintainer': 'MindSpore / Huawei.',
        'purpose': 'Lightweight MindSpore inference engine for edge devices.',
        'links': [
            'https://www.mindspore.cn/',
            'https://gitee.com/mindspore/mindspore',
        ],
        'notes': [
            'MindSpore Lite model files (.ms / .mindir).',
        ],
    },
    'mxnet': {
        'exts': ['.json', '.params'],
        #['.mar']
        'name': 'MXNet',
        'maintainer': 'Apache Software Foundation.',
        'purpose': 'Deep learning framework for training/inference.',
        'links': [
            'https://mxnet.apache.org',
            'https://github.com/apache/mxnet',
        ],
        'notes': [
            '.params + JSON symbol files.',
        ],
    },
    'ncnn': {
        'exts': ['.param', '.bin', '.cfg.ncnn', '.weights.ncnn', '.ncnnmodel'],
        'name': 'NCNN',
        'maintainer': 'Tencent',
        'purpose': 'Mobile inference framework for CNNs.',
        'links': [
            'https://ncnn.tencent.com/',
            'https://github.com/Tencent/ncnn',
        ],
        'notes': [
            '.param + .bin binary files.',
        ],
    },
    'nnabla': {
        'exts': ['.nntxt'],
        # ['.nnp'],
        'name': 'NNabla',
        'maintainer': 'Sony / open-source community.',
        'purpose': 'Deep learning framework (Sony).',
        'links': [
            'https://nnabla.org/',
            'https://github.com/sony/nnabla',
        ],
        'notes': [
            '.nnp (Neural Network Pack) files.',
        ],
    },
    'nnc': {
        'exts': ['.nnc'],
        'name': 'NNC (Neural Network Coding / NNC Standard)',
        'maintainer': 'ISO/IEC (MPEG) as part of the MPEG‑7 suite, with reference implementations by Fraunhofer HHI',
        'purpose': 'Standard for compressing and representing neural networks efficiently (Neural Network Coding). ',
        'links': [
            'https://github.com/fraunhoferhhi/nncodec',
        ],
        'notes': [
            'ISO/IEC 15938‑17 (MPEG‑7 Part 17) defines Neural Network Coding (NNC).',
        ],
    },
    'nnef': {
        'exts': ['.nnef', '.dat'],
        'name': 'NNEF',
        'maintainer': 'Khronos Group.',
        'purpose': 'Standard for exchanging neural network models across frameworks.',
        'links': [
            'https://www.khronos.org/nnef',
            'https://github.com/KhronosGroup/NNEF-Tools',
        ],
        'notes': [
            'Text-based .nnef + binary weight files.',
        ],
    },
    'numpy': {
        'exts': ['.npz', '.npy', '.pkl', '.pickle', '.model', '.model2', '.mge', '.joblib'],
        'name': 'NumPy',
        'maintainer': 'NumPy community.',
        'purpose': 'General numeric computing; often used to store model weights.',
        'links': [
            'https://numpy.org',
            'https://github.com/numpy/numpy',
        ],
        'notes': [
            'Serialization format: .npy / .npz.',
        ],
    },
    'om': {
        'exts': ['.om', '.onnx', '.pb', '.engine', '.bin'],
        # [], [/^IMOD/, /^PICO/]);
        'name': 'OM (Huawei MindSpore)',
        'maintainer': 'MindSpore / Huawei.',
        'purpose': 'Compiled model for MindSpore inference engine.',
        'links': [
            'https://www.mindspore.cn/',
            'https://gitee.com/mindspore/mindspore',
        ],
        'notes': [
            'Serialization format: .om binary model files.',
        ],
    },
    'onednn': {
        'exts': ['.json'],
        'name': 'oneDNN',
        'maintainer': 'Intel',
        'purpose': 'CPU-optimized deep learning primitives library.',
        'links': [
            'https://oneapi-src.github.io/oneDNN/',
            'https://github.com/oneapi-src/oneDNN',
        ],
        'notes': [
            'Low-level operator library; no standard model format.',
        ],
    },
    'onnx': {
        'exts': ['.onnx', '.onnx.data', '.onnx.meta', '.onn', '.pb', '.onnxtxt', '.pbtxt', '.prototxt', '.txt', '.model', '.pt', '.pth', '.pkl', '.ort', '.ort.onnx', '.ngf', '.json', '.bin', 'onnxmodel'],
        #'containers': [],
        #'contents': [/^\x08[\x00-\x10]\x12[\x00-\x20]\w\w/, /^\x08[\x00-\x10]\x12\x00\x1A/, /^\x08[\x00-\x10]\x3A/, /^\s*ir_version:\s\d+/, /^....ORTM/]);
        'name': 'ONNX',
        'maintainer': 'Linux Foundation / ONNX community.',
        'purpose': 'Open standard for exchanging ML models across frameworks.',
        'links': [
            'https://onnx.ai',
            'https://github.com/onnx/onnx',
        ],
        'notes': [
            'Serialization format: Protobuf .onnx.',
        ],
    },
    'openvino': {
        'exts': ['.xml', '.bin'],
        'name': 'OpenVINO',
        'maintainer': 'Intel',
        'purpose': 'Intel’s toolkit for optimizing ML models for CPU/GPU/VPU.',
        'links': [
            'https://docs.openvino.ai/',
            'https://github.com/openvinotoolkit/openvino',
        ],
        'notes': [
            'Serialization format: IR files (.xml + .bin).',
        ],
    },
    'paddle': {
        'exts': ['.pdmodel', '.pdiparams', '.pdparams', '.pdopt', '.paddle', '__model__', '.__model__', '.pbtxt', '.txt', '.tar', '.tar.gz', '.nb', '.json'],
        'name': 'PaddlePaddle',
        'maintainer': 'Baidu / Paddle community.',
        'purpose': 'Deep learning framework (China / Baidu).',
        'links': [
            'https://www.paddlepaddle.org.cn/',
            'https://github.com/PaddlePaddle/Paddle',
        ],
        'notes': [
            'Serialization format: .pdmodel + .pdiparams.',
        ],
    },
    'pickle': {
        'exts': ['.pkl', '.pickle', '.joblib', '.model', '.meta', '.pb', '.pt', '.h5', '.pkl.z', '.joblib.z', '.pdstates', '.mge', '.bin', '.npy', '.pth'],
        'name': 'Pickle',
        'maintainer': 'Python Software Foundation.',
        'purpose': 'Python object serialization; often used for saving ML objects.',
        'links': [
            'https://docs.python.org/3/library/pickle.html',
        ],
        'notes': [
            'Serialization format: Binary .pkl files.',
        ],
    },
    'pytorch': {
        'exts': ['.pt', '.pth', '.ptl', '.pt1', '.pt2', '.pyt', '.pyth', '.pkl', '.pickle', '.h5', '.t7', '.model', '.dms', '.tar', '.ckpt', '.chkpt', '.tckpt', '.bin', '.pb', '.zip', '.nn', '.torchmodel', '.torchscript', '.pytorch', '.ot', '.params', '.trt', '.ff', '.ptmf', '.jit', '.bin.index.json', 'model.json', '.ir', 'serialized_exported_program.json', 'serialized_state_dict.json', 'archive_format'],
        #'containers': ['.model', '.pt2'],
        #'contents': [/^\x80.\x8a\x0a\x6c\xfc\x9c\x46\xf9\x20\x6a\xa8\x50\x19/]
        'name': 'PyTorch',
        'maintainer': 'Meta / PyTorch community.',
        'purpose': 'Deep learning framework for training and inference.',
        'links': [
            'https://pytorch.org',
            'https://github.com/pytorch/pytorch',
        ],
        'notes': [
            'Serialization format: .pt / .pth (TorchScript / state_dict).',
        ],
    },
    'qnn': {
        'exts': ['.json', '.bin', '.serialized', '.dlc'],
        'name': 'QNN',
        'maintainer': 'ARM',
        'purpose': 'Quantized neural network library for ARM devices.',
        'links': [
            'https://developer.arm.com/technologies/machine-learning',
            'https://github.com/ARM-software/ComputeLibrary',
        ],
        'notes': [
            'Binary / framework-dependent (compiled models).',
        ],
    },
    'rknn': {
        'exts': ['.rknn', '.nb', '.onnx', '.json', '.bin'],
        # /^model$/], [], [/^RKNN/, /^VPMN/], /^....RKNN/);
        'name': 'RKNN',
        'maintainer': 'Rockchip',
        'purpose': 'Neural network inference on Rockchip NPU.',
        'links': [
            'https://www.rknn.ai/',
            'https://github.com/rockchip-linux/rknn-toolkit',
        ],
        'notes': [
            'Serialization format: .rknn binary files.',
        ],
    },
    'safetensors': {
        'exts': ['.safetensors', '.safetensors.index.json'],
        'name': 'SafeTensors',
        'maintainer': 'Hugging Face.',
        'purpose': 'Fast and secure tensor serialization for ML models.',
        'links': [
            'https://github.com/huggingface/safetensors',
            'https://github.com/huggingface/safetensors',
        ],
        'notes': [
            'Serialization format: .safetensors binary format.',
        ],
    },
    'sentencepiece': {
        'exts': ['.model'],
        'name': 'SentencePiece',
        'maintainer': 'Google.',
        'purpose': 'Tokenization library for text preprocessing in NLP.',
        'links': [
            'https://github.com/google/sentencepiece',
            'https://github.com/google/sentencepiece',
        ],
        'notes': [
            'Serialization format: .model / .vocab binary files.',
        ],
    },
    'sklearn': {
        'exts': ['.pkl', '.pickle', '.joblib', '.model', '.meta', '.pb', '.pt', '.h5', '.pkl.z', '.joblib.z', '.pickle.dat', '.bin'],
        'name': 'scikit-learn (sklearn)',
        'maintainer': 'scikit-learn community.',
        'purpose': 'Classical ML algorithms in Python.',
        'links': [
            'https://scikit-learn.org/',
            'https://github.com/scikit-learn/scikit-learn',
        ],
        'notes': [
            'Serialization format: Pickle (.pkl) or joblib (.joblib).',
        ],
    },
    'tengine': {
        'exts': ['.tmfile'],
        'name': 'Tengine',
        'maintainer': 'Open AI Lab (OAID).',
        'purpose': 'Mobile/embedded deep learning inference engine.3',
        'links': [
            'https://tengine.org/',
            'https://github.com/OAID/Tengine',
        ],
        'notes': [
            'Serialization format: .tmfile / framework-specific IR.',
        ],
    },
    'tensorrt': {
        'exts': ['.trt', '.trtmodel', '.engine', '.model', '.txt', '.uff', '.pb', '.tmfile', '.onnx', '.pth', '.dnn', '.plan', '.pt', '.dat', '.bin'],
        #[], [/^ptrt/, /^ftrt/]);
        'name': 'TensorRT',
        'maintainer': 'NVIDIA',
        'purpose': 'Optimized runtime for NVIDIA GPUs (inference acceleration).',
        'links': [
            'https://developer.nvidia.com/tensorrt',
            'https://github.com/NVIDIA/TensorRT',
        ],
        'notes': [
            'Serialization format: .plan binary engine files.',
        ],
    },
    'tf': {
        'exts': ['.pb', '.meta', '.pbtxt', '.prototxt', '.txt', '.pt', '.json', '.index', '.ckpt', '.graphdef', '.pbmm'],
        # /.data-[0-9][0-9][0-9][0-9][0-9]-of-[0-9][0-9][0-9][0-9][0-9]$/, /^events.out.tfevents./, /^.*group\d+-shard\d+of\d+(\.bin)?$/], ['.zip']);
        'name': 'TensorFlow (TF)',
        'maintainer': 'Google',
        'purpose': 'End-to-end ML framework for training/inference.',
        'links': [
            'https://www.tensorflow.org/',
            'https://github.com/tensorflow/tensorflow',
        ],
        'notes': [
            'Serialization format: SavedModel (directory with .pb + variables)',
        ],
    },
    'tflite': {
        'exts': ['.tflite', '.lite', '.tfl', '.bin', '.pb', '.tmfile', '.h5', '.model', '.json', '.txt', '.dat', '.nb', '.ckpt', '.onnx'],
        #[], [/^....TFL3/]);
        'name': 'TensorFlow Lite (TFLite)',
        'maintainer': 'Google / TensorFlow team.',
        'purpose': 'Lightweight inference engine for mobile/embedded devices.',
        'links': [
            'https://www.tensorflow.org/lite',
            'https://github.com/tensorflow/tensorflow/tree/master/tensorflow/lite',
        ],
        'notes': [
            'Serialization format: .tflite flatbuffer files.',
        ],
    },
    'tnn': {
        'exts': ['.tnnproto', '.tnnmodel'],
        'name': 'TNN',
        'maintainer': 'Tencent',
        'purpose': 'ightweight, cross-platform deep learning inference engine.',
        'links': [
            'https://tkestack.com/tnn',
            'https://github.com/Tencent/TNN',
        ],
        'notes': [
            'Serialization format: .tnnproto + .tnnmodel.',
        ],
    },
    # TODO: Torch separate from PyTorch?!
    'torch': {
        'exts': ['.t7', '.net'],
        'name': 'Torch',
        'maintainer': 'Meta / PyTorch community.',
        'purpose': 'Deep learning framework for training and inference.',
        'links': [
            'https://pytorch.org',
            'https://github.com/pytorch/pytorch',
        ],
        'notes': [
            'Serialization format: .pt / .pth (TorchScript or state_dict).',
        ],
    },
    'transformers': {
        'exts': ['.json'],
        'name': 'Transformers (Hugging Face)',
        'maintainer': 'Hugging Face.',
        'purpose': 'Pretrained NLP models and architectures.',
        'links': [
            'https://huggingface.co/transformers',
            'https://github.com/huggingface/transformers',
        ],
        'notes': [
            'Serialization format: PyTorch (.bin), TensorFlow (.ckpt), or SafeTensors (.safetensors).',
        ],
    },
    'tvm': {
        'exts': ['.json', '.params'],
        'name': 'TVM',
        'maintainer': 'Apache Software Foundation / community.',
        'purpose': 'ML compiler stack for optimizing models on multiple hardware backends.',
        'links': [
            'https://tvm.apache.org/',
            'https://github.com/apache/tvm',
        ],
        'notes': [
            'Serialization format: .so / compiled runtime modules + relay IR.',
        ],
    },
    'uff': {
        'exts': ['.uff', '.pb', '.pbtxt', '.uff.txt', '.trt', '.engine'],
        'name': 'UFF (Universal Framework Format)',
        'maintainer': 'NVIDIA',
        'purpose': 'Intermediate representation for TensorRT conversion from other frameworks.',
        'links': [
            'https://docs.nvidia.com/deeplearning/tensorrt/archives/index.html',
            'https://github.com/NVIDIA/TensorRT',
        ],
        'notes': [
            'Serialization format: .uff binary format.',
        ],
    },
    'vnnmodel': {
        'exts': ['.vnnmodel'],
        'name': 'VNN (Verifiable Neural Networks) Challenge/Standard',
        'maintainer': 'Academic/open‑source community driving the VNN Challenge.',
        'purpose': 'Standardized models/benchmarks for verifiable neural network research (robustness verification).',
        'links': [
            'https://vnnlib.cs.uiuc.edu/',
            'https://github.com/sisl/VNN‑Benchmark‑Suite',
        ],
        'notes': [
            'Models typically in ONNX or framework formats with VNNLib property files describing verification tasks.',
        ],
    },
    'weka': {
        'exts': ['.model'],
        'name': 'Weka',
        'maintainer': 'University of Waikato / Weka community.',
        'purpose': 'Java-based ML suite for classical algorithms and experimentation.',
        'links': [
            'https://www.cs.waikato.ac.nz/ml/weka/',
            'https://github.com/Waikato/weka-3-8',
        ],
        'notes': [
            'Serialization format: Java serialized .model / .arff files.',
        ],
    },
    'xgboost': {
        'exts': ['.xgb', '.xgboost', '.json', '.model', '.bin', '.txt'],
        # [], [/^{L\x00\x00/, /^binf/, /^bs64/, /^\s*booster\[0\]:/]
        'name': 'XGBoost',
        'maintainer': 'DMLC / XGBoost contributors.',
        'purpose': 'Gradient boosting decision tree framework.',
        'links': [
            'https://xgboost.ai/',
            'https://github.com/dmlc/xgboost',
        ],
        'notes': [
            'Serialization format: Binary model files (.json, .bin).',
        ],
    },
    'xmodel': {
        'exts': ['.xmodel'],
        'name': 'XModel',
        'maintainer': 'Xilinx / Vitis-AI community.',
        'purpose': 'Neural network model format for Xilinx FPGA/AI acceleration.',
        'links': [
            'https://www.xilinx.com/products/design-tools/vitis/ai.html',
            'https://github.com/Xilinx/Vitis-AI',
        ],
        'notes': [
            'Serialization format: .xmodel binary files.',
        ],
    },
    
}


ext_to_type = {}
for typ in typedb:
    for ext in typedb[typ]['exts']:
        if ext not in ext_to_type:
            ext_to_type[ext] = []
        if typ not in ext_to_type[ext]:
            ext_to_type[ext].append(typ)


def ident_by_extension(fname):
    candidates_by_ext = []
    for ext in ext_to_type:
        if fname.endswith(ext):
            candidates_by_ext.extend(ext_to_type[ext])
    return candidates_by_ext
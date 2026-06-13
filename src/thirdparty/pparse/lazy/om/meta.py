from __future__ import annotations


class Partition:
    MODELDEF: int = 0  # ModelDef - model graph definition, operators, attributes (protobuf / ge::proto::ModelDef)
    WEIGHTDEF: int = 1  # WeightDefRaw - weight/tensor data
    TASKDEF: int = 2  # TaskDefTask - schedule information (operator execution tasks, kernel descriptors)
    FLOWDEF: int = 3  # FlowDef - subgraph/flow


# class PartitionType(IntEnum):
#     MODEL_DEF       = 0   # Graph IR (protobuf)
#     WEIGHTS         = 1   # Weight tensors
#     TBE_KERNELS     = 2   # Compiled TBE kernel binary
#     TASK_INFO       = 3   # Task / schedule metadata
#     PARTITION_TABLE = 8   # Self-referencing partition index
#     UNKNOWN         = -1
